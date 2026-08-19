# Tutu MCP — справочник по API

**Endpoint:** `https://mcp.tutu.ru/mcp` (Streamable HTTP, JSON-RPC 2.0, POST)
**Сервер:** `tutu-mcp-server` v0.38.0, protocolVersion `2025-06-18`
**Capabilities:** tools, resources, prompts (все `listChanged: false`, `resources.subscribe: false`)
**Авторизация:** не требуется (проверено анонимным запросом)
**Дата снятия:** 2026-08-19

> Сервер полностью **read-only**: поиск + сборка ссылки на оформление. Никаких платежей, личных кабинетов и броней на стороне Tutu. `create_checkout_link` — чистый билдер URL; корзину создаёт браузер пользователя в его сессии.

---

## 1. Инструменты (16)

### Поиск

| Tool | Назначение |
|---|---|
| `search_hotels` | отели по городу и датам |
| `search_avia` | авиабилеты между городами/аэропортами |
| `search_rail` | поезда РЖД |
| `search_bus` | междугородние автобусы |
| `search_etrain` | электрички |
| `search_multitransport` | мультимодальный «как доехать»: avia+rail+bus+etrain параллельно |

**Общие параметры всех `search_*` транспорта:**
`origin`, `destination` (легаси-алиасы `from_city`/`to_city`), `departure_date`,
`page` (1-indexed, ≤10), `page_size` (1..30, default 10),
`sort`: `price_asc`(default) | `price_desc` | `duration_asc` | `departure_asc`,
`price_max`, `direct_only`, `carriers`, `view`: `compact`(default) | `full`.

Специфичные:

- `search_avia`: `return_date`, `adults`, `children`, `infants`, `service_class`, `flight_numbers`
- `search_rail`: `passengers`, `train_numbers`, `seat_categories`
- `search_bus`: `adults`, `children`
- `search_etrain`: только базовые
- `search_multitransport`: `adults`, `modes`, `optimize_for`: `price`|`time` (вместо `sort`)
- `search_hotels`: `city_name` **или** `geo_id`, `check_in`/`check_out` (алиасы `checkin_date`/`checkout_date`), `adults`, `children_ages`, `stars`, `price_max`, `meals`, `hotel_types`, `min_rating`, `free_cancellation`, `breakfast_included`, `hotel_amenities`, `room_amenities`

### Детали

**`get_offer_details`** — карточка одного оффера/отеля.
`product_type*`: `hotels|avia|rail|railway|bus|etrain`; `offer_id`, `hotel_id`, `hotel_geo_id`, `details_ref`, `check_in`, `check_out`, `adults`, `children_ages`, `review_limit`, `review_offset`, `review_sort` (`postedAt|rating`), `review_order` (`desc|asc`), `review_topics`, `view`: `compact|rules|reviews|full`.

**`get_rail_seatmap`** — схема мест по вагонам для выбранного ж/д оффера.
`details_ref*` (object), `car_number`, `max_cars`, `max_seats_per_car`, `view` (`compact|full`), `task` (точечный вопрос вместо всей карты), `seats_together`.

### Плейбуки (без аргументов)

`get_avia_instructions`, `get_rail_instructions`, `get_bus_instructions`, `get_etrain_instructions`, `get_hotels_instructions`, `get_multitransport_instructions` — подробные правила по домену (progressive disclosure: вызывать один раз перед работой с новым доменом).

### Служебные

**`create_checkout_link`** — единственная ручка «перейти к оформлению» для всех продуктов. На вход передаются поля из `checkout_ref` оффера. Возвращает `{checkout_url, kind}`.

Полный набор полей: `product_type`, `transport`, `search_results_url`, `offer_hash`, `service_class`, `is_round_trip`, `return_departure_at`, `departure_at`, `passengers`, `passengers_full/adult/child/infant`, `departure_geo_city_id`/`arrival_geo_city_id`, `departure_avia_id`/`arrival_avia_id`, `departure_city_id`/`arrival_city_id`, `departure_station_code`/`arrival_station_code`, `departure_etrain_id`/`arrival_etrain_id`, `train_number`, `city_from`/`city_to`, `departure_id`/`arrival_id`, `departure_stop_id`/`arrival_stop_id`, `departure_stop_name`/`arrival_stop_name`, `departure_geo_point_id`/`arrival_geo_point_id`, `segment_hash`, `car_number`, `seat_numbers`, `seat_count`, `fare_type`, `gender_type`, `search_id`, `result_id`, `card_id`, `hotel_alias`, `offer_pack_hash`, `hotel_geo_id`, `check_in`, `check_out`, `adults`, `children_ages`, `fallback_url`.

**`fetch_resource`** — чтение ресурса `tutu://…`. Параметр: `uri*`.

---

## 2. Ресурсы

| URI | Что внутри |
|---|---|
| `tutu://geo` | **заглушка**: 2 города, 30 остановок, поля только `geo_id` и `name`, координат нет |
| `tutu://amenities/dictionary` | код удобства → русская подпись |
| `tutu://help/overview` | краткий обзор и индекс |
| `tutu://status` | здоровье сервера и апстримов |
| `tutu://special-offers` | спецпредложения (экспериментально, не источник истины) |
| `tutu://version` | билд-метаданные |
| `tutu://debug/memory` | снимок памяти процесса |

## 3. Промпты

`plan_trip` — единственный серверный промпт.

---

## 4. Модель данных ответа

**Транспортный оффер:** `price` (самый дешёвый вариант), `legs[].segments[]`, `search_results_url`, опциональный готовый `checkout_url`, объект `checkout_ref`.

- avia / bus / etrain дополнительно: `variants[]` — все тарифные семейства, дешёвые первыми, у каждого свой `offer_hash`.
- rail вместо этого: сводка `fares { count, price_from, price_to, currency, refundable_count, changeable_count, refundable_unknown, changeable_unknown, seat_categories, uncategorized_fares }`. `seat_categories` говорит, какие категории (сидячий/плацкарт/купе/СВ) продаются и от какой цены. Полная лестница классов — через `get_offer_details`.
- hotels: `best_offer.checkout_url` (готовая страница отеля) + `checkout_ref` для диплинка `explicit/hotel`.

**`meta`:** `has_more`, `total_matched`, `carriers_available[]` (`name` + `offers_count` + `price_from`), `post_filter_dropped_*`, `from`/`to` (+ `resolved_geo` для отелей) с `name` + `geo_id` + `region`, `modes_summary`, `unavailable[]`.

---

## 5. Каноничный флоу

1. **Search** → один из `search_*`.
2. **(опц.) Details** → `get_offer_details`, для ж/д ещё `get_rail_seatmap`.
3. **Checkout** → `create_checkout_link` с полями из `checkout_ref`.

Поведение `kind` в ответе `create_checkout_link`:

- **avia** → `deeplink` (mtp-deeplink на покупку). Прямой round-trip диплинкуется, если передать `is_round_trip` + `return_departure_at`; иначе и для стыковочного round-trip → `search_redirect` на страницу поиска. Обязательно прокидывать `passengers_full/child/infant`, иначе корзина откроется на одного взрослого и сумма не сойдётся. Флаг `is_multi_pnr` = раздельные билеты, нужно показать `multi_pnr_note`.
- **rail / bus** → диплинк `explicit/train` / `explicit/bus`, по умолчанию открывает выбор мест. Если пользователь явно выбрал места (rail: `car_number` + `seat_numbers`; bus: `seat_numbers`) — возвращается `checkout_deeplink` с уже выбранными местами. Без нужных id — фолбэк `order_url` / `seats_url`.
- **hotels** → диплинк `explicit/hotel`. Хеш комнаты (`offerpack_hash` конкретного тарифа из `get_offer_details`) даёт `checkout_deeplink` прямо в корзину; `best_offer.offerpack_hash` из выдачи корзину НЕ создаёт.
- **etrain** → URL страницы расписания.

---

## 6. Правила вывода

- Цены рендерить как в payload, без округления. Цена отеля — уже итог за весь период и состав гостей (`price_basis: "stay_total"`), умножать на `stay.nights` нельзя.
- Не выдумывать опции, которых нет в `offers[]` / `hotels[]`, и не подменять отсутствующие поля веб-поиском. Если поля нет — так и говорить.
- URL воспроизводить ровно как вернул сервер — это непрозрачная строка, её нельзя пересобирать, перекодировать или подрезать параметры.
- Отзывы цитировать дословно, 1–2 фрагмента на плюс/минус, с датой.
- Всегда называть, какой город и область резолвились (`meta.from`/`meta.to`).
- Фильтр по перевозчику — только эхом `name` из `meta.carriers_available`.

---

## 7. Практическая заметка по доступу

Из облачного контейнера прямой `curl` к `mcp.tutu.ru` блокируется прокси (403 CONNECT). Обход: открыть `https://mcp.tutu.ru/mcp` в браузере (GET отдаёт 405, но страница грузится) и делать `fetch('/mcp', {method:'POST'})` с того же origin — CORS обходится, сессионный заголовок не требуется. На VPS с обычной сетью это не нужно.
