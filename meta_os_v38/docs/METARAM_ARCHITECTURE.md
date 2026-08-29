# MetaRAM v0.1 — Temporal Compressed Virtual Memory for TURBO Meta-OS

## Position in Meta-OS

MetaRAM is designed as a ring-3 pager/service cell. Ring-0 remains the small capability/memory/scheduler/hypervisor substrate.

## “Infinite virtual RAM” — precise meaning

MetaRAM does not claim infinite physical capacity. It provides a sparse logical temporal address space `(address_space_id, virtual_page_number, generation_timestamp)` whose history can be very large because unchanged generations need not allocate a new payload. Physical capacity remains bounded by DRAM + compressed pools + NVMe/MetaFS/remote backing.

## Tier model

1. HOT / DRAM RAW — frequently accessed pages, no compression latency.
2. WARM / DRAM COMPRESSED — LZ4 or zero/fill representation.
3. COLD / LOCAL BACKING — temporal SAME_PREV / XOR_LZ4 / LZ4 pages in NVMe swap or MetaFS.
4. FROZEN / SNAPSHOT — immutable MetaFS superblocks.
5. Optional remote/object tier.

Placement objective:

`J = α·physical_bytes + β·compress_ns + γ·decompress_ns + δ·expected_IO_ns + ε·write_wear`

## Measured prototype

Full HODC-120 treated as 4-KiB pages, four temporal generations with deterministic sparse mutations:

- logical page-generations: 24,920,064 B
- MetaRAM physical bytes incl. metadata: 3,004,424 B
- MetaRAM ratio: 8.294×
- MetaRAM encode: 990.9 MiB/s
- MetaRAM decode: 2834.6 MiB/s
- direct page-LZ4 bytes incl. metadata: 10,165,202 B
- direct page-LZ4 ratio: 2.452×
- direct page-LZ4 encode: 1541.2 MiB/s
- direct page-LZ4 decode: 5911.3 MiB/s

MetaRAM space efficiency relative to direct page-LZ4: 3.38×. The trade-off is intentional: direct LZ4 is faster, while temporal lineage saves much more memory. Hot pages bypass the temporal path.

## Next step

`FAULT -> lookup temporal page -> resolve/decompress -> validate -> map`

`RECLAIM -> classify hotness -> choose tier -> compress/delta -> publish immutable page version`
