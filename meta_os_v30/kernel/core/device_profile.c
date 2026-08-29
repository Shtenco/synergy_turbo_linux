#include <turbo/device_profile.h>

#include <string.h>

static turbo_device_profile_t profiles[TURBO_DEVICE_PROFILE_MAX];
static uint16_t profile_count;

void turbo_device_profiles_init(void) {
    memset(profiles, 0, sizeof(profiles));
    profile_count = 0u;
}

static bool valid_class(uint32_t cls) {
    return cls >= TURBO_DEVICE_STORAGE && cls <= TURBO_DEVICE_ACCELERATOR;
}

turbo_status_t turbo_device_profile_register(const turbo_device_profile_t *profile,
                                             uint16_t *out_index) {
    if (profile == NULL || out_index == NULL || !valid_class(profile->device_class) ||
        profile->qualification != TURBO_DEVICE_DISCOVERED ||
        profile_count >= TURBO_DEVICE_PROFILE_MAX) {
        return TURBO_ERR_INVALID;
    }
    profiles[profile_count] = *profile;
    profiles[profile_count].generation = profile->generation == 0u ? 1u : profile->generation;
    *out_index = profile_count++;
    return TURBO_OK;
}

turbo_status_t turbo_device_profile_transition(uint16_t index,
                                               turbo_device_qualification_t next) {
    if (index >= profile_count || next <= TURBO_DEVICE_NOT_PRESENT ||
        next > TURBO_DEVICE_FAILED) { return TURBO_ERR_INVALID; }
    turbo_device_profile_t *p = &profiles[index];
    if (p->qualification == TURBO_DEVICE_FAILED) { return TURBO_ERR_STALE; }
    if (next == TURBO_DEVICE_FAILED) {
        p->qualification = next;
        p->generation++;
        return TURBO_OK;
    }
    if ((uint32_t)next != p->qualification + 1u) { return TURBO_ERR_DENIED; }
    p->qualification = (uint32_t)next;
    return TURBO_OK;
}

turbo_status_t turbo_device_profile_get(uint16_t index,
                                        turbo_device_profile_t *out_profile) {
    if (index >= profile_count || out_profile == NULL) { return TURBO_ERR_INVALID; }
    *out_profile = profiles[index];
    return TURBO_OK;
}

static bool class_at_least(uint32_t cls, uint32_t q) {
    for (uint16_t i = 0u; i < profile_count; ++i) {
        if (profiles[i].device_class == cls && profiles[i].qualification >= q &&
            profiles[i].qualification != TURBO_DEVICE_FAILED) return true;
    }
    return false;
}

bool turbo_device_profile_desktop_io_ready(void) {
    return class_at_least(TURBO_DEVICE_DISPLAY, TURBO_DEVICE_MODELED_PASS) &&
           class_at_least(TURBO_DEVICE_INPUT, TURBO_DEVICE_MODELED_PASS) &&
           class_at_least(TURBO_DEVICE_STORAGE, TURBO_DEVICE_MODELED_PASS);
}

bool turbo_device_profile_physical_desktop_ready(void) {
    return class_at_least(TURBO_DEVICE_DISPLAY, TURBO_DEVICE_PHYSICAL_PASS) &&
           class_at_least(TURBO_DEVICE_INPUT, TURBO_DEVICE_PHYSICAL_PASS) &&
           class_at_least(TURBO_DEVICE_AUDIO, TURBO_DEVICE_PHYSICAL_PASS) &&
           class_at_least(TURBO_DEVICE_STORAGE, TURBO_DEVICE_PHYSICAL_PASS) &&
           class_at_least(TURBO_DEVICE_NETWORK, TURBO_DEVICE_PHYSICAL_PASS);
}
