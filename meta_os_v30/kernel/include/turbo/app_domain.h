#ifndef TURBO_APP_DOMAIN_H
#define TURBO_APP_DOMAIN_H

#include <turbo/elf64.h>
#include <turbo/status.h>
#include <turbo/types.h>

#define TURBO_APP_DOMAIN_MAX 64u
#define TURBO_APP_DOMAIN_VA_MIN UINT64_C(0x0000000040000000)
#define TURBO_APP_DOMAIN_VA_MAX UINT64_C(0x0000000080000000)
#define TURBO_APP_DOMAIN_MEMORY_MAX UINT64_C(0x40000000) /* 1 GiB/domain */
#define TURBO_APP_DOMAIN_CPU_WEIGHT_MAX 1000u

#define TURBO_APP_CAP_VFS     UINT64_C(1u << 0)
#define TURBO_APP_CAP_NETWORK UINT64_C(1u << 1)
#define TURBO_APP_CAP_DISPLAY UINT64_C(1u << 2)
#define TURBO_APP_CAP_INPUT   UINT64_C(1u << 3)
#define TURBO_APP_CAP_AUDIO   UINT64_C(1u << 4)
#define TURBO_APP_CAP_COMPUTE UINT64_C(1u << 5)
#define TURBO_APP_CAP_ALLOWED (TURBO_APP_CAP_VFS | TURBO_APP_CAP_NETWORK | \
                               TURBO_APP_CAP_DISPLAY | TURBO_APP_CAP_INPUT | \
                               TURBO_APP_CAP_AUDIO | TURBO_APP_CAP_COMPUTE)

typedef uint32_t turbo_app_handle_t;

typedef enum turbo_app_domain_state {
    TURBO_APP_EMPTY = 0,
    TURBO_APP_PREPARED = 1,
    TURBO_APP_RUNNABLE = 2,
    TURBO_APP_STOPPED = 3
} turbo_app_domain_state_t;

typedef struct turbo_app_domain_request {
    uint16_t owner_cell;
    uint16_t reserved;
    uint32_t cpu_weight;
    uint64_t memory_limit;
    uint64_t capability_mask;
    uint8_t image_digest[32];
} turbo_app_domain_request_t;

typedef struct turbo_app_domain_info {
    turbo_app_handle_t handle;
    uint16_t slot;
    uint16_t owner_cell;
    uint32_t generation;
    uint32_t state;
    uint32_t cpu_weight;
    uint64_t memory_limit;
    uint64_t capability_mask;
    uint64_t entry;
    uint16_t segment_count;
    uint16_t reserved;
    uint8_t image_digest[32];
} turbo_app_domain_info_t;

void turbo_app_domain_system_init(void);
turbo_status_t turbo_app_domain_create(const void *elf_bytes,
                                       size_t elf_size,
                                       const turbo_app_domain_request_t *request,
                                       turbo_app_handle_t *out_handle);
turbo_status_t turbo_app_domain_activate(turbo_app_handle_t handle);
turbo_status_t turbo_app_domain_stop(turbo_app_handle_t handle);
turbo_status_t turbo_app_domain_destroy(turbo_app_handle_t handle);
turbo_status_t turbo_app_domain_info(turbo_app_handle_t handle,
                                     turbo_app_domain_info_t *out_info);
uint32_t turbo_app_domain_live_count(void);
uint32_t turbo_app_domain_runnable_count(void);

#endif
