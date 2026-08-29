#ifndef TURBO_PHYSICAL_MEMORY_H
#define TURBO_PHYSICAL_MEMORY_H

#include <turbo/boot_memory.h>
#include <turbo/status.h>
#include <turbo/types.h>

#define TURBO_PHYSICAL_PAGE_SIZE 4096u
#define TURBO_PMM_MAX_PHYSICAL UINT64_C(0x2000000000) /* 128 GiB */
#define TURBO_HHDM_BASE UINT64_C(0xFFFF800000000000)
#define TURBO_PMM_MAX_FRAMES (TURBO_PMM_MAX_PHYSICAL / TURBO_PHYSICAL_PAGE_SIZE)
#define TURBO_PMM_MAX_EXTENTS 256u

typedef struct turbo_physical_extent {
    uint64_t start_frame;
    uint64_t page_count;
} turbo_physical_extent_t;

typedef struct turbo_physical_memory_state {
    turbo_physical_extent_t free_extents[TURBO_PMM_MAX_EXTENTS];
    uint32_t extent_count;
    uint32_t managed_frames;
    uint32_t free_frames;
    uint32_t allocation_cursor;
    uint64_t highest_managed_address;
} turbo_physical_memory_state_t;

turbo_status_t turbo_physical_memory_init(const turbo_boot_memory_map_t *map,
                                           uintptr_t kernel_start,
                                           uintptr_t kernel_end);
turbo_status_t turbo_physical_page_allocate(uintptr_t *out_physical_address);
turbo_status_t turbo_physical_page_free(uintptr_t physical_address);
turbo_status_t turbo_physical_contiguous_allocate(uint16_t page_count,
                                                    uint16_t alignment_pages,
                                                    uintptr_t maximum_address,
                                                    uintptr_t *out_physical_address);
turbo_status_t turbo_physical_contiguous_free(uintptr_t physical_address,
                                                uint16_t page_count);
void turbo_physical_reserve_range(uintptr_t start, uintptr_t end);
const turbo_physical_memory_state_t *turbo_physical_memory_state(void);

void *turbo_physical_to_virtual(uintptr_t physical_address);
uintptr_t turbo_virtual_to_physical(const void *virtual_address);
bool turbo_hhdm_contains(const void *virtual_address);

#endif
