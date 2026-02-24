# turbo_linux

Набор экспериментов с виртуальными кубитными вычислениями в userspace и HPC-ускорениями.

## Добавлено

- `virtual_qubit_turbo_5.15.patch` — экспериментальный патч ядра Linux 5.15 (Ubuntu 22.04.5) для policy `SCHED_VQ_TURBO`.
- `KERNEL_PATCH_UBUNTU_22_04_5_VQ_TURBO.md` — инструкция по применению и ограничения.
- `build_vq_turbo_kernel.sh` — автоматизированный скрипт сборки ядра с патчем.
