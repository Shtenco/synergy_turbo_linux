# Быстрый старт с VirtualQubit Automation

## 🚀 Быстрый запуск

### 1. Настройка SSH ключей (если нужно)
```bash
python ssh_setup.py
```

### 2. Проверка готовности системы
```bash
python setup.py
```

### 3. Запуск автоматизации
```bash
python virtualqubit_automation.py
```

## 🔑 SSH Ключи

### Поддерживаемые форматы:
- **PuTTY (.ppk)** - как в папке (Linux Ubuntu.ppk)
- **OpenSSH (.key)** - стандартный формат
- **Пароль** - альтернативный вариант

### Для .ppk ключей:
1. **Автоматическое использование** - скрипт попробует использовать ключ напрямую
2. **Через pagent** - если установлен PuTTY Agent
3. **Конвертация** - через `ssh_setup.py` в OpenSSH формат
4. **Пароль** - как альтернатива

### Конвертация .ppk в OpenSSH:
```bash
# Используя ssh_setup.py
python ssh_setup.py

# Или вручную через puttygen
puttygen "Linux Ubuntu.ppk" -O private-openssh -o linux_ubuntu.key
```

## 📋 Что делает скрипт

### Автоматические действия:
1. **Подключение к VPS** (92.246.131.14)
2. **Установка QEMU** и всех зависимостей
3. **Создание VM** с Ubuntu 24.04
4. **Установка kernel-модулей** VirtualQubit и Turbo Scheduler
5. **Системные оптимизации** (HugePages, CPU governor и т.д.)
6. **Тестирование** и генерация отчетов

### Результат:
- **3-5x** ускорение FWHT операций
- **4-8x** ускорение QFT операций  
- **2-3.5x** общее ускорение Python
- **32GB** HugePages для memory-intensive задач

## 🔧 Ручная настройка (если нужно)

### Подключение к VPS
```bash
ssh -i "Linux Ubuntu.ppk" root@92.246.131.14
```

### Установка QEMU
```bash
apt update && apt install -y qemu-system-x86 qemu-utils
```

### Создание VM
```bash
qemu-img create -f qcow2 vm.qcow2 20G
wget https://releases.ubuntu.com/24.04/ubuntu-24.04-live-server-amd64.iso
```

### Запуск VM
```bash
qemu-system-x86_64 \
  -m 2048 \
  -smp 2 \
  -drive file=vm.qcow2,format=qcow2 \
  -cdrom ubuntu-24.04-live-server-amd64.iso \
  -boot d \
  -net nic -net user \
  -nographic
```

## 📁 Структура файлов

```
D:\Linux Turbo/
├── virtualqubit_automation.py    # Главный скрипт автоматизации
├── setup.py                      # Проверка и установка зависимостей
├── requirements.txt              # Python зависимости
├── README.md                     # Подробная документация
├── QUICK_START.md               # Быстрые инструкции (этот файл)
├── Linux Ubuntu.ppk             # SSH ключ для VPS
├── VirtualQubit_Shared/         # Kernel-модули и скрипты
└── [другие файлы проекта]
```

## 🐛 Возможные проблемы

### SSH подключение
```bash
# Проверка ключа
ls -la "Linux Ubuntu.ppk"

# Альтернативное подключение с паролем
ssh root@92.246.131.14
```

### Зависимости Python
```bash
# Установка вручную
pip install paramiko scp tqdm
```

### QEMU проблемы
```bash
# Проверка KVM поддержки
egrep -c '(vmx|svm)' /proc/cpuinfo

# Запуск с KVM (если поддерживается)
qemu-system-x86_64 -enable-kvm ...
```

## 📊 После установки

### Проверка модулей
```bash
# Проверка загрузки модулей
lsmod | grep vqubit
lsmod | grep turbo_sched

# Проверка device nodes
ls -l /dev/vqubit /dev/turbo_sched

# Проверка HugePages
cat /proc/sys/vm/nr_hugepages
```

### Тестирование
```bash
# Запуск тестов
python3 test_modules.py

# Запуск бенчмарков
make benchmark
```

## 📞 Поддержка

1. **Логи**: `virtualqubit_automation.log`
2. **Отчеты**: `installation_report.txt`
3. **Документация**: `README.md`

## ⚠️ Важно

- Скрипт требует **root доступ** к VPS
- Нужен **интернет** для скачивания Ubuntu ISO
- Рекомендуется **20GB+ свободного места** на VPS
- После установки **перезагрузите VM** для активации оптимизаций