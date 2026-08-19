# HTTP API

Base URL в Docker — тот же origin, что у frontend. OpenAPI доступен по `/docs`, схема — `/openapi.json`.

## Сводка

| Метод | Путь | Ответ | Назначение |
|---|---|---|---|
| `GET` | `/healthz` | JSON | Готовность процесса и режим данных |
| `GET` | `/_sse_smoke` | SSE | Проверка потоковой доставки через proxy |
| `POST` | `/api/parse` | JSON | Свободный текст → категории и радиус |
| `GET` | `/api/parse/health` | JSON | Доступность AI-парсинга |
| `POST` | `/api/places` | JSON | Локальный поиск мест |
| `GET` | `/api/coverage` | JSON | Покрытие текущего снимка данных |
| `POST` | `/api/price` | SSE | Маршрут, цены, предупреждения и checkout-ссылки |

## `POST /api/parse`

```json
{"text":"хочу древний храм и промышленный музей неподалёку", "radius_km":100}
```

Ответ:

```json
{
  "ingredients": ["ancient_temple", "industrial_museum"],
  "radius_km": 100,
  "unmatched": []
}
```

`radius_km` необязателен. Неизвестные поля игнорируются. При любом отказе модели endpoint возвращает 200, пустой `ingredients` и исходный текст в `unmatched`. `GET /api/parse/health` возвращает `enabled` и `default_radius_km`; значение `enabled` показывает только наличие ключа, а не доступность внешнего API.

## `POST /api/places`

```json
{
  "ingredients": ["ancient_temple", "industrial_museum"],
  "radius_km": 100,
  "limit": 20
}
```

Ограничения: `ingredients` не пуст, все ID присутствуют в `ingredients.yaml`, радиус равен 50, 100 или 150. `limit` по умолчанию 20. Неизвестные поля игнорируются.

Сокращенный ответ:

```json
{
  "total_found": 12,
  "places": [{
    "cluster_id": "c:Ярославль|Ярославская область",
    "title": "Ярославль",
    "hubs": [{
      "hub_id": "Ярославль|Ярославская область",
      "name": "Ярославль",
      "region": "Ярославская область",
      "lat": 57.626,
      "lon": 39.887,
      "probe_status": "sellable"
    }],
    "center": {"lat": 57.626, "lon": 39.887},
    "diameter_km": 18.4,
    "coverage": {
      "matched": ["ancient_temple", "industrial_museum"],
      "missing": []
    },
    "rarity": {"rank": 1, "total_places_with_combo": 3},
    "objects": [{
      "id": "n-123-ancient_temple",
      "name": "Название объекта",
      "ingredient": "ancient_temple",
      "lat": 57.6,
      "lon": 39.8,
      "significance": 7,
      "wikidata": "Q123",
      "start_date": {"raw":"1670", "from":1670, "to":1670},
      "opening_hours": null,
      "hours_status": "unknown"
    }]
  }]
}
```

Ошибки приложения возвращаются как FastAPI JSON `{"detail":"..."}`:

| Код | Условие |
|---|---|
| 400 | пустой список, неизвестная категория или недопустимый радиус |
| 422 | нарушение Pydantic-типа тела |
| 500 | поврежденный `coverage.json` или внутренняя ошибка |

## `GET /api/coverage`

Возвращает содержимое файла из `BURGER_COVERAGE`. Frontend нормализует исторические варианты полей `loaded`/`regions_loaded`, список `admin_level_4`, массив регионов, время снимка и число POI. Если файла нет, API честно возвращает пустое покрытие и поясняющую `note`.

## `POST /api/price`

```json
{
  "cluster_id": "c:Ярославль|Ярославская область",
  "origin": "Москва",
  "days": 3,
  "month": "2026-10",
  "adults": 2,
  "children_ages": [8],
  "budget_scope": "transport"
}
```

`days` и `adults` должны быть не меньше 1, `month` имеет формат `YYYY-MM`, `budget_scope` — `transport` или `all`. Неизвестный кластер возвращает обычный HTTP 404 до начала SSE. Неверный месяц — 400, ошибки типов — 422.

Успешный ответ имеет `Content-Type: text/event-stream`, `Cache-Control: no-cache`, `X-Accel-Buffering: no`. Формат кадра:

```text
event: leg
data: {"from_name":"Москва","to_name":"Ярославль",...}

```

### Порядок и типы событий

| Событие | Основные поля | Семантика |
|---|---|---|
| `resolved` | `origin`, `hubs`, `guard` | Результат резолвинга и проверки региона; обычно первое событие |
| `leg` | направления, `mode(s)`, `price`, `duration_min`, `date`, `source` | Одно успешно оцененное плечо |
| `hotel` | `city`, `min_price`, `nights`, `price_basis`, `source` | Стоимость проживания за весь stay |
| `warning` | `code`, `message`, `hub_id`, `leg`, `recovered?` | Недоступность, мисрезолв или использование резерва |
| `breakdown` | `transport`, `lodging`, `total`, `budget_scope`, `price_status` | Итоговая разбивка |
| `checkout` | `items[].checkout_url` | Ссылки оформления; API само ничего не покупает |
| `done` | `ok`, `cluster_id`, `price_status` | Терминальное событие |

`source` равен `live` или `cache`. `price_status` равен `fixture-confirmed` либо `live`; второй вариант требует включенного live-режима и успешно пройденного приемочного флага. Клиент должен обрабатывать неизвестные `warning.code`, не предполагая закрытый перечень.

### Пример клиента

```bash
curl -N -X POST http://localhost/api/price \
  -H 'Content-Type: application/json' \
  -d '{"cluster_id":"c:...","origin":"Москва","days":3,"month":"2026-10","adults":1,"children_ages":[],"budget_scope":"transport"}'
```

Для браузера используется `fetch()` и чтение `ReadableStream`, а не `EventSource`, поскольку запрос имеет метод POST и JSON body. Клиент должен уметь отменять поток через `AbortController`.

