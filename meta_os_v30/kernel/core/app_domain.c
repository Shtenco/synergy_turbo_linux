#include <turbo/app_domain.h>
#include <turbo/topology.h>

#include <string.h>

typedef struct turbo_app_slot {
    turbo_app_domain_info_t info;
    uint32_t generation;
} turbo_app_slot_t;

static turbo_app_slot_t slots[TURBO_APP_DOMAIN_MAX];
static uint32_t live_count;
static uint32_t runnable_count;

static turbo_app_handle_t make_handle(uint16_t slot, uint32_t generation) {
    return (turbo_app_handle_t)(((generation & UINT32_C(0x00FFFFFF)) << 8u) |
                                ((uint32_t)slot + 1u));
}

static turbo_status_t decode_handle(turbo_app_handle_t handle,
                                    uint16_t *out_slot,
                                    uint32_t *out_generation) {
    if (handle == 0u || out_slot == NULL || out_generation == NULL) {
        return TURBO_ERR_INVALID;
    }
    const uint32_t encoded_slot = handle & UINT32_C(0xFF);
    if (encoded_slot == 0u || encoded_slot > TURBO_APP_DOMAIN_MAX) {
        return TURBO_ERR_INVALID;
    }
    *out_slot = (uint16_t)(encoded_slot - 1u);
    *out_generation = handle >> 8u;
    if (*out_generation == 0u) { return TURBO_ERR_INVALID; }
    return TURBO_OK;
}

static turbo_status_t lookup(turbo_app_handle_t handle, turbo_app_slot_t **out_slot) {
    uint16_t slot = 0u;
    uint32_t generation = 0u;
    turbo_status_t status = decode_handle(handle, &slot, &generation);
    if (status != TURBO_OK || out_slot == NULL) { return status; }
    turbo_app_slot_t *entry = &slots[slot];
    if (entry->info.state == TURBO_APP_EMPTY) { return TURBO_ERR_NOT_FOUND; }
    if (entry->generation != generation || entry->info.handle != handle) {
        return TURBO_ERR_STALE;
    }
    *out_slot = entry;
    return TURBO_OK;
}

void turbo_app_domain_system_init(void) {
    memset(slots, 0, sizeof(slots));
    live_count = 0u;
    runnable_count = 0u;
    for (uint16_t i = 0u; i < TURBO_APP_DOMAIN_MAX; ++i) {
        slots[i].generation = 1u;
    }
}

turbo_status_t turbo_app_domain_create(const void *elf_bytes,
                                       size_t elf_size,
                                       const turbo_app_domain_request_t *request,
                                       turbo_app_handle_t *out_handle) {
    if (elf_bytes == NULL || request == NULL || out_handle == NULL ||
        request->owner_cell >= TURBO_TOPOLOGY_CELL_COUNT ||
        request->cpu_weight == 0u ||
        request->cpu_weight > TURBO_APP_DOMAIN_CPU_WEIGHT_MAX ||
        request->memory_limit == 0u ||
        request->memory_limit > TURBO_APP_DOMAIN_MEMORY_MAX ||
        (request->capability_mask & ~TURBO_APP_CAP_ALLOWED) != 0u) {
        return TURBO_ERR_INVALID;
    }

    turbo_elf64_image_t image;
    turbo_status_t status = turbo_elf64_validate(elf_bytes, elf_size,
                                                  TURBO_APP_DOMAIN_VA_MIN,
                                                  TURBO_APP_DOMAIN_VA_MAX,
                                                  &image);
    if (status != TURBO_OK) { return status; }

    uint16_t free_slot = TURBO_APP_DOMAIN_MAX;
    for (uint16_t i = 0u; i < TURBO_APP_DOMAIN_MAX; ++i) {
        if (slots[i].info.state == TURBO_APP_EMPTY) {
            free_slot = i;
            break;
        }
    }
    if (free_slot == TURBO_APP_DOMAIN_MAX) { return TURBO_ERR_FULL; }

    turbo_app_slot_t *entry = &slots[free_slot];
    uint32_t generation = entry->generation;
    if (generation == 0u || generation > UINT32_C(0x00FFFFFF)) {
        generation = 1u;
        entry->generation = generation;
    }

    memset(&entry->info, 0, sizeof(entry->info));
    entry->info.handle = make_handle(free_slot, generation);
    entry->info.slot = free_slot;
    entry->info.owner_cell = request->owner_cell;
    entry->info.generation = generation;
    entry->info.state = TURBO_APP_PREPARED;
    entry->info.cpu_weight = request->cpu_weight;
    entry->info.memory_limit = request->memory_limit;
    entry->info.capability_mask = request->capability_mask;
    entry->info.entry = image.entry;
    entry->info.segment_count = image.segment_count;
    memcpy(entry->info.image_digest, request->image_digest,
           sizeof(entry->info.image_digest));

    live_count++;
    *out_handle = entry->info.handle;
    return TURBO_OK;
}

turbo_status_t turbo_app_domain_activate(turbo_app_handle_t handle) {
    turbo_app_slot_t *entry = NULL;
    turbo_status_t status = lookup(handle, &entry);
    if (status != TURBO_OK) { return status; }
    if (entry->info.state == TURBO_APP_RUNNABLE) { return TURBO_ERR_BUSY; }
    if (entry->info.state != TURBO_APP_PREPARED &&
        entry->info.state != TURBO_APP_STOPPED) { return TURBO_ERR_INVALID; }
    entry->info.state = TURBO_APP_RUNNABLE;
    runnable_count++;
    return TURBO_OK;
}

turbo_status_t turbo_app_domain_stop(turbo_app_handle_t handle) {
    turbo_app_slot_t *entry = NULL;
    turbo_status_t status = lookup(handle, &entry);
    if (status != TURBO_OK) { return status; }
    if (entry->info.state != TURBO_APP_RUNNABLE) { return TURBO_ERR_INVALID; }
    entry->info.state = TURBO_APP_STOPPED;
    if (runnable_count > 0u) { runnable_count--; }
    return TURBO_OK;
}

turbo_status_t turbo_app_domain_destroy(turbo_app_handle_t handle) {
    turbo_app_slot_t *entry = NULL;
    turbo_status_t status = lookup(handle, &entry);
    if (status != TURBO_OK) { return status; }
    if (entry->info.state == TURBO_APP_RUNNABLE) { return TURBO_ERR_BUSY; }
    const uint32_t old_generation = entry->generation;
    memset(&entry->info, 0, sizeof(entry->info));
    entry->generation = old_generation + 1u;
    if (entry->generation == 0u || entry->generation > UINT32_C(0x00FFFFFF)) {
        entry->generation = 1u;
    }
    if (live_count > 0u) { live_count--; }
    return TURBO_OK;
}

turbo_status_t turbo_app_domain_info(turbo_app_handle_t handle,
                                     turbo_app_domain_info_t *out_info) {
    if (out_info == NULL) { return TURBO_ERR_INVALID; }
    turbo_app_slot_t *entry = NULL;
    turbo_status_t status = lookup(handle, &entry);
    if (status != TURBO_OK) { return status; }
    *out_info = entry->info;
    return TURBO_OK;
}

uint32_t turbo_app_domain_live_count(void) { return live_count; }
uint32_t turbo_app_domain_runnable_count(void) { return runnable_count; }
