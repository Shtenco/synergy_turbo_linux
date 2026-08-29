# Prior-art boundary notes

This is an engineering prior-art screen, not a patentability opinion.

## Known nearby systems

- Linux zram: compressed RAM-backed block devices. Therefore “compress pages in RAM” is not new.
- Linux zswap: compressed in-RAM cache in front of backing swap. Therefore “compressed swap cache with eviction” is not new.
- VM migration delta compression: page-delta and adaptive page compression are established research topics.
- Btrfs / OpenZFS: snapshots, COW/block sharing and dedup are established.
- EROFS: compressed read-only filesystem with chunk/rolling-hash dedup and compressed image use cases. Therefore “compressed deduplicated image filesystem” is not new.
- SquashFS: mature solid/block compressed read-only filesystem.
- Precomp / Preflate / preflate-rs: exact reconstruction of DEFLATE streams from plaintext + reconstruction data is prior art.

## Consequence for SHTENCO claims

The strongest defensible distinction is not a generic primitive. It is the specific orchestration:

- exact serialized-cost / MDL graph across heterogeneous experts;
- non-regressing exact-admission;
- time-constrained historical COPY/phrase models;
- temporal page lineage used as a placement/delta decision source;
- joint physical accounting of byte core plus timestamp carrier;
- shared temporal lineage across pager and snapshot filesystem;
- exact-format reconstruction as a conditional segment expert rather than a universal preprocessor.

Before filing, run a professional patent search against these combinations and their individual substeps.
