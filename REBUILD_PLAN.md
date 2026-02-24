# План полной пересборки проекта

## Цель
С Windows-оркестратора подключаться к VPS по SSH-ключу, подготовить KVM-среду, применить turbo-патч к исходникам ядра, выполнить baseline/patched бенчмарк и сохранить результаты.

## Этапы
1. **Очистка репозитория**: удалить устаревшие дублирующиеся скрипты и старые гайды.
2. **Новая архитектура оркестратора**:
   - `orchestrator.py` — CLI входная точка.
   - `turbo_orchestrator/config.py` — конфигурация VPS/эксперимента.
   - `turbo_orchestrator/ssh_client.py` — SSH + конверсия `.ppk` через `puttygen`.
   - `turbo_orchestrator/workflow.py` — удаленные шаги установки, патча и измерений.
3. **Бенчмарк**:
   - baseline (`sysbench cpu`, 2 потока, 30 сек);
   - patched (`sysbench cpu` после применения patch + sysctl tuning);
   - расчет процента прироста.
4. **Сохранение результатов**:
   - JSON-отчет в `results/benchmark_*.json`.
5. **Запуск из Windows**:
   - установить Python + зависимости;
   - убедиться, что `puttygen` доступен в PATH;
   - запустить `python orchestrator.py --config config.example.json`.

## Критерии готовности
- Скрипт выполняется без ручного вмешательства.
- Отчет содержит baseline, patched, uplift_percent.
- SSH-ключи из репозитория поддерживаются.
