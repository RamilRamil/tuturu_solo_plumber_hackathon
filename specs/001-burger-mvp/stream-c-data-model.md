---
type: Data Model
title: Stream C — доступ к схеме фазы 2
description: Что поток C читает и пишет в таблицах schema.sql. DDL не дублируется. Модели не определяются заново.
tags: [spec-kit, "001", stream-c, data-model]
timestamp: 2026-08-19T16:40:00Z
feature: 001-burger-mvp
status: draft
derives_from: [stream-c-phase2.md, schema.sql]
---

# Stream C — Data Model

Истина колонок и PK: [schema.sql](../../schema.sql). Слой объектов:
[lib/models.py](../../lib/models.py). C **не** заводит SQLAlchemy и **не**
копирует CREATE TABLE.

Ниже — роль C: чтение / запись / запрет. Идентичность кластера — G2
(`make_cluster_id`); ингредиент `industrial_museum` в маске кластера на
поведение C не влияет, пока множество `hub.id` то же.

## Таблицы в контуре C

### `cluster` — только чтение

Нужна, чтобы `cluster_id` из запроса существовал. Публичный ключ = `id`
(множество хабов). PK таблицы `(id, radius_km)`: любая строка с этим `id`
достаточна; радиус из `/price` не приходит. Нет строки → HTTP 404, SSE не
открывать.

Поля смысла для C: `id`, `hub_ids`, `title` (человеческий текст, не ключ).

### `hub` — только чтение

Резолв имён и `expected_region` / `expected_region_source` для guard (G3 уже
в строке; C не пересчитывает OSM). `probe_status` узла **не** заменяет
продаваемость плеча. `sellable_modes` и `reachable_from_any` — снимки ингеста /
производное; билет после origin смотреть в `leg`.

C не пишет `hub`.

### `leg` — чтение (запись C до G10 не нужна)

Направленное ребро B2. PK `(origin_hub, dest_hub, date_probed)`.
`status` ∈ `{ok, no_route, misresolved}`.

- `ok` — можно эмитить `leg` (фикстура или кэш цены).
- `no_route` / нет ряда — `warning` `no_route`, карточку не удалять, составной
  путь не строить.
- `misresolved` на ребре — не схлопывать в «билетов нет» как у узла.

Обратное плечо = другой ряд (`B→A` ≠ `A→B`). Живые цены после G10 живут в
`route_cache`, а не подменой семантики `hub`. Матрицу D2 пишет A; C её не
пересчитывает.

### `route_cache` — чтение, затем запись (после живого вызова)

Ключ `(origin_hub, dest_hub, date)`. Читать **до** `call_tool`. Промах + live
→ записать `payload_json` + `fetched_at`. На демо без сети отдать кэш с
`source: cache` и при необходимости `warning` `cache_fallback`.

До G10 достаточно рядов, попавших из фикстур / эталона; запись live не
блокирует чекпоинт.

### `hotel_cache` — чтение, затем запись (после G10 для отелей)

Ключ `(hub_id, check_in, check_out, adults)`. `min_price` в событии = поле
`stay_total` из payload, **не** цена за ночь × `nights`. G10 не требует события
`hotel`.

### `misresolve_log` — запись через lib, не свой INSERT

При провале `check_resolve` / `TutuMcp.probe_destination` lib уже пишет лог.
C не дублирует схему INSERT. Не подменять это обновлением `hub.probe_status`.

### `mcp_cache` — запись только внутри `TutuMcp.call_tool`

C вызывает `call_tool`; кэш сырого MCP до guard. Прямой SQL в `mcp_cache` из
роутера запрещён.

## Вне контура C

| Таблица | Почему не C |
|---|---|
| `poi` | Фаза 1 / ингест. Часы объекта могут дать `warning` `hours_unknown` позже; таблицу C не заполняет. |
| `hub` WRITE | Ингест D1 / пробер A. |
| `cluster` WRITE | Поток B / прекомпут. |

## Правила, которые схема сама не произносит

- Цена `0` / `price_is_absent` → отсутствие режима, не тариф 0 RUB.
- `checkout_ref` непрозрачен; URL чекаута не пересобирать (контракт, не колонка).
- Origin в запросе — строка города; id хаба origin после резолва, не свободный
  slug.
- Неизвестный `cluster_id` не логируется как мисрезолв Tutu — это 404 контракта.

## Состояния потока (не колонка БД)

Запрос `/price`: `lookup` → `resolved` → нуль или более `leg`/`hotel`/`warning`
→ при показанной цене `breakdown` → `done`. Обрыв после 404 на lookup.
`price_status` в конце до live обоих сценариев = `fixture-confirmed`.
