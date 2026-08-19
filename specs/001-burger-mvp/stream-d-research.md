---
type: Research
title: Stream D — research (решения плана)
description: Phase 0 /speckit-plan. Decision / Rationale / Alternatives. NEEDS CLARIFICATION нет.
tags: [spec-kit, "001", stream-d, research]
timestamp: 2026-08-19T16:40:00Z
feature: 001-burger-mvp
status: draft
spec: stream-d-frontend.md
plan: stream-d-plan.md
---

# Stream D — Research

Все пункты Technical Context разрешены замороженными швами. Ниже — явные развилки, чтобы их не открывать на implement.

---

## 1. Карта: MapLibre, не Leaflet

**Decision:** MapLibre GL JS. Стек G8 / [plans/stack.md](../../plans/stack.md). Leaflet запрещён.

**Rationale:** На карте кластера — все объекты, не только топ карточки. Leaflet рисует каждую точку DOM-маркером; тысячи POI (F11) убивают кадр. MapLibre — WebGL, агрегация на GPU. Зафиксировано в mvp-spec §10 и [plans/worker-D-frontend.md](../../plans/worker-D-frontend.md).

**Alternatives considered:**

- Leaflet + кластеризация маркеров — отклонён: всё равно DOM, риск F11, стек уже заморожен.
- Deck.gl / kepler — лишняя зависимость, запрет новых библиотек без нужды.
- Только список без карты — ломает выдачу «карта + карточки рядом».

---

## 2. Старт: mock-first, не ждать B/C

**Decision:** Клиент стартует на моках, бит-в-бит совпадающих с [plans/api-contract.md](../../plans/api-contract.md). Переключатель `mock` / `live`. Фикстуры: эталон №1 + запасной бургер.

**Rationale:** Ключ параллельности orchestration §1: D не блокируется ингестом A и хендлерами B/C. G9 уже зелёный. Мок с задержками SSE проверяет UX G6 до живого Tutu.

**Alternatives considered:**

- Ждать `/api/places` от B — схлопывает параллельность в очередь.
- Мок «упрощённый» (`yar-rostov`, цена сразу на карточке) — разъедется с контрактом на G10.
- Live-only на VPS — нет отладки инкрементального SSE на ноутбуке без бэка.

---

## 3. Радиус: дискрет 50 / 100 / 150, max 150

**Decision:** Ползунок с защёлкой на {50, 100, 150}. Дефолт 100. Выше 150 — нельзя в UI (порог D2). Не свободный range.

**Rationale:** V2: свободный ползунок требовал бы пересчёта тысяч пар < 200 мс. Бэкенд предпосчитывает три радиуса. Контракт: иное `radius_km` → 400. Верх жёстко = порог матрицы D2 (orchestration §6).

**Alternatives considered:**

- Непрерывный 0–300 км — не влезает в бюджет фазы 1; ломает предпосчёт `cluster(id, radius_km)`.
- Только 100 км — не даёт счётчик мест на шагах и UX «шире/уже».
- Шаги 25/50/100 — не совпадают с контрактом и PK предпосчёта.

Следствие: смена шага при том же множестве хабов **не** меняет `cluster_id`.

---

## 4. Эталон: `industrial_museum`, не `industrial_site`

**Decision:** Запрос эталона №1 = `ancient_temple` + `industrial_museum`. Не заводы.

**Rationale:** В `fixtures/rows/poi.json` честный слой промтуризма — музеи (`industrial_museum`, `density_label: rare`). `industrial_site` — действующие заводы, нулей в эталонной выборке. Решение оркестратора 2026-08-19; спека D уже принята с этим комбо.

**Alternatives considered:**

- Маппить `industrial_site` → `industrial_museum` на фронте — скрытая ложь, B явно не маппит.
- Оставить заводы в меню без метки rare/disclaimer — пользователь соберёт пустышку и решит, что сервис сломан.

---

## 5. Share: percent-encode всего `cluster_id`

**Decision:** В URL шеринга (после G10) класть `cluster_id` только как query-параметр после `encodeURIComponent` (UTF-8) всей строки. Не path segment. Декод → тот же id в `POST /api/price`.

**Rationale:** Id содержит кириллицу, `|` и запятую (`c:Ростов|Ярославская область,Ярославль|Ярославская область`). Сырой path ломает роутинг. Контракт: *Share URLs must percent-encode the whole cluster_id*.

**Alternatives considered:**

- Короткий slug `yar-rostov` — отменён G2; радиус и фаза не в id, но множество хабов — да.
- Base64 id — лишний диалект; percent-encode достаточно и обратим.
- Два id (фаза 1 / фаза 2) — рвёт G10.

---

## 6. Край: `:8080` nginx

**Decision:** Демо-край D = nginx `:8080` (`docker-compose.g6.yml`). Клиент ходит на `/api/` того же origin (F10).

**Rationale:** G6 доказал SSE без буфера на burger nginx `:8080`. Вешать демо на чужой домен / gzip-прокси отвергнуто (ломает стрим). Канон: [plans/deploy-vps.md](../../plans/deploy-vps.md).

**Alternatives considered:**

- Path на чужом сайте — отвергнут.
- Браузер → `backend:8000` в обход nginx — SSE на проде не тот, что G6.

---

## 7. Каталог меню: `ingredients.yaml`, не новый эндпоинт

**Decision:** Плотность карточек меню — поля `density_label` / `density_measured` из [ingredients.yaml](../../ingredients.yaml) (локальный каталог / мок). Контракт G2 эндпоинта меню не содержит.

**Rationale:** Worker-D упоминает «плотность из `/api`», но замороженный контракт — только `/api/places` и `/api/price`. Выдумывать третий путь без Архитектора нельзя.

**Alternatives considered:**

- Ждать каталог от B — блокер меню до часа 10 без нужды.
- Хардкод 20 подписей без density — нарушение FR-D2 / §8.
