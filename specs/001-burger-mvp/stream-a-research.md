---
type: Research
title: Stream A — ингест волны 1 (D1 факт, D3 стоп)
description: Phase 0 research after live D1. Decision / Rationale / Alternatives. Implement D3+ только после зелёного оркестратора.
tags: [spec-kit, "001", stream-a, research]
timestamp: 2026-08-19T13:38:00Z
feature: 001-burger-mvp
status: draft
spec: worker-A-ingest.md
---

# Research: Stream A — ингест

Сбор D3/D2/D4/D5 остановлен оркестратором. Ниже — факты с диска, не оценки.
Источники: `data/wave1_summary.json`, `data/softfail_log.json`, `data/burger.db`
(чтение), отсутствие `data/coverage.json`.

## R1. D1 волна 1 — реестр узлов есть

**Decision:** волна 1 D1 закрыта. Повторные пробы и перетряхивание `burger.db`
не делать до зелёного на D3.

**Rationale (файлы):**

| Поле | Значение | Откуда |
|---|---|---|
| cities | 268 | `wave1_summary.json` (`dM` ≤ 400) |
| probed | 267 | тот же файл |
| sellable (пробы) | 178 | `counts.sellable` |
| not_sellable | 88 | `counts.not_sellable` |
| misresolved | 1 | `counts.misresolved` |
| errors | `[]` | повтор после двух TimeoutError |
| regression_pass | true | `regression_missing: []` |
| date | 2026-09-09 | weekday +3 weeks |
| at | 2026-08-19T13:33:49Z | |

В `hub` после записи origin: **268** строк, `probe_status` =
`sellable 179 / not_sellable 88 / misresolved 1`. Лишний sellable — Москва
(см. R2), не 179-я проба Tutu.

Единственный `misresolved` в БД: `Радужный|Владимирская область` →
`resolved_region` = Ханты-Мансийский АО (омоним V5). Не схлопнут в
`not_sellable`.

Регресс B1 п.4: Ярославль, Ростов Великий, Рязань, Коломна, Тула, Калуга,
Владимир, Иваново — `regression_missing: []`.

**Alternatives considered:**

- Перепрогон 268 живьём «для чистоты» — отвергнут оркестратором.
- Считать Москву дырой реестра — нет: строка в `hub` есть, нет только MCP-пробы
  Москва→Москва.

## R2. Не probed из 268 — origin Москва

**Decision:** 267 проб = все кандидаты волны 1 кроме origin. Origin вставляется
без `search_multitransport`.

**Rationale:** `ingest/probe_hubs.py` исключает
`name=Москва` + `subject=Москва` из пула dest. `wave1_summary.probed=267`.
В БД `Москва|Москва`: `probe_status=sellable`, `tutu_geo_id=null`,
`checked_at` проставлен. Это не таймаут и не дыра фильтра `dM`.

**Alternatives considered:** проба Москва→Москва — не делалась, не включать в D1
задним числом до решения оркестратора.

## R3. 260 softfail — per-mode, не баг пробера

**Decision:** лог валиден как митигация silent-failure «per-mode soft-fail».
Это не порча `probe_status` и не ложный misresolve.

**Rationale:** `data/softfail_log.json` ровно **260** записей.

- Во всех 260 `requested` = `avia, bus, etrain, railway`.
- Во всех 260 ключ `avia` **отсутствует** в `modes_summary`.
- 146: summary = `bus, etrain, railway` (нет только avia).
- 114: summary = `bus, etrain` (нет avia и railway).
- `avia` в summary: **0**.

Код (`ingest/common.py` `log_mode_softfail`) сравнивает множество
`modes_requested` с **ключами** `modes_summary`, не с count. Расхождение
«запросили avia — ключа нет» = как в field-test / data-collection: нет
`avia_id` / `railway_id`, режим выпадает из summary молча. Продаваемость
узла читается из count>0, не из полноты ключей.

260 / 267 ≈ почти все пробы; 7 без записи = либо нет `modes_requested`, либо
ключи совпали (не разбиралось по сырому `mcp_cache` в этом стопе).

**Alternatives considered:**

- Считать 260 багом ингеста и чинить статусы — нет, статусы трёхисходные.
- Сравнивать count, не keys — отдельное решение на implement, не сейчас.

## R4. D3 POI не собраны

**Decision:** D3 не готов. Implement парсера не расширять до зелёного.

**Rationale:**

- `data/coverage.json` **нет**.
- `poi` в `data/burger.db`: **0** строк.
- PBF на диске есть (скачан до стопа): `data/osm/yaroslavl_oblast-latest.osm.pbf`,
  45 213 826 байт (совпадает с G7). `*.pbf` в gitignore, не коммитить.
- Пакет `osmium` 4.3.1 импортируется (`import osmium` OK). Это не pyosmium на
  PyPI.
- Живой `parse_osm.py` был запущен после D1 и **остановлен** до записи POI.

**Alternatives considered:** дожать текущий прогон OSM — отвергнуто стопом.

## R5. D2 / D4 / D5 не гонялись

**Decision:** скрипты на диске (`ingest/probe_legs.py`, `enrich_wikidata.py`,
`warmup_cache.py`) не считать выполненными.

**Rationale:** нет прогона, нет артефактов матрицы/wikidata/прогрева сверх D1
(ноги Москва→hub из D1 — снимок origin-пробы, не матрица D2).

## R6. Подмена fixtures/ — нет

**Decision:** лаунчеру: волна 1 **не** готова к подмене золота. Сами
`fixtures/` не трогали.

**Rationale:** критерий G10 для A = D1+D3. D1 есть, D3 (POI) нет.

## R7. Шов и стоп

**Decision:** ждать зелёный оркестратора на D3. Не мержить в main. Не
force-push. `schema.sql` / `lib/**` / `backend/**` / `fixtures/` не менять.

Код, который уже есть и не расширялся в этом стопе: `ingest/common.py`,
`ingest/probe_hubs.py`, `ingest/parse_osm.py` (написан, не довёл выгрузку).
