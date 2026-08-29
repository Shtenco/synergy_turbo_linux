#ifndef TURBO_DEVICE_PROFILE_H
#define TURBO_DEVICE_PROFILE_H

#include <turbo/status.h>
#include <turbo/types.h>

#define TURBO_DEVICE_PROFILE_MAX 32u

typedef enum turbo_device_class {
    TURBO_DEVICE_STORAGE = 1,
    TURBO_DEVICE_NETWORK = 2,
    TURBO_DEVICE_DISPLAY = 3,
    TURBO_DEVICE_INPUT = 4,
    TURBO_DEVICE_AUDIO = 5,
    TURBO_DEVICE_ACCELERATOR = 6
} turbo_device_class_t;

typedef enum turbo_device_qualification {
    TURBO_DEVICE_NOT_PRESENT = 0,
    TURBO_DEVICE_DISCOVERED = 1,
    TURBO_DEVICE_CONTAINED = 2,
    TURBO_DEVICE_QUEUE_READY = 3,
    TURBO_DEVICE_MODELED_PASS = 4,
    TURBO_DEVICE_PHYSICAL_PASS = 5,
    TURBO_DEVICE_FAILED = 6
} turbo_device_qualification_t;

typedef struct turbo_device_profile {
    uint32_t device_class;
    uint32_t qualification;
    uint32_t vendor_id;
    uint32_t device_id;
    uint64_t iommu_domain;
    uint64_t dma_aperture;
    uint32_t irq_count;
    uint32_t queue_count;
    uint64_t generation;
} turbo_device_profile_t;

void turbo_device_profiles_init(void);
turbo_status_t turbo_device_profile_register(const turbo_device_profile_t *profile,
                                             uint16_t *out_index);
turbo_status_t turbo_device_profile_transition(uint16_t index,
                                               turbo_device_qualification_t next);
turbo_status_t turbo_device_profile_get(uint16_t index,
                                        turbo_device_profile_t *out_profile);
bool turbo_device_profile_desktop_io_ready(void);
bool turbo_device_profile_physical_desktop_ready(void);

#endif
