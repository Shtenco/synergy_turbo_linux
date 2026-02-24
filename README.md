# Turbo Linux Rebuild (Windows Orchestrator → VPS → KVM)

Проект пересобран с нуля под единый сценарий: **Windows Python оркестратор** подключается к VPS по SSH-ключу, готовит KVM окружение, применяет patch к kernel source и считает прирост производительности относительно baseline Linux профиля (2 GB RAM / 2 vCPU).

## Структура
- `orchestrator.py` — точка запуска.
- `turbo_orchestrator/config.py` — dataclass-конфиг.
- `turbo_orchestrator/ssh_client.py` — SSH + поддержка PuTTY `.ppk`.
- `turbo_orchestrator/workflow.py` — pipeline установки/патча/benchmark.
- `config.example.json` — пример конфигурации.
- `REBUILD_PLAN.md` — план пересборки и внедрения.
- `virtual_qubit_turbo_5.15.patch` — patch, применяемый на VPS.

## Быстрый старт (Windows)
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python orchestrator.py --config config.example.json
```

## Что делает оркестратор
1. Подключается к VPS (`root@92.246.131.14`) по SSH-ключу из репозитория.
2. Ставит пакеты для KVM и сборки ядра.
3. Снимает baseline (`sysbench cpu --threads=2 --time=30`).
4. Копирует patch на VPS и применяет к `linux-source`.
5. Применяет runtime tuning (`sched_autogroup`, `swappiness`).
6. Повторно запускает benchmark и считает `uplift_percent`.
7. Сохраняет JSON-отчет в `results/`.

## Примечания
- Для `.ppk` нужен `puttygen` в PATH.
- Скрипт рассчитан на Ubuntu 24.04 VPS.
- Перед запуском проверьте, что ключи доступа актуальны.
