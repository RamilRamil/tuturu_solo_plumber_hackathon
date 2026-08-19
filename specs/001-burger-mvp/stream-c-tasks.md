---
type: Tasks
title: Stream C — tasks фазы 2
description: Dependency-ordered checklist for POST /api/price SSE. Spec Kit tasks spirit without .specify/. No product code in this iteration.
tags: [spec-kit, "001", stream-c, tasks]
timestamp: 2026-08-19T17:21:00Z
feature: 001-burger-mvp
status: draft
spec: stream-c-phase2.md
plan: stream-c-plan.md
---

# Stream C — tasks фазы 2

Исполнять **после** зелёного лаунчера на implement. Итерация self-check
продуктовый код `POST /api/price` **не** пишет. После PASS и зелёного
лаунчера — implement по T005+ в файлах владения.

Спека: [stream-c-phase2.md](stream-c-phase2.md). План:
[stream-c-plan.md](stream-c-plan.md). Контракт payload:
[plans/api-contract.md](../../plans/api-contract.md) (не копировать сюда).
Конституция: [knowledge/invariants/](../../knowledge/invariants/). Каркаса
`.specify/` нет и заводить нельзя. Бандл остаётся `specs/001-burger-mvp/`.

Приоритет источников: `schema.sql` > `plans/api-contract.md` >
`plans/00-orchestration.md` §0 > `mvp-spec.md`.

## СТОП этой итерации (self-check)

Отчёт лаунчеру и **стоп implement**. Не писать `backend/routers/price.py`
и `tests/test_price*` в этом шаге. Не трогать остальные `stream-c-*.md`.
Не создавать `.specify/` и `specs/002-*`.

## Файлы реализации (код позже, сейчас не писать)

Разрешено **только**:

| Путь | Роль |
|---|---|
| `backend/routers/price.py` | `POST /api/price`, SSE |
| `backend/services/*price*` | опционально, **если** лаунчер разрешит новую папку; иначе вся логика в роутере |
| `tests/test_price*` | контракт и сценарии 1–6 |

**Запрещено трогать:** `backend/app.py`, `lib/**`, `backend/routers/places.py`,
`frontend/**`, `schema.sql`, `fixtures/**`, `nginx/**`. Не копировать
`lib/tutu_mcp.py` — только импорт.

Роутер уже подключён в `app.py` (`include_router(price.router)`). Шов не менять.

Эталонный `cluster_id` брать из [fixtures/etalon_1.json](../../fixtures/etalon_1.json)
(пара хабов). **Не** `places[0]`: одиночный Ярославль
(`fixtures/backup_single_hub.json`) может стоять выше пары.

## Инварианты (сверка до кода)

| Инвариант | Как задача соблюдает | Нарушение = стоп |
|---|---|---|
| [phase-boundary](../../knowledge/invariants/phase-boundary.md) | Сеть Tutu только в `/api/price`, только после отбора топ-5. SSE, не sync. Окна лениво (V3). Первый `leg` ~3 с, не после всех плеч. | Сеть в `/api/places`; пачка SSE; 140 окон сразу |
| [sellability-is-edge](../../knowledge/invariants/sellability-is-edge.md) | Продаваемость из таблицы `leg` (направленное ребро). Обратное плечо — отдельная проверка. Составной маршрут не изобретать. | Флаг узла как «билет есть»; один вызов на туда-обратно |
| [guard-before-price](../../knowledge/invariants/guard-before-price.md) | Любой `search_*` / `probe_destination` через `lib.tutu_mcp` **до** события с ценой. `misresolved` ≠ `not_sellable`. | Свой `check_resolve`; цена до guard |
| [source-of-truth-precedence](../../knowledge/invariants/source-of-truth-precedence.md) | Payload и 404 — только api-contract. DDL — schema.sql. Guard — lib. | Локальный контракт/схема в роутере |

`SC-ranking` — поток B, не смешивать. `SC-price` (4342 RUB ±15%) **не** валит
G10. До live Tutu на **обоих** сценариях (эталон №1 и запасной одноузловой)
`price_status` = `fixture-confirmed`.

## MVP на G10 (час 26)

Срезы плана 1–5. Минимум: HTTP-контракт + `resolved` + ≥1 `leg` + `done`
**по одному**; `fixture-confirmed`. Сценарии 1, 2, 6.

После G10 (не падение сборки): отель `stay_total`, `checkout_url` as-is,
обратные плечи (сценарий 4), ленивые окна (сценарий 5), кэш-фолбэк.

---

## Phase 1: Setup (не story)

Цель: убедиться, что шов и фикстуры на месте; код не писать, пока лаунчер
не дал зелёный на implement.

**Independent Test:** `backend/routers/price.py` существует и пустой;
`backend/app.py` уже делает `include_router(price.router)`;
`fixtures/etalon_1.json` содержит парный `cluster_id`; `test_guard.py` зелёный.

- [ ] T001 Confirm empty `POST` owner is `backend/routers/price.py` and that `backend/app.py` already includes `price.router` (read-only; do not edit `app.py`)
- [ ] T002 Confirm etalon pair `cluster_id` in `fixtures/etalon_1.json` (not `places[0]`, not `fixtures/backup_single_hub.json` alone) for later `/api/price` requests
- [ ] T003 Confirm golden rows exist for C start: `fixtures/rows/legs.json`, `fixtures/rows/hotel_cache.json`, `fixtures/rows/clusters.json`, `fixtures/rows/hubs.json` (read-only; do not edit fixtures)
- [ ] T004 Confirm guard seam is import-only: `lib/tutu_mcp.py` exports `TutuMcp`, `check_resolve`, `price_is_absent`; timeout >= 30 s and concurrency cap 4 already in constructor (do not copy the module)

---

## Phase 2: Foundational (блокирует все сценарии)

Цель: каркас `POST /api/price` в том же FastAPI: поля запроса, lookup
`cluster.id` (G2, радиус не в запросе), 404 до SSE, заголовки как у
`/_sse_smoke`. Живой Tutu не обязателен.

**Independent Test:** неизвестный ASCII id (`c:no-such-hub`) → HTTP **404**,
тело не `text/event-stream` и не `event: warning`. Известный id из таблицы
`cluster` открывает SSE (`Cache-Control: no-cache`, `X-Accel-Buffering: no`).

- [ ] T005 Add request model for FR-C1 fields (`cluster_id`, `origin`, `days`, `month`, `adults`, `children_ages`, `budget_scope`) in `backend/routers/price.py` (payload shape only from `plans/api-contract.md`)
- [ ] T006 Open SQLite via `BURGER_DB` (default `data/burger.db`); read `cluster` by public `id` only (PK is `(id, radius_km)` — any row with that id is enough) in `backend/routers/price.py`
- [ ] T007 Unknown `cluster_id` → HTTP 404 **before** `StreamingResponse`; do not emit SSE `warning` for missing cluster (`backend/routers/price.py`)
- [ ] T008 SSE helper: one frame per yield (`event:` + `data:` + blank line); `await` between frames like `/_sse_smoke` so G6 does not get one blob at the end; headers `Cache-Control` / `X-Accel-Buffering: no`; `media_type` `text/event-stream` in `backend/routers/price.py`
- [ ] T009 Import `TutuMcp`, `check_resolve`, `price_is_absent` from `lib.tutu_mcp` in `backend/routers/price.py` (forbid a local `check_resolve` / MCP parser in this file; pass `timeout_s>=30`, `max_concurrency<=4`)
- [ ] T010 Load golden fixtures in tests via `lib.load_fixtures.load_golden_fixtures` + temp `BURGER_DB` in `tests/test_price.py` (do not edit `lib/**`)
- [ ] T011 [P] Contract tests for 404 vs SSE open in `tests/test_price.py` (unknown id; etalon id from `fixtures/etalon_1.json`)

---

## Phase 3: User Story 1 — счастливый путь (эталон на фикстурах) (P1)

**Goal:** origin Москва, 3 дня в `2026-10`, 1 взрослый, `cluster_id` пары из
`fixtures/etalon_1.json` → поток цен по мере готовности.

**Independent Test:** `curl -N` (или TestClient по кадрам): сначала
`event: resolved` (guard `ok`), затем отдельно `event: leg` (~3 с, не после
всех плеч), затем `breakdown` (если цена уже ушла) и `event: done`. Не пачка
в конце. `price_status` = `fixture-confirmed`. Сумма 4342 **не** критерий
pass/fail.

- [ ] T012 [P] [US1] Write failing tests for resolved / first leg / breakdown / done as **separate** SSE frames (not one concatenated body) in `tests/test_price.py` using `cluster_id` from `fixtures/etalon_1.json`
- [ ] T013 [US1] Emit `resolved` (origin + hubs, `guard` in `{ok, misresolved}`) **before** any priced `leg` in `backend/routers/price.py`
- [ ] T014 [US1] Read directed `leg` / `route_cache` for first hop (fixture Moscow→Yaroslavl); yield first `leg` after ~3 s pause; do not wait remaining hops (`backend/routers/price.py`)
- [ ] T015 [US1] Drop mode if `price_is_absent` / price `0` RUB; `source` in `{live, cache}`; `checkout_ref` opaque pass-through (`backend/routers/price.py`)
- [ ] T016 [US1] If any price was shown, emit `breakdown` **before** `done`; both carry `price_status: fixture-confirmed` (do not treat 4342 as `SC-price`) in `backend/routers/price.py`
- [ ] T017 [US1] Emit `done` `{ok, cluster_id, price_status}` matching request id from `fixtures/etalon_1.json` in `backend/routers/price.py`

---

## Phase 4: User Story 2 — неизвестный кластер (P1, G10)

**Goal:** id не из таблицы `cluster` не открывает «успешный» поток цен.

**Independent Test:** `POST /api/price` with `cluster_id` `c:no-such-hub` →
HTTP **404**. No `event: warning`. No `text/event-stream`.

Depends on T007. Story-level tests may already live in T011; this phase is
the acceptance lock.

- [ ] T018 [US2] Assert 404 body is not an SSE warning stream in `tests/test_price.py`
- [ ] T019 [US2] Keep lookup-only 404 (do not log unknown id as Tutu misresolve) in `backend/routers/price.py`

---

## Phase 5: User Story 6 — G10 сквозной (P1)

**Goal:** тот же парный `cluster_id`, что должен вернуть `/api/places` для
эталона, но **взятый из** `fixtures/etalon_1.json`, не `places[0]`.

**Independent Test:** подставить id из эталона в `/api/price`; получить
`resolved` + ≥1 `leg` + `done` по одному; `fixture-confirmed`. Топ-5 и
`SC-ranking` — ответственность B. Прямой успех только на `:8000` при красном
nginx **не** закрывает G6-путь (приёмка человека через nginx).

- [ ] T020 [US6] G10 test: etalon `cluster_id` from `fixtures/etalon_1.json` (explicitly not backup single-hub id) in `tests/test_price.py`
- [ ] T021 [US6] Lock pair click: assert the priced `cluster_id` equals `fixtures/etalon_1.json` (two hubs) and is **not** `fixtures/backup_single_hub.json`; do **not** take `places[0]`. Comment that demo/G10 clicks the pair card because single-hub Yaroslavl MAY rank above (`tests/test_price.py`)
- [ ] T022 [US6] Do not fail tests on breakdown total 4342; fail only if `price_status` is not `fixture-confirmed` before live both scenarios (`tests/test_price.py`)

---

## Phase 6: User Story 3 — мисрезолв origin или хаба (P2)

**Goal:** омоним («Ростов» без полного имени) не показывает чужие цены.

**Independent Test:** guard из `lib.tutu_mcp` отбрасывает выдачу **до** `leg`
с ценой; уходит `warning` `misresolved`; строка в `misresolve_log` пишется
**lib**, не своим INSERT; статус не схлопнут в `not_sellable`.

- [ ] T023 [P] [US3] Tests: misresolve warning, no priced leg from rejected region, not collapsed to `not_sellable` in `tests/test_price.py` (reuse `fixtures/tutu/rostov.json` / G5 raw; do not copy guard)
- [ ] T024 [US3] Call `check_resolve` / `TutuMcp.probe_destination` before emitting any `leg` price in `backend/routers/price.py`
- [ ] T025 [US3] On guard fail: `warning` `{code: misresolved, ...}`; skip that hop price; do not write `hub.probe_status` (`backend/routers/price.py`)

---

## Phase 7: User Story 4 — одностороннее плечо B2 (P2)

**Goal:** продаваемость — ребро. Торжок→Москва `no_route` при Тверь→Торжок ok.

**Independent Test:** читать `leg` по `(origin_hub, dest_hub)`; обратное плечо
— **отдельный** lookup/вызов на каждый город; нет ряда / `no_route` →
`warning` `no_route`; составной путь не строить; карточку не удалять.

- [ ] T026 [P] [US4] Tests from `fixtures/rows/legs.json` Torzhok→Moscow `no_route` vs Tver→Torzhok `ok` in `tests/test_price.py`
- [ ] T027 [US4] Ticketability from table `leg` only (ignore `hub.sellable_modes` / `reachable_from_any` as hop truth) in `backend/routers/price.py`
- [ ] T028 [US4] Reverse hop: **separate** directed `leg` lookup / `call_tool` per city (A→B is not B→A); if last city has no return, try previous city; never one round-trip search and never invent a composite (`backend/routers/price.py`)
- [ ] T029 [US4] Emit `warning` `no_route` with `leg.from_hub` / `leg.to_hub`; keep stream `ok` (card greys in UI — Worker D) in `backend/routers/price.py`

---

## Phase 8: User Story 5 — окна дат лениво V3 (P2)

**Goal:** первое недельное окно показать; остальные догрузить. Не 140
синхронных вызовов. Budget без окон: 35 на топ-5 (ингест/фаза 1, не C в G10).

**Independent Test:** первый `leg` приходит с **первого** окна; следующие окна
не блокируют первый кадр. Cap 4 живёт в `TutuMcp`, C его не поднимает.

- [ ] T030 [P] [US5] Tests: first window yields a `leg` before later windows are computed in `tests/test_price.py`
- [ ] T031 [US5] Lazy windows: N days in `month`; probe one weekly window first; enqueue the rest after first `leg` (`backend/routers/price.py` or `backend/services/*price*` if allowed)
- [ ] T032 [US5] Do not fire 140 calls up front; G10 may use the single fixture window `2026-10-09` (+ neighbor dates in `leg`) (`backend/routers/price.py`)

---

## Phase 9: Polish — hotel, checkout, cache (после G10, не валит сборку)

**Goal:** закрыть FR отеля и чекаута без снятия `fixture-confirmed`.

**Independent Test:** `hotel.min_price` = `stay_total`, не `nights * nightly`;
`checkout_url` байт-в-байт как в payload; кэш читается до `call_tool`;
промах + нет сети → `warning` `cache_fallback`, `source: cache`.

- [ ] T033 [P] Hotel tests: `price_basis: stay_total`, do not multiply by `nights`; payload from `fixtures/rows/hotel_cache.json` in `tests/test_price.py`
- [ ] T034 Emit `hotel` per overnight hub after first `leg` when `budget_scope` is `all` (G10 does not require `hotel`) in `backend/routers/price.py`
- [ ] T035 Checkout: `create_checkout_link` args = opaque `checkout_ref`; reproduce `checkout_url` exactly; avia pass `passengers_full` / `child` / `infant` in `backend/routers/price.py`
- [ ] T036 Skip `checkout` event if no URLs; if present, one `checkout` event with `items[]` (`backend/routers/price.py`)
- [ ] T037 Read `route_cache` / `hotel_cache` **before** live `call_tool`; live only inside `/api/price`; never from `/api/places` (`backend/routers/price.py`)
- [ ] T038 Soft-fail: compare `modes_requested` vs `modes_summary` and log; fast empty Tutu (0.1–0.8 s) = missing `*_id`, not free fare (`backend/routers/price.py`)
- [ ] T039 String literals in product/test Python stay ASCII; Cyrillic values come from fixtures/DB (`backend/routers/price.py`, `tests/test_price.py`)
- [ ] T040 Re-run `tests/test_guard.py` — if red, **stop** (do not patch `lib/**`). Then run `tests/test_price*`. Fail implement if `backend/routers/price.py` defines its own `check_resolve` or copies `lib/tutu_mcp.py`

---

## Dependencies

```text
Phase 1 (T001-T004)  →  Phase 2 (T005-T011)
                              │
                              ├─ US2 T018-T019 (404 lock; uses T007)
                              │
                              └─ US1 T012-T017 (happy path)
                                        │
                                        └─ US6 T020-T022 (G10; needs US1 events)
                                                  │
                        G10 candidate ────────────┘
                                                  │
                    post-G10: US3 T023-T025 (needs guard import T009)
                              US4 T026-T029 (needs leg read T014)
                              US5 T030-T032 (must not block US1 first leg)
                              Polish T033-T040 (hotel/checkout/cache)
```

US2 можно закрывать параллельно с US1 после T007. US3/US4/US5 не блокируют
G10, но блокируют полный FR. US6 не вызывает `/api/places` и не берёт
`places[0]`.

## Parallel opportunities

- T011 / T012 / T018 / T020 — тесты в `tests/test_price.py` лучше **последовательно** в одном файле (один модуль).
- T023, T026, T030, T033 — `[P]` относительно продукта, если тесты пишутся до кода фазы.
- Роутер `backend/routers/price.py` — **не** параллелить несколько агентов (один файл).
- `backend/services/*price*` — параллелить с роутером только после явного разрешения новой папки.

## Independent tests (сводка)

| Story | Independent Test |
|---|---|
| US1 | etalon id → `resolved`, затем `leg` ~3 с, затем `done`; не пачка; `fixture-confirmed` |
| US2 | unknown id → HTTP 404, не SSE |
| US3 | guard reject → `warning` misresolved, цены омонима нет |
| US4 | `leg` directed; reverse separate; `no_route` warning; no composite |
| US5 | first window visible; later windows lazy |
| US6 | same pair `cluster_id` from `etalon_1.json`, not `places[0]`; G10 triple; not SC-price |

## Implementation strategy (когда лаунчер даст зелёный)

1. TDD: `tests/test_price.py` на 404 + etalon SSE до наполнения роутера.
2. Foundational + US1 + US2 + US6 → кандидат G10.
3. US3–US5 и polish — после G10, тем же файловым контуром.
4. Живой Tutu и снятие `fixture-confirmed` — только после **обоих** сценариев
   (эталон + backup). Не в этой очереди tasks как pass G10.
5. Если `tests/test_guard.py` красный — стоп, эскалация архитектору, не чинить
   `lib/**`.

## SSE event names (порядок в потоке, не пачка)

`resolved` → `leg` (первый ~3 с) → далее по готовности `leg` / `hotel` /
`warning` → при показанной цене `breakdown` → `checkout` если есть URL →
`done`. Имена: `resolved` | `leg` | `hotel` | `breakdown` | `checkout` |
`warning` | `done`. Payload — только api-contract.

## Self-check (после tasks, до implement)

Конституция = [knowledge/invariants/](../../knowledge/invariants/), не `.specify/`.
Продуктовый код в этом шаге не писался. Дыры, которые закрыты правкой tasks:
T008/T012 (кадры SSE не пачкой), T021 (id пары — assert, не только комментарий),
T009/T040 (guard только из lib), T028 (обратное плечо отдельным вызовом).

| Check | Lock | Result |
|---|---|---|
| T021 клик пары | `cluster_id` = `fixtures/etalon_1.json` (два хаба); **не** `places[0]`; **не** `backup_single_hub.json`. Комментарий: в демо кликать карточку пары, одиночный Ярославль может быть выше. C UI не пишет. | PASS |
| Guard из lib, не копия | T004, T009, T024, T040: `from lib.tutu_mcp import ...`; свой `check_resolve` в `price.py` = стоп | PASS |
| SSE по одному | T008 `await` между кадрами; T012/T014 первый `leg` ~3 с не после всех плеч; имена `resolved\|leg\|hotel\|breakdown\|checkout\|warning\|done` | PASS |
| `fixture-confirmed` | T016, T017, T022; 4342 не валит G10; `SC-price` только после live **обоих** сценариев | PASS |
| Обратное плечо отдельно | T027 `leg` ребро; T028 отдельный lookup/`call_tool` на город; не один round-trip; не составной маршрут | PASS |
| phase-boundary | Tutu только `/api/price` (T037); окна лениво T031–T032; сеть не в `places.py` (файл не трогать) | PASS |
| sellability-is-edge | T027–T029 | PASS |
| guard-before-price | T013 до цены; T024 до `leg` | PASS |
| source-of-truth-precedence | payload/404 = api-contract (T005/T007); DDL не копировать; mvp-spec §5/§12 не читать как истину | PASS |
| FR-C1..C20 coverage | каждый FR имеет ≥1 task (см. таблицу Coverage ниже) | PASS |
| Residual (не дыра G10) | порядок городов по географии — эталонные `leg` T014; `hours_unknown` не в G10; hotel/checkout Phase 9 | PASS (note) |

**Coverage FR → tasks**

| FR | Tasks |
|---|---|
| FR-C1 request fields | T005 |
| FR-C2 unknown id 404 | T007, T011, T018, T019 |
| FR-C3 G2 id (set of hubs) | T002, T006, T021 |
| FR-C4 SSE names one-by-one | T008, T012 |
| FR-C5 first leg ~3 s | T014 |
| FR-C6 guard import-only | T004, T009, T024, T040 |
| FR-C7 misresolved ≠ not_sellable | T013, T023, T025 |
| FR-C8 sellability = `leg` | T027 |
| FR-C9 reverse per city | T028, T029 |
| FR-C10 no composite | T028 |
| FR-C11 lazy windows V3 | T031, T032 |
| FR-C12 checkout_url as-is | T035, T036 |
| FR-C13 hotel stay_total | T033, T034 |
| FR-C14 price 0 = absence | T015 |
| FR-C15 timeout ≥ 30, cap 4 | T004, T009 |
| FR-C16 fixture-confirmed | T016, T017, T022 |
| FR-C17 fixtures until A | T003, T010 |
| FR-C18 cache before live | T037 |
| FR-C19 breakdown before done | T016 |
| FR-C20 G10 triple | T020, T021 |

**Вердикт self-check:** PASS. Готов к implement: **да** (после зелёного лаунчера).
Код в этой итерации не писать.

## Gates (этот артефакт / итерация)

| Gate | Result | Notes |
|---|---|---|
| Specify C exists | PASS | `stream-c-phase2.md` not rewritten |
| Plan / research / data-model / quickstart | PASS | existing files left intact |
| Tasks + Self-check | PASS | this file; T008/T009/T012/T021/T028/T040 tightened |
| `.specify/` created | FAIL (forbidden) | skipped by design |
| `specs/002-*` created | FAIL (forbidden) | skipped by design |
| Product `/api/price` implemented | FAIL | STOP this iteration; ready next |
| `SC-price` / 4342 as G10 fail | FAIL (forbidden) | tasks forbid it |
| Invariants named | PASS | phase-boundary, sellability-is-edge, guard-before-price, source-of-truth-precedence |
| Etalon id source | PASS | `fixtures/etalon_1.json`, not `places[0]` (T021 assert) |
| File ownership listed | PASS | `price.py`, optional `*price*` service, `tests/test_price*` |
| `test_guard.py` / lib seam | PASS | import only; red guard = stop |
| Self-check five locks | PASS | pair click, lib guard, SSE frames, fixture-confirmed, reverse hop |

## Notes

- 40 задач (T001–T040). G10 MVP = Phase 1–5 (T001–T022).
- Строковые литералы в будущем Python — ASCII; кириллица только из фикстур/БД.
- Merge-back worktree: `/apply-worktree`. Cleanup: `/delete-worktree`.
