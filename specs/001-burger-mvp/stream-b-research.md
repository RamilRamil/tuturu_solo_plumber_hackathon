---
type: Research
title: Stream B — решения фазы 1
description: Phase 0 research. Decision / Rationale / Alternatives. Неизвестных NEEDS CLARIFICATION не осталось.
tags: [spec-kit, "001", stream-b, research]
timestamp: 2026-08-19T12:35:00Z
feature: 001-burger-mvp
status: draft
spec: stream-b-phase1.md
---

# Research: Stream B — фаза 1

Все пункты Technical Context закрыты. Ниже — зафиксированные решения, не
открывать заново на implement.

## R1. Кластеризация — диски вокруг узлов, не DBSCAN

**Decision:** кандидат места = один продаваемый узел **или пара** узлов на
расстоянии ≤ `radius_km`. Объекты — в `r_local` (дефолт 25 км) от любого узла
набора. Диаметр — фактический по крайним POI.

**Rationale:** пользователь понимает ползунок как диаметр набора. Плотностная
связность на 100 км склеивает пол-страны и даёт немонотонный счётчик.
Диски сразу привязаны к транспорту. Инвариант
[discs-not-dbscan](../../knowledge/invariants/discs-not-dbscan.md).

**Alternatives considered:**

- DBSCAN / иерархия / «компонента связности по POI» — отвергнуто инвариантом.
- Только одиночные узлы — ломает эталон-пару (B4).
- Диаметр по узлам, не по POI — врёт карточке (допуск `2 × r_local` пропадет).

## R2. Точный `ingredient_id`, эталон = `industrial_museum`

**Decision:** покрытие = точное равенство `poi.ingredient_id` id из запроса.
Эталон №1 = `ancient_temple` + `industrial_museum`. Не маппить
`industrial_museum`↔`industrial_site`. Не добавлять фейковые `industrial_site`
POI. Запасной бургер = `ancient_temple` + `ruins` (не `spring`).

**Rationale:** оркестратор, 2026-08-19: честный слой «музей промышленности»,
не действующие заводы. Так SC-B1 достижим на золотых `fixtures/rows/poi.json`.
Словарь разделяет два id ([ingredients.yaml](../../ingredients.yaml)).
Канон: [plans/00-orchestration.md](../../plans/00-orchestration.md) §0 B4,
[fixtures/etalon_1.json](../../fixtures/etalon_1.json), пример
[plans/api-contract.md](../../plans/api-contract.md).

**Alternatives considered:**

- Оставить бургер `industrial_site` и алиасить museum→site — ложь в карточке и
  расхождение со словарём.
- Дописать фейковые `industrial_site` в фикстуры — запрет оркестратора; B
  фикстуры не правит.
- Семейство «industrial_*» как один ингредиент — ломает плотность и дисклеймеры.

## R3. Coverage доминирует лексикографикой, не большим весом

**Decision:** сортировка `places[]`: (1) `len(coverage.matched)` убыв.;
(2) `cluster_score` убыв. Формула score и веса `w1..w6` — конфиг, как в
[plans/worker-B-phase1.md](../../plans/worker-B-phase1.md). Пока нет калибровки
D3, достаточно любых неотрицательных весов: лексикографика держит полное
покрытие выше неполного. При равном coverage (одиночный Ярославль vs пара
эталона — оба 2) исход решает score; веса **не** калибровать, чтобы пара
стала #1. SC-B1 hard = пара существует в `places[]` с полным покрытием, не
обязательно в топ-5. Топ-5 — smoke на фикстурах.

**Rationale:** иначе карточка с одним matched вытеснит полное покрытие.
Это **не** защита пары от полного одиночного Ярославля: у него тоже оба
ингредиента. Инвариант
[coverage-dominates-ranking](../../knowledge/invariants/coverage-dominates-ranking.md);
F2 в readiness-gate закрыт контрактом.

**Alternatives considered:**

- Один скаляр `cluster_score` с огромным `w1` — хрупко, легко сломать калибровкой.
- Сортировка только по coverage без score — потеряет редкость и компактность
  внутри одного уровня покрытия.
- Ранжировать по цене/`leg` — нарушает границу фаз и требует сеть.

## R4. Пары нерезаемы; запасной бургер — страховка, не замена

**Decision:** генерация пар обязательна среди `probe_status=sellable`.
Регресс держит **оба** сценария (эталон-пара и одноузловой запас).
При пожаре таймлайна пары не режутся первыми.

**Rationale:** B4 «держим оба». Инвариант
[pairs-are-not-cut](../../knowledge/invariants/pairs-are-not-cut.md).
Исходный cut-list mvp-spec §12 отменён.

**Alternatives considered:**

- Только запасной одноузловой критерий — продукт теряет «сосуществуют в радиусе».
- Резать пары первыми — автоматический провал SC-B1.

## R5. Продаваемость в фазе 1 — статус пробы, не билет

**Decision:** в карточке только `hubs[].probe_status`. Не слать
`sellable: true`. Таблицу `leg` для отбора/ранжирования `/api/places` не
читать. Непродаваемые узлы остаются (пометка «своим ходом»); `misresolved`
не схлопывать в `not_sellable`. Пары — только sellable–sellable.

**Rationale:** билет — свойство ребра после origin (фаза 2). Инвариант
[sellability-is-edge](../../knowledge/invariants/sellability-is-edge.md).

**Alternatives considered:**

- Фильтровать выдачу по `reachable_from_any` / `leg` — посереет или исчезнет
  масса карточек до ввода origin.
- Схлопнуть три исхода пробы в boolean — ломает B1.

## R6. Личность кластера = множество узлов; percent-encode не в id

**Decision:** `cluster_id = lib.models.make_cluster_id(hub_ids)`. Радиус и фаза
не входят. Кириллица и `|` в id допустимы. Запятая в `hub_id` запрещена
(`make_hub_id` отвергает). Percent-encode UTF-8 всего `cluster_id` — для
share-URL (поток D, FR-D16), не для JSON-поля и не для ключа SQLite.

**Rationale:** один id на 50/100/150 км при том же наборе узлов; C принимает
его в `/api/price`. Канон:
[plans/api-contract.md](../../plans/api-contract.md) раздел `cluster_id`.

**Alternatives considered:**

- Включить `radius_km` в id — ломает шеринг и фазу 2 при движении ползунка.
- ASCII-slug / hash — расходится с замороженным примером эталона.
- Класть percent-encoded строку в JSON — двойное кодирование у D.

## R7. Дискретный радиус и роль таблицы `cluster`

**Decision:** вход `radius_km` ∈ {50, 100, 150}; иначе 400, не «тихий clamp».
Алгоритм кандидатов один и тот же; строки `cluster(id, radius_km)` — кэш
набора узлов на шаг ползунка, не готовый ranked `places[]`. Coverage и порядок
считаются **на запрос** (бургер каждый раз другой).

**Rationale:** V2 — свободный ползунок не влезает в 200 мс на тысячах пар.
На золотых фикстурах узлов мало: живой проход дисков допустим и **обязателен
для SC-B1/B2** (таблица `cluster` пуста). После волны 1 предпосчёт пар на три
шага — оптимизация, не смена контракта и не замена регресса.

**Alternatives considered:**

- Отдавать `clusters.json` как топ-5 без пересечения с POI бургера — не
  проверяет coverage и скрывает одиночного Ярославля с тем же покрытием
  (Goodhart).
- Непрерывный радиус на лету — отвергнуто V2.

## R8. Нет отдельного меню-эндпоинта

**Decision:** каталог и плотность — [ingredients.yaml](../../ingredients.yaml).
Фронт читает файл сам. B только валидирует id входа. Новый метод в контракт
не добавлять.

**Rationale:** замороженный G2 содержит только `/api/places` и `/api/price`.

**Alternatives considered:** `GET /api/ingredients` — правка шва через
архитектора, вне скоупа plan B.

## R9. Процесс и стоп

**Decision:** обработчик фазы 1 — в существующем FastAPI на порту 8000
(один процесс с C). Исходящей сети в пути `/api/places` нет. После этого
research/design — стоп; `tasks.md` и код кластеризации ждут контроль.

**Rationale:** [plans/stack.md](../../plans/stack.md) G8;
[phase-boundary](../../knowledge/invariants/phase-boundary.md).

**Alternatives considered:** второй сервис только для places — нарушает стек.
