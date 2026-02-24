#!/usr/bin/env python3
"""
Setup script for VirtualQubit Automation
Проверяет и устанавливает зависимости, проверяет готовность системы
"""

import os
import sys
import subprocess
import importlib.util
from pathlib import Path


def check_python_version():
    """Проверка версии Python"""
    print("Проверка версии Python...")
    if sys.version_info < (3, 8):
        print("❌ Требуется Python 3.8 или выше")
        print(f"Текущая версия: {sys.version}")
        return False
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    return True


def check_required_files():
    """Проверка наличия необходимых файлов"""
    print("Проверка наличия необходимых файлов...")
    
    required_files = [
        "VirtualQubit_Shared",
        "virtualqubit_automation.py",
        "requirements.txt",
        "README.md"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print("❌ Не найдены следующие файлы:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        return False
    
    print("✓ Все необходимые файлы найдены")
    return True


def check_ssh_key():
    """Проверка наличия SSH ключа"""
    print("Проверка SSH ключа...")
    
    ssh_key = "Linux Ubuntu.ppk"
    if Path(ssh_key).exists():
        print(f"✓ SSH ключ найден: {ssh_key}")
        return True
    else:
        print(f"⚠️  SSH ключ не найден: {ssh_key}")
        print("   Скрипт будет запрашивать пароль при подключении")
        return False


def check_python_dependencies():
    """Проверка Python зависимостей"""
    print("Проверка Python зависимостей...")
    
    required_packages = ["paramiko", "scp", "tqdm"]
    missing_packages = []
    
    for package in required_packages:
        spec = importlib.util.find_spec(package)
        if spec is None:
            missing_packages.append(package)
        else:
            print(f"✓ {package} - установлен")
    
    if missing_packages:
        print("❌ Не установлены следующие пакеты:")
        for package in missing_packages:
            print(f"   - {package}")
        return False
    
    return True


def install_dependencies():
    """Установка Python зависимостей"""
    print("Установка Python зависимостей...")
    
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✓ Зависимости установлены")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка установки зависимостей: {e}")
        return False


def create_shortcut():
    """Создание ярлыка для запуска"""
    print("Создание ярлыка для запуска...")
    
    # Создание batch файла для Windows
    if os.name == 'nt':
        shortcut_content = '''@echo off
echo VirtualQubit Turbo Kernel Automation
echo ======================================
python virtualqubit_automation.py
pause
'''
        with open("run_automation.bat", "w") as f:
            f.write(shortcut_content)
        print("✓ Создан ярлык: run_automation.bat")
    
    # Создание shell скрипта для Linux/Mac
    else:
        shortcut_content = '''#!/bin/bash
echo "VirtualQubit Turbo Kernel Automation"
echo "======================================"
python3 virtualqubit_automation.py
'''
        with open("run_automation.sh", "w") as f:
            f.write(shortcut_content)
        os.chmod("run_automation.sh", 0o755)
        print("✓ Создан скрипт: run_automation.sh")
    
    return True


def print_summary():
    """Вывод итоговой информации"""
    print("\n" + "="*60)
    print("📋 ПРОВЕРКА ГОТОВНОСТИ СИСТЕМЫ")
    print("="*60)
    
    checks = [
        ("Python версия", check_python_version()),
        ("Необходимые файлы", check_required_files()),
        ("SSH ключ", check_ssh_key()),
        ("Python зависимости", check_python_dependencies())
    ]
    
    passed_checks = sum(1 for _, result in checks if result)
    total_checks = len(checks)
    
    print(f"\nРезультаты проверки: {passed_checks}/{total_checks}")
    
    for check_name, result in checks:
        status = "✓" if result else "❌"
        print(f"{status} {check_name}")
    
    if passed_checks == total_checks:
        print("\n🎉 Все проверки пройдены! Система готова к работе.")
        print("\nДля запуска автоматизации:")
        print("   python virtualqubit_automation.py")
        if os.name == 'nt':
            print("   или")
            print("   run_automation.bat")
        else:
            print("   или")
            print("   ./run_automation.sh")
        return True
    else:
        print(f"\n❌ {total_checks - passed_checks} проверок не пройдено.")
        print("\nРекомендуемые действия:")
        if not check_python_dependencies():
            print("1. Установите зависимости: pip install -r requirements.txt")
        if not check_required_files():
            print("2. Убедитесь, что все файлы VirtualQubit находятся в текущей директории")
        if not check_ssh_key():
            print("3. Скопируйте SSH ключ Linux Ubuntu.ppk в текущую директорию")
        return False


def main():
    """Главная функция"""
    print("VirtualQubit Automation Setup")
    print("="*40)
    
    # Проверка Python версии
    if not check_python_version():
        sys.exit(1)
    
    # Проверка файлов
    if not check_required_files():
        print("\nПоместите все файлы VirtualQubit в текущую директорию и повторите попытку.")
        sys.exit(1)
    
    # Проверка зависимостей
    if not check_python_dependencies():
        print("\nУстановка зависимостей...")
        if not install_dependencies():
            print("Не удалось установить зависимости. Попробуйте вручную:")
            print("pip install paramiko scp tqdm")
            sys.exit(1)
    
    # Создание ярлыков
    create_shortcut()
    
    # Итоговая проверка
    success = print_summary()
    
    if success:
        print("\nГотово! Можно запускать автоматизацию.")
    else:
        print("\nИсправьте ошибки и повторите проверку.")
        sys.exit(1)


if __name__ == "__main__":
    main()