# SHTENCO Compression / Meta-OS IP — Technical Claim Families v0.1

**Status:** technical invention-disclosure draft, not a legal opinion or a filed patent claim set.

A patent attorney should perform jurisdiction-specific claim drafting and a formal prior-art search before filing. Broad ideas such as compressed RAM, COW snapshots, deduplication, CDC, DEFLATE reconstruction, delta coding and per-file compression are known. The candidate novelty below is therefore framed around narrower combinations, cost functions, state transitions and exact-admission rules.

## Claim family 1 — Segment-MDL reversible expert graph

A method for exact lossless representation of a heterogeneous byte object in which:

1. candidate boundaries are proposed from local structural features or content-defined chunking;
2. each candidate segment is evaluated against a plurality of reversible experts;
3. a route graph is optimized using an objective containing actual serialized payload bytes plus route/parameter metadata;
4. the encoder admits a route only after exact decoding validation or a deterministic lower-bound proof;
5. a raw or legacy representation remains a non-regression floor.

Potential dependent claims: boundary refinement; segment type priors; entropy-coded route IDs; work/latency penalty; shared dictionaries; exact-format experts.

## Claim family 2 — Exact reconstruction expert inside an MDL router

A method in which a segment containing an already-compressed representation is parsed into semantic plaintext plus a reconstruction-decision stream, re-compressed with a stronger backend, compared by total serialized cost against untouched and alternative experts, and selected only when the complete object is bit-exactly reconstructible and smaller.

**Prior-art boundary:** bare DEFLATE precompression/reconstruction is known (Precomp/Preflate). The candidate claim must be narrower: format-reconstruction as one segment expert in an exact non-regressing MDL graph, potentially across multiple stream formats and mixed objects.

## Claim family 3 — Temporal COPY graph with time-constrained historical references

A lossless temporal representation using only model entries whose timestamps precede the target timestamp, where COPY edges reference `(historical entry, offset, length)`, edge identifiers/offset continuation/lengths are coded relative to prior graph edges, literals are jointly context-coded, model identity and target digest are verified, and the encoder rejects target leakage/non-preceding model state.

Potential dependents: multi-parent references; path-conditioned priors; DP/beam parse using true code length; lineage-specific prediction.

## Claim family 4 — Learned phrase grammar coupled to a temporal state carrier

A temporal-history codec in which variable-length byte phrases are learned only from earlier model state, phrase choice is represented by probability/rank, at least part of phrase metadata is mapped into a monotonically ordered timestamp-state sequence using combinatorial rank plus bounded timestamp residual state, and byte-core plus temporal carrier are jointly optimized under explicit physical accounting.

This claim must not assert that timestamps create free information capacity. If timestamps are stored, their physical cost is included.

## Claim family 5 — Learned route-cost predictor with exact admission

A reversible compression system in which a learned model predicts `Δserialized_bytes` and/or latency for candidate experts, prediction is used only to prune/order candidates, the actual chosen representation is verified against exact serialized byte count, a legacy/raw floor prevents regression, and uncertainty can trigger broader evaluation.

## Claim family 6 — Bounded recursive MDL cascade

A method for applying zero, one or more additional compression stages where each next stage is predicted/evaluated on the prior representation, depth is bounded, a stage is accepted only when byte gain exceeds chain metadata and optionally latency cost, and decoding stores/reconstructs the reverse stage graph exactly.

The practical embodiment currently uses a depth-2 frontier because exhaustive testing found a useful second-stage edge but no robust third-stage benefit.

## Claim family 7 — Exact structured-table finite-difference order selection

A method for losslessly coding repeated textual/table rows in which row literals/skeletons are separated from variable numeric fields, numeric strings are converted to exact integer or common-scale decimal representations while retaining lexical reconstruction information, each numeric column selects the minimum serialized representation among finite-difference orders `Δ⁰...Δᴺ`, and exact original text formatting is restored.

Patentability caution: delta-of-delta and columnar coding are known individually; novelty must rest on exact lexical reconstruction + per-column order-selection + integration into the segment MDL graph.

## Claim family 8 — Unified temporal storage substrate for MetaRAM + MetaFS

A computer storage architecture sharing temporal content lineage across virtual-memory pages and filesystem snapshots, in which:

1. logical state is addressed by object/page identity and generation timestamp;
2. unchanged state resolves to an earlier generation without payload duplication;
3. changed state may be stored as XOR/delta against a predecessor or independently compressed;
4. a placement objective chooses raw DRAM, compressed DRAM, local compressed backing store or immutable filesystem superblock according to serialized bytes, access recency and decode/I/O cost;
5. filesystem snapshots and paged memory use compatible content identities/generation semantics while remaining outside the minimal ring-0 kernel.

Potential independent embodiments: MetaRAM temporal pager; MetaFS snapshot store; unified migration/checkpoint store.

## Recommended filing structure

Do not file one giant claim that says “AI compressed OS.” A stronger initial portfolio would be:

- Application A: temporal COPY / phrase / storage lineage (families 3, 4, 8).
- Application B: heterogeneous exact compression router (families 1, 2, 5, 6, 7).
- Keep implementation thresholds, corpus-derived heuristics and route priors as trade secrets where disclosure would not materially improve claim scope.
