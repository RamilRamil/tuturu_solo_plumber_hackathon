---
type: Implementation Plan
title: Stream C — план фазы 2 до G10
description: Technical context, инварианты и срезы до чекпоинта G10. Контракт SSE не копируется. Код POST /api/price этим файлом не пишется.
tags: [spec-kit, "001", stream-c, plan, phase-2]
timestamp: 2026-08-19T16:40:00Z
feature: 001-burger-mvp
status: draft
derives_from: [stream-c-phase2.md, stream-c-research.md]
---

# Stream C — Implementation Plan

Спека [stream-c-phase2.md](stream-c-phase2.md) принята. Этот файл — дух
`/speckit-plan` в OKF-бандле 001. Стоп после плана: нет `tasks.md`, нет
implement, нет хендлера `/api/price`.

Связанные артефакты той же фазы: [stream-c-research.md](stream-c-research.md),
[stream-c-data-model.md](stream-c-data-model.md),
[stream-c-quickstart.md](stream-c-quickstart.md).

## Technical Context

| Поле | Значение |
|---|---|
| Language | Python 3.12 (заморозка G8) |
| Process | Один FastAPI с роутерами B+C, порт 8000. C **не** поднимает второй процесс. |
| Storage | SQLite `data/burger.db`; модели только `lib/models.py`. DDL не дублировать. |
| MCP | Импорт `lib.tutu_mcp` (`TutuMcp`, `check_resolve`, `price_is_absent`). Не копия. |
| Identity | `cluster_id` = G2, `lib.models.make_cluster_id`. Ключ C — этот id, не ингредиенты. |
| Etalon hubs | Множество хабов эталона **не менялось**. C принимает `cluster_id` из `fixtures/etalon_1.json` (пара), не `places[0]` фазы 1. |
| Encoding | Cyrillic и `\|` в id допустимы. Тело JSON — UTF-8. Не класть сырой id в path-сегмент; шеринг percent-encode (FR-D16, поток D). |
| Edge SSE | Burger nginx: laptop `:80`, VPS `:8080`. `proxy_buffering off`. Не чужой gzip/redirect-прокси. G6 уже зелёный на `_sse_smoke`. |
| Testing (G10) | Кусок C: `resolved` + ≥1 `leg` + `done` **по одному**. `price_status: fixture-confirmed`. `SC-price` не валит сборку. |
| Timeout | `CALL_TIMEOUT_S >= 30` в клиенте; C не ужимает. Cap конкурентности 4. |
| Scale to G10 | Один эталонный `cluster_id` + 404 на неизвестный. Топ-5 live и окна дат — после скелета, окна лениво (V3). |
| Unknowns | Нет. `NEEDS CLARIFICATION` = 0. |

**Не входит в этот план:** кластеризация B, фронт D, ингест A/D5, живой `SC-price` (часы 44–48), второй `tutu_mcp.py`.

## Invariants Check (вместо constitution)

Каркас `.specify/` и constitution в репо нет — гейты = load-bearing инварианты.
Нарушение без обоснования = ERROR, план недействителен.

| Инвариант | Как C соблюдает | Нарушение |
|---|---|---|
| [guard-before-price](../../knowledge/invariants/guard-before-price.md) | Любой `search_*` / `probe_destination` до события с ценой. Guard в lib. | Свой `check_resolve`; цена до guard; `misresolved` → `not_sellable`. |
| [sellability-is-edge](../../knowledge/invariants/sellability-is-edge.md) | Продаваемость плеча из таблицы `leg` (направленная). Обратное плечо — отдельная проверка. | Флаг узла как «билет есть»; составной маршрут «с доездом». |
| [phase-boundary](../../knowledge/invariants/phase-boundary.md) | Tutu только в `/api/price`, только после отбора топ-5. SSE, не sync. Окна лениво. | Сеть в `/api/places`; ждать все плечи; 140 окон сразу. |
| [single-source-seams](../../knowledge/invariants/single-source-seams.md) | Один процесс, один контракт, один MCP-модуль. | Второй FastAPI на другом порту; локальный парсер Tutu. |

Пост-дизайн: те же четыре строки зелёные. `contracts/` в бандле **не** заводится —
истина SSE уже [plans/api-contract.md](../../plans/api-contract.md).

## Project Structure (куда ляжет код позже)

Существует сейчас: `backend/app.py` (только `/healthz`, `/_sse_smoke`).
После зелёного на implement (не сейчас): роутер C в **том же** приложении.
C не создаёт деревья вне принятого скелета и не трогает `schema.sql` / `lib/tutu_mcp.py`.

Старт данных: `lib/load_fixtures.py` + `fixtures/rows/legs.json`,
`fixtures/rows/hotel_cache.json`, `fixtures/etalon_1.json`.

## Срезы до G10 (конец часа 26)

Порядок исполнения **после** приёмки этого плана. Каждый срез оставляет
события по одному (G6). Живой Tutu до G10 не обязателен: фикстуры + кэш-ряды.

1. **Каркас SSE.** `POST /api/price` в том же FastAPI. Неизвестный `cluster_id`
   → HTTP 404 (не `warning`). Заголовки как у `_sse_smoke`. Край — nginx, не
   прямой `:8000` на приёмке G6-пути.
2. **Lookup кластера.** Читать `cluster`/`hub` по G2-id (множество хабов;
   `radius_km` в поиске не участвует). Ингредиент `industrial_museum` не парсить
   из id.
3. **`resolved`.** Origin и хабы через импорт lib + guard. Мисрезолв →
   `warning` + строка лога из lib, цена не уходит.
4. **Первый `leg` ~3 с.** Читать направленный `leg` / `route_cache` фикстур
   (Москва→Ярославль эталона). Отдать событие, не ждать остальные плечи.
5. **Закрытие потока.** Если цена уже была — `breakdown` затем `done`, оба со
   статусом `fixture-confirmed`. Минимум G10: `resolved` + ≥1 `leg` + `done`.

**После G10 (не критерий этой сборки):** отели `stay_total`, `checkout_url`
как вернул сервер, обратные плечи, ленивые окна, кэш-фолбэк демо, live Tutu
и снятие `fixture-confirmed` только после **обоих** сценариев.

## Complexity Tracking

Оправданная сложность (не расползание):

- SSE вместо JSON: латентность Tutu до 26,7 с; иначе спиннер при готовом плече.
- Отдельная таблица `leg`: доказанная асимметрия рёбер (B2).
- `fixture-confirmed`: фикстура≠live; G10 не требует 4342 RUB.

Не делать: второй сервис, жадные 140 вызовов, свой DDL.
