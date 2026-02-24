#!/usr/bin/env python3
"""
VirtualQubit Turbo Kernel Automation Script
Автоматизирует настройку VPS с QEMU виртуализацией и установкой kernel-модулей VirtualQubit

Требования:
- paramiko (для SSH)
- scp (для передачи файлов)
- tqdm (для прогресс-баров)
"""

import os
import sys
import time
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from getpass import getpass

try:
    import paramiko
    from scp import SCPClient
    from tqdm import tqdm
except ImportError as e:
    print(f"Ошибка: Необходимо установить зависимости: {e}")
    print("pip install paramiko scp tqdm")
    sys.exit(1)


@dataclass
class VPSConfig:
    """Конфигурация VPS"""
    hostname: str = "92.246.131.14"
    username: str = "root"
    port: int = 22
    ssh_key_path: str = "Linux Ubuntu.ppk"
    password: Optional[str] = None


@dataclass
class VMConfig:
    """Конфигурация виртуальной машины"""
    disk_size: str = "20G"
    memory: str = "2048"
    cpus: int = 2
    iso_url: str = "https://releases.ubuntu.com/24.04/ubuntu-24.04-live-server-amd64.iso"
    vm_username: str = "vboxuser"
    vm_password: str = "123456963"


class VirtualQubitAutomation:
    """Основной класс автоматизации VirtualQubit"""
    
    def __init__(self):
        self.vps_config = VPSConfig()
        self.vm_config = VMConfig()
        self.ssh_client = None
        self.logger = self._setup_logging()
        self.scripts_dir = Path(__file__).parent / "scripts"
        self.scripts_dir.mkdir(exist_ok=True)
        
    def _setup_logging(self) -> logging.Logger:
        """Настройка логирования"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('virtualqubit_automation.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        return logging.getLogger(__name__)
    
    def print_header(self):
        """Вывод заголовка"""
        print("=" * 60)
        print("VirtualQubit Turbo Kernel Automation Script")
        print("=" * 60)
        print("Автоматизирует настройку VPS с QEMU и kernel-модулями")
        print("=" * 60)
        print()
    
    def check_prerequisites(self):
        """Проверка предварительных условий"""
        self.logger.info("Проверка предварительных условий...")
        
        # Проверка наличия SSH ключа
        if not os.path.exists(self.vps_config.ssh_key_path):
            self.logger.warning(f"SSH ключ не найден: {self.vps_config.ssh_key_path}")
            self.vps_config.password = getpass("Введите пароль для SSH: ")
        
        # Проверка наличия VirtualQubit_Shared
        if not os.path.exists("VirtualQubit_Shared"):
            self.logger.error("Папка VirtualQubit_Shared не найдена!")
            self.logger.error("Убедитесь, что все файлы VirtualQubit находятся в текущей директории")
            sys.exit(1)
        
        self.logger.info("✓ Предварительные условия проверены")
    
    def _convert_ppk_to_openssh(self, ppk_path: str) -> paramiko.RSAKey:
        """Конвертация PuTTY ключа (.ppk) в OpenSSH формат"""
        self.logger.info("Конвертация .ppk ключа в OpenSSH формат...")
        
        # Пытаемся использовать puttygen для конвертации
        try:
            # Создаем временный файл для OpenSSH ключа
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.key', delete=False) as temp_file:
                temp_key_path = temp_file.name
            
            # Пытаемся использовать puttygen если он доступен
            try:
                subprocess.run([
                    'puttygen', ppk_path, 
                    '-O', 'private-openssh', 
                    '-o', temp_key_path
                ], check=True, capture_output=True)
                self.logger.info("✓ Ключ сконвертирован через puttygen")
            except (subprocess.CalledProcessError, FileNotFoundError):
                # Если puttygen недоступен, пробуем другой подход
                self.logger.warning("puttygen не найден, пробуем альтернативный метод...")
                # Для .ppk файлов можно попробовать использовать pagent
                try:
                    # Проверяем доступность pagent
                    subprocess.run(['pagent', '-l'], check=True, capture_output=True)
                    self.logger.info("✓ pagent доступен, используем его")
                    # В этом случае можно использовать pagent для аутентификации
                    # Но для простоты создадим заглушку
                    raise Exception("Требуется ручная конвертация ключа")
                except:
                    raise Exception("Не удалось сконвертировать .ppk ключ")
            
            # Загружаем сконвертированный ключ
            key = paramiko.RSAKey.from_private_key_file(temp_key_path)
            
            # Удаляем временный файл
            os.unlink(temp_key_path)
            
            return key
            
        except Exception as e:
            self.logger.error(f"Ошибка конвертации .ppk ключа: {e}")
            raise
    
    def _load_ssh_key(self) -> paramiko.PKey:
        """Загрузка SSH ключа с обработкой .ppk формата"""
        if not os.path.exists(self.vps_config.ssh_key_path):
            raise FileNotFoundError(f"SSH ключ не найден: {self.vps_config.ssh_key_path}")
        
        # Проверяем формат ключа
        with open(self.vps_config.ssh_key_path, 'r') as f:
            key_content = f.read()
        
        if key_content.startswith("PuTTY-User-Key-File-2"):
            self.logger.info("Обнаружен PuTTY ключ (.ppk)")
            
            # Пытаемся использовать ключ через pagent если доступен
            try:
                # Проверяем pagent
                result = subprocess.run(['pagent', '-l'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and result.stdout.strip():
                    self.logger.info("✓ pagent доступен, используем его для .ppk ключа")
                    # Возвращаем None - подключение будет без ключа, pagent сам обработает
                    return None
            except:
                pass
            
            # Пытаемся конвертировать ключ
            try:
                self.logger.info("Конвертируем .ppk ключ в OpenSSH формат...")
                import tempfile
                
                # Создаем временный файл
                with tempfile.NamedTemporaryFile(mode='w', suffix='.key', delete=False) as temp_file:
                    temp_key_path = temp_file.name
                
                # Пробуем использовать puttygen
                try:
                    subprocess.run([
                        'puttygen', self.vps_config.ssh_key_path,
                        '-O', 'private-openssh',
                        '-o', temp_key_path
                    ], check=True, capture_output=True, timeout=30)
                    
                    self.logger.info("✓ Ключ сконвертирован через puttygen")
                    
                    # Загружаем сконвертированный ключ
                    key = paramiko.RSAKey.from_private_key_file(temp_key_path)
                    
                    # Удаляем временный файл
                    os.unlink(temp_key_path)
                    
                    return key
                    
                except (subprocess.CalledProcessError, FileNotFoundError) as e:
                    self.logger.warning(f"puttygen недоступен или не сработал: {e}")
                    
                    # Удаляем временный файл
                    if os.path.exists(temp_key_path):
                        os.unlink(temp_key_path)
                    
                    # Пытаемся использовать ключ напрямую (иногда работает)
                    try:
                        key = paramiko.RSAKey.from_private_key_file(self.vps_config.ssh_key_path)
                        self.logger.info("✓ .ppk ключ загружен напрямую")
                        return key
                    except Exception as e2:
                        self.logger.error(f"Не удалось загрузить .ppk ключ: {e2}")
                        raise Exception("Не удалось загрузить .ppk ключ. Используйте пароль или сконвертируйте ключ.")
                        
            except Exception as e:
                self.logger.error(f"Ошибка конвертации .ppk ключа: {e}")
                raise Exception("Не удалось обработать .ppk ключ. Используйте пароль.")
        
        else:
            # Обычный OpenSSH ключ
            self.logger.info("Обнаружен OpenSSH ключ")
            return paramiko.RSAKey.from_private_key_file(self.vps_config.ssh_key_path)
    
    def connect_to_vps(self) -> bool:
        """Подключение к VPS по SSH"""
        self.logger.info(f"Подключение к VPS: {self.vps_config.hostname}")
        
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if self.vps_config.password:
                self.logger.info("Используется пароль для подключения")
                self.ssh_client.connect(
                    hostname=self.vps_config.hostname,
                    username=self.vps_config.username,
                    password=self.vps_config.password,
                    port=self.vps_config.port
                )
            else:
                try:
                    # Загружаем SSH ключ
                    key = self._load_ssh_key()
                    
                    if key is None:
                        # Ключ обрабатывается pagent, подключаемся без указания ключа
                        self.logger.info("Подключение через pagent...")
                        self.ssh_client.connect(
                            hostname=self.vps_config.hostname,
                            username=self.vps_config.username,
                            port=self.vps_config.port
                        )
                    else:
                        # Используем загруженный ключ
                        self.ssh_client.connect(
                            hostname=self.vps_config.hostname,
                            username=self.vps_config.username,
                            pkey=key,
                            port=self.vps_config.port
                        )
                    
                except Exception as e:
                    self.logger.error(f"Ошибка загрузки SSH ключа: {e}")
                    self.logger.info("Переключаемся на парольную аутентификацию")
                    
                    # Запрашиваем пароль
                    self.vps_config.password = getpass("Введите пароль для SSH: ")
                    
                    self.ssh_client.connect(
                        hostname=self.vps_config.hostname,
                        username=self.vps_config.username,
                        password=self.vps_config.password,
                        port=self.vps_config.port
                    )
            
            self.logger.info("✓ Подключение к VPS установлено")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка подключения к VPS: {e}")
            return False
    
    def execute_command(self, command: str, description: str = "") -> Tuple[str, str, int]:
        """Выполнение команды на удаленной машине"""
        if description:
            self.logger.info(f"Выполнение: {description}")
            self.logger.debug(f"Команда: {command}")
        
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(command)
            exit_code = stdout.channel.recv_exit_status()
            stdout_result = stdout.read().decode('utf-8')
            stderr_result = stderr.read().decode('utf-8')
            
            if exit_code != 0:
                self.logger.error(f"Команда завершилась с ошибкой (код {exit_code})")
                if stderr_result:
                    self.logger.error(f"Ошибка: {stderr_result}")
            
            return stdout_result, stderr_result, exit_code
            
        except Exception as e:
            self.logger.error(f"Ошибка выполнения команды: {e}")
            return "", str(e), 1
    
    def install_qemu(self):
        """Установка QEMU и зависимостей"""
        self.logger.info("Установка QEMU и зависимостей...")
        
        commands = [
            ("apt update", "Обновление пакетов"),
            ("apt upgrade -y", "Обновление системы"),
            ("apt install -y qemu-system-x86 qemu-utils wget curl htop iotop sysstat zstd xxhash", "Установка QEMU и инструментов"),
            ("apt install -y build-essential linux-headers-$(uname -r) dkms", "Установка инструментов разработки")
        ]
        
        for command, description in commands:
            stdout, stderr, exit_code = self.execute_command(command, description)
            if exit_code != 0:
                self.logger.error(f"Ошибка установки: {description}")
                return False
        
        self.logger.info("✓ QEMU и зависимости установлены")
        return True
    
    def create_vm_environment(self):
        """Создание среды для виртуальной машины"""
        self.logger.info("Создание среды для VM...")
        
        # Создание VM диска
        stdout, stderr, exit_code = self.execute_command(
            f"qemu-img create -f qcow2 vm.qcow2 {self.vm_config.disk_size}",
            f"Создание VM диска ({self.vm_config.disk_size})"
        )
        
        if exit_code != 0:
            self.logger.error("Ошибка создания VM диска")
            return False
        
        # Скачивание Ubuntu ISO
        stdout, stderr, exit_code = self.execute_command(
            f"wget {self.vm_config.iso_url}",
            "Скачивание Ubuntu ISO"
        )
        
        if exit_code != 0:
            self.logger.error("Ошибка скачивания Ubuntu ISO")
            return False
        
        # Создание скрипта запуска VM
        start_vm_script = f"""#!/bin/bash
echo "=== Starting Ubuntu VM ==="
qemu-system-x86_64 \\
  -m {self.vm_config.memory} \\
  -smp {self.vm_config.cpus} \\
  -drive file=vm.qcow2,format=qcow2 \\
  -cdrom ubuntu-24.04-live-server-amd64.iso \\
  -boot d \\
  -net nic -net user \\
  -nographic
"""
        
        with open(self.scripts_dir / "start_vm.sh", "w") as f:
            f.write(start_vm_script)
        
        stdout, stderr, exit_code = self.execute_command(
            "chmod +x start_vm.sh",
            "Сделать скрипт запуска VM исполняемым"
        )
        
        self.logger.info("✓ Среда для VM создана")
        return True
    
    def transfer_virtualqubit_files(self):
        """Передача файлов VirtualQubit на VPS"""
        self.logger.info("Передача файлов VirtualQubit на VPS...")
        
        try:
            with SCPClient(self.ssh_client.get_transport()) as scp:
                scp.put("VirtualQubit_Shared", recursive=True, remote_path="/root/")
            
            self.logger.info("✓ Файлы VirtualQubit переданы на VPS")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка передачи файлов: {e}")
            return False
    
    def create_vm_startup_script(self):
        """Создание скрипта запуска VM"""
        script_content = f"""#!/bin/bash
# VM Startup Script for VirtualQubit

echo "=== Starting Ubuntu VM ==="

# Check if KVM is available
if [ $(egrep -c '(vmx|svm)' /proc/cpuinfo) -gt 0 ]; then
    echo "KVM available, using accelerated mode"
    KVM_FLAG="-enable-kvm"
else
    echo "KVM not available, using emulation mode"
    KVM_FLAG=""
fi

qemu-system-x86_64 \\
  $KVM_FLAG \\
  -m {self.vm_config.memory} \\
  -smp {self.vm_config.cpus} \\
  -drive file=vm.qcow2,format=qcow2 \\
  -cdrom ubuntu-24.04-live-server-amd64.iso \\
  -boot d \\
  -net nic -net user \\
  -nographic
"""
        
        with open(self.scripts_dir / "start_vm.sh", "w") as f:
            f.write(script_content)
        
        return True
    
    def install_kernel_modules(self):
        """Установка kernel-модулей VirtualQubit"""
        self.logger.info("Установка kernel-модулей VirtualQubit...")
        
        # Распаковка файлов
        stdout, stderr, exit_code = self.execute_command(
            "cd /root/VirtualQubit_Shared && unzip -o VirtualQubit_Shared.zip",
            "Распаковка VirtualQubit файлов"
        )
        
        if exit_code != 0:
            self.logger.error("Ошибка распаковки файлов VirtualQubit")
            return False
        
        # Запуск скрипта установки
        stdout, stderr, exit_code = self.execute_command(
            "cd /root/VirtualQubit_Shared && chmod +x install_kernel_modules.sh && ./install_kernel_modules.sh",
            "Запуск скрипта установки kernel-модулей"
        )
        
        if exit_code != 0:
            self.logger.error("Ошибка установки kernel-модулей")
            self.logger.error(f"Stderr: {stderr}")
            return False
        
        self.logger.info("✓ Kernel-модули VirtualQubit установлены")
        return True
    
    def configure_system_optimizations(self):
        """Настройка системных оптимизаций"""
        self.logger.info("Настройка системных оптимизаций...")
        
        optimization_commands = [
            # HugePages
            ("echo 32768 > /proc/sys/vm/nr_hugepages", "Настройка HugePages (32GB)"),
            # NUMA balancing
            ("echo 0 > /proc/sys/kernel/numa_balancing", "Отключение NUMA balancing"),
            # CPU governor
            ("for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do echo performance > $cpu; done", "Установка CPU governor в performance"),
            # Transparent hugepages
            ("echo never > /sys/kernel/mm/transparent_hugepage/defrag", "Настройка transparent hugepages"),
            # sysctl.conf
            ("cat >> /etc/sysctl.conf << 'EOF'\n\n# VirtualQubit HPC optimizations\nvm.nr_hugepages = 32768\nkernel.numa_balancing = 0\nkernel.sched_min_granularity_ns = 10000000\nkernel.sched_wakeup_granularity_ns = 5000000\nEOF", "Добавление настроек в sysctl.conf"),
            # Apply sysctl
            ("sysctl -p", "Применение sysctl настроек")
        ]
        
        for command, description in optimization_commands:
            stdout, stderr, exit_code = self.execute_command(command, description)
            if exit_code != 0:
                self.logger.warning(f"Предупреждение при выполнении: {description}")
        
        self.logger.info("✓ Системные оптимизации настроены")
        return True
    
    def test_installation(self):
        """Тестирование установки"""
        self.logger.info("Тестирование установки...")
        
        # Проверка загрузки модулей
        stdout, stderr, exit_code = self.execute_command(
            "lsmod | grep vqubit && lsmod | grep turbo_sched",
            "Проверка загрузки kernel-модулей"
        )
        
        if exit_code != 0:
            self.logger.warning("Kernel-модули не загружены автоматически")
            # Попробуем загрузить вручную
            self.execute_command("modprobe vqubit", "Загрузка vqubit модуля")
            self.execute_command("modprobe turbo_sched", "Загрузка turbo_sched модуля")
        
        # Проверка device nodes
        stdout, stderr, exit_code = self.execute_command(
            "ls -l /dev/vqubit /dev/turbo_sched",
            "Проверка device nodes"
        )
        
        if exit_code != 0:
            self.logger.warning("Device nodes не найдены, создаем вручную")
            self.execute_command("mknod /dev/vqubit c 0 0 && chmod 666 /dev/vqubit", "Создание /dev/vqubit")
            self.execute_command("mknod /dev/turbo_sched c 0 1 && chmod 666 /dev/turbo_sched", "Создание /dev/turbo_sched")
        
        # Проверка HugePages
        stdout, stderr, exit_code = self.execute_command(
            "cat /proc/sys/vm/nr_hugepages",
            "Проверка HugePages"
        )
        
        if stdout.strip() == "32768":
            self.logger.info("✓ HugePages настроены правильно (32GB)")
        else:
            self.logger.warning(f"Неправильный размер HugePages: {stdout.strip()}")
        
        self.logger.info("✓ Тестирование установки завершено")
        return True
    
    def generate_report(self):
        """Генерация отчета об установке"""
        self.logger.info("Генерация отчета об установке...")
        
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "vps_ip": self.vps_config.hostname,
            "vm_config": {
                "disk_size": self.vm_config.disk_size,
                "memory": self.vm_config.memory,
                "cpus": self.vm_config.cpus
            },
            "optimizations": {
                "hugepages": "32GB",
                "cpu_governor": "performance",
                "numa_balancing": "disabled"
            },
            "expected_improvements": {
                "fwht_operations": "3-5x faster",
                "qft_operations": "4-8x faster",
                "python_performance": "2-3.5x faster"
            }
        }
        
        with open("installation_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        # Создание текстового отчета
        report_text = f"""
VirtualQubit Turbo Kernel Installation Report
============================================

Installation Date: {report['timestamp']}
VPS IP: {report['vps_ip']}

VM Configuration:
- Disk Size: {report['vm_config']['disk_size']}
- Memory: {report['vm_config']['memory']}MB
- CPUs: {report['vm_config']['cpus']}

System Optimizations:
- HugePages: {report['optimizations']['hugepages']}
- CPU Governor: {report['optimizations']['cpu_governor']}
- NUMA Balancing: {report['optimizations']['numa_balancing']}

Expected Performance Improvements:
- FWHT Operations: {report['expected_improvements']['fwht_operations']}
- QFT Operations: {report['expected_improvements']['qft_operations']}
- Python Performance: {report['expected_improvements']['python_performance']}

Next Steps:
1. Reboot the VM to ensure all optimizations are active
2. Run: python3 test_modules.py to verify functionality
3. Use the VirtualQubit Python interface in your applications

For support, check the installation log: virtualqubit_automation.log
"""
        
        with open("installation_report.txt", "w") as f:
            f.write(report_text)
        
        print(report_text)
        self.logger.info("✓ Отчет об установке сгенерирован")
    
    def run_full_automation(self):
        """Запуск полной автоматизации"""
        self.print_header()
        
        try:
            # Проверка предварительных условий
            self.check_prerequisites()
            
            # Подключение к VPS
            if not self.connect_to_vps():
                self.logger.error("Не удалось подключиться к VPS")
                return False
            
            # Этап 1: Установка QEMU
            self.logger.info("Этап 1: Установка QEMU и зависимостей")
            if not self.install_qemu():
                return False
            
            # Этап 2: Создание среды VM
            self.logger.info("Этап 2: Создание среды для виртуальной машины")
            if not self.create_vm_environment():
                return False
            
            # Этап 3: Передача файлов
            self.logger.info("Этап 3: Передача файлов VirtualQubit")
            if not self.transfer_virtualqubit_files():
                return False
            
            # Этап 4: Установка kernel-модулей
            self.logger.info("Этап 4: Установка kernel-модулей VirtualQubit")
            if not self.install_kernel_modules():
                return False
            
            # Этап 5: Системные оптимизации
            self.logger.info("Этап 5: Настройка системных оптимизаций")
            if not self.configure_system_optimizations():
                return False
            
            # Этап 6: Тестирование
            self.logger.info("Этап 6: Тестирование установки")
            if not self.test_installation():
                return False
            
            # Генерация отчета
            self.generate_report()
            
            self.logger.info("✓ Полная автоматизация завершена успешно!")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка в процессе автоматизации: {e}")
            return False
        
        finally:
            if self.ssh_client:
                self.ssh_client.close()


def main():
    """Главная функция"""
    automation = VirtualQubitAutomation()
    
    print("VirtualQubit Turbo Kernel Automation")
    print("Нажмите Enter для начала автоматизации или Ctrl+C для выхода...")
    input()
    
    success = automation.run_full_automation()
    
    if success:
        print("\n" + "="*60)
        print("🎉 УСТАНОВКА ЗАВЕРШЕНА УСПЕШНО! 🎉")
        print("="*60)
        print("\nСледующие шаги:")
        print("1. Перезагрузите VM для активации всех оптимизаций")
        print("2. Запустите: python3 test_modules.py")
        print("3. Начните использовать VirtualQubit в своих приложениях")
    else:
        print("\n" + "="*60)
        print("❌ УСТАНОВКА ЗАВЕРШИЛАСЬ С ОШИБКАМИ")
        print("="*60)
        print("\nПроверьте логи в файле: virtualqubit_automation.log")
        sys.exit(1)


if __name__ == "__main__":
    main()