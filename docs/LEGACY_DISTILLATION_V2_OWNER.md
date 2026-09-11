# Legacy Distillation V2 — turbo_linux owner manifest

Assigned mechanisms: **3**, representing **15** extracted legacy code units.

Mechanism IDs: MECH-0216 MECH-0217 MECH-0218.

Domain: parallel/concurrency support patterns.

Promotion gate requires race-condition tests, deterministic/idempotent state transitions and matched benchmarks. Thread/process parallelism is not assumed faster; V1 already produced a workload where four threads were materially slower than sequential execution.