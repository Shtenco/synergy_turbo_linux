#ifndef TURBO_COMPOSITOR_H
#define TURBO_COMPOSITOR_H

#include <turbo/status.h>
#include <turbo/types.h>

#define TURBO_DESKTOP_MAX_SURFACES 64u
#define TURBO_DESKTOP_MAX_WIDTH 8192u
#define TURBO_DESKTOP_MAX_HEIGHT 8192u

typedef uint32_t turbo_surface_handle_t;

typedef struct turbo_surface_info {
    turbo_surface_handle_t handle;
    uint32_t width;
    uint32_t height;
    uint32_t stride;
    uint32_t pixel_format;
    uint64_t owner_domain;
    uint64_t frame_sequence;
    bool visible;
} turbo_surface_info_t;

void turbo_compositor_init(void);
turbo_status_t turbo_surface_create(uint64_t owner_domain,
                                    uint32_t width,
                                    uint32_t height,
                                    uint32_t stride,
                                    uint32_t pixel_format,
                                    turbo_surface_handle_t *out_handle);
turbo_status_t turbo_surface_present(turbo_surface_handle_t handle,
                                     uint64_t frame_sequence);
turbo_status_t turbo_surface_hide(turbo_surface_handle_t handle);
turbo_status_t turbo_surface_destroy(turbo_surface_handle_t handle);
turbo_status_t turbo_surface_info(turbo_surface_handle_t handle,
                                  turbo_surface_info_t *out_info);
uint32_t turbo_compositor_surface_count(void);

#endif
