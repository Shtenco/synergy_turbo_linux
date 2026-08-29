#define _GNU_SOURCE
#include "metaram.h"

#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <linux/userfaultfd.h>
#include <poll.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>

typedef struct {
    int uffd;
    uint8_t *region;
    size_t pages;
    mr_page_blob *blobs;
    uint8_t *raw_pages;
    int use_metaram;
    uint64_t handled;
    uint64_t service_ns;
    uint64_t decode_ns;
    int error;
} pager_ctx;

static uint64_t now_ns(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC_RAW, &t);
    return (uint64_t)t.tv_sec * 1000000000ull + (uint64_t)t.tv_nsec;
}

static void *pager_main(void *arg) {
    pager_ctx *ctx = (pager_ctx *)arg;
    struct pollfd pfd = {.fd = ctx->uffd, .events = POLLIN};
    uint8_t page[MR_PAGE_SIZE];

    while (ctx->handled < ctx->pages) {
        int pr = poll(&pfd, 1, 5000);
        if (pr <= 0) {
            ctx->error = (pr == 0) ? ETIMEDOUT : errno;
            return NULL;
        }

        struct uffd_msg msg;
        ssize_t n = read(ctx->uffd, &msg, sizeof(msg));
        if (n != (ssize_t)sizeof(msg)) {
            ctx->error = errno ? errno : EIO;
            return NULL;
        }
        if (msg.event != UFFD_EVENT_PAGEFAULT) {
            continue;
        }

        uint64_t t0 = now_ns();
        uintptr_t fault = (uintptr_t)msg.arg.pagefault.address & ~(uintptr_t)(MR_PAGE_SIZE - 1u);
        if (fault < (uintptr_t)ctx->region ||
            fault >= (uintptr_t)ctx->region + ctx->pages * MR_PAGE_SIZE) {
            ctx->error = EFAULT;
            return NULL;
        }
        size_t idx = (fault - (uintptr_t)ctx->region) / MR_PAGE_SIZE;

        const void *src;
        if (ctx->use_metaram) {
            uint64_t d0 = now_ns();
            if (mr_decompress_page(&ctx->blobs[idx], NULL, page) != 0) {
                ctx->error = EIO;
                return NULL;
            }
            ctx->decode_ns += now_ns() - d0;
            src = page;
        } else {
            src = ctx->raw_pages + idx * MR_PAGE_SIZE;
        }

        struct uffdio_copy cp;
        memset(&cp, 0, sizeof(cp));
        cp.src = (unsigned long)src;
        cp.dst = (unsigned long)fault;
        cp.len = MR_PAGE_SIZE;
        if (ioctl(ctx->uffd, UFFDIO_COPY, &cp) == -1) {
            ctx->error = errno;
            return NULL;
        }
        ctx->service_ns += now_ns() - t0;
        ctx->handled++;
    }
    return NULL;
}

static int create_uffd(void) {
    int fd = (int)syscall(SYS_userfaultfd, O_CLOEXEC | O_NONBLOCK);
    if (fd < 0) return -1;

    struct uffdio_api ua;
    memset(&ua, 0, sizeof(ua));
    ua.api = UFFD_API;
    if (ioctl(fd, UFFDIO_API, &ua) == -1) {
        close(fd);
        return -1;
    }
    return fd;
}

static int run_mode(const char *mode, const uint8_t *src, size_t pages, int use_metaram) {
    mr_page_blob *blobs = NULL;
    uint64_t stored = 0;
    if (use_metaram) {
        blobs = calloc(pages, sizeof(*blobs));
        if (!blobs) return 2;
        for (size_t i = 0; i < pages; ++i) {
            if (mr_compress_page(src + i * MR_PAGE_SIZE, NULL, i, 1,
                                 1800000000000000000ull + i, 0, &blobs[i]) != 0) {
                free(blobs); return 2;
            }
            stored += blobs[i].meta.stored_bytes + sizeof(mr_page_meta);
        }
    }

    uint8_t *region = mmap(NULL, pages * MR_PAGE_SIZE, PROT_READ | PROT_WRITE,
                           MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (region == MAP_FAILED) {
        free(blobs); return 2;
    }

    int uffd = create_uffd();
    if (uffd < 0) {
        fprintf(stderr, "USERFAULTFD_UNAVAILABLE errno=%d (%s)\n", errno, strerror(errno));
        munmap(region, pages * MR_PAGE_SIZE);
        free(blobs);
        return 77;
    }

    struct uffdio_register ur;
    memset(&ur, 0, sizeof(ur));
    ur.range.start = (unsigned long)region;
    ur.range.len = pages * MR_PAGE_SIZE;
    ur.mode = UFFDIO_REGISTER_MODE_MISSING;
    if (ioctl(uffd, UFFDIO_REGISTER, &ur) == -1) {
        fprintf(stderr, "UFFDIO_REGISTER failed errno=%d (%s)\n", errno, strerror(errno));
        close(uffd); munmap(region, pages * MR_PAGE_SIZE); free(blobs);
        return 77;
    }

    pager_ctx ctx = {
        .uffd = uffd, .region = region, .pages = pages,
        .blobs = blobs, .raw_pages = (uint8_t *)src, .use_metaram = use_metaram
    };
    pthread_t th;
    if (pthread_create(&th, NULL, pager_main, &ctx) != 0) return 2;

    volatile uint64_t checksum = 0;
    uint64_t t0 = now_ns();
    for (size_t i = 0; i < pages; ++i) {
        checksum += region[i * MR_PAGE_SIZE];
        checksum += region[i * MR_PAGE_SIZE + MR_PAGE_SIZE - 1];
    }
    uint64_t elapsed = now_ns() - t0;
    pthread_join(th, NULL);

    int exact = (ctx.error == 0) &&
                memcmp(region, src, pages * MR_PAGE_SIZE) == 0;

    double avg_fault_us = (double)elapsed / (double)pages / 1000.0;
    double avg_service_us = (double)ctx.service_ns / (double)pages / 1000.0;
    double avg_decode_us = use_metaram ? (double)ctx.decode_ns / (double)pages / 1000.0 : 0.0;
    double mib = (double)(pages * MR_PAGE_SIZE) / (1024.0 * 1024.0);
    double throughput = mib / ((double)elapsed / 1e9);

    printf("{\"mode\":\"%s\",\"pages\":%zu,\"logical_bytes\":%zu,"
           "\"stored_bytes\":%" PRIu64 ",\"faults\":%" PRIu64 ","
           "\"avg_fault_us\":%.6f,\"avg_service_us\":%.6f,\"avg_decode_us\":%.6f,"
           "\"fault_path_mib_s\":%.3f,\"exact\":%s,\"checksum\":%" PRIu64 "}\n",
           mode, pages, pages * MR_PAGE_SIZE, stored, ctx.handled,
           avg_fault_us, avg_service_us, avg_decode_us, throughput,
           exact ? "true" : "false", (uint64_t)checksum);

    struct uffdio_range rr = {.start = (unsigned long)region, .len = pages * MR_PAGE_SIZE};
    ioctl(uffd, UFFDIO_UNREGISTER, &rr);
    close(uffd);
    munmap(region, pages * MR_PAGE_SIZE);
    free(blobs);
    return exact ? 0 : 3;
}

int main(int argc, char **argv) {
    if (argc != 3) {
        fprintf(stderr, "usage: %s raw|metaram input.bin\n", argv[0]);
        return 2;
    }
    int use_metaram;
    if (strcmp(argv[1], "raw") == 0) use_metaram = 0;
    else if (strcmp(argv[1], "metaram") == 0) use_metaram = 1;
    else return 2;

    FILE *f = fopen(argv[2], "rb");
    if (!f) { perror("fopen"); return 2; }
    fseek(f, 0, SEEK_END);
    long sz = ftell(f); rewind(f);
    if (sz <= 0) return 2;
    size_t pages = ((size_t)sz + MR_PAGE_SIZE - 1u) / MR_PAGE_SIZE;
    uint8_t *src = calloc(pages, MR_PAGE_SIZE);
    if (!src) return 2;
    fread(src, 1, (size_t)sz, f); fclose(f);

    int rc = run_mode(argv[1], src, pages, use_metaram);
    free(src);
    return rc;
}
