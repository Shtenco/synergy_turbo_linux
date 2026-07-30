#ifndef TURBO_X64_H
#define TURBO_X64_H

#include <stddef.h>
#include <stdint.h>

#if !defined(__x86_64__)
#error "TURBO Core fast paths currently require x86_64"
#endif

#if defined(__GNUC__) || defined(__clang__)
#define TURBO_ALWAYS_INLINE __attribute__((always_inline)) inline
#define TURBO_NOINLINE __attribute__((noinline))
#define TURBO_LIKELY(x) __builtin_expect(!!(x), 1)
#define TURBO_UNLIKELY(x) __builtin_expect(!!(x), 0)
#else
#define TURBO_ALWAYS_INLINE inline
#define TURBO_NOINLINE
#define TURBO_LIKELY(x) (x)
#define TURBO_UNLIKELY(x) (x)
#endif

/* Ordered timestamp boundaries for microbenchmarks and kernel tracing. */
static TURBO_ALWAYS_INLINE uint64_t turbo_x64_tsc_begin(void)
{
    uint32_t lo;
    uint32_t hi;
    __asm__ volatile("lfence\n\trdtsc" : "=a"(lo), "=d"(hi) :: "memory");
    return ((uint64_t)hi << 32) | lo;
}

static TURBO_ALWAYS_INLINE uint64_t turbo_x64_tsc_end(void)
{
    uint32_t lo;
    uint32_t hi;
    uint32_t aux;
    __asm__ volatile("rdtscp\n\tlfence" : "=a"(lo), "=d"(hi), "=c"(aux) :: "memory");
    (void)aux;
    return ((uint64_t)hi << 32) | lo;
}

static TURBO_ALWAYS_INLINE void turbo_x64_relax(void)
{
    __asm__ volatile("pause" ::: "memory");
}

static TURBO_ALWAYS_INLINE void turbo_x64_prefetch_read(const void *ptr)
{
    __builtin_prefetch(ptr, 0, 3);
}

static TURBO_ALWAYS_INLINE void turbo_x64_prefetch_write(const void *ptr)
{
    __builtin_prefetch(ptr, 1, 3);
}

/* ERMS-friendly copy. Runtime benchmarking decides whether it beats compiler memcpy. */
static TURBO_ALWAYS_INLINE void turbo_x64_rep_movsb(void *dst, const void *src, size_t bytes)
{
    __asm__ volatile("rep movsb"
                     : "+D"(dst), "+S"(src), "+c"(bytes)
                     :
                     : "memory");
}

static TURBO_ALWAYS_INLINE void turbo_x64_rep_stosq(void *dst, uint64_t value, size_t qwords)
{
    __asm__ volatile("rep stosq"
                     : "+D"(dst), "+c"(qwords)
                     : "a"(value)
                     : "memory");
}

static TURBO_ALWAYS_INLINE unsigned turbo_x64_first_set_u64(uint64_t value)
{
    return (unsigned)__builtin_ctzll(value);
}

#endif
