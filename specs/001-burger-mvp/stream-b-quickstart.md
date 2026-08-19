---
type: Quickstart
title: Stream B — прогон SC-B1 / SC-B2
description: Как после кода (ещё не писать) прогнать офлайн-регресс ранжирования на fixtures/. Без SC-price.
tags: [spec-kit, "001", stream-b, quickstart]
timestamp: 2026-08-19T12:35:00Z
feature: 001-burger-mvp
status: draft
spec: stream-b-phase1.md
---

# Quickstart: SC-ranking на фикстурах

Этот файл — инструкция **после** зелёного контроля plan и появления
`POST /api/places`. Код кластеризации и хендлер **сейчас не писать**.
Живой Tutu и `POST /api/price` не входят в прогон B.

Контракт тел: [plans/api-contract.md](../../plans/api-contract.md).
Ожидаемые id: [fixtures/etalon_1.json](../../fixtures/etalon_1.json),
[fixtures/backup_single_hub.json](../../fixtures/backup_single_hub.json).

## 0. Предусловия (уже в репо)

- Схема и модели: `schema.sql`, `lib.models`.
- Загрузчик: `lib.load_fixtures.load_golden_fixtures`.
- Процесс: `uvicorn backend.app:app --host 0.0.0.0 --port 8000`
  (`BURGER_DB`, см. [plans/stack.md](../../plans/stack.md)).
- С хоста через nginx: `POST /api/` проксируется на бэк
  ([nginx/nginx.conf](../../nginx/nginx.conf)). Для регресса B достаточно
  бить в процесс на 8000.

Сети наружу в этом прогоне быть не должно.

## 1. Наполнить SQLite золотом

Создать пустой файл БД, навесить схему, вызвать `load_golden_fixtures` на
`fixtures/` (корневой каталог фикстур, не сырой G5). Переменная `BURGER_DB`
указывает на этот файл. Не коммитить живой `.db`.

Проверка загрузки (не приёмка ранжирования): в `hub` есть
`Ярославль|Ярославская область` и `Ростов|Ярославская область`; в `poi` есть
хотя бы один `industrial_museum` и один `ruins`.

Затем опустошить кэш кластеров — иначе SC-B1 читает `clusters.json` и
маскирует одиночного Ярославля с тем же покрытием:

```sql
DELETE FROM cluster;
```

Регресс SC-B1/SC-B2 гонять только после этого DELETE. Живой проход дисков по
`hub`+`poi` — источник правды.

## 2. SC-B1 — эталон №1 существует как пара

Когда хендлер появится: `POST /api/places` с телом

```json
{
  "ingredients": ["ancient_temple", "industrial_museum"],
  "radius_km": 100,
  "limit": 20
}
```

Pass (hard):

- HTTP 200, поле `places` — список.
- В `places[]` (любая позиция) есть
  `cluster_id` = значение из `fixtures/etalon_1.json`
  (`c:Ростов|Ярославская область,Ярославль|Ярославская область`).
- У этой карточки `coverage.matched` содержит оба id,
  `coverage.missing` пуст.
- SC-B3 на том же ответе.
- В запросе нет origin/дат/цен; в карточке нет поля билета `sellable`.
- Одиночный Ярославль с тем же `len(matched)=2` **может** стоять выше пары.

Smoke (не fail сборки, только фикстуры): пара среди первых пяти.

Fail hard: маппинг museum→site; пары нет в `places[]`; прогон против
непустой `cluster` без живого прохода дисков; нарушение SC-B3.

Percent-encode: в JSON id **сырой**. Кодирование UTF-8 всего id нужно только
если D кладёт его в URL шеринга.

## 3. SC-B2 — запасной одноузловой бургер существует

```json
{
  "ingredients": ["ancient_temple", "ruins"],
  "radius_km": 100,
  "limit": 20
}
```

Pass hard: в `places[]` есть `cluster_id` из `fixtures/backup_single_hub.json`
(`c:Ярославль|Ярославская область`) с полным покрытием. В топ-5 — smoke.
Пара Ярославль+Ростов не обязана быть первой.

## 4. Сопутствующие проверки (тот же стенд)

- **SC-B3:** в каждом из двух ответов нет карточки с меньшим
  `len(coverage.matched)` выше карточки с большим.
- **US4:** те же ингредиенты эталона, `radius_km` 50 и 150 — id пары совпадает
  с шагом 100, если набор узлов тот же.
- **Вход:** пустой `ingredients` или `radius_km` 200 → 400, не пустой 200.
- **Сеть:** в логах процесса нет исходящих HTTP на время этих POST.

Не pass/fail для B: сумма 4342, SSE, `checkout_url`, метка
`fixture-confirmed`.

## 5. G10 (конец часа 26) — только кусок B

Повторить шаги 2–3 на фикстурах (hard: существование + SC-B3; топ-5 smoke).
После подмены волной 1 (D1+D3) — те же два POST: hard-гейты остаются;
топ-5 smoke не требуется. Передача того же `cluster_id` в `/api/price` —
приёмка C, не этот quickstart.

## 6. Что не делать в этом файле

- Не добавлять тестовый код и debug-print в репозиторий на этапе plan.
- Не править `fixtures/rows/poi.json` (храмы Ярославля не вырезать).
- `clusters.json` не считать топ-5; для SC-B* таблица `cluster` пуста.
- Не считать прогон против мока цены доказательством SC-price.
