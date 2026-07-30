# TURBO Core x86_64 Fast-Path Lab

This subtree is the clean-room seed of **TURBO Core**. It is independent of the
Linux scheduler patch and keeps only useful ideas from the old repository:
bounded structures, O(1) scheduling, per-core-friendly queues, counters and
reproducible measurements.

## What exists now

- sealed capability issue/resolve path;
- fixed-capacity O(1) 64-priority scheduler;
- cacheline-separated SPSC IPC ring;
- x86_64 fast-path primitives using `LFENCE`, `RDTSC`, `RDTSCP`, `PAUSE`,
  `REP MOVSB`, `REP STOSQ` and compiler-generated bit scan;
- baseline and `-march=native` binaries;
- freestanding compilation check suitable for later kernel integration;
- correctness tests and median-of-seven cycle benchmark;
- JSON result files plus machine/compiler metadata.

## About “our own x64 instructions”

A software project cannot add a new physical x86_64 opcode to existing CPUs.
That requires a CPU/microcode implementation and toolchain support. TURBO Core
therefore defines a **TURBO.X64 software instruction contract**:

| TURBO operation | Current x86_64 lowering |
|---|---|
| `TURBO.CLOCK.BEGIN` | `LFENCE; RDTSC` |
| `TURBO.CLOCK.END` | `RDTSCP; LFENCE` |
| `TURBO.RELAX` | `PAUSE` |
| `TURBO.SCHED.NEXT` | bitmap + first-set-bit instruction |
| `TURBO.MEM.COPY` | measured choice between compiler copy and `REP MOVSB` |
| `TURBO.CAP.CHECK` | keyed SipHash-2-4, rights mask and seal compare |

Later, a custom emulator, FPGA soft-core or CPU extension could map the same
contract to actual new instructions without changing the kernel-facing API.

## Build and test

```bash
cd turbo_core
make test
make bench
```

For an environment report and both variants:

```bash
./scripts/run_bench.sh
```

Outputs:

- `results/baseline.json`
- `results/native.json`
- `results/environment.txt`

## Benchmark interpretation

Numbers are per-operation medians on the current machine. They are not universal
OS performance claims. CI virtual machines are used only for correctness and
regression visibility, not as a stable leaderboard.

The benchmark deliberately reports both cycles and calibrated nanoseconds. Use
cycles for same-CPU code comparisons; use nanoseconds for latency intuition.
Always retain raw JSON and environment metadata.

## Next kernel milestones

1. Move these primitives into the freestanding Stage-0 tree.
2. Add page allocator, address spaces and Ring-3 entry/exit.
3. Measure real syscall, IPC handoff and context-switch latency in QEMU/KVM.
4. Add AP startup and per-CPU runqueues before cross-core work stealing.
5. Compare matched artifacts against Linux using `cyclictest`, `hackbench`,
   `perf bench sched`, IPC microbenchmarks and mixed workloads.
6. Add security gates: W^X, NX, SMAP/SMEP, CET where available, fuzzing and
   formal models for capability transitions.
