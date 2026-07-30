#include "turbo/core.h"

static TURBO_ALWAYS_INLINE uint64_t turbo_rotl64(uint64_t value, unsigned shift)
{
    return (value << shift) | (value >> (64u - shift));
}

static TURBO_ALWAYS_INLINE void turbo_sip_round(uint64_t *v0,
                                                 uint64_t *v1,
                                                 uint64_t *v2,
                                                 uint64_t *v3)
{
    *v0 += *v1;
    *v1 = turbo_rotl64(*v1, 13);
    *v1 ^= *v0;
    *v0 = turbo_rotl64(*v0, 32);
    *v2 += *v3;
    *v3 = turbo_rotl64(*v3, 16);
    *v3 ^= *v2;
    *v0 += *v3;
    *v3 = turbo_rotl64(*v3, 21);
    *v3 ^= *v0;
    *v2 += *v1;
    *v1 = turbo_rotl64(*v1, 17);
    *v1 ^= *v2;
    *v2 = turbo_rotl64(*v2, 32);
}

static uint64_t turbo_cap_seal(const turbo_cap_context *ctx,
                               uint64_t object_id,
                               uint32_t rights,
                               uint32_t generation)
{
    const uint64_t meta = ((uint64_t)generation << 32) | rights;
    const uint64_t final_block = UINT64_C(16) << 56;
    uint64_t v0 = UINT64_C(0x736f6d6570736575) ^ ctx->key0;
    uint64_t v1 = UINT64_C(0x646f72616e646f6d) ^ ctx->key1;
    uint64_t v2 = UINT64_C(0x6c7967656e657261) ^ ctx->key0;
    uint64_t v3 = UINT64_C(0x7465646279746573) ^ ctx->key1;

    v3 ^= object_id;
    turbo_sip_round(&v0, &v1, &v2, &v3);
    turbo_sip_round(&v0, &v1, &v2, &v3);
    v0 ^= object_id;

    v3 ^= meta;
    turbo_sip_round(&v0, &v1, &v2, &v3);
    turbo_sip_round(&v0, &v1, &v2, &v3);
    v0 ^= meta;

    v3 ^= final_block;
    turbo_sip_round(&v0, &v1, &v2, &v3);
    turbo_sip_round(&v0, &v1, &v2, &v3);
    v0 ^= final_block;
    v2 ^= UINT64_C(0xff);
    turbo_sip_round(&v0, &v1, &v2, &v3);
    turbo_sip_round(&v0, &v1, &v2, &v3);
    turbo_sip_round(&v0, &v1, &v2, &v3);
    turbo_sip_round(&v0, &v1, &v2, &v3);
    return v0 ^ v1 ^ v2 ^ v3;
}

turbo_capability turbo_cap_issue(const turbo_cap_context *ctx,
                                 uint64_t object_id,
                                 uint32_t rights,
                                 uint32_t generation)
{
    turbo_capability cap = {
        .object_id = object_id,
        .rights = rights,
        .generation = generation,
        .seal = turbo_cap_seal(ctx, object_id, rights, generation),
    };
    return cap;
}

bool turbo_cap_resolve(const turbo_cap_context *ctx,
                       const turbo_capability *cap,
                       uint32_t requested_rights,
                       uint64_t *object_id_out)
{
    const uint64_t expected = turbo_cap_seal(
        ctx, cap->object_id, cap->rights, cap->generation);
    const bool seal_ok = (expected == cap->seal);
    const bool rights_ok = (cap->rights & requested_rights) == requested_rights;

    if (TURBO_UNLIKELY(!(seal_ok && rights_ok))) {
        return false;
    }

    if (object_id_out != NULL) {
        *object_id_out = cap->object_id;
    }
    return true;
}

void turbo_scheduler_init(turbo_scheduler *scheduler)
{
    scheduler->ready_bitmap = 0;
    scheduler->runnable = 0;
    for (uint32_t priority = 0; priority < TURBO_PRIORITY_LEVELS; ++priority) {
        scheduler->head[priority] = TURBO_TASK_NONE;
        scheduler->tail[priority] = TURBO_TASK_NONE;
    }
    for (uint32_t task = 0; task < TURBO_MAX_TASKS; ++task) {
        scheduler->next[task] = TURBO_TASK_NONE;
    }
}

bool turbo_scheduler_enqueue(turbo_scheduler *scheduler,
                             uint16_t task_id,
                             uint8_t priority)
{
    if (TURBO_UNLIKELY(task_id >= TURBO_MAX_TASKS ||
                       priority >= TURBO_PRIORITY_LEVELS)) {
        return false;
    }

    scheduler->next[task_id] = TURBO_TASK_NONE;
    if (scheduler->head[priority] == TURBO_TASK_NONE) {
        scheduler->head[priority] = task_id;
        scheduler->tail[priority] = task_id;
        scheduler->ready_bitmap |= UINT64_C(1) << priority;
    } else {
        scheduler->next[scheduler->tail[priority]] = task_id;
        scheduler->tail[priority] = task_id;
    }
    scheduler->runnable++;
    return true;
}

bool turbo_scheduler_next(turbo_scheduler *scheduler,
                          uint16_t *task_id_out,
                          uint8_t *priority_out)
{
    const uint64_t bitmap = scheduler->ready_bitmap;
    if (TURBO_UNLIKELY(bitmap == 0)) {
        return false;
    }

    const uint8_t priority = (uint8_t)turbo_x64_first_set_u64(bitmap);
    const uint16_t task_id = scheduler->head[priority];
    const uint16_t next = scheduler->next[task_id];

    scheduler->head[priority] = next;
    scheduler->next[task_id] = TURBO_TASK_NONE;
    scheduler->runnable--;

    if (next == TURBO_TASK_NONE) {
        scheduler->tail[priority] = TURBO_TASK_NONE;
        scheduler->ready_bitmap &= ~(UINT64_C(1) << priority);
    }

    if (task_id_out != NULL) {
        *task_id_out = task_id;
    }
    if (priority_out != NULL) {
        *priority_out = priority;
    }
    return true;
}

void turbo_ipc_init(turbo_ipc_ring *ring)
{
    atomic_init(&ring->head, 0u);
    atomic_init(&ring->tail, 0u);
}

bool turbo_ipc_push(turbo_ipc_ring *ring, const turbo_ipc_message *message)
{
    const uint32_t tail = atomic_load_explicit(&ring->tail, memory_order_relaxed);
    const uint32_t head = atomic_load_explicit(&ring->head, memory_order_acquire);
    if (TURBO_UNLIKELY((uint32_t)(tail - head) == TURBO_IPC_CAPACITY)) {
        return false;
    }

    ring->slots[tail & TURBO_IPC_MASK] = *message;
    atomic_store_explicit(&ring->tail, tail + 1u, memory_order_release);
    return true;
}

bool turbo_ipc_pop(turbo_ipc_ring *ring, turbo_ipc_message *message_out)
{
    const uint32_t head = atomic_load_explicit(&ring->head, memory_order_relaxed);
    const uint32_t tail = atomic_load_explicit(&ring->tail, memory_order_acquire);
    if (TURBO_UNLIKELY(head == tail)) {
        return false;
    }

    *message_out = ring->slots[head & TURBO_IPC_MASK];
    atomic_store_explicit(&ring->head, head + 1u, memory_order_release);
    return true;
}
