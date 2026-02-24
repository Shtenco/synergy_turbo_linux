#!/usr/bin/env python3
"""
Quick SSH Fix Script
Быстрое решение проблем с SSH ключами для VirtualQubit Automation
"""

import os
import sys
import subprocess
import getpass
from pathlib import Path


def check_and_fix_ssh():
    """Проверка и быстрое решение проблем с SSH"""
    print("🔧 Quick SSH Fix for VirtualQubit Automation")
    print("=" * 50)
    
    ssh_key = "Linux Ubuntu.ppk"
    
    if not os.path.exists(ssh_key):
        print(f"❌ SSH ключ не найден: {ssh_key}")
        print("Пожалуйста, убедитесь, что файл находится в текущей директории")
        return False
    
    print(f"✓ Найден SSH ключ: {ssh_key}")
    
    # Проверяем формат ключа
    with open(ssh_key, 'r') as f:
        key_content = f.read()
    
    if key_content.startswith("PuTTY-User-Key-File-2"):
        print("✓ Обнаружен PuTTY ключ (.ppk)")
        
        # Пытаемся использовать pagent
        try:
            result = subprocess.run(['pagent', '-l'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                print("✓ pagent доступен - .ppk ключ будет работать")
                return True
        except:
            pass
        
        # Пытаемся конвертировать
        try:
            print("🔧 Пробуем конвертировать .ppk в OpenSSH формат...")
            
            # Создаем временный файл
            temp_key = ssh_key.replace('.ppk', '.key')
            
            # Пробуем puttygen
            result = subprocess.run([
                'puttygen', ssh_key,
                '-O', 'private-openssh',
                '-o', temp_key
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print(f"✓ Ключ сконвертирован: {temp_key}")
                os.chmod(temp_key, 0o600)
                return True
            else:
                print(f"⚠️  puttygen не сработал: {result.stderr}")
        except Exception as e:
            print(f"⚠️  Ошибка конвертации: {e}")
        
        # Финальное решение - использовать пароль
        print("\n🔧 Решение проблемы:")
        print("1. Использовать пароль вместо ключа")
        print("2. Или сконвертировать ключ вручную")
        
        use_password = input("\nИспользовать пароль для подключения? (y/n): ").lower().strip()
        
        if use_password == 'y':
            hostname = input("IP VPS (по умолчанию 92.246.131.14): ").strip() or "92.246.131.14"
            username = input("Имя пользователя (по умолчанию root): ").strip() or "root"
            password = getpass.getpass("Введите пароль: ")
            
            # Сохраняем в конфиг
            config = {
                "hostname": hostname,
                "username": username,
                "password": password
            }
            
            with open('.ssh_config.json', 'w') as f:
                import json
                json.dump(config, f, indent=2)
            
            print("✓ Конфигурация сохранена")
            print("⚠️  Скрипт автоматически переключится на парольную аутентификацию")
            return True
        else:
            print("⚠️  Для использования .ppk ключа:")
            print("1. Установите PuTTY и pagent")
            print("2. Или сконвертируйте ключ вручную:")
            print(f"   puttygen \"{ssh_key}\" -O private-openssh -o linux_ubuntu.key")
            return False
    
    else:
        print("✓ Обнаружен OpenSSH ключ")
        return True


def main():
    """Главная функция"""
    if check_and_fix_ssh():
        print("\n🎉 SSH проблема решена!")
        print("\nТеперь можно запускать основной скрипт:")
        print("python virtualqubit_automation.py")
    else:
        print("\n❌ SSH проблема не решена")
        print("\nПопробуйте:")
        print("1. python ssh_setup.py")
        print("2. Или используйте пароль в основном скрипте")


if __name__ == "__main__":
    main()