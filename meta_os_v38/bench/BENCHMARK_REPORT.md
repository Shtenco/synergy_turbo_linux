# MetaRAM + MetaFS Benchmark Report

## MetaRAM HODC-120 page-generation benchmark

| Metric | MetaRAM temporal | Direct page LZ4 |
|---|---:|---:|
| Logical bytes | 24,920,064 | 24,920,064 |
| Physical bytes incl. metadata | 3,004,424 | 10,165,202 |
| Effective ratio | **8.294×** | 2.452× |
| Encode MiB/s | 990.9 | **1541.2** |
| Decode MiB/s | 2834.6 | **5911.3** |

MetaRAM space efficiency relative to direct page-LZ4: **3.38×**.

Codec decisions: RAW=261, ZERO=7, LZ4=1310, XOR_LZ4=1466, SAME_PREV=3040.

## MetaFS static

| Representation | Bytes |
|---|---:|
| MetaFS-X v0.2 | **1,280,915** |
| tar.zst-19 | 1,325,685 |
| tar.xz-9e | **1,258,844** |

## MetaFS four snapshots

| Representation | Bytes |
|---|---:|
| MetaFS-X v0.2 | **1,474,064** |
| 4 independent tar.zst-19 | 5,306,687 |
| 4 independent tar.xz-9e | 5,039,952 |
| one combined solid tar.zst-19 | 1,342,428 |
| one combined solid tar.xz-9e | 1,261,760 |

The correct filesystem comparison depends on semantics: independent snapshots preserve per-snapshot objects; one combined solid archive is a stronger archival baseline but does not provide the same update/mount/random-access model.
