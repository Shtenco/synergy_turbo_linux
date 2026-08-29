#define _GNU_SOURCE
#include "metaram.h"
#include "turbo/core.h"

#include <inttypes.h>
#include <pthread.h>
#include <sched.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

enum {
    MSG_PAGE_FAULT = 0x4d525046u,
    MSG_PAGE_READY = 0x4d525052u,
    MSG_STOP       = 0x4d525053u
};

typedef struct {
    turbo_ipc_ring req;
    turbo_ipc_ring rep;
    mr_page_blob *blobs;
    uint8_t *frames;
    size_t pages;
    _Atomic uint64_t service_ns;
    _Atomic uint64_t decode_ns;
    _Atomic uint64_t faults;
    _Atomic int error;
} pager_service;

static uint64_t ns(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC_RAW, &t);
    return (uint64_t)t.tv_sec * 1000000000ull + (uint64_t)t.tv_nsec;
}

static void pin_thread(unsigned cpu) {
#ifdef __linux__
    cpu_set_t set;
    CPU_ZERO(&set);
    CPU_SET(cpu % (unsigned)CPU_SETSIZE, &set);
    (void)pthread_setaffinity_np(pthread_self(), sizeof(set), &set);
#else
    (void)cpu;
#endif
}

static void *pager_main(void *arg) {
    pager_service *s = (pager_service *)arg;
    pin_thread(1);
    turbo_ipc_message m;
    for (;;) {
        if (!turbo_ipc_pop(&s->req, &m)) { turbo_x64_relax(); continue; }
        if (m.tag == MSG_STOP) break;
        if (m.tag != MSG_PAGE_FAULT) { atomic_store(&s->error, 1); break; }
        size_t idx = (size_t)m.words[0];
        uint64_t seq = m.words[1];
        if (idx >= s->pages) { atomic_store(&s->error, 2); break; }
        uint64_t t0 = ns();
        uint64_t d0 = ns();
        uint8_t *frame = s->frames + idx * MR_PAGE_SIZE;
        if (mr_decompress_page(&s->blobs[idx], NULL, frame) != 0) { atomic_store(&s->error, 3); break; }
        uint64_t d1 = ns();
        turbo_ipc_message rep = {.tag = MSG_PAGE_READY,.words = {idx,seq,(uint64_t)(uintptr_t)frame,s->blobs[idx].meta.checksum32,s->blobs[idx].meta.generation,s->blobs[idx].meta.access_ns}};
        while (!turbo_ipc_push(&s->rep, &rep)) turbo_x64_relax();
        atomic_fetch_add(&s->decode_ns, d1 - d0);
        atomic_fetch_add(&s->service_ns, ns() - t0);
        atomic_fetch_add(&s->faults, 1);
    }
    return NULL;
}

static int load_input(const char *path, uint8_t **out, size_t *pages_out) {
    FILE *f = fopen(path, "rb"); if (!f) return -1;
    fseek(f, 0, SEEK_END); long sz = ftell(f); rewind(f);
    if (sz <= 0) { fclose(f); return -1; }
    size_t pages = ((size_t)sz + MR_PAGE_SIZE - 1u) / MR_PAGE_SIZE;
    uint8_t *p = calloc(pages, MR_PAGE_SIZE); if (!p) { fclose(f); return -1; }
    fread(p, 1, (size_t)sz, f); fclose(f); *out = p; *pages_out = pages; return 0;
}

int main(int argc, char **argv) {
    if (argc != 2) { fprintf(stderr, "usage: %s input.bin\n", argv[0]); return 2; }
    uint8_t *src = NULL; size_t pages = 0;
    if (load_input(argv[1], &src, &pages) != 0) return 2;
    pager_service *s = aligned_alloc(TURBO_CACHELINE, sizeof(*s)); if (!s) return 2;
    memset(s, 0, sizeof(*s)); turbo_ipc_init(&s->req); turbo_ipc_init(&s->rep); s->pages = pages;
    s->blobs = calloc(pages, sizeof(*s->blobs)); s->frames = aligned_alloc(MR_PAGE_SIZE, pages * MR_PAGE_SIZE);
    if (!s->blobs || !s->frames) return 2; memset(s->frames, 0, pages * MR_PAGE_SIZE);
    uint64_t physical = 0;
    for (size_t i = 0; i < pages; ++i) {
        if (mr_compress_page(src + i * MR_PAGE_SIZE, NULL, i, 1,1800000000000000000ull + i, 0, &s->blobs[i]) != 0) return 3;
        physical += s->blobs[i].meta.stored_bytes + sizeof(mr_page_meta);
    }
    pthread_t pager; if (pthread_create(&pager, NULL, pager_main, s) != 0) return 3; pin_thread(0);
    uint64_t total_rt = 0, min_rt = UINT64_MAX, max_rt = 0, checksum = 0;
    for (size_t i = 0; i < pages; ++i) {
        turbo_ipc_message req = {.tag = MSG_PAGE_FAULT,.words = {i, i + 1u, 0, 0, 0, 0}};
        uint64_t t0 = ns(); while (!turbo_ipc_push(&s->req, &req)) turbo_x64_relax();
        turbo_ipc_message rep;
        do { if (atomic_load(&s->error)) return 4; if (!turbo_ipc_pop(&s->rep, &rep)) { turbo_x64_relax(); continue; } } while (rep.tag != MSG_PAGE_READY || rep.words[1] != i + 1u);
        uint64_t dt = ns() - t0; total_rt += dt; if (dt < min_rt) min_rt = dt; if (dt > max_rt) max_rt = dt;
        uint8_t *frame = (uint8_t *)(uintptr_t)rep.words[2];
        if (frame != s->frames + i * MR_PAGE_SIZE) return 5;
        if (memcmp(frame, src + i * MR_PAGE_SIZE, MR_PAGE_SIZE) != 0) return 6;
        checksum += frame[0] + frame[MR_PAGE_SIZE - 1u];
    }
    turbo_ipc_message stop = {.tag = MSG_STOP}; while (!turbo_ipc_push(&s->req, &stop)) turbo_x64_relax(); pthread_join(pager, NULL);
    uint64_t faults = atomic_load(&s->faults), service = atomic_load(&s->service_ns), decode = atomic_load(&s->decode_ns);
    double logical_mib = (double)(pages * MR_PAGE_SIZE) / (1024.0 * 1024.0), rt_s = (double)total_rt / 1e9;
    printf("{\"path\":\"turbo_ipc_ring -> MetaRAM pager -> frame reply\",\"pages\":%zu,\"logical_bytes\":%zu,\"physical_bytes\":%" PRIu64 ",\"effective_ratio\":%.6f,\"faults\":%" PRIu64 ",\"avg_roundtrip_us\":%.6f,\"min_roundtrip_us\":%.6f,\"max_roundtrip_us\":%.6f,\"avg_service_us\":%.6f,\"avg_decode_us\":%.6f,\"end_to_end_mib_s\":%.3f,\"exact\":true,\"checksum\":%" PRIu64 "}\n",pages,pages * MR_PAGE_SIZE,physical,(double)(pages * MR_PAGE_SIZE) / (double)physical,faults,(double)total_rt / (double)pages / 1000.0,(double)min_rt / 1000.0,(double)max_rt / 1000.0,(double)service / (double)pages / 1000.0,(double)decode / (double)pages / 1000.0,logical_mib / rt_s,checksum);
    free(s->blobs); free(s->frames); free(s); free(src); return 0;
}
