# Meta-OS v38 Storage Wave 2

## MetaRAM pager service

The new benchmark uses the existing TURBO `turbo_ipc_ring` boundary: fault request -> ring-3 MetaRAM decode/check -> frame reply. On the HODC OS+Data-Center page set (1135 pages), the median of seven exact runs was **3.258 us/page request-to-reply**, **2.917 us/page pager service**, **2.768 us/page decode/check**, and **1199 MiB/s** logical throughput. All seven runs restored every 4-KiB page exactly.

`bench/metaram_userfaultfd.c` also implements a real Linux missing-page path (`CPU access -> userfaultfd -> MetaRAM -> UFFDIO_COPY -> resume`). The current execution sandbox reports `ENOSYS` and the harness exits 77, so no hardware page-fault latency is claimed from this environment.

## MetaFS-X v0.3

v0.3 adds a direct chunk index, lazy mmap-backed superblock loading, previous-snapshot dictionary candidates, and an exact lineage candidate `current_chunk XOR predecessor_chunk -> solid compression`. Generic preset dictionaries were measured but lost the exact byte-cost competition on the four-snapshot workload, so MDL rejected them. Three lineage-XOR superblocks were selected.

Four HODC snapshots: v0.2 = 1,474,064 B / 16.896x; v0.3 = **1,285,067 B / 19.381x**, exact 4/4. This is **12.82% fewer physical image bytes** and **14.71% higher effective ratio**.

## Shared MetaRAM/MetaFS CID

`CIDv1 = SHA-256(plaintext content)`. The CAS representation is independent of identity: fast policy uses ZERO/LZ4/RAW; compact policy may use zlib-9. A cold MetaRAM page can therefore become one immutable CAS object and later be referenced by MetaFS without a second payload.

512-page bridge: standalone MetaFS payload image = 352,583 B; SharedCAS MetaFS incremental image = **35,756 B**, a **9.86x / 89.86%** reduction in incremental snapshot bytes. With fast compressed CAS, total physical storage is 30.20% below keeping the same CAS plus an independent MetaFS payload; compact CAS gives 37.98% reduction. All 497 unique page objects were external MetaFS references and exact restore passed.

Important: the 58.65x external-reference image ratio is an incremental snapshot-image ratio, not total physical storage ratio; CAS bytes must also be counted.
