---
type: Execution Prompt
title: Бэкенд — живая цена: код готов, «fixture-confirmed» — это флаги + авторизация Tutu
description: АКТУАЛИЗИРОВАНО. Стык B→C (parse_cluster_id_hubs) и live-ветка уже в коде. Tutu MCP проверен — публичный, без токена. «Постоянно fixture-confirmed» = env-флаги (P3) + price_status по ручному флагу, а не по факту (P1). Плюс P4: транспортная ссылка покупки не строится (нужен create_checkout_link).
tags: [spec-kit, "001", execution, backend, price, tutu, honesty]
feature: 001-burger-mvp
timestamp: 2026-08-19T21:15:00Z
status: bugfix-open
---

# Статус: код live уже есть, проблема в флагах/авторизации/честности

Сверено по backend/services/price.py и lib/tutu_mcp.py в основном репо:
- B1 (стык 404) ✅ parse_cluster_id_hubs(cluster_id) есть — C резолвит хабы из
  cluster_id, таблица cluster не нужна. Проверить, что live cluster_id → не 404.
- B2 (live-ветка) ✅ live_tutu_enabled() + live_on + mcp.call_tool(...) в коде.
  Это НЕ no-op больше. Вопрос — включена ли она и работает ли.

Почему видно «fixture-confirmed» всегда — три причины, чинить их:

```
Роль: чат-лаунчер. Код живой цены готов, но пользователь всегда видит
«fixture-confirmed». Причина не в коде фич, а в трёх местах ниже. Владелец:
backend/services/price.py, lib/tutu_mcp.py — координировать с C и владельцем lib.

## P1 — price_status врёт по ручному флагу, а не по факту (🔴 честность)
overall_price_status() = "live" ТОЛЬКО если env BURGER_SC_PRICE_ACCEPTED выставлен,
иначе хардкод "fixture-confirmed" — независимо от того, откуда реально пришли плечи.
Это ручное утверждение, развязанное с правдой (нарушает silent-failure-map:
метка не отражает источник).
Сделать: выводить overall price_status ИЗ фактических источников плеч/жилья
(leg.source/hotel.source, они уже проставляются live|cache):
  - все плечи live → "live";
  - есть cache → "mixed" / "cache" (честно);
  - фикстура → "fixture".
Убрать зависимость общей метки от BURGER_SC_PRICE_ACCEPTED (или оставить флаг
только как гейт демо-приёмки, но НЕ как источник слова "live"). Пер-плечевые метки
live/cache в PriceStream уже честные — общую подогнать под них.

## P2 — авторизация Tutu: РЕШЕНО, токен НЕ нужен (проверено live)
Проверено 2026-08-19: POST mcp.tutu.ru/mcp с initialize БЕЗ Authorization →
200 за 0.26с, tutu-mcp-server v0.40.0, read-only. Плюс в mcp_cache уже 863 реальных
ответа (839 multitransport + 24 hotels). Значит эндпоинт публичный, auth-заголовок
добавлять НЕ надо. P2 как блокер снят.
Остаётся честность: сбой live ловится `except Exception -> cache_fallback` МОЛЧА.
При откате из-за сети/ошибки поднимать видимый warning с причиной (канал warning в
SSE есть), чтобы не выглядело как live, когда live не сработал (silent-failure-map).

## P4 — ссылка покупки: транспорт БЕЗ готового checkout_url (🔴 «как купить»)
Из инструкции Tutu-сервера: транспортные оферы НАМЕРЕННО не несут готовой ссылки —
её даёт отдельный вызов create_checkout_link(checkout_ref). C сейчас только читает
поле obj.get("checkout_url") (checkout_url_from_obj) — у транспорта оно null, готовый
url есть лишь у отелей и etrain. Значит на live кнопка «Купить на Tutu» для плеч
проезда НЕ появится.
Сделать: для выбранного офера вызвать create_checkout_link с его checkout_ref и
прокинуть возвращённый checkout_url в SSE-событие checkout. Ссылку отдавать ТОЧНО
как вернул инструмент — не пересобирать/не переэкодировать (прямое требование Tutu).
Заглушка tutu.ru/example — только в моке (mocks/priceStream.ts), на live не влияет,
но mock удаляется по R5 фронта.

## P3 — live не включён на деплое (🟠 операционка)
live гейтится env BURGER_LIVE_TUTU; демо-темп — BURGER_PRICE_DEMO_PACE. Если на VPS
эти флаги не выставлены — идём в кэш по определению.
Сделать: на боевом окружении выставить BURGER_LIVE_TUTU=1, прогреть mcp_cache по
эталону заранее (чтобы демо не ждало 3–27 с вживую), проверить, что в ответе плечи
идут с source=live, а не cache.

## Что НЕ трогать
- Контракт api-contract.md, формат SSE, схему cluster_id.
- Guard check_resolve, три исхода, price_is_absent — сохранить.
- Пер-плечевые метки source в PriceStream — они правильные, править только общую.

## Готово, когда
- На live с валидными флагами и (если нужен) токеном Tutu: плечи приходят
  source=live, общий price_status = "live"/"mixed" ПО ФАКТУ, а не "fixture-confirmed".
- Если live недоступен (нет токена/сети) — виден warning с причиной, а не немой
  откат в кэш под видом fixture.
- Реальный cluster_id с burger.db → /api/price не 404 (регресс B1).
```

# Заметка надзора (не в лаунчер)

- Главный сдвиг с прошлой версии: код уже live-способный (parse_cluster_id_hubs,
  live_tutu_enabled, call_tool). «Fixture-confirmed» — не «не написали», а флаги +
  авторизация + честность метки.
- P2 — самый вероятный настоящий корень: без Authorization live падает и молча
  становится кэшем. Это одновременно баг честности (silent-failure-map): система
  не должна выглядеть работающей на live, когда live не работает.
- P1 — архитектурный запах: price_status как ручной env-флаг может «врать» в обе
  стороны (live-метка на кэше, fixture-метка на live). Выводить из фактического
  источника — единственный честный вариант.

## B3 — доступ к Tutu MCP: РЕШЕНО
Проверено live: mcp.tutu.ru/mcp публичный, без токена, отвечает 200. Внешнего
блокера нет. «Fixture-confirmed» = флаги (P1/P3) + честность метки, НЕ доступ.
Как проверить в будущем:
  - кэш: sqlite3 data/burger.db "SELECT COUNT(*) FROM mcp_cache;" (реальные ответы);
  - live: POST initialize на эндпоинт curl'ом — 200 без Authorization.
