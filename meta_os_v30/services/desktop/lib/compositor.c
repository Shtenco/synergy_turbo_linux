#include "compositor.h"

#include <string.h>

typedef struct turbo_surface_slot {
    turbo_surface_info_t info;
    uint32_t generation;
} turbo_surface_slot_t;

static turbo_surface_slot_t surfaces[TURBO_DESKTOP_MAX_SURFACES];
static uint32_t surface_count;

static turbo_surface_handle_t make_handle(uint16_t slot, uint32_t generation) {
    return (turbo_surface_handle_t)((generation << 8u) | ((uint32_t)slot + 1u));
}

static turbo_status_t lookup(turbo_surface_handle_t handle, turbo_surface_slot_t **out) {
    if (handle == 0u || out == NULL) return TURBO_ERR_INVALID;
    uint32_t enc = handle & UINT32_C(0xFF);
    uint32_t gen = handle >> 8u;
    if (enc == 0u || enc > TURBO_DESKTOP_MAX_SURFACES || gen == 0u) return TURBO_ERR_INVALID;
    turbo_surface_slot_t *s = &surfaces[enc - 1u];
    if (s->info.handle == 0u) return TURBO_ERR_NOT_FOUND;
    if (s->generation != gen || s->info.handle != handle) return TURBO_ERR_STALE;
    *out = s; return TURBO_OK;
}

void turbo_compositor_init(void) {
    memset(surfaces, 0, sizeof(surfaces)); surface_count = 0u;
    for (uint16_t i=0u;i<TURBO_DESKTOP_MAX_SURFACES;++i) surfaces[i].generation=1u;
}

turbo_status_t turbo_surface_create(uint64_t owner_domain, uint32_t width,
                                    uint32_t height, uint32_t stride,
                                    uint32_t pixel_format,
                                    turbo_surface_handle_t *out_handle) {
    if (owner_domain == 0u || width == 0u || height == 0u ||
        width > TURBO_DESKTOP_MAX_WIDTH || height > TURBO_DESKTOP_MAX_HEIGHT ||
        stride < width * 4u || out_handle == NULL) return TURBO_ERR_INVALID;
    for (uint16_t i=0u;i<TURBO_DESKTOP_MAX_SURFACES;++i) {
        if (surfaces[i].info.handle == 0u) {
            turbo_surface_slot_t *s=&surfaces[i];
            s->info.handle=make_handle(i,s->generation); s->info.width=width;
            s->info.height=height; s->info.stride=stride; s->info.pixel_format=pixel_format;
            s->info.owner_domain=owner_domain; s->info.visible=false; s->info.frame_sequence=0u;
            surface_count++; *out_handle=s->info.handle; return TURBO_OK;
        }
    }
    return TURBO_ERR_FULL;
}

turbo_status_t turbo_surface_present(turbo_surface_handle_t handle, uint64_t frame_sequence) {
    turbo_surface_slot_t *s=NULL; turbo_status_t st=lookup(handle,&s); if(st!=TURBO_OK)return st;
    if(frame_sequence<=s->info.frame_sequence)return TURBO_ERR_STALE;
    s->info.frame_sequence=frame_sequence;s->info.visible=true;return TURBO_OK;
}

turbo_status_t turbo_surface_hide(turbo_surface_handle_t handle) {
    turbo_surface_slot_t *s=NULL;turbo_status_t st=lookup(handle,&s);if(st!=TURBO_OK)return st;
    s->info.visible=false;return TURBO_OK;
}

turbo_status_t turbo_surface_destroy(turbo_surface_handle_t handle) {
    turbo_surface_slot_t *s=NULL;turbo_status_t st=lookup(handle,&s);if(st!=TURBO_OK)return st;
    uint32_t gen=s->generation+1u;memset(&s->info,0,sizeof(s->info));s->generation=gen?gen:1u;
    if (surface_count > 0u) { surface_count--; }
    return TURBO_OK;
}

turbo_status_t turbo_surface_info(turbo_surface_handle_t handle, turbo_surface_info_t *out_info) {
    turbo_surface_slot_t *s=NULL;if(out_info==NULL)return TURBO_ERR_INVALID;
    turbo_status_t st=lookup(handle,&s);if(st!=TURBO_OK)return st;*out_info=s->info;return TURBO_OK;
}

uint32_t turbo_compositor_surface_count(void){return surface_count;}
