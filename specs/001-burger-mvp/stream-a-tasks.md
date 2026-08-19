---
type: Tasks
title: Stream A — задачи ингеста волны 1
description: Чеклист D1 done / D3+ не execute. Self-check против инвариантов. Стоп до зелёного на D3.
tags: [spec-kit, "001", stream-a, tasks]
timestamp: 2026-08-19T13:41:00Z
feature: 001-burger-mvp
status: draft
spec: ../../plans/worker-A-ingest.md
plan: stream-a-research.md
constitution: ../../knowledge/invariants/
---

# Tasks: Stream A — ингест

**Spec**: [plans/worker-A-ingest.md](../../plans/worker-A-ingest.md)
**Research**: [stream-a-research.md](stream-a-research.md)
**Конституция**: [knowledge/invariants/](../../knowledge/invariants/)
**Каркаса `.specify/` нет** и не заводится.

Эта итерация — самоанализ. Пункты D3+ **не execute**. Живые пробы не
перезапускать. `fixtures/` не подменять.

G10 для A: волна 1 (D1+D3) готова подменить золотые `fixtures/`.
**Сейчас: НЕТ.**

## Phase D1 — реестр узлов (факт, done)

- [x] T0. Каталог `ingest/`, импорт `lib.tutu_mcp` (`TutuMcp`, `check_resolve`,
      `price_is_absent`); копии MCP/guard нет
- [x] T1. Волна 1: 268 городов `dM<=400` из `data/cities_ru.json`
- [x] T2. Origin Москва; concurrency cap=4; timeout >= 30 с; кэш в SQLite до
      обработки (`mcp_cache`)
- [x] T3. Три исхода `sellable` / `not_sellable` / `misresolved`; ретрай
      алиас → имя → «имя, субъект»; misresolved не схлопнут
- [x] T4. Алиасы B1+V5 в `data/city_aliases.json`
- [x] T5. Регресс B1 п.4: Ярославль, Ростов Великий, Рязань, Коломна, Тула,
      Калуга, Владимир, Иваново — `regression_pass: true`
- [x] T6. Артефакт `data/wave1_summary.json` (2026-08-19T13:33:49Z):
      probed 267, sellable 178, not_sellable 88, misresolved 1, errors `[]`

Не перепрогонять.

## Phase D3 — POI OSM (чеклист, не execute)

Зависимость: D1 done. Скрипт `ingest/parse_osm.py` на диске; прогон убит до
INSERT. `poi` = 0. `coverage.json` нет.

- [ ] T7. Прогнать `parse_osm.py` на G7 PBF Ярославской области (пакет
      `osmium`, не pyosmium на PyPI; не `russia-latest`)
- [ ] T8. Записать `poi` (теги `ingredients.yaml`, без `ruins=yes`;
      промтуризм = `industrial_museum`, не `man_made=works` как туризм)
- [ ] T9. `start_date` from/to; `hours_status` open/closed/unknown;
      `significance` по формуле yaml
- [ ] T10. `admin_level=4` + `data/coverage.json` (карта покрытия V4)
- [ ] T11. Привязка POI к `hub_id` волны 1; эталон Ярославль и Ростов
      Великий имеют `ancient_temple` (+ у Ярославля `industrial_museum`)
- [ ] T12. `*.pbf` не коммитить

Блокер G10 A: без T8–T11 подмена fixtures запрещена.

## Phase D2 — матрица перегонов (чеклист, не execute)

Зависимость: D1 + D3 с POI на обеих сторонах. Скрипт `ingest/probe_legs.py`
есть; не гонялся. Ноги Москва→hub из D1 — не матрица D2.

- [ ] T13. Только sellable пары ≤150 км, POI с обеих сторон; A→B и B→A
      раздельно; писать `leg.status` ok/no_route/misresolved
- [ ] T14. Пересчёт бюджета (доля sellable после D1: 178/267 dest) и
      `reachable_from_any` с ребра, не как свойство направления
- [ ] T15. Регресс таблиц data-collection §D2 (Тверь→Торжок, Ярославль→Ростов
      Великий, …) — после живого D2

## Phase D4 — Wikidata (чеклист, не execute)

Зависимость: D3. Скрипт `ingest/enrich_wikidata.py` есть; не гонялся.

- [ ] T16. SPARQL по классам yaml; матч тег `wikidata` иначе ~100 м; P571

## Phase D5 — прогрев кэша (чеклист, не execute)

Зависимость: эталонные hub из D1 (есть) + желательно D3 для продукта; скрипт
`ingest/warmup_cache.py` есть; не гонялся.

- [ ] T17. 4 эталона × 4 окна окт-2026 × {1,2} взр → `route_cache` /
      `hotel_cache`; цена отеля = `stay_total`; эталон №1 4342 RUB как
      регресс фолбэка, не SC-price

## G10 A

- [ ] T18. Волна 1 D1+D3 готова к подмене золотых `fixtures/` — **НЕТ**
      (D1 да, D3 нет). Сами fixtures не трогать; доложить лаунчеру.

## Dependencies

```
T0–T6 (D1 done)
    → T7–T12 (D3)  ← G10 A блокируется здесь
        → T13–T15 (D2)  нужен poi.hub_id
        → T16 (D4)
        → T17 (D5, частично может стартовать с D1 hubs)
    → T18 G10 только после T8–T11
```

## Self-check

Сверка с конституцией `knowledge/invariants/`. Код в этой итерации не менялся.

### Согласовано

- [three-probe-outcomes](../../knowledge/invariants/three-probe-outcomes.md):
  три статуса в `hub`; Радужный остался `misresolved`; Ростов Великий в
  реестре через алиас; регресс восьми имён pass. Ретрай в
  `TutuMcp.probe_destination`, не копия.
- [guard-before-price](../../knowledge/invariants/guard-before-price.md):
  guard только из `lib/tutu_mcp.py` (`check_resolve` / внутри probe).
  Ингест не завёл второй guard.
- [sellability-is-edge](../../knowledge/invariants/sellability-is-edge.md):
  схема `leg` направленная; D1 пишет Москва→hub как ребро; D2 задуман как
  пары узлов. `hub.sellable_modes` — снимок пробы из Москвы, не направление
  произвольного плеча.
- [silent-failure-map](../../knowledge/invariants/silent-failure-map.md):
  0 RUB = `price_is_absent` в lib; per-mode расхождение **залогировано**
  (260 записей); мисрезолв не проглочен как not_sellable.

### Дыры (факт)

1. **0 POI.** `coverage.json` нет. Частичная выгрузка OSM в silent-failure-map
   лечится картой покрытия — карты нет, слой «такого нет» для меню сейчас
   неотличим от «ещё не парсили».
2. **Москва без MCP.** Строка `Москва|Москва` sellable без
   `search_multitransport`, `tutu_geo_id=null`. Не дыра фильтра `dM`.
3. **1 misresolved: Радужный|Владимирская область** → ХМАО. Алиас V5
   «имя, субъект» исчерпан; исход честный. Эталон B1 п.4 не задет.
4. **260 avia softfail.** `modes_requested` всегда 4 режима; ключа `avia` в
   summary нет ни разу (114 ещё без `railway`). Не баг статуса узла; шум
   лога vs count в summary — на implement, не сейчас.
5. **D3-охват ≠ 268 городов.** План воркера ещё пишет `russia-latest`;
   заморозка G7 + скрипт — только Ярославская область. Для эталона (Ярославль,
   Ростов) достаточно; для графа волны 1 покрытие дырявое (V4).
6. **D2/D4/D5 не гонялись.** `parse_osm.py` ни разу не довёл apply до INSERT
   (риск wall/RSS с `locations=True` не измерен этим прогоном).

### Вердикт

**К запуску D3 — готов** (вход D1 в `burger.db`, `osmium` импортируется, PBF
G7 45 213 826 байт на диске, скрипт есть). Не стартовать без зелёного
оркестратора.

**К G10 / подмене fixtures — не готов:** нет D3-выхода (0 POI).

Стоп.
