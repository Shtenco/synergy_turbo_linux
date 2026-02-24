# VQ Turbo kernel patch kit (Ubuntu 22.04.5 / Linux 5.15)

> Цель: **максимально ускорить** квантово-симуляционные/векторные пайплайны за счет
> отдельного policy `SCHED_VQ_TURBO` и выделенного VQ runqueue на CPU.

## Что улучшено в этой версии

- Добавлен per-CPU `vq_rq` (очередь, счётчики, runtime clock).
- Добавлен task-local state (`vq_run_list`, `vq_exec_ns`) вместо переиспользования чужих полей.
- Добавлена инициализация в fork-path (`vq_turbo_task_fork`).
- Добавлен более агрессивный и быстрый select CPU:
  - выбор CPU с минимальной длиной VQ-очереди,
  - ограничение VQ-«виртуальных кубитных ядер» через `kernel.vq_num_cores`.
- Добавлен turbo preempt path по временному квантованию (`kernel.vq_timeslice_ns`) и boost-фактору.

## Артефакты

- `virtual_qubit_turbo_5.15.patch` — RFC-patch для linux 5.15 tree.
- `build_vq_turbo_kernel.sh` — apply/build/install script (+ `--dry-run`, `--llvm`).

## Быстрый запуск

```bash
sudo apt update
sudo apt install -y build-essential fakeroot libncurses-dev bison flex libssl-dev libelf-dev dwarves clang lld

apt source linux-image-unsigned-$(uname -r)
cd linux-*/

# быстрый smoke-check патча
/workspace/turbo_linux/build_vq_turbo_kernel.sh "$PWD" --dry-run

# сборка (gcc)
/workspace/turbo_linux/build_vq_turbo_kernel.sh "$PWD"

# или сборка (clang/lld)
/workspace/turbo_linux/build_vq_turbo_kernel.sh "$PWD" --llvm
```

## Runtime tuning (агрессивный пресет)

```bash
sudo sysctl -w kernel.vq_turbo_enabled=1
sudo sysctl -w kernel.vq_num_cores=12
sudo sysctl -w kernel.vq_timeslice_ns=900000
sudo sysctl -w kernel.vq_boost_percent=60

cat /proc/vq_turbo
```

## Рекомендации для максимального ускорения

1. Изолировать VQ-core set через `isolcpus`, `nohz_full`, `rcu_nocbs` в GRUB.
2. Для VQ workload использовать `taskset/cset` и не смешивать их с noisy background.
3. Отключить deep C-states и держать high-performance governor.
4. Сопоставить NUMA memory policy с CPU, где работают VQ-задачи.
5. Валидировать профилем:
   - `perf sched record/report`
   - `trace-cmd record -e sched:*`
   - latency tail p99/p999 на реальном workload.

## Важно

- Это **экспериментальный RFC patch-set** (не upstream, не production-ready из коробки).
- Требуется прогон compile+boot+stress на вашей целевой конфигурации железа.
