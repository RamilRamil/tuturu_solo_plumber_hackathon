---
type: Implementation Plan
title: Stream B — plan фазы 1
description: Technical context, сверка инвариантов, фазы работ B до G10, зависимости от фикстур. Стоп до tasks/implement.
tags: [spec-kit, "001", stream-b, plan]
timestamp: 2026-08-19T12:35:00Z
feature: 001-burger-mvp
status: draft
spec: stream-b-phase1.md
---

# Implementation Plan: Stream B — фаза 1

**Spec**: [stream-b-phase1.md](stream-b-phase1.md)
**Дата**: 2026-08-19
**Контракт (не копировать)**: [plans/api-contract.md](../../plans/api-contract.md)
**Модели (импорт, не копия)**: [lib/models.py](../../lib/models.py) ← [schema.sql](../../schema.sql)

Каркаса `.specify/` нет и не заводится. Артефакты plan живут в этом бандле.

Связанные документы этой фазы:

- [stream-b-research.md](stream-b-research.md)
- [stream-b-data-model.md](stream-b-data-model.md)
- [stream-b-quickstart.md](stream-b-quickstart.md)

OpenAPI / `contracts/` не создавать: шов = `plans/api-contract.md`.

## Summary

Поток B отдаёт мгновенный список мест по бургеру и дискретному радиусу.
Кандидаты — диски вокруг узлов (один узел или пара), не плотность.
Ранжирование — лексикографика coverage, затем `cluster_score`.
Эталон №1 = `ancient_temple` + `industrial_museum` (решение оркестратора,
orchestration §0 B4). `cluster_id` считает `lib.models.make_cluster_id`
(множество `hub_id`; percent-encode — для URL шеринга у D, не внутри id).

До G10 зеленеют **SC-B1** и **SC-B2** на `fixtures/`. SC-price и
`POST /api/price` — не этот план.

## Technical Context

| Поле | Значение |
|---|---|
| Language / Version | Python 3.12 (заморозка G8, [plans/stack.md](../../plans/stack.md)) |
| Primary Dependencies | FastAPI + uvicorn уже в `backend/`; `sqlite3`; `lib.models`, `lib.load_fixtures` |
| Storage | SQLite `BURGER_DB` (`data/burger.db` в compose). Старт — загрузка золотых `fixtures/rows/` |
| Testing | Офлайн SC-ranking на фикстурах (SC-B1, SC-B2, SC-B3). Пустая `cluster`. Без сети, без Tutu |
| Target Platform | Один процесс бэка, порт **8000**; с хоста — через nginx `/api/` ([nginx/nginx.conf](../../nginx/nginx.conf)) |
| Project Type | Роутер фазы 1 внутри существующего `backend.app:app` (C живёт в том же процессе) |
| Performance Goals | Синхронный ответ без исходящей сети; бюджет шва < 200 мс |
| Constraints | Не плодить модели/SQLAlchemy. Не звать MCP. Не маппить `industrial_museum`→`industrial_site`. Не писать фейковые `industrial_site` POI. Радиус только 50/100/150 |
| Scale / Scope | На фикстурах — единицы узлов. После волны 1 — до ~268 узлов; свободный пересчёт тысяч пар на лету не обещать (V2) |
| Unknowns | Нет `NEEDS CLARIFICATION`. Веса `w1..w6` калибруются после D3 (F1); лексикографика от весов не зависит |

## Constitution / Invariants Check

Конституции Spec Kit (`.specify/memory/constitution.md`) в репозитории нет.
Гейты = инварианты `knowledge/invariants/`. Нарушение без обоснования = ERROR.

| Инвариант | Гейт для B | Вердикт design |
|---|---|---|
| [discs-not-dbscan](../../knowledge/invariants/discs-not-dbscan.md) | Кандидат = диск узла или пара ≤ `radius_km`; POI в `r_local`; нет DBSCAN/цепочек | PASS |
| [coverage-dominates-ranking](../../knowledge/invariants/coverage-dominates-ranking.md) | Сортировка: `len(matched)` убыв., затем `cluster_score`; не один скаляр. Пара эталона не обязана быть выше полного одиночного Ярославля | PASS |
| [pairs-are-not-cut](../../knowledge/invariants/pairs-are-not-cut.md) | Пары — кандидаты; эталон-пара и запасной одноузловой оба в регрессе | PASS |
| [sellability-is-edge](../../knowledge/invariants/sellability-is-edge.md) | Нет `sellable: true` на узле; в карточке `probe_status`; `leg` не участвует в отборе фазы 1 | PASS |
| [phase-boundary](../../knowledge/invariants/phase-boundary.md) | `POST /api/places` без исходящей сети и без origin | PASS |
| [source-of-truth-precedence](../../knowledge/invariants/source-of-truth-precedence.md) | Импорт `lib.models`; контракт по ссылке; §5/§12 mvp-spec не воспроизводить | PASS |

Повторная сверка после design (research + data-model + quickstart): гейты те же,
нарушений нет. Обоснованных исключений нет.

## Project Structure (куда ляжет код — не писать сейчас)

Существующее, B **импортирует**:

- `schema.sql`, `lib/models.py` (`Hub`, `Poi`, `Cluster`, `make_hub_id`, `make_cluster_id`, `connect`)
- `lib/load_fixtures.py` (`load_golden_fixtures`)
- `backend/app.py` — сейчас только `/healthz` и `/_sse_smoke`
- `ingredients.yaml` — валидация id входа, не второй словарь

После зелёного контроля plan (вне этого этапа): роутер `POST /api/places` в том
же FastAPI-приложении; веса ранжирования — конфиг рядом с обработчиком, не новая
таблица. Свои модели и свой DDL запрещены.

## Фазы работ B до G10

Эта поставка = Spec Kit **Phase 0 + Phase 1 design**. Phase 2 (`tasks.md`) и
implement **не начинать**.

| Этап plan | Часы оркестрации | Что | Сейчас |
|---|---|---|---|
| Specify | после G9 | [stream-b-phase1.md](stream-b-phase1.md) | принят |
| Phase 0 research | — | [stream-b-research.md](stream-b-research.md) | этот комплект |
| Phase 1 design | — | data-model + quickstart; контракт = ссылка | этот комплект |
| **СТОП** | — | контроль оркестратора | **здесь** |
| W1 диски | ~3–10 | кандидаты узел/пара + POI в `r_local`, гаверсинус | после зелёного |
| W2 `cluster_id` + `/api/places` | ~10–16 | `make_cluster_id`; тело как в контракте; 400 на плохой вход | после зелёного |
| W3 ранжирование B3 | ~10–16 | лексикографика + `cluster_score`; `coverage` / `rarity` | после зелёного |
| W4 rarity + регресс | ~16–26 | SC-B1, SC-B2, SC-B3 на фикстурах | до G10 |
| G10 | конец часа 26 | оба бургера в топ-5; в C уходит `cluster_id` **пары** из etalon_1, не обязательно `places[0]` | кусок B |

После G10 поток B на таймлайне пуст (часы 26–48 — C/D/живой SC-price).

## Зависимости от фикстур

B стартует на золотых файлах, не на живом ингесте A. Подмена волной 1 не должна
менять контракт и формулу ранжирования.

| Артефакт | Зачем B |
|---|---|
| [fixtures/etalon_1.json](../../fixtures/etalon_1.json) | SC-B1: бургер `ancient_temple`+`industrial_museum`, 100 км, `cluster_id` пары в топ-5 (не обязан #1) |
| [fixtures/backup_single_hub.json](../../fixtures/backup_single_hub.json) | SC-B2: `ancient_temple`+`ruins`, 100 км, одноузловой Ярославль |
| [fixtures/rows/hubs.json](../../fixtures/rows/hubs.json) | узлы, `probe_status`, `lat`/`lon`, `population` |
| [fixtures/rows/poi.json](../../fixtures/rows/poi.json) | объекты с точным `ingredient_id` (Ярославль несёт оба ингредиента эталона — не вырезать храмы) |
| [fixtures/rows/clusters.json](../../fixtures/rows/clusters.json) | кэш набора узлов; для SC-B1/B2 таблицу `cluster` опустошить после загрузки |
| `lib.load_fixtures.load_golden_fixtures` | единственный загрузчик строк в SQLite |

Не зависимости B (не читать для ранжирования фазы 1): `legs.json`,
`hotel_cache.json`, `mcp_cache.json`, цены в `etalon_1.json`.

Ожидаемые личности (канон контракта, percent-encode не входит в строку id):

- эталон: `c:Ростов|Ярославская область,Ярославль|Ярославская область`
- запас: `c:Ярославль|Ярославская область`

На фикстурах Борисоглебский — `not_sellable` (G3): в пары не входит; может
остаться карточкой «своим ходом».

## Complexity Tracking

Новых таблицы/стеков нет. Сложность = соблюсти четыре инварианта и точный
`ingredient_id`. Предпосчёт пар на 50/100/150 — оптимизация V2, не смена модели.
