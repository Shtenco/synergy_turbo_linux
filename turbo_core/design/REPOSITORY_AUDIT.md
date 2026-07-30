# Audit of the existing Turbo Linux experiment

## What is worth preserving

- Automated baseline/result collection and JSON reports.
- Per-CPU runqueue thinking, bounded hot paths, explicit timeslice controls.
- Windows-to-remote-host orchestration as a future hardware-lab runner.
- Runtime counters for enqueue, dequeue, pick, migration and preemption.

## What cannot be used as evidence of acceleration

The current workflow applies a patch to unpacked Linux source, but does not build,
install or boot that kernel before the second `sysbench` run. The patched result
therefore cannot contain an effect from the scheduler patch.

The second run also changes `sched_autogroup_enabled` and `swappiness`, so even a
real reboot would conflate the kernel change with unrelated tuning.

`sysbench cpu` is primarily a compute-throughput test. It is not a sufficient
scheduler benchmark. Scheduler work needs wakeup latency, context-switch,
runqueue contention, migration, tail latency and mixed-load measurements.

The old VQ patch uses a clock-bit expression as a pseudo-random preemption/boost
condition. That is neither a CPU-frequency boost mechanism nor a predictable
latency policy, and its `turbo_boost_hits` counter is never incremented.

## New rule

No performance claim is accepted unless the exact artifact under test is built,
identified, executed, compared against a matched baseline, repeated, and reported
with raw samples and environment metadata.
