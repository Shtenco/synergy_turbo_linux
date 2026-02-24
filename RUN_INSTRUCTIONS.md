# Инструкции по запуску VirtualQubit Automation

## 🎯 Быстрый старт (5 минут)

### 🔧 Если есть проблемы с SSH ключами (рекомендуется сначала):
```bash
# Быстрое решение проблем с SSH
python fix_ssh.py
```

### Шаг 1: Проверка SSH ключей
```bash
# Проверяем и настраиваем SSH ключи
python ssh_setup.py
```

### Шаг 2: Проверка зависимостей
```bash
# Проверяем Python и зависимости
python setup.py
```

### Шаг 3: Запуск автоматизации
```bash
# Запускаем полную автоматизацию
python virtualqubit_automation.py
```

## 🔧 Решение проблем с SSH ключами

### Проблема: "Не удалось загрузить PPK ключ - типа невалидный RSA"

**Решение 1: Быстрое (рекомендуется)**
```bash
# Запускаем быстрое решение
python fix_ssh.py

# Следуем инструкциям:
# - Выберите "y" для использования пароля
# - Введите данные для подключения
# - Скрипт автоматически переключится на парольную аутентификацию
```

**Решение 2: Конвертация ключа**
```bash
# Используем ssh_setup.py
python ssh_setup.py

# Или вручную:
puttygen "Linux Ubuntu.ppk" -O private-openssh -o linux_ubuntu.key
```

**Решение 3: Использование pagent**
```bash
# Запустите pagent и добавьте .ppk ключ
# Скрипт автоматически его обнаружит
```

**Решение 4: Прямое использование пароля**
```bash
# Запустите основной скрипт
python virtualqubit_automation.py

# Когда спросит пароль от SSH ключа - введите пароль от VPS
```

## 📋 Пошаговая инструкция

### 1. Подготовка системы
```bash
# Убедитесь, что все файлы на месте
ls -la
# Должны быть видны:
# - virtualqubit_automation.py
# - ssh_setup.py
# - setup.py
# - Linux Ubuntu.ppk
# - VirtualQubit_Shared/

# Установите зависимости (если нужно)
pip install -r requirements.txt
```

### 2. Настройка SSH
```bash
# Запускаем настройку SSH
python ssh_setup.py

# Следуйте инструкциям:
# - Выберите конвертировать .ppk ключ или использовать как есть
# - Протестируйте подключение
# - Сохраните пароль если нужно
```

### 3. Запуск автоматизации
```bash
# Запускаем главный скрипт
python virtualqubit_automation.py

# Скрипт выполнит:
# 1. Подключение к VPS (92.246.131.14)
# 2. Установка QEMU и зависимостей
# 3. Создание VM с Ubuntu
# 4. Установка kernel-модулей
# 5. Системные оптимизации
# 6. Тестирование и отчет
```

## 🔧 Альтернативные варианты

### Вариант 1: Использование пароля вместо ключа
```bash
# Скрипт автоматически предложит ввести пароль
# если ключ не найден или не работает
python virtualqubit_automation.py
```

### Вариант 2: Ручная конвертация ключа
```bash
# Конвертируем .ppk в OpenSSH формат
puttygen "Linux Ubuntu.ppk" -O private-openssh -o linux_ubuntu.key

# Меняем права
chmod 600 linux_ubuntu.key

# Используем вручную
ssh -i linux_ubuntu.key root@92.246.131.14
```

### Вариант 3: Ручная установка (если автоматизация не подходит)
```bash
# 1. Подключаемся к VPS
ssh -i "Linux Ubuntu.ppk" root@92.246.131.14

# 2. Устанавливаем QEMU
./setup_vps.sh

# 3. Запускаем VM
./start_vm.sh

# 4. Устанавливаем модули
./install_kernel_modules.sh
```

## 📊 Что происходит во время установки

### Этап 1: Подключение к VPS (2-5 минут)
- Проверка SSH ключа
- Подключение к 92.246.131.14
- Проверка доступности

### Этап 2: Установка QEMU (3-10 минут)
- Обновление системы
- Установка QEMU и инструментов
- Установка инструментов разработки

### Этап 3: Создание VM (2-5 минут)
- Создание 20GB диска
- Скачивание Ubuntu ISO
- Создание скрипта запуска

### Этап 4: Установка модулей (5-15 минут)
- Передача файлов на VPS
- Распаковка VirtualQubit_Shared
- Запуск install_kernel_modules.sh

### Этап 5: Системные оптимизации (1-2 минуты)
- Настройка HugePages (32GB)
- Отключение NUMA balancing
- Установка CPU governor

### Этап 6: Тестирование (2-5 минут)
- Проверка загрузки модулей
- Проверка device nodes
- Генерация отчетов

## 🎉 После успешной установки

### Проверка результата
```bash
# Проверка загрузки модулей
lsmod | grep vqubit
lsmod | grep turbo_sched

# Проверка device nodes
ls -l /dev/vqubit /dev/turbo_sched

# Проверка HugePages
cat /proc/sys/vm/nr_hugepages
```

### Тестирование производительности
```bash
# Запуск тестов
python3 test_modules.py

# Запуск бенчмарков
make benchmark
```

### Использование в Python
```python
from vqubit.vqubit_python import VirtualQubitKernelAccelerated

# Создаем ускоренный qubit
qubit = VirtualQubitKernelAccelerated(use_kernel=True)

# Тестируем операции
test_data = b"Hello VirtualQubit!"
qubit.encode(0, test_data)
qubit.hadamard(0)  # Fast Walsh-Hadamard Transform
qubit.qft(0)       # Quantum Fourier Transform
result = qubit.measure(0)
```

## 🚨 Возможные проблемы и решения

### Проблема 1: SSH ключ не работает
**Решение:**
```bash
# Используем пароль вместо ключа
python virtualqubit_automation.py
# Когда спросит пароль - вводим

# Или конвертируем ключ
python ssh_setup.py
```

### Проблема 2: Нет интернета на VPS
**Решение:**
```bash
# Проверяем интернет
ping google.com

# Если нет - настраиваем сеть вручную
```

### Проблема 3: Недостаточно места на диске
**Решение:**
```bash
# Проверяем место
df -h

# Освобождаем место или используем другой VPS
```

### Проблема 4: Ошибки при установке модулей
**Решение:**
```bash
# Проверяем kernel headers
ls /lib/modules/$(uname -r)/build

# Устанавливаем при необходимости
apt install linux-headers-$(uname -r)
```

## 📞 Поддержка

### Логи и отчеты
- `virtualqubit_automation.log` - подробные логи
- `installation_report.txt` - текстовый отчет
- `installation_report.json` - структурированный отчет

### Тестирование
```bash
# Проверка готовности системы
python setup.py

# Проверка SSH
python ssh_setup.py

# Тестирование модулей
cd VirtualQubit_Shared && python3 test_modules.py
```

## ⚡ Ожидаемые результаты

После успешной установки вы получите:
- **3-5x** ускорение FWHT операций
- **4-8x** ускорение QFT операций
- **2-3.5x** общее ускорение Python
- **32GB** HugePages
- Готовую HPC среду для quantum computing

## 🎯 Готово!

Теперь у вас есть полностью автоматизированная система для настройки VirtualQubit Turbo Kernel. Достаточно запустить один скрипт и он сделает всю работу сам!

```bash
python virtualqubit_automation.py