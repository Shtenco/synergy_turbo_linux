# Kernel patch (Ubuntu 22.04.5 / Linux 5.15) — Virtual Qubit Cores + Turbo Scheduler

> ⚠️ **Важно:** это инженерный/исследовательский патч для Linux scheduler layer.
> Он не добавляет «настоящее квантовое железо», а добавляет **виртуальные кубитные ядра**
> как новый класс планирования `SCHED_VQ_TURBO` и инфраструктуру рантайма в kernel-space.

## Что входит

- `virtual_qubit_turbo_5.15.patch` — unified diff для дерева Linux 5.15.
- Новый scheduler class `vq_turbo_sched_class`.
- Новый policy `SCHED_VQ_TURBO`.
- Sysctl-интерфейс для управления:
  - `kernel.vq_turbo_enabled`
  - `kernel.vq_num_cores`
  - `kernel.vq_timeslice_ns`
  - `kernel.vq_boost_percent`
- `/proc/vq_turbo` со статистикой.

## Файлы, которые добавляются патчем

- `include/linux/vq_turbo.h`
- `kernel/sched/vq_turbo.c`

## Файлы, которые изменяются патчем

- `include/uapi/linux/sched.h`
- `include/linux/sched/prio.h`
- `kernel/sched/Makefile`
- `kernel/sched/Kconfig`
- `kernel/sched/core.c`
- `kernel/sysctl.c`
- `fs/proc/base.c`

## Быстрый сценарий применения на Ubuntu 22.04.5

```bash
sudo apt update
sudo apt install -y build-essential fakeroot libncurses-dev bison flex libssl-dev libelf-dev dwarves

# 1) Получить kernel source Ubuntu 5.15
apt source linux-image-unsigned-$(uname -r)
cd linux-*/

# 2) Скопировать patch
cp /path/to/virtual_qubit_turbo_5.15.patch .

# 3) Применить
patch -p1 < virtual_qubit_turbo_5.15.patch

# 4) Конфиг
cp /boot/config-$(uname -r) .config
yes "" | make oldconfig
scripts/config --enable CONFIG_SCHED_VQ_TURBO

# 5) Сборка (долго)
make -j$(nproc)
make -j$(nproc) modules
sudo make modules_install
sudo make install
sudo update-grub
sudo reboot
```

## Использование после загрузки ядра

```bash
# Включение фичи
sudo sysctl -w kernel.vq_turbo_enabled=1
sudo sysctl -w kernel.vq_num_cores=8
sudo sysctl -w kernel.vq_timeslice_ns=2000000
sudo sysctl -w kernel.vq_boost_percent=35

# Проверка статистики
cat /proc/vq_turbo
```

## Пример API для userspace

Патч резервирует новый policy `SCHED_VQ_TURBO=8` и позволяет выставлять его через `sched_setscheduler()`:

```c
struct sched_param p = { .sched_priority = 0 };
sched_setscheduler(0, SCHED_VQ_TURBO, &p);
```

## Ограничения

- Привязка к ветке Linux 5.15 (Ubuntu 22.04 LTS). На других ветках потребуются rebase-правки.
- Это экспериментальный scheduler path: перед production нужны soak-тесты, lockdep, perf/ftrace профилирование.
- Не заменяет CFS/RT/Deadline, а добавляет отдельный policy для выбранных задач.
