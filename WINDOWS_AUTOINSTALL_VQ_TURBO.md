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
