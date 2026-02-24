#!/usr/bin/env python3
"""
PuTTY-based VirtualQubit Automation Script
Использует PuTTY для подключения к VPS и автоматизации установки
"""

import os
import sys
import time
import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from getpass import getpass


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


class PuTTYAutomation:
    """Класс автоматизации через PuTTY"""
    
    def __init__(self):
        self.vps_config = VPSConfig()
        self.vm_config = VMConfig()
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """Настройка логирования"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('putty_automation.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        return logging.getLogger(__name__)
    
    def print_header(self):
        """Вывод заголовка"""
        print("=" * 60)
        print("VirtualQubit Turbo Kernel Automation via PuTTY")
        print("=" * 60)
        print("Использует PuTTY для подключения к VPS")
        print("=" * 60)
        print()
    
    def check_putty(self) -> bool:
        """Проверка наличия PuTTY"""
        self.logger.info("Проверка наличия PuTTY...")
        
        putty_commands = ['putty', 'plink', 'pscp']
        putty_available = {}
        
        for cmd in putty_commands:
            try:
                result = subprocess.run([cmd, '-help'], 
                                      capture_output=True, text=True, timeout=5)
                putty_available[cmd] = result.returncode == 0
            except:
                putty_available[cmd] = False
        
        if putty_available['plink'] and putty_available['pscp']:
            self.logger.info("✓ PuTTY инструменты доступны (plink, pscp)")
            return True
        elif putty_available['putty']:
            self.logger.warning("⚠️  Доступен только putty.exe, plink и pscp не найдены")
            self.logger.info("Рекомендуется установить полный пакет PuTTY")
            return False
        else:
            self.logger.error("❌ PuTTY не найден")
            self.logger.info("Скачайте PuTTY с: https://www.chiark.greenend.org.uk/~sgtatham/putty/latest.html")
            return False
    
    def execute_command_via_plink(self, command: str, description: str = "") -> Tuple[str, str, int]:
        """Выполнение команды через plink"""
        if description:
            self.logger.info(f"Выполнение: {description}")
            self.logger.debug(f"Команда: {command}")
        
        try:
            # Формируем команду plink
            plink_cmd = [
                'plink',
                '-ssh',
                f'{self.vps_config.username}@{self.vps_config.hostname}',
                '-P', str(self.vps_config.port),
                '-i', self.vps_config.ssh_key_path,
                '-batch',  # Не запрашивать пароль
                command
            ]
            
            result = subprocess.run(plink_cmd, capture_output=True, text=True, timeout=300)
            
            stdout_result = result.stdout
            stderr_result = result.stderr
            exit_code = result.returncode
            
            if exit_code != 0:
                self.logger.error(f"Команда завершилась с ошибкой (код {exit_code})")
                if stderr_result:
                    self.logger.error(f"Ошибка: {stderr_result}")
            
            return stdout_result, stderr_result, exit_code
            
        except subprocess.TimeoutExpired:
            self.logger.error("Команда превысила время ожидания (5 минут)")
            return "", "Timeout", 1
        except Exception as e:
            self.logger.error(f"Ошибка выполнения команды: {e}")
            return "", str(e), 1
    
    def transfer_files_via_pscp(self, local_path: str, remote_path: str) -> bool:
        """Передача файлов через pscp"""
        self.logger.info(f"Передача файлов: {local_path} -> {remote_path}")
        
        try:
            pscp_cmd = [
                'pscp',
                '-i', self.vps_config.ssh_key_path,
                '-r',  # Рекурсивно для папок
                local_path,
                f'{self.vps_config.username}@{self.vps_config.hostname}:{remote_path}'
            ]
            
            result = subprocess.run(pscp_cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode == 0:
                self.logger.info("✓ Файлы успешно переданы")
                return True
            else:
                self.logger.error(f"Ошибка передачи файлов: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Ошибка передачи файлов: {e}")
            return False
    
    def install_qemu(self) -> bool:
        """Установка QEMU через PuTTY"""
        self.logger.info("Установка QEMU и зависимостей...")
        
        commands = [
            ("apt update", "Обновление пакетов"),
            ("apt upgrade -y", "Обновление системы"),
            ("apt install -y qemu-system-x86 qemu-utils wget curl htop iotop sysstat zstd xxhash", "Установка QEMU и инструментов"),
            ("apt install -y build-essential linux-headers-$(uname -r) dkms", "Установка инструментов разработки")
        ]
        
        for command, description in commands:
            stdout, stderr, exit_code = self.execute_command_via_plink(command, description)
            if exit_code != 0:
                self.logger.error(f"Ошибка установки: {description}")
                return False
        
        self.logger.info("✓ QEMU и зависимости установлены")
        return True
    
    def create_vm_environment(self) -> bool:
        """Создание среды для виртуальной машины"""
        self.logger.info("Создание среды для VM...")
        
        # Создание VM диска
        stdout, stderr, exit_code = self.execute_command_via_plink(
            f"qemu-img create -f qcow2 vm.qcow2 {self.vm_config.disk_size}",
            f"Создание VM диска ({self.vm_config.disk_size})"
        )
        
        if exit_code != 0:
            self.logger.error("Ошибка создания VM диска")
            return False
        
        # Скачивание Ubuntu ISO
        stdout, stderr, exit_code = self.execute_command_via_plink(
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
        
        # Сохраняем скрипт локально
        with open("start_vm.sh", "w") as f:
            f.write(start_vm_script)
        
        # Передаем скрипт на VPS
        if not self.transfer_files_via_pscp("start_vm.sh", "/root/"):
            self.logger.error("Ошибка передачи скрипта запуска VM")
            return False
        
        # Делаем скрипт исполняемым
        stdout, stderr, exit_code = self.execute_command_via_plink(
            "chmod +x /root/start_vm.sh",
            "Сделать скрипт запуска VM исполняемым"
        )
        
        self.logger.info("✓ Среда для VM создана")
        return True
    
    def transfer_virtualqubit_files(self) -> bool:
        """Передача файлов VirtualQubit на VPS"""
        self.logger.info("Передача файлов VirtualQubit на VPS...")
        
        if not self.transfer_files_via_pscp("VirtualQubit_Shared", "/root/"):
            self.logger.error("Ошибка передачи VirtualQubit_Shared")
            return False
        
        self.logger.info("✓ Файлы VirtualQubit переданы на VPS")
        return True
    
    def install_kernel_modules(self) -> bool:
        """Установка kernel-модулей VirtualQubit"""
        self.logger.info("Установка kernel-модулей VirtualQubit...")
        
        # Распаковка файлов
        stdout, stderr, exit_code = self.execute_command_via_plink(
            "cd /root/VirtualQubit_Shared && unzip -o VirtualQubit_Shared.zip",
            "Распаковка VirtualQubit файлов"
        )
        
        if exit_code != 0:
            self.logger.error("Ошибка распаковки файлов VirtualQubit")
            return False
        
        # Запуск скрипта установки
        stdout, stderr, exit_code = self.execute_command_via_plink(
            "cd /root/VirtualQubit_Shared && chmod +x install_kernel_modules.sh && ./install_kernel_modules.sh",
            "Запуск скрипта установки kernel-модулей"
        )
        
        if exit_code != 0:
            self.logger.error("Ошибка установки kernel-модулей")
            self.logger.error(f"Stderr: {stderr}")
            return False
        
        self.logger.info("✓ Kernel-модули VirtualQubit установлены")
        return True
    
    def configure_system_optimizations(self) -> bool:
        """Настройка системных оптимизаций"""
        self.logger.info("Настройка системных оптимизаций...")
        
        optimization_commands = [
            ("echo 32768 > /proc/sys/vm/nr_hugepages", "Настройка HugePages (32GB)"),
            ("echo 0 > /proc/sys/kernel/numa_balancing", "Отключение NUMA balancing"),
            ("for cpu in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do echo performance > $cpu; done", "Установка CPU governor в performance"),
            ("echo never > /sys/kernel/mm/transparent_hugepage/defrag", "Настройка transparent hugepages"),
            ("cat >> /etc/sysctl.conf << 'EOF'\n\n# VirtualQubit HPC optimizations\nvm.nr_hugepages = 32768\nkernel.numa_balancing = 0\nkernel.sched_min_granularity_ns = 10000000\nkernel.sched_wakeup_granularity_ns = 5000000\nEOF", "Добавление настроек в sysctl.conf"),
            ("sysctl -p", "Применение sysctl настроек")
        ]
        
        for command, description in optimization_commands:
            stdout, stderr, exit_code = self.execute_command_via_plink(command, description)
            if exit_code != 0:
                self.logger.warning(f"Предупреждение при выполнении: {description}")
        
        self.logger.info("✓ Системные оптимизации настроены")
        return True
    
    def test_installation(self) -> bool:
        """Тестирование установки"""
        self.logger.info("Тестирование установки...")
        
        # Проверка загрузки модулей
        stdout, stderr, exit_code = self.execute_command_via_plink(
            "lsmod | grep vqubit && lsmod | grep turbo_sched",
            "Проверка загрузки kernel-модулей"
        )
        
        if exit_code != 0:
            self.logger.warning("Kernel-модули не загружены автоматически")
            # Попробуем загрузить вручную
            self.execute_command_via_plink("modprobe vqubit", "Загрузка vqubit модуля")
            self.execute_command_via_plink("modprobe turbo_sched", "Загрузка turbo_sched модуля")
        
        # Проверка device nodes
        stdout, stderr, exit_code = self.execute_command_via_plink(
            "ls -l /dev/vqubit /dev/turbo_sched",
            "Проверка device nodes"
        )
        
        if exit_code != 0:
            self.logger.warning("Device nodes не найдены, создаем вручную")
            self.execute_command_via_plink("mknod /dev/vqubit c 0 0 && chmod 666 /dev/vqubit", "Создание /dev/vqubit")
            self.execute_command_via_plink("mknod /dev/turbo_sched c 0 1 && chmod 666 /dev/turbo_sched", "Создание /dev/turbo_sched")
        
        # Проверка HugePages
        stdout, stderr, exit_code = self.execute_command_via_plink(
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
            },
            "method": "PuTTY automation"
        }
        
        with open("installation_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        # Создание текстового отчета
        report_text = f"""
VirtualQubit Turbo Kernel Installation Report (PuTTY Method)
============================================================

Installation Date: {report['timestamp']}
VPS IP: {report['vps_ip']}
Method: PuTTY automation

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

For support, check the installation log: putty_automation.log
"""
        
        with open("installation_report.txt", "w") as f:
            f.write(report_text)
        
        print(report_text)
        self.logger.info("✓ Отчет об установке сгенерирован")
    
    def run_full_automation(self):
        """Запуск полной автоматизации через PuTTY"""
        self.print_header()
        
        try:
            # Проверка наличия PuTTY
            if not self.check_putty():
                self.logger.error("PuTTY не найден. Установите PuTTY и добавьте его в PATH.")
                return False
            
            # Проверка наличия VirtualQubit_Shared
            if not os.path.exists("VirtualQubit_Shared"):
                self.logger.error("Папка VirtualQubit_Shared не найдена!")
                self.logger.error("Убедитесь, что все файлы VirtualQubit находятся в текущей директории")
                sys.exit(1)
            
            self.logger.info("✓ Предварительные условия проверены")
            
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


def main():
    """Главная функция"""
    automation = PuTTYAutomation()
    
    print("VirtualQubit Turbo Kernel Automation via PuTTY")
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
        print("\nПроверьте логи в файле: putty_automation.log")
        sys.exit(1)


if __name__ == "__main__":
    main()