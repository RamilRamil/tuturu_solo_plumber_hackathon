---
type: Quickstart
title: Stream C — проверка куска C на G10
description: Как убедиться, что POST /api/price по cluster_id эталона отдаёт resolved, хотя бы один leg и done по одному. Не SC-price. Команды печатает агент, живой прогон — человек.
tags: [spec-kit, "001", stream-c, quickstart, G10]
timestamp: 2026-08-19T16:40:00Z
feature: 001-burger-mvp
status: draft
derives_from: [stream-c-phase2.md, stream-c-plan.md]
---

# Stream C — Quickstart (кусок C на G10)

Это проверка **после** implement (сейчас код `/api/price` ещё не пишется).
Критерий оркестрации §3 п.3–4, не п.1–2 (`SC-ranking` — поток B).

Контракт полей: [plans/api-contract.md](../../plans/api-contract.md). Сюда
payloads не копировать.

## Что должно быть зелёным заранее

- Фикстуры загружены в SQLite (`fixtures/` → `data/burger.db`).
- Эталонный id **тот же**, что у `/places` и у
  [fixtures/etalon_1.json](../../fixtures/etalon_1.json). Состав ингредиентов
  в примере мест (`industrial_museum`) множество хабов **не меняет**.
- Стек поднят так, чтобы клиент шёл в **nginx**, не в `backend:8000`:
  Mac — compose `:80`; VPS — `docker-compose.g6.yml` **`:8080`**.
  Не чужой домен и не gzip/redirect-прокси поверх SSE.
- G6-smoke на том же крае когда-то уже показал паузы между событиями
  (`GET /_sse_smoke`).

## Эталонный `cluster_id`

Строка G2 (кириллица + `|`). В JSON-теле UTF-8, не path-сегмент.

Значение: поле `cluster_id` в `fixtures/etalon_1.json` (два хаба: Ростов и
Ярославль, Ярославская область). Origin/даты/взрослые — как в том же файле
(`month` `2026-10`, `days` 3, `adults` 1). `budget_scope` по умолчанию
`transport`.

## Прогон 1 — счастливый путь (через nginx)

Печатать (человек выполняет). `-N` обязателен, иначе буфер клиента склеит кадры.

Mac, край `:80`:

```bash
curl -N -s -D - \
  -H "Content-Type: application/json; charset=utf-8" \
  -H "Accept: text/event-stream" \
  --data-binary @- \
  http://127.0.0.1/api/price <<'EOF'
{"cluster_id":"<paste etalon cluster_id>","origin":"Moscow","days":3,"month":"2026-10","adults":1,"children_ages":[],"budget_scope":"transport"}
EOF
```

VPS-край (предпочтительно для G10 как прод-путь): тот же POST на
`http://<demo-host>:8080/api/price`. Runbook SSH/rsync:
[plans/deploy-vps.md](../../plans/deploy-vps.md). Агент SSH/docker не гоняет.

**Pass куска C:**

1. HTTP 200, `Content-Type` содержит `text/event-stream`.
2. Сначала кадр `event: resolved`, затем отдельно `event: leg`, затем отдельно
   `event: done` (между ними пауза, не три `data:` одним комком в конце).
3. Допустимы лишние кадры (`hotel`, `breakdown`, `warning`, `checkout`) — тоже
   по одному. Если цена уже ушла, `breakdown` до `done`.
4. В `done` (и в `breakdown`, если есть) `price_status` = `fixture-confirmed`.
5. Не требовать сумму 4342 и живую ссылку Tutu — это не G10.

**Fail:** пачка всех событий в одном чтении; первый `leg` только после полного
маршрута; прямой успех с `:8000` при красном nginx; `fixture-confirmed` снят
без live обоих сценариев.

## Прогон 2 — неизвестный id

Тот же POST, `cluster_id` заведомо не из таблицы `cluster` (например ASCII
`c:no-such-hub`).

**Pass:** HTTP **404**. Тело не SSE-поток с `warning`.

## Прогон 3 — стык с B (сквозной G10)

1. `POST /api/places` с бургером эталона (ингредиенты как у B / фикстуры,
   включая `industrial_museum`).
2. Взять `cluster_id` из [fixtures/etalon_1.json](../../fixtures/etalon_1.json)
   (пара хабов), **не** `places[0]`: одиночный Ярославль может стоять выше пары.
3. Подставить в `/api/price` без перекодирования id в другой формат.

**Pass:** id совпал; кусок C из прогона 1 зелёный. Топ-5 — ответственность B.

## Чего не проверять этим quickstart

- Live Tutu, ±15% к 4342, свежесть `checkout_url`.
- Серые карточки в UI (D).
- Жадно все недельные окна месяца.
- Guard на «Ростов»→Ростов-на-Дону — регресс lib, не обязательный кадр G10;
  но цена омонима в `leg` = красный инвариант, если вдруг всплывёт.
