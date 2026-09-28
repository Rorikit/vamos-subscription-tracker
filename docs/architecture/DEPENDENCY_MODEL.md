# Dependency Model

Этот документ описывает нормализацию cross-module dependencies для Vamos Architecture Model.

## Принцип

Наблюдаемое взаимодействие в коде не равно архитектурной зависимости.

Extractor сохраняет raw-сигналы в `observed_interactions`, а затем сворачивает их в canonical-зависимости в `cross_module_dependencies`.

Направление зависимости:

```text
A -> B
```

означает: модуль A зависит от модуля B.

## Observed Interaction

Raw-сигнал содержит:

- `id`
- `from`
- `to`
- `source`
- `target`
- `interaction_type`
- `observed_field`
- `evidence`
- `source_type`
- `confidence`

Observed interaction не используется как самостоятельная линия главного графа.

## Canonical Dependency

Canonical dependency содержит:

- `id`
- `from`
- `to`
- `type`
- `interaction_types`
- `classification`
- `importance`
- `default_visibility`
- `reason`
- `evidence`
- `observed_interactions`
- `via_services`
- `via_entities`
- `source_type`
- `confidence`

## Classification

- `DOMAIN` - бизнес-зависимость между предметными модулями.
- `APPLICATION` - прикладная оркестрация без владения доменной логикой.
- `DATA` - чтение или использование данных другого модуля.
- `CONTROL` - авторизация, роли, права доступа.
- `OBSERVABILITY` - аудит, журналирование, уведомления.
- `UI_COMPOSITION` - экран или shell собирает данные других модулей.
- `INFRASTRUCTURE` - окружение, деплой, база, контейнеры.

## Importance

- `PRIMARY` - показывается в главной карте системы.
- `SECONDARY` - важная зависимость для detail-view и инспектора.
- `SUPPORTING` - сквозная, служебная или UI-зависимость.

## Default Visibility

- `MAIN` - видна в дефолтной System Map.
- `DETAIL` - видна в деталях модуля и dependency inspector.
- `HIDDEN` - хранится только как техническая диагностика.

## Cross-Cutting Modules

Auth классифицируется как `CONTROL/SUPPORTING/DETAIL`.

Audit и notifications классифицируются как `OBSERVABILITY/SUPPORTING/DETAIL`.

Settings и Dashboard классифицируются как `UI_COMPOSITION/SUPPORTING/DETAIL`.

Teachers являются справочником, который потребляют Schedule, Visits, Practice и Finance. Направление должно быть от потребляющего модуля к Teachers.

Infrastructure остается expected isolated и не должен искусственно подключаться к доменному графу.

## Overrides

Файл `dependency-overrides.json` уточняет классификацию уже найденных evidence-backed зависимостей.

Override не может создавать новую зависимость без observed evidence или существующего declared edge.

## Cycles

`CIRCULAR_DEPENDENCY` определяется только среди `PRIMARY` и `SECONDARY` зависимостей.

Циклы, состоящие только из `SUPPORTING`, игнорируются.

## Metrics

Snapshot публикует:

- `observed_interaction_count`
- `canonical_dependency_count`
- `primary_dependency_count`
- `secondary_dependency_count`
- `supporting_dependency_count`
- `unclassified_candidate_count`
- `suspicious_isolated_count`
- `circular_dependency_count`
