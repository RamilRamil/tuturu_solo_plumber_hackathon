---
type: Tasks
title: Stream B — tasks фазы 1
description: Spec Kit / OKF checklist for POST /api/places. SC-B1/B2 hard = exists in places[] with full coverage; top-5 is smoke only. No product code in this file.
tags: [spec-kit, "001", stream-b, tasks]
timestamp: 2026-08-19T13:41:00Z
feature: 001-burger-mvp
status: draft
spec: stream-b-phase1.md
plan: stream-b-plan.md
---

# Tasks: Stream B — фаза 1

**Spec**: [stream-b-phase1.md](stream-b-phase1.md)
**Plan**: [stream-b-plan.md](stream-b-plan.md)
**Contract**: [plans/api-contract.md](../../plans/api-contract.md)
**Models (import only)**: [lib/models.py](../../lib/models.py)

Каркаса `.specify/` нет и не заводится. `specs/002-*` не создавать.
Конституция = [knowledge/invariants/](../../knowledge/invariants/).
Нарушение без обоснования = ERROR.

**СТОП этой итерации:** только этот файл. Implement кода — после зелёного
лаунчера. Коммит в `main` запрещён.

## Ownership (frozen for implement)

Писать **только**:

| Path | Role |
|---|---|
| `backend/routers/places.py` | `POST /api/places` (router already empty; `app.include_router` exists) |
| `backend/services/cluster*` | discs, candidates, score, config `w1..w6` |
| `tests/test_places*` | hard SC-B1 / SC-B2 / SC-B3; top-5 smoke comments only |

**Не трогать:** `backend/app.py`, `lib/**`, `backend/routers/price.py`,
`frontend/**`, `schema.sql`, `fixtures/**`, `ingredients.yaml`.

Импорт разрешён: `lib.models.make_cluster_id`, `lib.models.connect`,
`lib.load_fixtures.load_golden_fixtures`. Свои dataclass/DDL/SQLAlchemy — нет.

## SC-ranking (do not reopen)

Hard vs smoke (orchestrator freeze 2026-08-19): «pair in top-5» is **smoke**
on golden fixtures, not a build pass/fail, not a promise after wave 1.

- **SC-B1 hard.** Burger `ancient_temple` + `industrial_museum`, `radius_km` = 100.
  After `load_golden_fixtures` run `DELETE FROM cluster`. Live disc pass is
  source of truth. Pair `cluster_id` from `fixtures/etalon_1.json` is **in
  `places[]` (any index)** with `coverage.matched` = both ingredients and
  `coverage.missing` = `[]`. Plus **SC-B3** on the same response.
  Pair is **not** required to be `#1` or in top-5. Single-hub Yaroslavl with
  `len(coverage.matched)=2` is a legal complete answer, not a fail.
  Wave 1 must not fail the test if the pair lands at `#6`.
  Do not cut Yaroslavl temples from `poi.json`. Do not map
  `industrial_museum` ↔ `industrial_site`. Do not tune `w1..w6`.
- **SC-B1 smoke.** On golden fixtures only: pair among `places[:5]`. Comment
  in tests, **not** an assert. Not part of G10 / SC-B5.
- **SC-B2 hard.** Burger `ancient_temple` + `ruins`, `radius_km` = 100.
  Single-hub Yaroslavl (`fixtures/backup_single_hub.json`) is **in `places[]`**
  with full coverage. Top-5 = smoke only.
- **SC-B2 smoke.** Backup id among `places[:5]` on golden fixtures. Comment,
  not assert.
- **SC-B3 hard.** No place with smaller `len(coverage.matched)` ranks above a
  place with a larger count. Run on the SC-B1 (and SC-B2) response.
- **SC-price is not B.** Do not mix ranking tests with price/SSE.

Expected ids (raw JSON, not percent-encoded):

- etalon pair: `c:Ростов|Ярославская область,Ярославль|Ярославская область`
- backup: `c:Ярославль|Ярославская область`

## Invariants gate (pre-implement)

Sourced from [stream-b-plan.md](stream-b-plan.md) Constitution check.
Re-checked against this task list. No exceptions.

| Invariant | Gate for B | Verdict |
|---|---|---|
| [discs-not-dbscan](../../knowledge/invariants/discs-not-dbscan.md) | Candidate = one hub or pair ≤ `radius_km`; POI in `r_local` (default 25 km); no DBSCAN/chains; `diameter_km` from extreme POI | **PASS** |
| [coverage-dominates-ranking](../../knowledge/invariants/coverage-dominates-ranking.md) | Sort: `len(matched)` desc, then `cluster_score` desc. Weights in config. Do not calibrate `w1..w6` so the etalon pair is forced `#1` | **PASS** |
| [pairs-are-not-cut](../../knowledge/invariants/pairs-are-not-cut.md) | Pair candidates required; US1 and US2 both in regression | **PASS** |
| [sellability-is-edge](../../knowledge/invariants/sellability-is-edge.md) | Card has `hubs[].probe_status`; no `sellable: true`; do not read `leg` in `/api/places` | **PASS** |
| [phase-boundary](../../knowledge/invariants/phase-boundary.md) | No outbound network; no origin/dates/prices on `/api/places` | **PASS** |
| [source-of-truth-precedence](../../knowledge/invariants/source-of-truth-precedence.md) | `schema.sql` > api-contract > orchestration §0 > mvp-spec. §5 and §12 cancelled. Import `lib.models`, do not copy | **PASS** |

FAIL would be: DBSCAN, `clusters.json` as ranked output, museum↔site alias, pair forced `#1` or forced top-5 via weights, hard-assert on `places[:5]`, network in places, editing seams.

---

## Phase 1 — Setup (no product logic)

Goal: name the files B will own. FastAPI process and `include_router` already
exist. Do not create `.specify/`. Do not add dependencies (no pip/npm).

- [ ] T001 Confirm empty router `backend/routers/places.py` is the only HTTP seam; do not edit `backend/app.py`
- [ ] T002 [P] Reserve ranking config (`w1..w6`, `r_local_km=25`, allowed radii `{50,100,150}`, ancient year 1600) in `backend/services/cluster_config.py`

---

## Phase 2 — Foundational (blocks all US)

Goal: live discs on `hub`+`poi`, contract-shaped `POST /api/places`, empty
`cluster` table during ranking. Must finish before story phases.

- [ ] T003 Haversine distance (km) in `backend/services/cluster_geo.py`
- [ ] T004 Candidate generation in `backend/services/cluster_candidates.py`: every hub as a single-hub set; pairs only among `probe_status=sellable` with hub distance ≤ `radius_km`
- [ ] T005 Attach POI in `r_local` of any hub of the set in `backend/services/cluster_places.py`; match burger by exact `ingredient_id` only; skip clusters with zero matched POI
- [ ] T006 Public id via `lib.models.make_cluster_id` in `backend/services/cluster_places.py` (set of `hub.id`; radius not in id)
- [ ] T007 Coverage (`matched`/`missing`), rarity field (`rank` 1-based in same matched-set, `total_places_with_combo`) as an honest cluster count with the same `matched` — not a "rare combo" wow. Complementary-burger rarity wow is out of 001 and not promised at G10. `cluster_score` from plan B, lexicographic sort in `backend/services/cluster_rank.py`. Do not tune `w1..w6` because N is small.
- [ ] T008 `POST /api/places` in `backend/routers/places.py`: body `ingredients`, `radius_km` (default 100), `limit` (default 20); validate ids against `ingredients.yaml` without a second catalog endpoint; `radius_km` not in `{50,100,150}` → HTTP 400; empty `ingredients` → HTTP 400; read `BURGER_DB`; do not query `cluster` as ranked output; do not call Tutu/MCP/`leg`
- [ ] T009 Shared test fixture in `tests/test_places.py`: `load_golden_fixtures` then `DELETE FROM cluster`; set `BURGER_DB` to that temp db; FastAPI `TestClient` against existing `backend.app:app`

**Independent test (foundation):** handler returns JSON `{total_found, places}` for a valid burger without touching `origin` or SSE. Table `cluster` row count is 0 during the call.

---

## Phase 3 — US1 эталон №1 существует как пара (P1)

**Story:** traveler builds `ancient_temple` + `industrial_museum`, radius 100 km;
etalon pair exists in the list with full coverage.

**Independent Test (hard):** golden `fixtures/`, no phase 2, no ingest. Empty
`cluster`. Pair `cluster_id` from `fixtures/etalon_1.json` is **in `places[]`**
(any index) with both ingredients matched and `missing=[]`. SC-B3 on the same
response. Single-hub Yaroslavl with coverage=2 **may** rank above the pair.
Top-5 on fixtures = smoke, not this Independent Test.

- [ ] T010 [US1] SC-B1 **hard** test in `tests/test_places.py`: POST ingredients `ancient_temple`,`industrial_museum`, `radius_km` 100, `limit` 20; assert etalon pair id **IN `places[]`**, NOT `places[:5]`; assert that card `coverage.matched` has both ids and `missing` is `[]`; assert request/response have no origin/price/`sellable` boolean. Optional comment: on golden fixtures the pair is often in the first five — **not** an assert
- [ ] T011 [US1] Assert in `tests/test_places.py` that single-hub Yaroslavl with `len(matched)=2` does **not** fail the suite if it ranks above the pair (including if the pair is `#6`+)
- [ ] T012 [US1] Keep Yaroslavl `ancient_temple` POI in the live disc path in `backend/services/cluster_places.py` (no fixture edits; no museum↔site alias)

---

## Phase 4 — US2 запасной одноузловой бургер (P1)

**Story:** if pairs slip, traveler still gets an honest single-hub place.

**Independent Test (hard):** `ancient_temple` + `ruins`, 100 km →
`c:Ярославль|Ярославская область` **in `places[]`** with full coverage.
In top-5 on fixtures = smoke, not this test.

- [ ] T013 [P] [US2] SC-B2 **hard** test in `tests/test_places.py`: POST `ancient_temple`,`ruins`, `radius_km` 100; assert backup id from `fixtures/backup_single_hub.json` **IN `places[]`**, NOT `places[:5]`. Optional comment that it is often in the first five on gold — **not** an assert. G10 uses this hard gate (existence + full coverage), not top-5
- [ ] T014 [US2] Single-hub candidates remain even when pairs exist, in `backend/services/cluster_candidates.py`

Depends on: Phase 2. Parallel with US1 tests after T009.

---

## Phase 5 — US3 полное покрытие выше неполного (P1)

**Story:** same burger as US1. A cluster covering both interests always ranks
above a cluster covering one. Does **not** require pair above full single-hub
Yaroslavl (both coverage=2). Ties broken by `cluster_score`; do not tune weights
to crown the pair.

**Independent Test:** in the ordered `places[]` no card with smaller
`len(coverage.matched)` appears above a card with a larger count. (SC-B3)

- [ ] T015 [US3] SC-B3 **hard** test in `tests/test_places.py` on the same US1 response as T010 and on the US2 response; this gate is part of G10 with SC-B1/B2
- [ ] T016 [US3] Lexicographic key `(len(matched), cluster_score)` only in `backend/services/cluster_rank.py`; leave `w1..w6` as config defaults in `backend/services/cluster_config.py` (no Goodhart fit for pair `#1`, for pair-in-top-5, or because fixture N is small)

Depends on: Phase 2. Uses same fixtures as US1/US2.

---

## Phase 6 — US4 ползунок не меняет личность набора (P2)

**Story:** traveler clicks 50 / 100 / 150 km. Same hub set → same `cluster_id`
for phase 2 and share URL.

**Independent Test:** if the etalon pair is produced at more than one step,
ids match. `radius_km` outside `{50,100,150}` → HTTP 400, not clamp.

- [ ] T017 [US4] Tests in `tests/test_places.py`: invalid radius (e.g. 200) → 400; `make_cluster_id` of the etalon hub set is identical at 50/100/150 even when a step omits the pair because hub distance > radius
- [ ] T018 [US4] Discrete radius check only in `backend/routers/places.py` (no silent cap at 150)

Depends on: T006, T008.

---

## Phase 7 — US5 непродаваемый узел не исчезает (P2)

**Story:** a hub with interests but no ticket-at-all still appears, marked
"on your own", not "sellable in every direction".

**Independent Test:** `probe_status` reaches the card; no node-level `sellable`
flag; `misresolved` is not collapsed to `not_sellable`. Borisoglebsky
(`not_sellable` in fixtures) may appear as a single-hub card and must not
enter a pair.

- [ ] T019 [P] [US5] Tests in `tests/test_places.py`: `hubs[].probe_status` in `{sellable, not_sellable, misresolved}`; response JSON has no `sellable` key on hubs; a `misresolved` hub is not rewritten to `not_sellable`
- [ ] T020 [US5] Pair filter `sellable`–`sellable` only; non-sellable hubs stay as single-hub cards in `backend/services/cluster_candidates.py`

Depends on: T004, T008.

---

## Phase 8 — Polish / edges / G10 slice

- [ ] T021 [P] Empty `ingredients` and unknown ingredient id → HTTP 400 in `tests/test_places.py` and `backend/routers/places.py`
- [ ] T022 [P] `diameter_km` from extreme POI (may exceed `radius_km` up to `2 * r_local`); honest number on the card via `backend/services/cluster_places.py`
- [ ] T023 Object `significance` by mvp-spec §9 formula in `backend/services/cluster_places.py` (cached `poi.significance` optional); antiquity threshold filters `ancient_temple` membership only, never replaces coverage
- [ ] T024 Phase-1 payload has no origin/dates/passengers/prices; `/api/places` path does not import `lib.tutu_mcp` or read `leg` — guard in `backend/routers/places.py` and `tests/test_places.py`
- [ ] T025 G10 slice in `tests/test_places.py`: **hard** SC-B1 + SC-B2 + SC-B3 (existence in `places[]` + full coverage + lexicographic coverage). Not «both in top-5». Wave 1 must not fail this task if the pair moves to `#6`. Demo/C still consumes **pair** id from `etalon_1.json`, not necessarily `places[0]`

---

## Dependencies

```text
T001,T002
    -> T003,T004,T005,T006,T007,T008,T009
        -> US1 (T010-T012)  P1
        -> US2 (T013-T014)  P1  [parallel with US1 after T009]
        -> US3 (T015-T016)  P1  [after T007]
        -> US4 (T017-T018)  P2  [after T006,T008]
        -> US5 (T019-T020)  P2  [after T004,T008]
            -> T021-T025 polish
```

MVP for launcher green-on-code: **Phase 2 + US1 + US2 + US3** (hard SC-B1/B2/B3).
US4 and US5 before G10. Do not wait on Worker C/D. Top-5 is smoke only.

## Parallel examples

- After T009: T010 (US1) and T013 (US2) can be written in parallel.
- T002, T003 are different files and can start together once T001 is confirmed.
- T021 and T022 touch different assertions/files after the handler exists.

## Implementation strategy (for the next green, not now)

1. Config + geo + candidates + places + rank modules under `backend/services/cluster*`.
2. Fill `backend/routers/places.py` only.
3. `tests/test_places.py` always: load gold → `DELETE FROM cluster` → live discs.
4. Stop at G10 ranking slice (hard existence + SC-B3). No `/api/price`, no frontend, no fixture surgery, no hard top-5.

## Out of scope (report to launcher if blocked)

- Seam edits (`schema.sql`, `lib/**`, `plans/api-contract.md`, `fixtures/**`, `backend/app.py`).
- Red `tests/test_guard.py` (stop; do not "fix" guard by editing lib).
- Precompute write-back into `cluster` as ranked output (optional cache later; forbidden for SC-B*).
- Hard-assert «in top-5» (smoke only; wave 1 may push the pair to `#6`).
- Menu endpoint, density API, DBSCAN, origin in places.

## Counts

| Phase | Story | Tasks |
|---|---|---|
| 1 Setup | — | T001–T002 (2) |
| 2 Foundational | — | T003–T009 (7) |
| 3 | US1 P1 | T010–T012 (3) |
| 4 | US2 P1 | T013–T014 (2) |
| 5 | US3 P1 | T015–T016 (2) |
| 6 | US4 P2 | T017–T018 (2) |
| 7 | US5 P2 | T019–T020 (2) |
| 8 Polish | — | T021–T025 (5) |
| **Total** | | **25** |

---

## Self-check (OKF, 2026-08-19)

Canon: `plans/00-orchestration.md` §0 (smoke vs hard) **beats** stale copies of
`stream-b-phase1.md` / plan / research / quickstart **in this worktree**.
Those copies were not rewritten here (architect owns them on `main`).
Implement must follow **this file + §0**, not local «оба в топ-5» as a hard gate.

Checked invariants: `coverage-dominates-ranking`, `discs-not-dbscan`,
`pairs-are-not-cut`, `phase-boundary`, `source-of-truth-precedence`
(plus `sellability-is-edge` already in the gate table). Worktree text of
`coverage-dominates-ranking` still says «пара в топ-5»; §0 overrides that
sentence. Tasks do **not** hard-assert top-5.

| Checkpoint | Tasks | Vs freeze §0 | Hole? |
|---|---|---|---|
| T010 SC-B1 | pair id **IN `places[]`**, NOT `places[:5]`; matched both, `missing=[]`; smoke comment only | hard = exists + full coverage; top-5 = smoke | none |
| T013 SC-B2 | backup id **IN `places[]`**, NOT `places[:5]` | hard = single-hub Yaroslavl exists with full coverage; top-5 = smoke | none |
| T015 / T025 | G10 = hard SC-B1+B2+B3; wave 1 `#6` must not fail | G10 is structural + SC-B3, not «both in top-5» | none |
| T016 | no weight fit for `#1`, top-5, or small N | do not calibrate `w1..w6` to crown the pair | none (tightened this pass) |
| T009 | `load_golden_fixtures` then `DELETE FROM cluster` | live discs; empty `cluster` | none |
| T007 rarity | honest `total_places_with_combo`; not wow; complementary wow out of 001 / not G10 | rarity is a counter on this burger | none (tightened this pass) |

Stale in **this worktree** (not edited): `stream-b-phase1.md` SC-B1/US1 still
«в топ-5»; `stream-b-plan.md` G10 «оба в топ-5»; `stream-b-research.md` R3
«SC-B1 = пара в топ-5»; `stream-b-quickstart.md` fail if pair missing from
top-5. That is a copy lag, not a tasks hole. Do not implement against those
lines.

### Verdict

| Invariant | Self-check |
|---|---|
| discs-not-dbscan | **PASS** (T003–T005, T022; no DBSCAN) |
| coverage-dominates-ranking | **PASS** (T015–T016; pair not forced `#1`/top-5) |
| pairs-are-not-cut | **PASS** (T004, T010, T013; both burgers in hard regression) |
| phase-boundary | **PASS** (T008, T024; no network/origin in `/api/places`) |
| source-of-truth-precedence | **PASS** (tasks defer to §0 over stale worktree spec) |

**Ready for implement: yes.** Code is still not written in this iteration.
