# MetaFS-X v0.2 — Snapshot-aware Ultra-Compressed Filesystem Image

MetaFS-X is the immutable compressed storage/image layer for TURBO Meta-OS. Rich filesystem parsing remains outside ring-0.

## On-disk concepts

- compressed snapshot manifest;
- content-defined chunks;
- SHA-256 identities;
- cross-file/cross-snapshot dedup;
- first-seen unique chunks packed into ~1 MiB solid superblocks;
- each superblock selects the smallest of Zstd-19 / Brotli-11 / XZ-9e;
- ordered chunk IDs and file SHA-256;
- snapshot generation timestamp.

## Static HODC-120

- logical: 6,226,347 B
- MetaFS-X v0.2: 1,280,915 B = 4.861×, exact
- tar.zst-19: 1,325,685 B
- tar.xz-9e: 1,258,844 B

MetaFS is 3.50% smaller than tar.zst-19 and 1.75% larger than tar.xz-9e on the static tree.

## Four COW snapshots

- logical across four snapshots: 24,905,499 B
- MetaFS-X: 1,474,064 B = 16.896×
- chunk-reference dedup: 72.6%
- all four snapshots restore exactly
- four independent tar.zst-19: 5,306,687 B
- four independent tar.xz-9e: 5,039,952 B

MetaFS uses 3.60× less space than independent zstd snapshots and 3.42× less than independent xz snapshots.

A single combined solid archive is still smaller (tar.zst 1,342,428 B; tar.xz 1,261,760 B), but it does not provide the same per-snapshot update/mount/random-address model.

## v0.3 targets

- history dictionaries from prior snapshots;
- exact ZIP/PDF/DEFLATE semantic experts;
- lazy O(1) superblock index;
- block-aligned mmap/DMA layout;
- signed manifest / version floor;
- GC of unreachable generations;
- MetaRAM page-cache sharing by content identity.
