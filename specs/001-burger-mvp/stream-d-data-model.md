---
type: Data Model
title: Stream D — UI-модель (проекция контракта)
description: Сущности экрана как проекция plans/api-contract.md и ingredients.yaml. Своей БД у потока D нет.
tags: [spec-kit, "001", stream-d, data-model]
timestamp: 2026-08-19T16:40:00Z
feature: 001-burger-mvp
status: draft
spec: stream-d-frontend.md
plan: stream-d-plan.md
contract: plans/api-contract.md
---

# Stream D — Data Model

D **не** заводит SQLite, не копирует `schema.sql`, не определяет `hub.id`.  
Все ident-поля — ASCII-имена контракта. Кириллица только в значениях (`name`, `title`, `cluster_id`).

Канон полей Place / SSE: [plans/api-contract.md](../../plans/api-contract.md).  
Ниже — как они лежат в состоянии UI и какие проекции добавляет экран (не хранилище).

---

## Источники

| Источник | Что даёт UI |
|---|---|
| [ingredients.yaml](../../ingredients.yaml) | Каталог меню: `id`, `name_ru`, `group`, `density_label`, `density_measured` |
| `POST /api/places` | `total_found`, `places[]` (фаза 1) |
| `POST /api/price` SSE | события по тому же `cluster_id` (фаза 2) |
| Клиент | бургер, радиус, origin, состав, `mock`/`live`, визуал карточки |
| A / D3 (позже) | список залитых регионов для карты покрытия |

---

## Burger (клиент, не ответ API)

Состав поиска фазы 1. **Origin не входит.**

| Поле | Тип / домен | Правила |
|---|---|---|
| `ingredients` | `string[]` (yaml `id`) | непустой перед запросом; эталон = `ancient_temple`, `industrial_museum` |
| `radius_km` | `50` \| `100` \| `150` | дефолт 100; иное не слать |
| `limit` | number | дефолт 20, как контракт |

Связь: один Burger → один запрос places → много `Place`.

---

## Ingredient (каталог)

| Поле | Домен |
|---|---|
| `id` | ascii id yaml |
| `density_label` | `dense` \| `medium` \| `rare` \| `absent_in_region` (в yaml бывает `null` — в UI всё равно нужна видимая метка: показать «нет замера», не скрыть) |
| `density_measured` | number \| null (храмы 370, водопады 0) |

Валидация UI: карточка без видимой плотности = дефект FR-D2.

---

## Place (проекция ответа `/api/places`)

Идентичность = `cluster_id` (множество `hub.id`, **не** радиус, **не** фаза, **не** `title`).

| Поле | Смысл |
|---|---|
| `cluster_id` | ключ карточки, SSE и шеринга |
| `title` | человеческий текст |
| `hubs` | `Hub[]` |
| `center` | `lat`, `lon` |
| `diameter_km` | фактический диаметр; подпись честная (F17), может быть > `radius_km` |
| `coverage.matched` / `coverage.missing` | полное покрытие vs «почти подходит» |
| `rarity.rank` / `rarity.total_places_with_combo` | как пришло; UI не считает заново и не подписывает «редкая связка» на эталоне |
| `objects` | `PoiObject[]` — все на карте, топ в карточке |

Порядок в массиве `places[]` = ранг B3. UI не sort.

Эталон №1 (фикстура):

```
cluster_id = c:Ростов|Ярославская область,Ярославль|Ярославская область
```

Запасной:

```
cluster_id = c:Ярославль|Ярославская область
```

---

## Hub

| Поле | Домен / правило |
|---|---|
| `hub_id` | `name\|subject`, запятая запрещена (бэкенд) |
| `probe_status` | `sellable` \| `not_sellable` \| `misresolved` |
| `lat`, `lon`, `name`, `region` | как в контракте |

`not_sellable` → пометка «дальше своим ходом», карточка жива.  
Не слать и не ждать `sellable: true` как в старом mvp-spec §4.

---

## PoiObject

| Поле | Правило UI |
|---|---|
| `id`, `name`, `ingredient`, `lat`, `lon` | маркер карты |
| `significance` | для порядка внутри карточки, не для цен |
| `opening_hours` | может быть null |
| `hours_status` | `open` \| `closed` \| `unknown`; null/пусто тега → `unknown`, не `closed` |

---

## PlaceCardView (только UI)

Проекция `Place` + события фазы 2. **Не** удаляет Place из списка.

| Поле | Домен |
|---|---|
| `visual` | `full` \| `almost` \| `grey` |
| `grey_reason` | текст причины; обязателен при `grey` |
| `on_your_own` | true если любой хаб `not_sellable` |
| `phase1_index` | индекс в ответе places (0-based), топ-5 = первые полные |

Переходы `visual`:

```
full  --coverage.missing непусто--> almost
full|almost --недостижимо после origin--> grey
grey --x--> (нет удаления, нет возврата в «не было»)
```

При пожаре B4 блок `almost` можно не рендерить; `full` эталона остаётся.

---

## PriceStream (проекция SSE `/api/price`)

Запрос (клиент собирает, не хранит как таблицу):

| Поле | Правило |
|---|---|
| `cluster_id` | **тот же**, что у выбранной карточки |
| `origin` | после фазы 1 |
| `days` | ≥ 1 |
| `month` | `YYYY-MM` |
| `adults` | ≥ 1 |
| `children_ages` | `number[]`, дефолт `[]` |
| `budget_scope` | `transport` \| `all`; дефолт `transport` |

События (накапливать по мере прихода, не ждать `done`):

| `event` | Ключевые поля | UI |
|---|---|---|
| `resolved` | `origin.guard`, `hubs[].guard` | `misresolved` ≠ `not_sellable` |
| `leg` | `price`, `mode`, `source` | `price == 0` не показывать как «0 ₽» |
| `hotel` | `min_price`, `nights`, `price_basis` | не умножать на `nights` (`stay_total`) |
| `breakdown` | `transport`, `lodging`, `total`, `price_status` | обязателен, если была цена |
| `checkout` | `items[].checkout_url` | открыть as-is |
| `warning` | `code`, `message` | карточка серая, не 404 |
| `done` | `cluster_id`, `price_status`, `ok` | конец потока |

Неизвестный `cluster_id` → HTTP 404 **до** SSE, не `warning`.

Состояние потока: `idle` → `streaming` → `done` \| `error`.  
Пока нет live Tutu по **обоим** сценариям: `price_status = fixture-confirmed`.

---

## ShareParams (после G10)

| Поле | Правило |
|---|---|
| `cluster_id` | сырой id из Place |
| query value | `encodeURIComponent(cluster_id)` целиком (UTF-8) |
| плюс | `ingredients`, `radius_km`, `origin`, `days`, `month` |

Не path segment. Смена только радиуса без смены множества хабов — тот же id.

---

## CoverageRegion (V4, после G10)

| Поле | Смысл |
|---|---|
| `loaded` | регионы от A (D3) |
| `hole` | остальные — штриховка |

Фронт список регионов не выдумывает. Пустая фаза 1 в дыре ≠ «такой комбинации нет».

---

## Что D не моделирует

- Таблицы `leg` / `cluster` / `poi` / кэш Tutu.
- Формулу `cluster_score` и лексикографику B3.
- Guard внутри `lib/tutu_mcp.py`.
- Свои короткие id вместо `cluster_id`.
