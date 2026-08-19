---
type: Implementation Plan
title: Stream D — plan (фронт до G10)
description: Technical context, инварианты inversion/phase-boundary, фазы до G10, mock/live. Дух /speckit-plan. Стоп — не tasks, не implement.
tags: [spec-kit, "001", stream-d, plan]
timestamp: 2026-08-19T16:40:00Z
feature: 001-burger-mvp
status: draft
spec: stream-d-frontend.md
sources:
  - stream-d-frontend.md
  - plans/stack.md
  - plans/api-contract.md
  - plans/worker-D-frontend.md
  - plans/deploy-vps.md
---

# Stream D — Implementation Plan

Дух `/speckit-plan`. Спека принята: [stream-d-frontend.md](stream-d-frontend.md).
Эта итерация заканчивается design-артефактами. **Не** `tasks.md`, **не** implement, **не** `frontend/src`.

Связанные файлы этой фазы:

- исследование — [stream-d-research.md](stream-d-research.md)
- UI-модель — [stream-d-data-model.md](stream-d-data-model.md)
- приёмка на моках — [stream-d-quickstart.md](stream-d-quickstart.md)

Контракт API **не** копировать в `specs/.../contracts/`: канон — [plans/api-contract.md](../../plans/api-contract.md).

---

## Technical Context

| Поле | Значение |
|---|---|
| Language / Version | TypeScript; Node **20** |
| UI | React **18** + Vite + **npm** |
| Map | MapLibre GL JS (**не** Leaflet) |
| Storage | Нет своей БД у D. UI — проекция контракта + [ingredients.yaml](../../ingredients.yaml) |
| Testing | Ручной сценарий [stream-d-quickstart.md](stream-d-quickstart.md); SC-ranking в UI по золотым фикстурам |
| Target | Браузер за nginx. Локалка: compose `:80`. Демо-край: **`:8080`** (`docker-compose.g6.yml`) |
| Не край | чужой домен; gzip/redirect-прокси; прямой `:8000` в демо |
| Project type | web frontend (владелец — Worker D; сейчас в репо placeholder `frontend/index.html`) |
| Scale | G10 = конец часа 26; топ-5 мест + SSE по одному `cluster_id` |
| Performance | Фаза 1 — мгновенно с мока/локального `/api/places` (< 200 мс на бэке). Фаза 2 — первый `leg` ~3 с, события по одному (G6) |
| Constraints | Стек G8 заморожен. Моки = контракт. `checkout_url` as-is. Эталон = `ancient_temple` + `industrial_museum` |

**NEEDS CLARIFICATION:** нет. Швы G2/G8/G9 заморожены.

---

## Invariants (Constitution Check)

Проектных `.specify/` / constitution.md нет и **не заводить**. Ворота — инварианты репозитория.

| Инвариант | Следствие для D | Нарушение |
|---|---|---|
| [inversion-direction-is-output](../../knowledge/invariants/inversion-direction-is-output.md) | Origin **не** условие фазы 1. Вход — бургер + радиус. | Поле города до карты мест |
| [phase-boundary](../../knowledge/invariants/phase-boundary.md) | Фаза 1 без цен/бюджета/`breakdown`. SSE только после origin по топ-5. | Цена на карточке до origin; ждать все `leg` пачкой |
| [sellability-is-edge](../../knowledge/invariants/sellability-is-edge.md) | `probe_status` на хабе; билет — ребро фазы 2. Недостижимое **сереет**, не удаляется | `sellable` как атрибут узла из mvp-spec §5 |
| [coverage-dominates-ranking](../../knowledge/invariants/coverage-dominates-ranking.md) | UI **не** переранжирует `places[]` | Свой sort по плотности/цене |
| [pairs-are-not-cut](../../knowledge/invariants/pairs-are-not-cut.md) | Эталон-пара не режется; при пожаре режется «почти подходит» | Спрятать двуххабовый эталон |
| [source-of-truth-precedence](../../knowledge/invariants/source-of-truth-precedence.md) | `schema.sql` > api-contract > orchestration §0 > mvp-spec | Мок с `yar-rostov` / `industrial_site` как эталон |

Дополнительно (контракт, не отдельный инвариант-файл):

- Share URL (FR-D16, часы 40–44): **percent-encode** всего `cluster_id` (UTF-8). Не класть сырую строку в path segment (`|`, запятая, кириллица).
- Цена в UI до live обоих сценариев — `fixture-confirmed`.

**Gate:** нарушений нет; исключения не требуются.

---

## Project Structure (цель после implement — сейчас не создавать)

Репо уже имеет placeholder `frontend/` для compose. Когда оркестратор откроет implement:

```
frontend/                 # Vite app, npm, Node 20
  src/                    # запрещено трогать в этой итерации
  public/                 # моки JSON + SSE-скрипт задержек
```

Моки читают форму [fixtures/etalon_1.json](../../fixtures/etalon_1.json) и [fixtures/backup_single_hub.json](../../fixtures/backup_single_hub.json), но **ответы** клиенту — объекты Place / SSE из api-contract, не обёртка `legs[]` фикстуры as-is.

Клиент ходит на `/api/places` и `/api/price` **через nginx** (буферизация выключена).

---

## Фазы до G10 (час 26)

Порядок из [plans/worker-D-frontend.md](../../plans/worker-D-frontend.md) и orchestration §3. Implement — только после tasks (следующий этап, не этот).

| Окно | Что на экране | G10? |
|---|---|---|
| 3–10 | Меню с `density_label`; ползунок 50/100/150 max 150; каркас карты на моках | нет |
| 10–16 | Фаза 1: карта + топ-5 карточек, **без цен**. Эталон и запасной в топ-5 на своих запросах | SC-ranking в UI |
| 16–26 | Origin → SSE по `cluster_id` карточки; раскладка; серые с причиной | да |
| **конец 26 = G10** | Пользователь видит топ `/places` и стрим `/price` **на одном** `cluster_id` | критерий сборки |
| 26–34 | «Почти подходит», карта покрытия (V4) — после G10, не блокер чекпоинта | нет |
| 40–44 | Шеринг с percent-encode `cluster_id` | нет |

**Критерий G10 для D (видимое):**

1. Эталон №1 (`ancient_temple` + `industrial_museum`, 100 км): пара в видимом топ-5, не обязательно #1; для SSE кликнуть карточку пары.
2. Запасной (`ancient_temple` + `ruins`, 100 км) в видимом топ-5 на своём запросе.
3. По `cluster_id` эталона: `resolved` + ≥1 `leg` + `done` **по одному**, не пачкой.
4. Итог с меткой `fixture-confirmed`. `checkout_url` не переписан.

---

## mock / live

| Режим | Источник | Зачем |
|---|---|---|
| `mock` | Локальные ответы = api-contract + золотые фикстуры. SSE с **паузами** между `event:` (как G6 smoke) | Параллельный старт, не ждать B/C/A |
| `live` | Тот же клиент, `POST /api/*` через nginx на бэкенд :8000 | G10 на волне 1 / фикстурах бэка |

Переключатель на экране (FR-D17). Подмена фикстур реальными данными A **не** меняет поля UI.

Мок фазы 1 не содержит цен. Мок фазы 2 эмитит события по имени контракта: `resolved` \| `leg` \| `hotel` \| `breakdown` \| `checkout` \| `warning` \| `done`.

---

## Complexity Tracking

Новых библиотек и второго бандла `specs/002-*` нет. Leaflet не подключать. Своей схемы SQLite у D нет.

---

## Stop

Plan phase 0–1 для потока D закрыт артефактами выше.

**Дальше не делать в этой итерации:** `/speckit-tasks`, код React, правки `frontend/src`, `index.md`, orchestration, `.specify/`.
