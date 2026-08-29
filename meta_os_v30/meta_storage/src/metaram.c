#include "metaram.h"

#include <lz4.h>
#include <stdint.h>
#include <string.h>
#include <zlib.h>

static int all_zero(const uint8_t *p) {
    uint64_t x = 0;
    for (size_t i = 0; i < MR_PAGE_SIZE; i += sizeof(uint64_t)) {
        uint64_t q;
        memcpy(&q, p + i, sizeof(q));
        x |= q;
    }
    return x == 0;
}

static int all_fill(const uint8_t *p) {
    const uint8_t x = p[0];
    for (size_t i = 1; i < MR_PAGE_SIZE; ++i)
        if (p[i] != x) return 0;
    return 1;
}

static int same_page(const uint8_t *a, const uint8_t *b) {
    return b && memcmp(a, b, MR_PAGE_SIZE) == 0;
}

static uint32_t crc_page(const uint8_t *p) {
    return (uint32_t)crc32(0, p, MR_PAGE_SIZE);
}

const char *mr_codec_name(uint16_t codec) {
    switch (codec) {
    case MR_RAW: return "RAW";
    case MR_ZERO: return "ZERO";
    case MR_FILL: return "FILL";
    case MR_LZ4: return "LZ4";
    case MR_XOR_LZ4: return "XOR_LZ4";
    case MR_SAME_PREV: return "SAME_PREV";
    default: return "UNKNOWN";
    }
}

int mr_compress_page(const uint8_t page[MR_PAGE_SIZE],
                     const uint8_t *prev,
                     uint64_t logical_page_id,
                     uint64_t generation,
                     uint64_t access_ns,
                     int hot_hint,
                     mr_page_blob *out) {
    if (!page || !out) return -1;
    memset(out, 0, sizeof(*out));
    out->meta.logical_page_id = logical_page_id;
    out->meta.generation = generation;
    out->meta.access_ns = access_ns;
    out->meta.checksum32 = crc_page(page);

    if (all_zero(page)) {
        out->meta.codec = MR_ZERO;
        out->meta.stored_bytes = 0;
        return 0;
    }
    if (all_fill(page)) {
        out->meta.codec = MR_FILL;
        out->payload[0] = page[0];
        out->meta.stored_bytes = 1;
        return 0;
    }
    if (same_page(page, prev)) {
        out->meta.codec = MR_SAME_PREV;
        out->meta.stored_bytes = 0;
        return 0;
    }

    if (hot_hint) {
        unsigned seen[256] = {0};
        unsigned uniq = 0;
        for (size_t i = 0; i < MR_PAGE_SIZE; i += 64) {
            if (!seen[page[i]]) { seen[page[i]] = 1; ++uniq; }
        }
        if (uniq > 48) {
            out->meta.codec = MR_RAW;
            memcpy(out->payload, page, MR_PAGE_SIZE);
            out->meta.stored_bytes = MR_PAGE_SIZE;
            return 0;
        }
    }

    int best_n = LZ4_compress_default((const char *)page,
                                      (char *)out->payload,
                                      MR_PAGE_SIZE,
                                      (int)sizeof(out->payload));
    uint16_t best_codec = MR_LZ4;

    uint8_t xor_page[MR_PAGE_SIZE];
    uint8_t xor_comp[MR_MAX_COMPRESSED];
    if (prev) {
        for (size_t i = 0; i < MR_PAGE_SIZE; ++i)
            xor_page[i] = page[i] ^ prev[i];
        int n = LZ4_compress_default((const char *)xor_page,
                                     (char *)xor_comp,
                                     MR_PAGE_SIZE,
                                     (int)sizeof(xor_comp));
        if (n > 0 && (best_n <= 0 || n < best_n)) {
            best_n = n;
            best_codec = MR_XOR_LZ4;
            memcpy(out->payload, xor_comp, (size_t)n);
        }
    }

    if (best_n <= 0 || best_n >= (int)MR_PAGE_SIZE - 64) {
        out->meta.codec = MR_RAW;
        memcpy(out->payload, page, MR_PAGE_SIZE);
        out->meta.stored_bytes = MR_PAGE_SIZE;
        return 0;
    }

    out->meta.codec = best_codec;
    out->meta.stored_bytes = (uint32_t)best_n;
    return 0;
}

int mr_decompress_page(const mr_page_blob *blob,
                       const uint8_t *prev,
                       uint8_t page_out[MR_PAGE_SIZE]) {
    if (!blob || !page_out) return -1;
    switch (blob->meta.codec) {
    case MR_RAW:
        if (blob->meta.stored_bytes != MR_PAGE_SIZE) return -2;
        memcpy(page_out, blob->payload, MR_PAGE_SIZE);
        break;
    case MR_ZERO:
        memset(page_out, 0, MR_PAGE_SIZE);
        break;
    case MR_FILL:
        if (blob->meta.stored_bytes != 1) return -3;
        memset(page_out, blob->payload[0], MR_PAGE_SIZE);
        break;
    case MR_SAME_PREV:
        if (!prev) return -4;
        memcpy(page_out, prev, MR_PAGE_SIZE);
        break;
    case MR_LZ4: {
        int n = LZ4_decompress_safe((const char *)blob->payload,
                                    (char *)page_out,
                                    (int)blob->meta.stored_bytes,
                                    MR_PAGE_SIZE);
        if (n != MR_PAGE_SIZE) return -5;
        break;
    }
    case MR_XOR_LZ4: {
        if (!prev) return -6;
        uint8_t tmp[MR_PAGE_SIZE];
        int n = LZ4_decompress_safe((const char *)blob->payload,
                                    (char *)tmp,
                                    (int)blob->meta.stored_bytes,
                                    MR_PAGE_SIZE);
        if (n != MR_PAGE_SIZE) return -7;
        for (size_t i = 0; i < MR_PAGE_SIZE; ++i)
            page_out[i] = tmp[i] ^ prev[i];
        break;
    }
    default:
        return -8;
    }
    if ((uint32_t)crc32(0, page_out, MR_PAGE_SIZE) != blob->meta.checksum32)
        return -9;
    return 0;
}
