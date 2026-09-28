# Архитектурный слой Vamos Subscription Tracker

Эта папка содержит единый машинно-читаемый источник архитектуры проекта:

`docs/architecture/architecture_snapshot.json`

Текущий контракт:

- `schema_version`: 2
- `model_contract_version`: 1

Snapshot используется приложением Vamos Architecture Hub и валидируется перед сборкой/деплоем.

## Файлы

- `architecture_snapshot.json` - canonical snapshot: модули, сущности, состояния, бизнес-процессы, use cases, API, компоненты, деплой, источники истины и traceability.
- `architecture_contract.py` - нормализатор v2: добавляет metamodel, relation registry, derived models и служебную метаинформацию.
- `validate_snapshot.py` - структурная проверка snapshot и запись `validation_report`.
- `readiness.py` - diagnostic engine для `readiness_report`: model readiness, coverage, traceability и isolated module diagnostics.
- `refresh_snapshot.py` - обновляет metadata, применяет контракт и запускает валидатор.
- `MODEL_READINESS.md` - правила READY/PARTIAL/MISSING/INVALID и диагностические rule IDs.
- `DEPENDENCY_MODEL.md` - правила нормализации observed interactions в canonical cross-module dependencies.
- `STATE_MODELING.md` - правила canonical state model: persisted, derived, operational statuses and transitions.
- `dependency_model.py` - классификатор зависимостей, importance/visibility и circular dependency diagnostics.
- `state_model.py` - нормализатор состояний и переходов без смешивания persisted/derived/operational state.
- `dependency-overrides.json` - evidence-backed уточнения классификации без создания новых связей.
- `METAMODEL.md` - допустимые типы объектов и общие правила модели.
- `GLOSSARY.md` - словарь терминов.
- `model-contracts/` - минимальные контракты данных для будущих UML/Sequence/Data/Component/Deployment представлений.
- `adr/` - архитектурные решения.
- `SUMMARY.md` - короткая человеческая сводка по архитектурному аудиту.

## Как обновлять snapshot

После значимых изменений backend/frontend выполнить:

```powershell
server\.venv\Scripts\python.exe docs\architecture\refresh_snapshot.py
```

Ожидаемый результат:

```text
Snapshot validation passed: 15 modules, 15 entities, 73 api endpoints.
Snapshot validation warnings: 2
```

Предупреждения допустимы только если конфликт явно описан в `sources_of_truth.conflicts`.

## Автообновление при деплое

Deploy-скрипты `deploy/git-auto-deploy.sh` и `deploy/bootstrap-v1-staging.sh` запускают:

```bash
python3 docs/architecture/refresh_snapshot.py
```

Это обновляет `metadata.generated_at`, `metadata.git_commit`, `metadata.git_branch`, применяет v2 contract и валидирует JSON перед Docker build.

Важно: текущий `refresh_snapshot.py` не является полноценным extractor из кода. Он нормализует и валидирует уже описанный snapshot. Когда появится extractor, его нужно подключить внутри этого же скрипта до валидации.

## Правила качества

- Все `id` стабильны и не зависят от порядка в массиве.
- Все связи используют зарегистрированный `relation_type`.
- Actor, Role, UseCase, BusinessProcess, Entity и DataTable не смешиваются.
- Каждая derived/declared сущность имеет `source_type`, `confidence` и `evidence`.
- Wildcard-ссылки вроде `api.*` не допускаются в смысловых связях.
- Состояние принадлежит ровно одной сущности; transition не может пересекать разные state machines.
- `PERSISTED_STATE`, `DERIVED_STATE` и `OPERATIONAL_STATUS` не смешиваются в одной persisted state machine.
- Продуктовая логика приложения не меняется ради обновления документации.
- `observed_interactions` хранят raw-сигналы из кода, а `cross_module_dependencies` содержит нормализованные архитектурные зависимости.
- Главная System Map показывает только `PRIMARY/MAIN`; детали и inspector показывают `SECONDARY` и `SUPPORTING`.
- Architecture Hub `/domain-model` строит предметную projection из canonical `entities`, `relationships`, `business_rules`, `sources_of_truth` и `stateful_entities`.

## Проверки

Python validator:

```powershell
server\.venv\Scripts\python.exe docs\architecture\validate_snapshot_test.py
server\.venv\Scripts\python.exe docs\architecture\readiness_test.py
server\.venv\Scripts\python.exe docs\architecture\dependency_model_test.py
server\.venv\Scripts\python.exe docs\architecture\state_model_test.py
```

Architecture Hub:

```powershell
cd architecture-hub
npm run architecture:validate
npm run architecture:readiness
npm run test
npm run type-check
npm run lint
npm run build
```
