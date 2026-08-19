---
type: Execution Prompt
title: Баг доступности билетов — цена плеча читается не из того поля (электрички/короткие хопы)
description: На Москва→Мытищи/Химки система пишет «билета нет», хотя у Tutu есть 7 электричек от 139₽. Причина: quote_from_route_doc берёт тариф только из offers[], а search_multitransport для etrain/коротких маршрутов возвращает цену в meta.modes_summary.<mode>.min_price без offers[]. Продаваемость (modes_summary) и цена (offers) расходятся → ложное no_route.
tags: [spec-kit, "001", execution, backend, price, bug, blocker]
feature: 001-burger-mvp
timestamp: 2026-08-19T22:10:00Z
status: bug-open
---

# Наряд: починить ложное «билета нет»

Вставить в чат-лаунчер. Точечный баг котировки плеча в backend/services/price.py.
Контракт SSE и cluster_id не трогаем.

Диагноз проверен живьём через клиент проекта (lib.tutu_mcp):

  Москва → Мытищи, 2026-10-15:
    meta.modes_summary.etrain = {count: 7, min_price: 139, min_duration_min: 22}
    offers = None
    sellable_modes_from_meta(...) = "etrain"   (город ПРАВИЛЬНО продаётся)
    _min_positive_price(offers)  = None        (цена «отсутствует» — ЛОЖНО)
  Москва → Химки — идентично (7 электричек от 139).

Корень: quote_from_route_doc (price.py:455) берёт цену ТОЛЬКО из offers/variants
(payload_offers → pick_priced_offer). Для etrain/коротких хопов search_multitransport
отдаёт сводку в meta.modes_summary.<mode>.min_price и НЕ отдаёт offers[]. Раз offers
пуст → offer=None → return None → плечо трактуется как no_route/no_price → «билета нет».
Продаваемость и цена читают РАЗНЫЕ поля одного ответа и расходятся.

```
Роль: чат-лаунчер. Баг: короткие/электричные плечи (Москва→Мытищи, →Химки и т.п.)
ложно показывают «билета нет», хотя билеты есть (7 электричек от 139₽). Владелец:
backend/services/price.py. Контракт не менять.

## Инварианты
- single-source-seams: продаваемость и цена плеча должны опираться на ОДИН источник.
  Сейчас sellable читает modes_summary, а цена — offers → противоречие.
- silent-failure-map: «no_route», которого на деле нет (просто не прочитали цену) —
  это система врёт молча. Недопустимо.
- guard-before-price сохранить: guard резолва как был, чиним только извлечение тарифа.

## Fix F1 — фолбэк тарифа на modes_summary (🔴 главное)
В quote_from_route_doc: если payload_offers пуст ИЛИ pick_priced_offer вернул None,
НЕ возвращать None сразу. Прочитать meta.modes_summary:
  - выбрать самый дешёвый режим с count>0 и положительным min_price
    (price_is_absent(min_price)==False; помнить: 0 у etrain = отсутствие, не тариф);
  - использовать этот min_price как цену плеча, а имя режима — как mode/modes.
Только если и в modes_summary нет ни одного продаваемого режима с ценой — тогда
честный no_price/no_route.
Единый источник: тариф брать из того же modes_summary, что решает продаваемость.

## Fix F2 — партийная цена adults>1 (🟠 корректность)
Инструкция Tutu: transport price может быть per_seat (rail/etrain) или party_total
(avia/bus), см. meta.pricing.basis; при adults>1 у per_seat есть min_price_party.
При фолбэке на modes_summary для adults>1 использовать партийную сумму, если она
есть, иначе явно НЕ умножать вручную наугад — брать что вернул Tutu. (Если сводка
не даёт партийную цену — пометить как «от N₽ за 1», а не врать умножением.)

## Fix F3 — ссылка покупки для etrain (🟡 деградация, не блокер)
modes_summary даёт число, но НЕ даёт checkout_ref. Для реальной кнопки покупки
электрички нужен per-mode search (search_etrain → schedule checkout_url) ИЛИ
create_checkout_link. Если ref нет — показывать цену без deeplink и честную подпись
(«электричка от 139₽, ссылка — на расписании Tutu»), а не прятать плечо. НЕ выдумывать
ссылку (инструкция Tutu запрещает пересобирать url).

## Что НЕ трогать
- sellable_modes_from_meta — он уже правильный, читает modes_summary. Подгонять под
  него надо цену, а не наоборот.
- Формат SSE (leg/breakdown/checkout), cluster_id, guard.

## Готово, когда
- Москва→Мытищи и Москва→Химки дают плечо с ценой ~139₽ (etrain), НЕ «билета нет».
- Любое плечо, где sellable_modes непусто, НЕ падает в no_route из-за пустого offers.
- adults>1 не даёт наугад умноженную цену.
- Регресс эталона (Москва→Углич «своим ходом», Москва→Ярославль avia) не сломан.
- Добавить тест: маршрут с modes_summary без offers → цена из modes_summary.
```

# Заметка надзора (не в лаунчер)

- Это самый заметный на демо баг: короткие поездки — первое, что тыкают, и «билета
  нет» на Химки читается как «продукт сломан». Приоритет высокий.
- Архитектурный корень — рассинхрон двух прочтений одного ответа Tutu (продаваемость
  из modes_summary, цена из offers). После F1 источник один. Это тот же класс, что
  и P1 из PROMPT-backend-live-price (метка врёт не по факту) — честность источника.
- Связка с волной-1: узлы вроде Мытищи в БД помечены sellable ПРАВИЛЬНО (probe читал
  modes_summary). То есть данные не врут — врёт только ценовое плечо. Значит fix
  локальный в price.py, перепрошивать БД не нужно.
- F3 пересекается с P4 (create_checkout_link) из наряда живой цены — свести, чтобы
  ссылку покупки чинили в одном месте, а не дважды.
