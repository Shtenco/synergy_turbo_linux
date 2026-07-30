#ifndef TURBO_CORE_H
#define TURBO_CORE_H

#include <stdalign.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "turbo/x64.h"

#define TURBO_CACHELINE 64u
#define TURBO_PRIORITY_LEVELS 64u
#define TURBO_MAX_TASKS 256u
#define TURBO_TASK_NONE UINT16_MAX
#define TURBO_IPC_CAPACITY 1024u
#define TURBO_IPC_MASK (TURBO_IPC_CAPACITY - 1u)

_Static_assert((TURBO_IPC_CAPACITY & TURBO_IPC_MASK) == 0u,
               "IPC capacity must be a power of two");

enum turbo_rights {
    TURBO_RIGHT_READ = 1u << 0,
    TURBO_RIGHT_WRITE = 1u << 1,
    TURBO_RIGHT_EXEC = 1u << 2,
    TURBO_RIGHT_SIGNAL = 1u << 3,
    TURBO_RIGHT_MAP = 1u << 4,
    TURBO_RIGHT_ADMIN = 1u << 31
};

typedef struct {
    uint64_t object_id;
    uint32_t rights;
    uint32_t generation;
    uint64_t seal;
} turbo_capability;

typedef struct {
    uint64_t key0;
    uint64_t key1;
} turbo_cap_context;

typedef struct {
    uint16_t head[TURBO_PRIORITY_LEVELS];
    uint16_t tail[TURBO_PRIORITY_LEVELS];
    uint16_t next[TURBO_MAX_TASKS];
    uint64_t ready_bitmap;
    uint32_t runnable;
} turbo_scheduler;

typedef struct {
    uint64_t tag;
    uint64_t words[6];
} turbo_ipc_message;

_Static_assert(sizeof(turbo_ipc_message) == 56u, "IPC message must remain compact");

typedef struct {
    alignas(TURBO_CACHELINE) _Atomic uint32_t head;
    uint8_t head_pad[TURBO_CACHELINE - sizeof(_Atomic uint32_t)];
    alignas(TURBO_CACHELINE) _Atomic uint32_t tail;
    uint8_t tail_pad[TURBO_CACHELINE - sizeof(_Atomic uint32_t)];
    alignas(TURBO_CACHELINE) turbo_ipc_message slots[TURBO_IPC_CAPACITY];
} turbo_ipc_ring;

turbo_capability turbo_cap_issue(const turbo_cap_context *ctx,
                                 uint64_t object_id,
                                 uint32_t rights,
                                 uint32_t generation);
bool turbo_cap_resolve(const turbo_cap_context *ctx,
                       const turbo_capability *cap,
                       uint32_t requested_rights,
                       uint64_t *object_id_out);

void turbo_scheduler_init(turbo_scheduler *scheduler);
bool turbo_scheduler_enqueue(turbo_scheduler *scheduler,
                             uint16_t task_id,
                             uint8_t priority);
bool turbo_scheduler_next(turbo_scheduler *scheduler,
                          uint16_t *task_id_out,
                          uint8_t *priority_out);

void turbo_ipc_init(turbo_ipc_ring *ring);
bool turbo_ipc_push(turbo_ipc_ring *ring, const turbo_ipc_message *message);
bool turbo_ipc_pop(turbo_ipc_ring *ring, turbo_ipc_message *message_out);

#endif
