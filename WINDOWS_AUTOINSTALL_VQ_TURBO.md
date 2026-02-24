# Windows 10/11 auto-orchestrator for VQ Turbo lab

Скрипт `windows_vq_turbo_lab.py` делает следующее:

1. Запускает baseline CPU benchmark на хосте Windows.
2. Поднимает Ubuntu в WSL2 (автоматически, если дистрибутива нет).
3. Ставит зависимости в WSL.
4. Запускает тот же benchmark в гостевой среде.
5. Считает разницу в производительности в процентах.
6. Сохраняет JSON-отчёт.

## Требования

- Windows 10/11
- Python 3.10+
- Запуск из PowerShell/CMD от администратора

## Запуск

```powershell
python .\windows_vq_turbo_lab.py --mode wsl --distro Ubuntu --repo-win-path "C:\path\to\turbo_linux" --output .\vq_report.json
```

## Что в отчёте

- `baseline.throughput_mb_s` — throughput на хосте.
- `guest.throughput_mb_s` — throughput в WSL/VM.
- `percent_delta` — прирост/просадка, % относительно хоста.

## Примечания

- Режим `--mode hyperv` оставлен как заглушка, так как полностью unattended Hyper-V развертывание зависит от ISO, сети, шаблонов и политики безопасности вашей инфраструктуры.
- Для максимальной корректности сравнения запускайте скрипт несколько раз и усредняйте результаты.

## Troubleshooting (ошибка `wsl --install` exit status 1)

Если ранее падало на этапе `ensure_wsl_ubuntu` с `CalledProcessError`, новая версия скрипта теперь:

- проверяет, доступен ли WSL (`wsl --status`),
- пытается автоматически включить Windows features `Microsoft-Windows-Subsystem-Linux` и `VirtualMachinePlatform` (если запущено от администратора),
- делает `wsl --set-default-version 2` в best-effort режиме,
- устанавливает дистрибутив только если он реально отсутствует,
- выводит более понятную причину ошибки (нет прав администратора / выключена virtualization в BIOS / требуется первичная инициализация WSL).

Практически:

1. Откройте PowerShell **от администратора**.
2. Проверьте: `wsl --status` и `wsl -l -q`.
3. Если скрипт пишет, что включил features и нужен reboot — перезагрузите ПК.
4. Один раз запустите `wsl` вручную, завершите first-run setup Ubuntu.
5. Повторно запустите `windows_vq_turbo_lab.py`.
