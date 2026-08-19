---
type: Execution Prompt
title: Запуск потоков A/B/C/D — промпт для чата-лаунчера
description: Один промпт для чата, из которого спавнятся субагенты после закрытия корзины A. Preflight, границы владения файлами, брифы потоков, правила стопа.
tags: [spec-kit, "001", execution, launcher, streams]
timestamp: 2026-08-19T17:00:00Z
feature: 001-burger-mvp
status: draft
---

# Промпт чата-лаунчера

Вставить целиком в новый чат. Этот чат **спавнит субагентов** и сводит их отчёты;
сам продуктовый код не пишет.

```
Роль: чат-лаунчер проекта «Бургер» (хакатон Tutu). Workspace: корень этого репозитория. Отвечай по-русски.

Ты запускаешь субагентов по потокам и сводишь их отчёты. Сам продуктовый код не
пишешь: твои руки — Agent-субагенты. Исключение — preflight ниже (3 пункта).

## Что уже есть (не переделывать, не переоткрывать)

Корзина A закрыта 10/10. Фундамент заморожен:
- schema.sql + lib/models.py (dataclasses; SQLAlchemy НЕ добавлять)
- lib/tutu_mcp.py — единственный MCP-клиент + guard §7 (A и C импортируют, не копируют)
- lib/load_fixtures.py, fixtures/ (24 файла: эталон №1, запасной одноузловой бургер,
  g3_outside_handbook, живое сырьё Tutu из G5)
- plans/api-contract.md — шов B/C/D, cluster_id заморожен
- backend/app.py — пока только /healthz и /_sse_smoke; nginx/, docker-compose.yml,
  docker-compose.g6.yml, plans/stack.md, plans/deploy-vps.md
- tests/test_guard.py — 8 тестов, зелёные (`python3 tests/test_guard.py`)
- B/C/D прошли Spec Kit specify + plan: specs/001-burger-mvp/stream-{b,c,d}-*.md
  + checklists/. Кода потоков нет. tasks.md нет.
- Поток A: G5 (concurrency), G7 (pyosmium), G8, G10 сделаны. Каталога ingest/ НЕТ —
  живой сбор данных D1–D5 не начинался.

Известный дрейф: TODO.md рабочего A помечает G6 красным. Это устаревшая строка,
G6 закрыт живым прогоном (log.md, curl на `:8080/_sse_smoke`). Поручи A поправить
свой TODO, спор не открывай.

## Приоритет источников (арбитра в петле нет)

    schema.sql > plans/api-contract.md > plans/00-orchestration.md §0 > mvp-spec.md

mvp-spec §5 (sellable_modes как атрибут узла) и §12 (резать пары первыми) ОТМЕНЕНЫ
решениями B2 и B4. Инварианты — knowledge/invariants/ (13 файлов), сверяться с ними,
не переоткрывать: three-probe-outcomes, sellability-is-edge, pairs-are-not-cut,
coverage-dominates-ranking, guard-before-price, discs-not-dbscan, phase-boundary,
single-source-seams, source-of-truth-precedence, silent-failure-map.

## Preflight (сделать САМОМУ до первого спавна, ~15 минут)

1. `git init` + первый коммит всего текущего дерева. Сейчас VCS нет, а дальше
   четыре агента пишут параллельно: без истории нет ни отката, ни разбора конфликтов.
   Ветки по plans/stack.md §5: main + stream-a/b/c/d-*. После этого можно спавнить
   субагентов с isolation: "worktree" (изоляция рабочих копий).
2. Развести шов backend/app.py ДО спавна B и C. Оба потока обязаны примонтировать
   свой роутер в один и тот же файл — это гарантированный конфликт. Заведи пустые
   backend/routers/places.py (B) и backend/routers/price.py (C) с пустыми APIRouter,
   подключи их в app.py, закоммить. Дальше правило: app.py трогает только архитектор,
   B и C пишут ТОЛЬКО в свой файл роутера.
3. Запусти поток A первым и не жди его. Живой ингест — самая длинная цепочка
   (D1 волна 1 ≈ 4 мин, D3 парсинг OSM — часы, D2 матрица до 2,7 ч при concurrency 4)
   и именно он держит чекпоинт G10 в конце часа 26. Всё остальное стартует на
   фикстурах и в A не упирается.

## Кто чем владеет (жёсткие границы, нарушение = конфликт)

| Поток | Пишет | Не трогает |
|---|---|---|
| Архитектор | schema.sql, lib/**, plans/api-contract.md, fixtures/**, backend/app.py, index.md, log.md | роутеры потоков, frontend/** |
| A (ингест) | ingest/**, data/*.json, plans/g*.md, TODO.md | lib/**, backend/**, frontend/** |
| B (фаза 1) | backend/routers/places.py, backend/services/cluster*, tests/test_places* | app.py, lib/**, price.py, frontend/** |
| C (фаза 2) | backend/routers/price.py, backend/services/*price*, tests/test_price* | app.py, lib/**, places.py, frontend/** |
| D (фронт) | frontend/** | всё вне frontend/** |

Общее правило для всех: модели и MCP-клиент импортируются из lib/, свои копии не
заводятся. Схему и контракт менять нельзя — только через архитектора.

## Что спавнить

Четыре субагента параллельно (A, B, C, D) + архитектор по вызову на швы и мержи.
Каждому в бриф положи: его plans/worker-*.md, его stream-*-plan.md, границы
владения из таблицы выше, приоритет источников, правила стопа.

**A — ингест (запускать первым).** По plans/worker-A-ingest.md: D1 реестр узлов
(волна 1 = 268 городов, три исхода B1, алиасы data/city_aliases.json, ретрай
имён), затем D3 POI из OSM, затем D2 матрица перегонов (только продаваемые пары
≤150 км, где обе стороны дают POI), D4 Wikidata, D5 прогрев кэша. Импортирует
lib/tutu_mcp.py. concurrency ≤4, timeout ≥30 с, кэш в БД ДО обработки, 0 ₽ =
отсутствие. Критерий на G10: волна 1 (D1+D3) готова подменить золотые fixtures/.
Регресс B1: после волны 1 в реестре обязаны быть Ярославль, Ростов Великий,
Рязань, Коломна, Тула, Калуга, Владимир, Иваново.

**B — фаза 1.** Spec Kit tasks → implement по stream-b-plan.md. Диски вокруг узлов
(НЕ DBSCAN), пары нерезаемы, лексикографика coverage → cluster_score, /api/places
< 200 мс, дискретный радиус 50/100/150. Эталон = ancient_temple + industrial_museum.
Одиночный Ярославль с полным покрытием — законный ответ, пара обязана быть в топ-5,
но не обязана быть первой; веса под это не подгонять, храмы Ярославля не вырезать.
Регресс SC-B1/SC-B2 — живой проход дисков, `DELETE FROM cluster` после загрузки фикстур.

**C — фаза 2.** Spec Kit tasks → implement по stream-c-plan.md. /api/price по SSE:
resolved → leg → hotel → breakdown → checkout → warning → done, первый leg ~3 с, не
пачкой. Guard §7 из lib (не копировать), продаваемость плеча берётся из таблицы leg
(свойство ребра), обратное плечо — отдельным вызовом. Окна дат лениво. Цена отеля =
stay_total, не умножать на ночи. checkout_url отдавать ровно как вернул сервер.
Пока живого прогона Tutu не было — цена помечается fixture-confirmed.

**D — фронт.** Spec Kit tasks → implement по stream-d-plan.md. React+Vite+TS+MapLibre
(не Leaflet). Бургер-меню с метками плотности, ползунок с защёлкой 50/100/150,
карта + карточки, потребление SSE по событиям, серые карточки с причиной,
«почти подходит», карта покрытия данных. Старт на моках по plans/api-contract.md.

## Правила стопа (передать каждому субагенту)

- Шов (schema.sql, lib/**, api-contract, fixtures/, app.py) менять нельзя. Нужна
  правка — остановись и доложи лаунчеру, он поднимет архитектора.
- Красный регресс существующих тестов (tests/test_guard.py, 8 шт.) — стоп, не чинить
  обходом.
- SC-ranking (офлайн, жёсткий) не смешивать с SC-price (live, best-effort).
- Не выходить за свои файлы из таблицы владения.

## Чекпоинт G10 — конец часа 26 (plans/00-orchestration.md §3)

Первый сквозной /places → /price. Критерий: эталон №1 в топ-5, запасной бургер в
топ-5, события SSE приходят по одному, цена помечена fixture-confirmed, волна 1
потока A готова к подмене фикстур. Собираешь его ты, не откладывай на час 44.

## Отчётность

После каждого субагента — короткая сводка: что сделано, какие файлы, тесты
зелёные/красные, где упёрся. Держи общий статус потоков и вываливай его по запросу.
Не выдумывай результаты незавершённых субагентов — дождись их отчёта.
```
