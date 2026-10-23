<img src="assets/readme/hero.svg" width="100%" alt="TURBO CORE / X86-64 FAST PATHS"/>

# TURBO Core — x86-64 fast-path systems laboratory

A systems research platform focused on **bounded operations, explicit capability checks, fixed-capacity queues and repeatable timing experiments**. The contemporary turbo_core subtree is the central technical artifact; the Windows-to-VPS orchestration is a separate historical branch of investigation.

## Scientific proposition

Low-level performance improvements should be associated with precisely defined operations and measured on the same processor under matched conditions. A capability primitive, scheduler and message queue can provide a small, testable systems foundation before claiming benefits at operating-system scale.

## Implemented fast paths

The [turbo_core guide](turbo_core/README.md) documents a sealed capability issue/resolve design using keyed SipHash-2-4 and rights masks, an **O(1) bitmap-driven scheduler with 64 priority levels**, cacheline-separated SPSC ring IPC, and native x86-64 fast paths. The instruction-contract operations map to instructions or compiler primitives such as LFENCE, RDTSC/RDTSCP, PAUSE, REP MOVSB, REP STOSQ and bit scanning.

TURBO.X64 is a **software-level instruction contract**, not a claim to have created new physical processor opcodes. This interface could later be used by an emulator, FPGA soft core or CPU-specific backend while keeping kernel-facing API stable.

## Reproducible measurement

The repository includes baseline and native optimized build variants, a freestanding compilation check, correctness tests and [run_bench.sh](turbo_core/scripts/run_bench.sh), which produces baseline.json, native.json and environment.txt. The latter records UTC time, kernel information, compiler and CPU identification.

For matched median cycle measurements c(base) and c(native), the speed ratio and reduction are:

$$
S=\frac{c_{\mathrm{base}}}{c_{\mathrm{native}}},\qquad
R=100\left(1-\frac{c_{\mathrm{native}}}{c_{\mathrm{base}}}\right)\%.
$$

Both denominators must be positive. These are **microbenchmark comparisons** and must not be presented as general Linux or datacenter acceleration.

## Separate remote orchestration track

The historical orchestrator installs KVM/build dependencies, retrieves kernel sources, applies a patch, performs runtime tuning and runs sysbench on a remote host. Applying a kernel source patch **without independently showing a reboot into the patched kernel** does not establish that the benchmark measured a patched kernel. This is a reason to maintain clear run manifests, not to dismiss the core research.

## High-value applications

Bounded IPC and capability semantics are relevant to embedded execution, real-time message passing, protected service boundaries and low-latency runtimes. The next technical programme is a freestanding page allocator, address spaces, Ring-3 transition, context-switch instrumentation and matched Linux reference workloads.

## Execution

On a compatible x86-64 Linux host:

    cd turbo_core
    make test
    ./scripts/run_bench.sh

The commands describe source-defined procedures, not results executed in this documentation session. Keep deploy keys outside source control. Any earlier tracked private SSH key should be replaced and revoked before a remote benchmark environment is reused.

[Core](turbo_core/) · [Benchmark runner](turbo_core/scripts/run_bench.sh) · [Rebuild plan](REBUILD_PLAN.md)
