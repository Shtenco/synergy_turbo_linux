# TURBO Meta-OS v38 — MetaRAM + MetaFS-X + IP Portfolio Lab

Experimental branch target: `meta-os-v38-metaram-metafs-ip`.

This directory adds three linked workstreams while preserving the Meta-OS rule that rich pagers/filesystem parsers stay outside the minimal ring-0 kernel.

## MetaRAM

`src/metaram.c` + `include/metaram.h`

A 4-KiB temporal page codec with ZERO/FILL, SAME_PREV temporal lineage, XOR-LZ4 against the preceding generation, direct LZ4, RAW latency floor, access/generation timestamps, CRC validation and hot-page bypass.

Build:

```bash
make
./metaram_bench <memory-image.bin>
```

The included benchmark results are research measurements, not kernel page-fault latency claims.

## MetaFS-X

`metafs_v2.py`

Snapshot-aware immutable image prototype with CDC chunk identities, cross-file/cross-snapshot dedup, SHA-256 content identity, ~1 MiB solid superblocks and per-superblock `Zstd-19 / Brotli-11 / XZ-9e` selection.

The current implementation is an image packer/restorer, not yet a mountable filesystem.

## IP disclosure

See `docs/IP_CLAIMS_TECHNICAL_DRAFT.md` and `docs/PRIOR_ART_BOUNDARIES.md`.

These are engineering invention-disclosure drafts, not legal advice and not a statement that patent claims are novel or will be granted.

## Physical-capacity statement

MetaRAM does not make physical RAM infinite. It creates a sparse temporal virtual address/state model whose physical backing is bounded by DRAM, local storage, remote storage and compressibility. Timestamp metadata can reduce or carry state metadata, but cannot create free information capacity.
