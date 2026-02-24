# turbo_linux

Эксперименты с виртуальными кубитными вычислениями и turbo-планированием.

## Kernel patch kit (Ubuntu 22.04.5 / Linux 5.15)

- `virtual_qubit_turbo_5.15.patch` — RFC-патч `SCHED_VQ_TURBO` с per-CPU VQ runqueue.
- `KERNEL_PATCH_UBUNTU_22_04_5_VQ_TURBO.md` — детальная инструкция, tuning и ограничения.
- `build_vq_turbo_kernel.sh` — автоматизация apply/build/install (`--dry-run`, `--llvm`).
