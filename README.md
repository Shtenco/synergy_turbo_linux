# VirtualQubit Turbo Kernel Automation

Полностью автоматизированный скрипт для настройки VirtualQubit Turbo Kernel на VPS с использованием QEMU виртуализации.

## 🚀 Возможности

- **Полная автоматизация**: От подключения к VPS до тестирования kernel-модулей
- **QEMU виртуализация**: Автоматическая установка и настройка QEMU
- **Kernel-модули**: Установка VirtualQubit и Turbo Scheduler модулей
- **Системные оптимизации**: HugePages, CPU governor, NUMA balancing
- **Тестирование**: Автоматическая проверка установки и производительности
- **Отчетность**: Подробные логи и отчеты об установке

## 📋 Требования

### Системные требования
- Python 3.8+
- Доступ к VPS по SSH
- SSH ключ или пароль для подключения

### Python зависимости
```bash
pip install -r requirements.txt
```

### Файлы проекта
Убедитесь, что в текущей директории находятся:
- `VirtualQubit_Shared/` - папка с kernel-модулями
- `Linux Ubuntu.ppk` - SSH ключ (или будет запрошен пароль)

## ⚙️ Конфигурация

### VPS настройки
```python
VPSConfig(
    hostname="92.246.131.14",    # IP адрес VPS
    username="root",            # Имя пользователя
    ssh_key_path="Linux Ubuntu.ppk"  # Путь к SSH ключу
)
```

### VM настройки
```python
VMConfig(
    disk_size="20G",            # Размер диска VM
    memory="2048",              # Оперативная память (MB)
    cpus=2,                     # Количество CPU
    iso_url="..."               # URL Ubuntu ISO
)
```

## 🏃‍♂️ Запуск

### Базовый запуск
```bash
python virtualqubit_automation.py
```

### С кастомной конфигурацией
```bash
# Редактируем конфигурацию в скрипте
python virtualqubit_automation.py
```

## 📊 Этапы установки

1. **Проверка предварительных условий**
   - Наличие SSH ключа
   - Наличие VirtualQubit_Shared папки

2. **Подключение к VPS**
   - SSH подключение с использованием ключа или пароля
   - Проверка соединения

3. **Установка QEMU**
   - Обновление системы
   - Установка QEMU и зависимостей
   - Установка инструментов разработки

4. **Создание VM среды**
   - Создание VM диска (20GB)
   - Скачивание Ubuntu ISO
   - Создание скрипта запуска VM

5. **Передача файлов**
   - Копирование VirtualQubit_Shared на VPS
   - Проверка целостности файлов

6. **Установка kernel-модулей**
   - Распаковка файлов
   - Запуск install_kernel_modules.sh
   - Проверка успешной установки

7. **Системные оптимизации**
   - Настройка HugePages (32GB)
   - Отключение NUMA balancing
   - Установка CPU governor в performance
   - Настройка transparent hugepages

8. **Тестирование**
   - Проверка загрузки модулей
   - Проверка device nodes
   - Проверка системных настроек

9. **Генерация отчета**
   - Создание JSON отчета
   - Создание текстового отчета
   - Вывод результатов

## 📈 Ожидаемые улучшения производительности

- **FWHT операции**: 3-5x быстрее
- **QFT операции**: 4-8x быстрее
- **Общая производительность Python**: 2-3.5x быстрее
- **32GB HugePages** для memory-intensive операций

## 📁 Создаваемые файлы

### Логи и отчеты
- `virtualqubit_automation.log` - подробные логи установки
- `installation_report.json` - структурированный отчет
- `installation_report.txt` - текстовый отчет

### Скрипты
- `scripts/start_vm.sh` - скрипт запуска VM

## 🔧 Ручная настройка

Если автоматическая установка не подходит, используйте:

### VPS Setup
```bash
# Подключение к VPS
ssh -i "Linux Ubuntu.ppk" root@92.246.131.14

# Установка QEMU
apt update && apt install -y qemu-system-x86 qemu-utils

# Создание VM
qemu-img create -f qcow2 vm.qcow2 20G
wget https://releases.ubuntu.com/24.04/ubuntu-24.04-live-server-amd64.iso
```

### VM Installation
```bash
# Запуск VM
qemu-system-x86_64 \
  -m 2048 \
  -smp 2 \
  -drive file=vm.qcow2,format=qcow2 \
  -cdrom ubuntu-24.04-live-server-amd64.iso \
  -boot d \
  -net nic -net user \
  -nographic
```

### Kernel Modules
```bash
# Передача файлов
scp -r VirtualQubit_Shared root@vps_ip:/root/

# Установка модулей
cd /root/VirtualQubit_Shared
./install_kernel_modules.sh
```

## 🐛 Устранение неполадок

### SSH подключение
```bash
# Проверка SSH ключа
ls -la Linux\ Ubuntu.ppk

# Проверка подключения
ssh -i "Linux Ubuntu.ppk" root@92.246.131.14
```

### QEMU проблемы
```bash
# Проверка KVM поддержки
egrep -c '(vmx|svm)' /proc/cpuinfo

# Запуск с KVM
qemu-system-x86_64 -enable-kvm ...
```

### Module installation
```bash
# Проверка kernel headers
ls /lib/modules/$(uname -r)/build

# Проверка DKMS
dkms status

# Проверка загрузки модулей
lsmod | grep vqubit
```

## 📞 Поддержка

Для вопросов и поддержки:
1. Проверьте логи: `virtualqubit_automation.log`
2. Проверьте отчеты: `installation_report.txt`
3. Используйте ручные команды из раздела "Ручная настройка"

## 📄 Лицензия

Этот проект предназначен для использования с VirtualQubit Turbo Kernel.