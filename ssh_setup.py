#!/usr/bin/env python3
"""
SSH Setup Script for VirtualQubit Automation
Проверяет и настраивает SSH ключи для подключения к VPS
"""

import os
import sys
import subprocess
import getpass
from pathlib import Path


def check_ssh_key_format(key_path: str) -> str:
    """Проверка формата SSH ключа"""
    if not os.path.exists(key_path):
        return "missing"
    
    with open(key_path, 'r') as f:
        content = f.read()
    
    if content.startswith("-----BEGIN"):
        return "openssh"
    elif content.startswith("PuTTY-User-Key-File-2"):
        return "ppk"
    else:
        return "unknown"


def convert_ppk_to_openssh(ppk_path: str, output_path: str = None) -> bool:
    """Конвертация PuTTY ключа в OpenSSH формат"""
    if output_path is None:
        output_path = ppk_path.replace('.ppk', '.key')
    
    print(f"Конвертация {ppk_path} в {output_path}...")
    
    try:
        # Пытаемся использовать puttygen
        result = subprocess.run([
            'puttygen', ppk_path,
            '-O', 'private-openssh',
            '-o', output_path
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✓ Ключ успешно сконвертирован")
            os.chmod(output_path, 0o600)  # Устанавливаем правильные права
            return True
        else:
            print(f"❌ Ошибка конвертации: {result.stderr}")
            return False
            
    except FileNotFoundError:
        print("❌ puttygen не найден. Попробуем использовать ключ напрямую...")
        return False
    except subprocess.TimeoutExpired:
        print("❌ puttygen не ответил за 30 секунд")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


def setup_ssh_agent():
    """Настройка SSH агента"""
    print("Настройка SSH агента...")
    
    try:
        # Проверяем, запущен ли ssh-agent
        result = subprocess.run(['ssh-add', '-l'], capture_output=True, text=True)
        
        if result.returncode != 0:
            print("Запуск ssh-agent...")
            subprocess.run(['ssh-agent', '-s'], capture_output=True)
        
        print("✓ SSH агент настроен")
        return True
        
    except Exception as e:
        print(f"⚠️  Не удалось настроить SSH агент: {e}")
        return False


def test_ssh_connection(hostname: str, username: str, key_path: str = None, password: str = None):
    """Тестирование SSH подключения"""
    print(f"Тестирование подключения к {username}@{hostname}...")
    
    try:
        if key_path:
            # Тест с ключом
            result = subprocess.run([
                'ssh', '-i', key_path, '-o', 'ConnectTimeout=10',
                f'{username}@{hostname}', 'echo "SSH connection successful"'
            ], capture_output=True, text=True)
        else:
            # Тест с паролем (через sshpass если доступен)
            try:
                result = subprocess.run([
                    'ssh', '-o', 'ConnectTimeout=10',
                    f'{username}@{hostname}', 'echo "SSH connection successful"'
                ], capture_output=True, text=True)
            except:
                print("❌ Не удалось протестировать подключение с паролем")
                return False
        
        if result.returncode == 0:
            print("✓ SSH подключение успешно")
            return True
        else:
            print(f"❌ SSH подключение не удалось: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка тестирования подключения: {e}")
        return False


def main():
    """Главная функция"""
    print("SSH Setup for VirtualQubit Automation")
    print("=" * 50)
    
    # Проверка наличия SSH ключа
    ssh_key = "Linux Ubuntu.ppk"
    
    if os.path.exists(ssh_key):
        print(f"✓ Найден SSH ключ: {ssh_key}")
        
        key_format = check_ssh_key_format(ssh_key)
        print(f"Формат ключа: {key_format}")
        
        if key_format == "ppk":
            print("Обнаружен PuTTY ключ (.ppk)")
            
            # Предлагаем конвертировать
            convert = input("Конвертировать в OpenSSH формат? (y/n): ").lower().strip()
            
            if convert == 'y':
                if convert_ppk_to_openssh(ssh_key):
                    openssh_key = ssh_key.replace('.ppk', '.key')
                    print(f"✓ Ключ сконвертирован: {openssh_key}")
                    
                    # Тест подключения с конвертированным ключом
                    hostname = input("Введите IP VPS (по умолчанию 92.246.131.14): ").strip()
                    if not hostname:
                        hostname = "92.246.131.14"
                    
                    username = input("Введите имя пользователя (по умолчанию root): ").strip()
                    if not username:
                        username = "root"
                    
                    if test_ssh_connection(hostname, username, openssh_key):
                        print("🎉 SSH ключ готов к использованию!")
                    else:
                        print("⚠️  Подключение не удалось, но ключ сконвертирован")
                else:
                    print("⚠️  Не удалось сконвертировать ключ")
            
            elif convert == 'n':
                print("✓ Используем .ppk ключ как есть")
                
                # Проверяем наличие pagent
                try:
                    result = subprocess.run(['pagent', '-l'], capture_output=True, text=True)
                    if result.returncode == 0:
                        print("✓ pagent доступен, можно использовать .ppk ключ")
                    else:
                        print("⚠️  pagent недоступен, может потребоваться пароль")
                except:
                    print("⚠️  pagent не найден, может потребоваться пароль")
        
        elif key_format == "openssh":
            print("✓ OpenSSH ключ готов к использованию")
            
            # Тест подключения
            hostname = input("Введите IP VPS (по умолчанию 92.246.131.14): ").strip()
            if not hostname:
                hostname = "92.246.131.14"
            
            username = input("Введите имя пользователя (по умолчанию root): ").strip()
            if not username:
                username = "root"
            
            if test_ssh_connection(hostname, username, ssh_key):
                print("🎉 SSH ключ готов к использованию!")
            else:
                print("⚠️  Подключение не удалось")
        
        else:
            print(f"⚠️  Неизвестный формат ключа: {key_format}")
    
    else:
        print(f"❌ SSH ключ не найден: {ssh_key}")
        
        # Предлагаем использовать пароль
        use_password = input("Использовать пароль для подключения? (y/n): ").lower().strip()
        
        if use_password == 'y':
            hostname = input("Введите IP VPS (по умолчанию 92.246.131.14): ").strip()
            if not hostname:
                hostname = "92.246.131.14"
            
            username = input("Введите имя пользователя (по умолчанию root): ").strip()
            if not username:
                username = "root"
            
            password = getpass.getpass("Введите пароль: ")
            
            # Сохраняем пароль в безопасном месте (временно)
            with open('.ssh_password.tmp', 'w') as f:
                f.write(password)
            os.chmod('.ssh_password.tmp', 0o600)
            
            print("✓ Пароль сохранен для использования в скрипте")
            print("⚠️  Не забудьте удалить .ssh_password.tmp после использования")
        
        else:
            print("⚠️  Для подключения потребуется SSH ключ или пароль")
    
    print("\n" + "=" * 50)
    print("Рекомендации:")
    print("1. Убедитесь, что SSH ключ имеет правильные права (600)")
    print("2. Проверьте, что публичный ключ добавлен на VPS")
    print("3. Для .ppk ключей рекомендуется использовать puttygen для конвертации")
    print("4. Альтернативно можно использовать пароль для подключения")
    print("\nГотово! Можно запускать основной скрипт: python virtualqubit_automation.py")


if __name__ == "__main__":
    main()