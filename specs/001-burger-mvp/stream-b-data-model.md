---
type: Data Model
title: Stream B — сущности фазы 1
description: Ссылки на schema.sql / lib.models. Какие поля читает POST /api/places. DDL не дублировать.
tags: [spec-kit, "001", stream-b, data-model]
timestamp: 2026-08-19T12:35:00Z
feature: 001-burger-mvp
status: draft
spec: stream-b-phase1.md
---

# Data Model: Stream B

Источник истины колонок: [schema.sql](../../schema.sql).
Единственный слой моделей: [lib/models.py](../../lib/models.py)
(`Hub`, `Poi`, `Cluster`, `make_hub_id`, `make_cluster_id`).
B **не** заводит таблицы, SQLAlchemy и свои dataclass-копии схемы.

Контракт JSON: [plans/api-contract.md](../../plans/api-contract.md) — не
переписывать сюда.

## Что читает `POST /api/places`

### `hub` — читать

| Поле | Зачем фазе 1 |
|---|---|
| `id` | `hub_id`, вход в `make_cluster_id` |
| `name`, `subject` | подписи карточки (`region` ← `subject`) |
| `lat`, `lon` | диски, пары ≤ `radius_km`, центр набора |
| `probe_status` | пары только `sellable`; в JSON как есть; не boolean-билет |
| `population` | слагаемое `cluster_score` (`log(1 + population)`) |

Не использовать для отбора мест: `sellable_modes`, `reachable_from_any`,
`min_price_from_moscow`, поля guard/Tutu (`tutu_geo_id`, `resolved_*`,
`expected_region*`). Это ингест/фаза 2.

### `poi` — читать

| Поле | Зачем фазе 1 |
|---|---|
| `id`, `name`, `lat`, `lon` | объекты карточки |
| `ingredient_id` | точное покрытие бургера |
| `hub_id` | привязка к диску (плюс проверка `r_local` по координатам) |
| `wikidata`, `wikipedia`, `start_date_*`, `name`, `tags_json` | `significance` §9; «древний» по порогу 1600 |
| `opening_hours`, `hours_status` | прокинуть в объект; не фильтровать «нет часов = закрыт» |
| `significance` | можно взять как кэш строки; иначе пересчитать той же формулой |

Сопоставление с запросом — только равенство `ingredient_id`. Эталонный
второй id = `industrial_museum`.

### `cluster` — опциональный кэш, не ranked output

PK `(id, radius_km)` — см. комментарий в schema. Публичный ключ = `id`.
Поля `hub_ids`, `title`, `center_*`, `diameter_km`, `ingredient_mask` могут
ускорить выдачу на шаге ползунка. **Порядок `places[]` и `coverage` всегда
считаются от бургера запроса**, не из `ingredient_mask` в одиночку.

На старте фикстур строки уже есть в [fixtures/rows/clusters.json](../../fixtures/rows/clusters.json);
это **не** ranked output и **не** набор кандидатов для SC-ranking.
Предпосчёт пары без одиночного Ярославля с маской эталона маскирует ничью
по coverage (Goodhart). Источник правды — живой проход дисков по `hub`+`poi`.
Регресс SC-B1/SC-B2: после `load_golden_fixtures` выполнить `DELETE FROM cluster`
и не заполнять таблицу до конца прогона.

### `leg`, `route_cache`, `hotel_cache`, `mcp_cache`, `misresolve_log`

**Не читать** в пути `/api/places`. Продаваемость перегона — фаза 2.

## Что пишет B (после implement, не сейчас)

Допустимо обновлять/дополнять `cluster` на шагах 50/100/150 после расчёта
дисков. Нельзя менять формат `id`. Нельзя писать цены в `hub`.

## Производные (только в ответе, не колонки)

Считаются на запрос; в SQLite отдельных таблиц нет.

- **Coverage** — `matched` / `missing` относительно `ingredients[]`.
- **Rarity** — `rank` (1-based в группе того же matched-набора),
  `total_places_with_combo`; в score = `1 / total_places_with_combo`.
  На эталоне это честный счётчик соседей Ярославля, не вау редкости.
- **cluster_score** — формула плана B; веса в конфиге.
- **diameter_km** — по крайним POI кластера (если кэш расходится с POI —
  побеждает пересчёт).
- **cluster_id** — `make_cluster_id`, не percent-encoded.

## Связи

```
hub 1 --- * poi          (poi.hub_id)
hub set  --- cluster     (cluster.hub_ids; identity = set of hub.id)
hub * --- * hub          (пары только в памяти/кэше cluster, не таблица pair)
```

Валидация входа (не схема БД): `ingredients` непустой и id из
`ingredients.yaml`; `radius_km` ∈ {50, 100, 150}; `limit` по умолчанию 20.
Ошибки HTTP — в контракте.

## State

У узла в фазе 1 нет своего «состояния билета». Три исхода пробы уже в
`probe_status`. Переход «серая карточка после origin» — C+D, не B.
