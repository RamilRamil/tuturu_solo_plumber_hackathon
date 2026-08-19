---
type: Tasks
title: Stream D — tasks фронта
description: Spec Kit tasks для потока D (меню, карта, SSE). Implement только после зелёного лаунчера. Код в этой итерации не писать.
tags: [spec-kit, "001", stream-d, tasks]
timestamp: 2026-08-19T17:25:00Z
feature: 001-burger-mvp
status: draft
spec: stream-d-frontend.md
plan: stream-d-plan.md
---

# Tasks: Stream D — фронт

**Input**: [stream-d-frontend.md](stream-d-frontend.md), [stream-d-plan.md](stream-d-plan.md), [stream-d-data-model.md](stream-d-data-model.md), [stream-d-research.md](stream-d-research.md), [stream-d-quickstart.md](stream-d-quickstart.md)

**Prerequisites**: план и спека приняты. Конституция = [knowledge/invariants/](../../knowledge/invariants/). Каркаса `.specify/` нет и **не заводить**. `specs/002-*` **не** создавать. Существующие `stream-d-*.md` **не** переписывать.

**Tests**: автотесты не запрошены. Приёмка — ручной [stream-d-quickstart.md](stream-d-quickstart.md).

**Эта итерация:** только этот файл. Vite / npm / `frontend/src` — **после** зелёного лаунчера.

---

## Format

`- [ ] Tnnn [P?] [USn?] Description with file path`

- `[P]` — можно параллельно (разные файлы, нет зависимости на неготовый артефакт)
- `[US1]`…`[US5]` — только фазы user stories
- Setup / Foundational / Polish — без story label

---

## Path conventions (владение D)

Реализация **только** `frontend/**`:

```
frontend/
  Dockerfile              # можно; docker-compose.yml нельзя
  nginx.conf              # nginx контейнера frontend, не репо nginx/
  package.json            # npm, Node 20
  vite.config.ts
  index.html
  public/mocks/           # JSON ответов = api-contract, не legs[] фикстуры as-is
  src/
    main.tsx
    App.tsx
    types/contract.ts
    catalog/ingredients.ts
    api/client.ts
    api/places.ts
    api/price.ts
    api/sse.ts
    mocks/priceStream.ts
    share.ts
    components/
      ModeToggle.tsx
      IngredientMenu.tsx
      RadiusSlider.tsx
      PlaceList.tsx
      PlaceCard.tsx
      ClusterMap.tsx
      OriginForm.tsx
      PriceStream.tsx
      AlmostFits.tsx
      CoverageMap.tsx
      HoursStatus.tsx
```

**Не трогать:** `backend/**`, `lib/**`, `schema.sql`, `fixtures/**`, `ingest/**`, `plans/**`, `docker-compose.yml`, `nginx/**` (шов архитектора / G6), `knowledge/**`, другие `specs/001-burger-mvp/stream-d-*.md`.

Канон контракта: [plans/api-contract.md](../../plans/api-contract.md). Моки = объекты Place / SSE, не slug `yar-rostov`.

Стек G8: React **18** + Vite + TypeScript + **MapLibre**, npm, Node **20**. Leaflet **запрещён**.

Край: клиент ходит на `/api/` того же origin (nginx). Локалка compose `:80`. Демо `:8080`. Чужой домен не край.

---

## Invariant gates (сверка до implement)

| Инвариант | Следствие в задачах | Gate |
|---|---|---|
| [inversion-direction-is-output](../../knowledge/invariants/inversion-direction-is-output.md) | Origin не условие фазы 1. Поле города нет/неактивно, пока нет мест. `POST /api/places` без origin. | **PASS** |
| [phase-boundary](../../knowledge/invariants/phase-boundary.md) | US1 без цен/`breakdown`/checkout. SSE только после origin по **кликнутой** карточке пары, не по `places[0]`. События по одному, не пачка. | **PASS** |
| [pairs-are-not-cut](../../knowledge/invariants/pairs-are-not-cut.md) | Карточка пары эталона кликабельна. При пожаре режется «почти подходит», не пара. Запасной одноузловой бургер — страховка. | **PASS** |
| [coverage-dominates-ranking](../../knowledge/invariants/coverage-dominates-ranking.md) | UI **не** сортирует `places[]` (T016/T018). Видимая полоса до 5 — порядок B as-is. Позиция пары в моке **не** гейт D. | **PASS** |

**SC-D2 (UI-гейт, не SC-ranking бэкенда, не Independent Test, не G10 D):** клиент **не сортирует** `places[]` (T016/T018). SSE идёт с **кликнутой** карточки пары (`cluster_id` из `etalon_1.json` = `c:Ростов|Ярославская область,Ярославль|Ярославская область`), даже если одиночный Ярославль выше и даже если пара не в первых пяти мока (T026). Мок `places-etalon.json` **не обязан** класть пару в топ-5 и не самопроверяет ранжирование.

---

## Phase 1: Setup (каркас Vite)

**Goal:** placeholder `frontend/index.html` заменить на Vite app внутри `frontend/**`. Compose-шов снаружи не менять.

**Independent Test:** `frontend/package.json` объявляет React 18 + Vite + TS + maplibre-gl; Leaflet отсутствует; `frontend/Dockerfile` собирает static для nginx:80 контейнера frontend.

- [ ] T001 Replace placeholder with Vite + React 18 + TypeScript app in `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/index.html`, `frontend/src/main.tsx`
- [ ] T002 [P] Pin npm scripts (`dev` / `build`), Node 20, and `maplibre-gl` (not Leaflet) in `frontend/package.json`
- [ ] T003 [P] Multi-stage `frontend/Dockerfile` (node:20 build → nginx:1.27 serve `dist`); do not edit `docker-compose.yml`
- [ ] T004 [P] SPA fallback in `frontend/nginx.conf` (frontend container only, not repo `nginx/nginx.conf`)
- [ ] T005 Proxy `/api` and `/_sse_smoke` to same-origin nginx in `frontend/vite.config.ts` (live local `:80`)

---

## Phase 2: Foundational (блокирует все stories)

**Goal:** типы контракта, каталог меню, mock/live клиент, шелл без origin.

**Independent Test:** тумблер mock/live на экране; в mock режиме запросы не требуют живой backend; поле origin отсутствует или disabled до мест.

- [ ] T006 Project Place / Hub / Coverage / SSE event types bit-for-bit with api-contract in `frontend/src/types/contract.ts`
- [ ] T007 [P] Bake menu catalog (`id`, `name_ru`, `group`, `density_label`, `density_measured`) from `ingredients.yaml` into `frontend/src/catalog/ingredients.ts` (no new `/api` menu endpoint)
- [ ] T008 [P] Mock `POST /api/places` bodies as Place objects (etalon + backup) in `frontend/public/mocks/places-etalon.json` and `frontend/public/mocks/places-backup.json` — not fixture `legs[]` as-is, not `yar-rostov`; mock is **not** required to put the pair in top-5
- [ ] T009 Mock SSE emitter with ~1s pauses (`resolved` \| `leg` \| `hotel` \| `breakdown` \| `checkout` \| `warning` \| `done`) in `frontend/src/mocks/priceStream.ts`
- [ ] T010 Shared fetch client mock vs live (`POST /api/places`, `POST /api/price`) in `frontend/src/api/client.ts`
- [ ] T011 [P] Mode toggle `mock` / `live` (FR-D17) in `frontend/src/components/ModeToggle.tsx`
- [ ] T012 App shell: burger + radius first, origin hidden/inactive (inversion) in `frontend/src/App.tsx`

---

## Phase 3: User Story 1 — Бургер и места без origin (P1) — MVP

**Goal:** меню с плотностью, ползунок 50/100/150, карта + карточки (видимая полоса до 5, порядок бэка) **без цен и без origin**.

**Independent Test:** [stream-d-quickstart.md](stream-d-quickstart.md) сценарий A + C. Поле origin нет/неактивно. Цен на карточках нет. UI не сортирует `places[]`. «Пара в топ-5 мока» — **не** Independent Test.

**Acceptance mapped:** FR-D1…D6, SC-D1, SC-D2, SC-D3, SC-D5.

- [ ] T013 [US1] Ingredient cards (~20 from catalog) plus disabled «другое» (F5) in `frontend/src/components/IngredientMenu.tsx`
- [ ] T014 [P] [US1] Visible `density_label` on **every** card (`dense` / `medium` / `rare` / `absent_in_region`; null yaml → visible «нет замера») and optional `density_measured` (370 / 0) in `frontend/src/components/IngredientMenu.tsx`
- [ ] T015 [P] [US1] Discrete radius snaps 50 / 100 / 150, max 150, default 100, show `total_found` per step in `frontend/src/components/RadiusSlider.tsx`
- [ ] T016 [US1] `POST /api/places` without origin; empty ingredients → no request; do **not** re-sort `places[]` in `frontend/src/api/places.ts`
- [ ] T017 [US1] Place card: hubs, `diameter_km`, `coverage.matched` / `missing`, rarity **as returned** (`rarity.rank` / `rarity.total_places_with_combo`, no «редкая связка» on etalon), objects; **no** price, budget, breakdown, checkout in `frontend/src/components/PlaceCard.tsx`
- [ ] T018 [US1] Visible strip of up to 5 full-coverage cards in backend order (do **not** re-sort); cards beyond the strip stay clickable (pair may sit below #5) in `frontend/src/components/PlaceList.tsx`
- [ ] T019 [US1] MapLibre GL map (not Leaflet): objects of the **selected** cluster beside cards in `frontend/src/components/ClusterMap.tsx`
- [ ] T020 [US1] **SC-D2:** client does not sort `places[]`; pair card (`cluster_id` `c:Ростов|Ярославская область,Ярославль|Ярославская область` from `etalon_1.json`) is clickable for SSE even if single Yaroslavl is higher and even if the pair is not in the mock first five; `frontend/public/mocks/places-etalon.json` is **not** required to place the pair in top-5 and is not a ranking test — keep pair selectable in `frontend/src/components/PlaceList.tsx`
- [ ] T021 [US1] **SC-D3:** combo `ancient_temple` + `ruins` shows single-hub `c:Ярославль|Ярославская область` in backend/mock order; «in mock top-5» is not SC-D3 in `frontend/public/mocks/places-backup.json` and `frontend/src/components/PlaceList.tsx`
- [ ] T022 [US1] Same hub set at 50 / 100 / 150 keeps the same `cluster_id` (radius not in id) in `frontend/src/api/places.ts`

---

## Phase 4: User Story 2 — Origin и SSE по мере событий (P1) — G10

**Goal:** после клика по карточке (пара эталона) — origin/даты/состав → инкрементальный `/api/price`.

**Independent Test:** [stream-d-quickstart.md](stream-d-quickstart.md) сценарий B. Глазами: `resolved`, затем ≥1 `leg`, затем `done` с паузами, не пачкой. Тот же `cluster_id` **кликнутой** пары (не `places[0]`, не «первая в топ-5 мока»).

**Acceptance mapped:** FR-D7…D9, FR-D14, FR-D15, SC-D4, SC-D8.

- [ ] T023 [US2] Origin form (Moscow / days / `YYYY-MM` / `adults` / `children_ages` / `budget_scope` default `transport`) enabled only after a place card is selected in `frontend/src/components/OriginForm.tsx`
- [ ] T024 [US2] Incremental SSE parser over `fetch` POST body stream (not buffered EventSource-GET, not wait-for-done) in `frontend/src/api/sse.ts`
- [ ] T025 [US2] Render events as they arrive (`resolved`, `leg`, `hotel`, `breakdown`, `checkout`, `warning`, `done`) in `frontend/src/components/PriceStream.tsx`
- [ ] T026 [US2] Price request uses `cluster_id` of the **clicked pair card**, even if `places[0]` is single Yaroslavl **and even if the pair is not in the mock first five**, in `frontend/src/api/price.ts` and `frontend/src/App.tsx`
- [ ] T027 [US2] Layout transport / lodging / total required before treating stream as complete; `checkout_url` opened as-is (no rebuild/trim/host swap) in `frontend/src/components/PriceStream.tsx`
- [ ] T028 [US2] Show `price_status: fixture-confirmed` until live Tutu for **both** etalon and backup; do not label 4342 as SC-price in `frontend/src/components/PriceStream.tsx`
- [ ] T029 [P] [US2] Leg `price == 0` is absence (not «0 RUB»); `hotel.min_price` is `stay_total` (do not multiply by `nights`) in `frontend/src/components/PriceStream.tsx`
- [ ] T030 [P] [US2] Unknown `cluster_id` → HTTP 404 UI, not SSE `warning`; `guard=misresolved` is not `not_sellable` in `frontend/src/api/price.ts`
- [ ] T031 [US2] Mock delays: first `leg` ~3s after request, ~1s between later `event:` lines in `frontend/src/mocks/priceStream.ts`

---

## Phase 5: User Story 3 — Серые карточки и «почти подходит» (P2)

**Goal:** после origin список не укорачивается удалением; неполное покрытие отдельно.

**Independent Test:** [stream-d-quickstart.md](stream-d-quickstart.md) сценарий D. Число карточек то же; недостижимые серые с причиной.

**Acceptance mapped:** FR-D10, FR-D11, SC-D6. B4: резать «почти подходит» первым.

- [ ] T032 [US3] Unreachable after origin stay visible, grey, with reason; never splice out of the list in `frontend/src/components/PlaceCard.tsx` and `frontend/src/App.tsx`
- [ ] T033 [P] [US3] `probe_status=not_sellable` → mark «дальше своим ходом»; card remains in `frontend/src/components/PlaceCard.tsx`
- [ ] T034 [US3] Non-empty `coverage.missing` → separate «почти подходит» block, not mixed into full top-5 in `frontend/src/components/AlmostFits.tsx`
- [ ] T035 [US3] Timeline fire (B4): drop `AlmostFits` first; keep etalon pair card; do not hide two-hub clusters in `frontend/src/components/AlmostFits.tsx`

---

## Phase 6: User Story 4 — Честная дыра покрытия (P2, после G10)

**Goal:** жюри отличает «регион не залит» от «комбинации нет».

**Independent Test:** залитые области подписаны; дыры штриховкой/эквивалентом; пустая фаза 1 в дыре не называется «таких мест нет».

**Acceptance mapped:** FR-D12, SC-D7. Список регионов от A (D3), фронт не выдумывает канон; до live A — явный мок D3.

- [ ] T036 [US4] Coverage panel «данные загружены по N областям» plus hole hatch/legend in `frontend/src/components/CoverageMap.tsx`
- [ ] T037 [US4] Poor/empty phase 1 in unloaded region labeled as ingest hole, not missing ingredients, in `frontend/src/components/CoverageMap.tsx` and `frontend/src/App.tsx`

---

## Phase 7: User Story 5 — Часы объекта (P3)

**Goal:** три честных состояния; нет тега ≠ закрыто. Полный веб-поиск часов **не** в 001.

**Independent Test:** объект без `opening_hours` показывает `unknown`, не `closed`.

- [ ] T038 [US5] Render `hours_status` as `open` / `closed` / `unknown` in `frontend/src/components/HoursStatus.tsx`
- [ ] T039 [US5] Null/empty `opening_hours` maps to `unknown` (not `closed`) in `frontend/src/components/HoursStatus.tsx`
- [ ] T040 [US5] Do not implement full web hours lookup (F4); no extra network on object hover in `frontend/src/`

---

## Phase 8: Polish (после G10)

**Goal:** шеринг, live через nginx, ручной прогон quickstart.

- [ ] T041 Share query percent-encodes the **whole** `cluster_id` (UTF-8), not a path segment, in `frontend/src/share.ts`
- [ ] T042 [P] Restore burger + origin + dates + same `cluster_id` from query in `frontend/src/App.tsx`
- [ ] T043 Cache-fallback phase 2 shows source/time mark, not unlabeled live, in `frontend/src/components/PriceStream.tsx`
- [ ] T044 Manual G10 pass of quickstart A/B/C on mock, then live toggle against same-origin `/api/` (compose `:80` / demo `:8080`)

---

## Dependencies

```
Phase 1 Setup
    → Phase 2 Foundational (types, mocks, mock/live, shell)
        → Phase 3 US1 (P1)     ← MVP карта без origin
            → Phase 4 US2 (P1) ← G10: SSE на cluster_id пары
                → Phase 5 US3 (P2) серые + почти подходит
                → Phase 6 US4 (P2) карта покрытия (после G10)
                → Phase 7 US5 (P3) часы
                    → Phase 8 Polish (share, live)
```

- US1 не зависит от US2 (инверсия: места без origin).
- US2 зависит от US1: нужен клик по карточке пары (не обязательно из видимого топ-5).
- US3 зависит от списка US1 и момента origin US2.
- US4 / US5 не блокируют G10.
- T016/T018/T020 (не сортировать + пара кликабельна) обязательны до T026 (SSE на id кликнутой пары).
- «Пара в топ-5 мока» не Independent Test и не критерий G10 D.

---

## Parallel opportunities

- After T001: T002, T003, T004 together.
- After T006: T007, T008, T011 together.
- Inside US1 after T016: T017 + T019.
- Inside US2 after T024: T029 + T030.
- US4 and US5 after G10 can proceed in parallel (different components).

---

## Parallel example: User Story 1

```text
T013 IngredientMenu.tsx
T015 RadiusSlider.tsx
T019 ClusterMap.tsx
# then T018 PlaceList using T016 order as-is
```

## Parallel example: User Story 2

```text
T024 api/sse.ts
T023 OriginForm.tsx
# then T025 + T026 on selected pair cluster_id
```

---

## Implementation strategy

1. **MVP / G10** = Phase 1 + 2 + US1 + US2 (T001–T031). Пользователь видит выдачу `/places` (без своей сортировки) и стрим `/price` на `cluster_id` **кликнутой** пары. Позиция пары в топ-5 мока — не G10 D.
2. **SC-D2** закрывается T016 + T018 + T020 + T026 (не сортировать; клик пары даже вне первых пяти мока). T021 — порядок бэка, не «топ-5 мока».
3. **После G10:** US3 (серые), US4 (дыра), US5 (часы), share T041.
4. При пожаре B4: не делать US4/US5/share; **не** резать пару и US1/US2.

Мок-first: live-тумблер тот же клиент. Подмена фикстур данными A не меняет поля UI.

---

## Self-check (2026-08-19, до implement)

Сверка spec/plan/tasks с конституцией. Код / Vite / npm / `frontend/src` в этой итерации **не** писать.

| Проверка | Где в tasks | Итог |
|---|---|---|
| UI не сортирует `places[]` | T016 (`api/places.ts`), T018 (`PlaceList.tsx`) | **PASS** |
| SC-D2 = не сортировать + клик пары; мок не доказывает топ-5 | T020, T008; шапка SC-D2 | **PASS** |
| SSE с кликнутой пары, даже если одиночка выше и пара не в первых пяти мока | T026 | **PASS** |
| Rarity как с бэка, без вау-подписи «редкая связка» на эталоне | T017 | **PASS** |
| Карта MapLibre, не Leaflet | T002 (`maplibre-gl`), T019 (`ClusterMap.tsx`); Leaflet в Stop | **PASS** |
| [inversion-direction-is-output](../../knowledge/invariants/inversion-direction-is-output.md) | T012, T016: origin не вход фазы 1 | **PASS** |
| [phase-boundary](../../knowledge/invariants/phase-boundary.md) | T017 без цен; T023 после выбора карточки; T024/T025/T031 инкрементально | **PASS** |
| [pairs-are-not-cut](../../knowledge/invariants/pairs-are-not-cut.md) | T020/T026 пара кликабельна; T035 режется AlmostFits, не пара | **PASS** |
| [coverage-dominates-ranking](../../knowledge/invariants/coverage-dominates-ranking.md) | T016/T018 не переранжируют; ранг — работа B, не D | **PASS** |

Дыра в tasks по этим пунктам не найдена (T002 уточнён: явная зависимость `maplibre-gl`).

Копии `stream-d-frontend.md` / `stream-d-plan.md` / `stream-d-quickstart.md` в этом worktree могут ещё держать старую формулировку «пара в топ-5». Их **не** переписывать (запрет этой итерации). Implement идёт по **этому** файлу и заморозке оркестратора: SC-D2 ≠ топ-5 мока.

**Вердикт tasks:** PASS. **Готов к implement:** да. Код — только после зелёного лаунчера, не сейчас.

---

## Stop

После зелёного лаунчера — implement строго `frontend/**` по этому чеклисту.

**Не делать в implement без новой команды:** правки `backend/**`, `lib/**`, `schema.sql`, `fixtures/**`, `docker-compose.yml`, `nginx/**`, `.specify/`, `specs/002-*`, переранжирование `places[]`, Leaflet, чужой домен как край.
