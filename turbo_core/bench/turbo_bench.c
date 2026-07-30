#define _GNU_SOURCE
#include "turbo/core.h"

#include <errno.h>
#include <inttypes.h>
#include <math.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define SAMPLE_COUNT 7u
#define CAP_SET_SIZE 256u

static volatile uint64_t benchmark_sink;

typedef uint64_t (*bench_fn)(uint64_t iterations);

typedef struct {
    const char *name;
    double cycles_per_op;
    double ns_per_op;
    uint64_t iterations;
} bench_result;

static uint64_t monotonic_ns(void)
{
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC_RAW, &ts) != 0) {
        perror("clock_gettime");
        exit(EXIT_FAILURE);
    }
    return (uint64_t)ts.tv_sec * UINT64_C(1000000000) + (uint64_t)ts.tv_nsec;
}

static void pin_to_cpu_zero(void)
{
#if defined(__linux__)
    cpu_set_t set;
    CPU_ZERO(&set);
    CPU_SET(0, &set);
    if (sched_setaffinity(0, sizeof(set), &set) != 0 && errno != EINVAL) {
        fprintf(stderr, "warning: sched_setaffinity failed: %s\n", strerror(errno));
    }
#endif
}

static double calibrate_cycles_per_ns(void)
{
    struct timespec request = {.tv_sec = 0, .tv_nsec = 100000000};
    const uint64_t ns0 = monotonic_ns();
    const uint64_t t0 = turbo_x64_tsc_begin();
    while (nanosleep(&request, &request) != 0 && errno == EINTR) {
    }
    const uint64_t t1 = turbo_x64_tsc_end();
    const uint64_t ns1 = monotonic_ns();
    return (double)(t1 - t0) / (double)(ns1 - ns0);
}

static int compare_double(const void *lhs, const void *rhs)
{
    const double a = *(const double *)lhs;
    const double b = *(const double *)rhs;
    return (a > b) - (a < b);
}

static double median(double values[SAMPLE_COUNT])
{
    qsort(values, SAMPLE_COUNT, sizeof(values[0]), compare_double);
    return values[SAMPLE_COUNT / 2u];
}

static uint64_t bench_capability(uint64_t iterations)
{
    turbo_cap_context ctx = {
        .key0 = UINT64_C(0x6a09e667f3bcc909),
        .key1 = UINT64_C(0xbb67ae8584caa73b),
    };
    turbo_capability caps[CAP_SET_SIZE];
    for (uint32_t index = 0; index < CAP_SET_SIZE; ++index) {
        caps[index] = turbo_cap_issue(
            &ctx,
            UINT64_C(0x100000000) + index,
            TURBO_RIGHT_READ | TURBO_RIGHT_WRITE | TURBO_RIGHT_SIGNAL,
            index + 1u);
    }

    uint64_t sum = 0;
    const uint64_t start = turbo_x64_tsc_begin();
    for (uint64_t iteration = 0; iteration < iterations; ++iteration) {
        uint64_t object_id = 0;
        const turbo_capability *cap = &caps[iteration & (CAP_SET_SIZE - 1u)];
        if (turbo_cap_resolve(&ctx, cap, TURBO_RIGHT_READ, &object_id)) {
            sum ^= object_id + iteration;
        }
    }
    const uint64_t end = turbo_x64_tsc_end();
    benchmark_sink ^= sum;
    return end - start;
}

static uint64_t bench_scheduler(uint64_t iterations)
{
    turbo_scheduler scheduler;
    turbo_scheduler_init(&scheduler);
    for (uint16_t task = 0; task < 64u; ++task) {
        (void)turbo_scheduler_enqueue(&scheduler, task, (uint8_t)(task & 7u));
    }

    uint64_t sum = 0;
    const uint64_t start = turbo_x64_tsc_begin();
    for (uint64_t iteration = 0; iteration < iterations; ++iteration) {
        uint16_t task = 0;
        uint8_t priority = 0;
        (void)turbo_scheduler_next(&scheduler, &task, &priority);
        sum += task;
        (void)turbo_scheduler_enqueue(&scheduler, task, priority);
    }
    const uint64_t end = turbo_x64_tsc_end();
    benchmark_sink ^= sum;
    return end - start;
}

static uint64_t bench_ipc_roundtrip(uint64_t iterations)
{
    turbo_ipc_ring *ring = aligned_alloc(TURBO_CACHELINE, sizeof(*ring));
    if (ring == NULL) {
        perror("aligned_alloc");
        exit(EXIT_FAILURE);
    }
    turbo_ipc_init(ring);

    turbo_ipc_message tx = {.tag = UINT64_C(0x544d4f53), .words = {1, 2, 3, 4, 5, 6}};
    turbo_ipc_message rx = {0};
    uint64_t sum = 0;

    const uint64_t start = turbo_x64_tsc_begin();
    for (uint64_t iteration = 0; iteration < iterations; ++iteration) {
        tx.words[0] = iteration;
        (void)turbo_ipc_push(ring, &tx);
        (void)turbo_ipc_pop(ring, &rx);
        sum ^= rx.words[0] + rx.tag;
    }
    const uint64_t end = turbo_x64_tsc_end();

    benchmark_sink ^= sum;
    free(ring);
    return end - start;
}

static uint64_t bench_rep_movsb_256(uint64_t iterations)
{
    alignas(TURBO_CACHELINE) uint8_t src[256];
    alignas(TURBO_CACHELINE) uint8_t dst[256];
    for (size_t index = 0; index < sizeof(src); ++index) {
        src[index] = (uint8_t)(index * 17u + 3u);
    }

    uint64_t sum = 0;
    const uint64_t start = turbo_x64_tsc_begin();
    for (uint64_t iteration = 0; iteration < iterations; ++iteration) {
        turbo_x64_rep_movsb(dst, src, sizeof(src));
        sum += dst[iteration & 255u];
    }
    const uint64_t end = turbo_x64_tsc_end();
    benchmark_sink ^= sum;
    return end - start;
}

static uint64_t bench_memcpy_256(uint64_t iterations)
{
    alignas(TURBO_CACHELINE) uint8_t src[256];
    alignas(TURBO_CACHELINE) uint8_t dst[256];
    for (size_t index = 0; index < sizeof(src); ++index) {
        src[index] = (uint8_t)(index * 29u + 7u);
    }

    uint64_t sum = 0;
    const uint64_t start = turbo_x64_tsc_begin();
    for (uint64_t iteration = 0; iteration < iterations; ++iteration) {
        memcpy(dst, src, sizeof(src));
        sum += dst[iteration & 255u];
        __asm__ volatile("" ::: "memory");
    }
    const uint64_t end = turbo_x64_tsc_end();
    benchmark_sink ^= sum;
    return end - start;
}

static bool self_test(void)
{
    turbo_cap_context ctx = {
        .key0 = UINT64_C(0x123456789abcdef0),
        .key1 = UINT64_C(0xfedcba9876543210),
    };
    turbo_capability cap = turbo_cap_issue(
        &ctx, 42u, TURBO_RIGHT_READ | TURBO_RIGHT_WRITE, 9u);
    uint64_t object_id = 0;
    if (!turbo_cap_resolve(&ctx, &cap, TURBO_RIGHT_READ, &object_id) || object_id != 42u) {
        return false;
    }
    if (turbo_cap_resolve(&ctx, &cap, TURBO_RIGHT_EXEC, NULL)) {
        return false;
    }
    cap.seal ^= 1u;
    if (turbo_cap_resolve(&ctx, &cap, TURBO_RIGHT_READ, NULL)) {
        return false;
    }

    turbo_scheduler scheduler;
    turbo_scheduler_init(&scheduler);
    if (!turbo_scheduler_enqueue(&scheduler, 11u, 7u) ||
        !turbo_scheduler_enqueue(&scheduler, 22u, 2u)) {
        return false;
    }
    uint16_t task = 0;
    uint8_t priority = 0;
    if (!turbo_scheduler_next(&scheduler, &task, &priority) || task != 22u || priority != 2u) {
        return false;
    }

    turbo_ipc_ring *ring = aligned_alloc(TURBO_CACHELINE, sizeof(*ring));
    if (ring == NULL) {
        return false;
    }
    turbo_ipc_init(ring);
    const turbo_ipc_message tx = {.tag = 7u, .words = {9u, 0, 0, 0, 0, 0}};
    turbo_ipc_message rx = {0};
    const bool ipc_ok = turbo_ipc_push(ring, &tx) && turbo_ipc_pop(ring, &rx) &&
                        rx.tag == 7u && rx.words[0] == 9u;
    free(ring);
    return ipc_ok;
}

static bench_result run_benchmark(const char *name,
                                  bench_fn fn,
                                  uint64_t iterations,
                                  double cycles_per_ns)
{
    double samples[SAMPLE_COUNT];
    (void)fn(iterations / 20u + 1u);
    for (uint32_t sample = 0; sample < SAMPLE_COUNT; ++sample) {
        samples[sample] = (double)fn(iterations) / (double)iterations;
    }
    const double cycles = median(samples);
    bench_result result = {
        .name = name,
        .cycles_per_op = cycles,
        .ns_per_op = cycles / cycles_per_ns,
        .iterations = iterations,
    };
    return result;
}

static void print_json(const bench_result *results, size_t count, double cycles_per_ns)
{
    printf("{\n");
    printf("  \"architecture\": \"x86_64\",\n");
    printf("  \"cycles_per_ns\": %.6f,\n", cycles_per_ns);
    printf("  \"results\": [\n");
    for (size_t index = 0; index < count; ++index) {
        const bench_result *result = &results[index];
        printf("    {\"name\": \"%s\", \"iterations\": %" PRIu64
               ", \"cycles_per_op\": %.4f, \"ns_per_op\": %.4f}%s\n",
               result->name,
               result->iterations,
               result->cycles_per_op,
               result->ns_per_op,
               index + 1u == count ? "" : ",");
    }
    printf("  ],\n");
    printf("  \"sink\": %" PRIu64 "\n", benchmark_sink);
    printf("}\n");
}

int main(int argc, char **argv)
{
    bool json = false;
    bool only_test = false;
    uint64_t iterations = UINT64_C(3000000);

    for (int index = 1; index < argc; ++index) {
        if (strcmp(argv[index], "--json") == 0) {
            json = true;
        } else if (strcmp(argv[index], "--self-test") == 0) {
            only_test = true;
        } else if (strcmp(argv[index], "--iterations") == 0 && index + 1 < argc) {
            iterations = strtoull(argv[++index], NULL, 10);
            if (iterations < 1000u) {
                fprintf(stderr, "iterations must be >= 1000\n");
                return EXIT_FAILURE;
            }
        } else {
            fprintf(stderr, "usage: %s [--json] [--self-test] [--iterations N]\n", argv[0]);
            return EXIT_FAILURE;
        }
    }

    if (!self_test()) {
        fprintf(stderr, "TURBO Core self-test failed\n");
        return EXIT_FAILURE;
    }
    if (only_test) {
        puts("TURBO Core self-test: PASS");
        return EXIT_SUCCESS;
    }

    pin_to_cpu_zero();
    const double cycles_per_ns = calibrate_cycles_per_ns();
    bench_result results[] = {
        run_benchmark("capability_resolve", bench_capability, iterations, cycles_per_ns),
        run_benchmark("scheduler_pick_rotate", bench_scheduler, iterations, cycles_per_ns),
        run_benchmark("ipc_spsc_roundtrip", bench_ipc_roundtrip, iterations / 2u, cycles_per_ns),
        run_benchmark("rep_movsb_256", bench_rep_movsb_256, iterations / 4u, cycles_per_ns),
        run_benchmark("compiler_memcpy_256", bench_memcpy_256, iterations / 4u, cycles_per_ns),
    };

    if (json) {
        print_json(results, sizeof(results) / sizeof(results[0]), cycles_per_ns);
    } else {
        printf("TURBO Core x86_64 benchmark (median of %u samples)\n", SAMPLE_COUNT);
        printf("TSC calibration: %.3f GHz-equivalent\n", cycles_per_ns);
        for (size_t index = 0; index < sizeof(results) / sizeof(results[0]); ++index) {
            printf("%-26s %10.3f cycles/op  %10.3f ns/op\n",
                   results[index].name,
                   results[index].cycles_per_op,
                   results[index].ns_per_op);
        }
    }
    return EXIT_SUCCESS;
}
