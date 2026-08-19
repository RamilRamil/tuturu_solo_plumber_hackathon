---
type: Research
title: Stream C — решения плана фазы 2
description: Phase 0 /speckit-plan. Decision / Rationale / Alternatives. Все прежние неизвестные закрыты заморозками G2/G6/G8 и спекой.
tags: [spec-kit, "001", stream-c, research]
timestamp: 2026-08-19T16:40:00Z
feature: 001-burger-mvp
status: draft
derives_from: [stream-c-phase2.md]
---

# Stream C — Research

Неизвестных в Technical Context нет. Ниже — зафиксированные развилки, чтобы
implement не переоткрывал их.

## R1. Окна дат: лениво (V3), не 140 сразу

**Decision:** N дней в месяце, окна по неделям считать **лениво**. Без окон —
бюджет 35 вызовов на топ-5. Первое окно для топ-3 → показать → догрузка.
До G10 достаточно **одного** окна фикстуры эталона (`2026-10-09` и соседние
даты в `leg`).

**Rationale:** Жадно 4 окна × 35 = 140 вызовов: минуты вместо десятков секунд
при cap=4. Первый `leg` обязан прийти ~3 с — жадные окна ломают это.
Источник: `open-issues.md` V3, инвариант phase-boundary.

**Alternatives considered:**

- 140 синхронно — отвергнуто (V3, спиннер при готовых данных).
- Только 7 вызовов на кластер навсегда, без окон — отвергнуто продуктом §10
  (окна нужны, но не в первом кадре).
- Окна только по клику пользователя — допустимый фолбэк F8, не блокирует G10.

## R2. Транспорт ответа: SSE, не sync JSON

**Decision:** `POST /api/price` = `text/event-stream`. События по одному через
тот же nginx, что прод (`proxy_buffering off`). Имена и payload — только
[plans/api-contract.md](../../plans/api-contract.md), сюда не копировать.

**Rationale:** Медиана уникального маршрута ~3 с, хвост до 26,7 с. Sync UX
невозможен. G6 уже доказал, что край без буфера пропускает события с паузой.
Прямой `:8000` на приёмке G6-пути — ложная зелень.

**Alternatives considered:**

- Один JSON в конце — отвергнуто (phase-boundary, SC-C1).
- WebSocket — лишняя поверхность; контракт заморожен на SSE.
- SSE через чужой gzip/redirect-прокси на `:443` — отвергнуто (ломает стрим).
  Край: burger nginx `:8080` на VPS.

## R3. Один FastAPI с потоком B

**Decision:** Роутер C в существующем `backend/app.py` (или модуль, который
это приложение импортирует). Порт 8000. Один контейнер `backend`.

**Rationale:** Заморозка G8 / [plans/stack.md](../../plans/stack.md). Общий
SQLite, общий `cluster_id`, один nginx upstream. Два процесса = два расхождения
на G10 `/places`→`/price`.

**Alternatives considered:**

- Отдельный сервис C на другом порту — отвергнуто (G8).
- C в процессе ингеста A — отвергнуто (A на VPS-джобах, другая жизнь цикла).
- Проксировать `/api/price` в sidecar — нет выигрыша до G10.

## R4. Guard: импорт lib, не копия

**Decision:** `from lib.tutu_mcp import TutuMcp, check_resolve, price_is_absent`
(или эквивалентный импорт модуля). Тайм-аут и семафор уже в конструкторе
(`timeout_s < 30` и `max_concurrency > 4` — ValueError). Писать второй парсер
запрещено.

**Rationale:** Мисрезолв отдаёт полноценные цены без флага ошибки. Две копии
guard разъедутся. Lib уже пишет `mcp_cache` до бизнес-обработки и
`misresolve_log` при провале.

**Alternatives considered:**

- Скопировать `check_resolve` в backend — нарушение single-source-seams.
- Guard «после первого `leg`» — нарушение guard-before-price.
- Схлопнуть мисрезолв в `no_route` — потеря B1.

## R5. Ключ C = `cluster_id`, не ингредиенты

**Decision:** C принимает G2-строку как есть. Пример `/places` теперь с
`industrial_museum` вместо `industrial_site` — **множество хабов эталона не
менялось**, id тот же. C не парсит бургер из запроса `/price`.

**Rationale:** Identity = set of `hub.id`. Радиус и фаза и состав ингредиентов
в id не входят. Иначе шов B→C рвётся при любой правке словаря.

**Alternatives considered:**

- Искать кластер по title / ингредиентам — отвергнуто (G2).
- Включать radius в id — отвергнуто (тот же набор хабов на 50/100/150 = один id).
- ASCII-only slug — отвергнуто; кириллица в id заморожена, кодирование — на
  шеринге (D), не в JSON-теле `/price`.

## R6. Цена до live Tutu = `fixture-confirmed`

**Decision:** До живого прогона **обоих** сценариев (эталон №1 и запасной
одноузловой) `breakdown`/`done` несут `fixture-confirmed`. Цифра 4342 не
критерий G10. Снятие метки — часы 44–48 (`SC-price` ±15%).

**Rationale:** Фикстура против себя не доказывает прайсинг. Сборка часа 26
не должна краснеть из-за дрейфа Tutu (R1 в readiness-gate).

**Alternatives considered:**

- Считать эталон 4342 жёстким pass на G10 — отвергнуто оркестрацией §3.
- Молчать о статусе — жюри примет кэш за live.
- Ждать live Tutu, прежде чем писать `/price` — убивает параллельность после G9.
