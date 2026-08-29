#ifndef TURBO_METARAM_H
#define TURBO_METARAM_H

#include <stddef.h>
#include <stdint.h>

#define MR_PAGE_SIZE 4096u
#define MR_MAX_COMPRESSED (MR_PAGE_SIZE + 64u)

enum mr_codec {
    MR_RAW = 0,
    MR_ZERO = 1,
    MR_FILL = 2,
    MR_LZ4 = 3,
    MR_XOR_LZ4 = 4,
    MR_SAME_PREV = 5
};

typedef struct {
    uint64_t logical_page_id;
    uint64_t generation;
    uint64_t access_ns;
    uint32_t stored_bytes;
    uint16_t codec;
    uint16_t flags;
    uint32_t checksum32;
} mr_page_meta;

typedef struct {
    mr_page_meta meta;
    uint8_t payload[MR_MAX_COMPRESSED];
} mr_page_blob;

int mr_compress_page(const uint8_t page[MR_PAGE_SIZE],
                     const uint8_t *prev,
                     uint64_t logical_page_id,
                     uint64_t generation,
                     uint64_t access_ns,
                     int hot_hint,
                     mr_page_blob *out);

int mr_decompress_page(const mr_page_blob *blob,
                       const uint8_t *prev,
                       uint8_t page_out[MR_PAGE_SIZE]);

const char *mr_codec_name(uint16_t codec);

#endif
