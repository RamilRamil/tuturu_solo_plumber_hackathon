# План: Архитектор

Ты держишь целостность системы. Не пишешь фичи — задаёшь швы, ревьюишь их и не
даёшь потокам разъехаться. Твой выход — час 0–3, дальше ревью.

Читать: `mvp-spec.md` §4–5, `open-issues.md` B1–B4, `plans/00-orchestration.md`.

## Час 0–1 — заморозить схему БД (блокер для A/B/C)

`schema.sql` + модели (`models.py` / SQLAlchemy или dataclass — выбрать одно).
Отталкиваться от mvp-spec §5, но с правками из open-issues:

- `hub` — как в data-collection-spec §D1 (name, subject, lat, lon, population,
  tutu_geo_id, resolved_name, resolved_region, sellable_modes, min_price_from_moscow,
  latency_ms, checked_at). Добавить `probe_status` ∈ {sellable, not_sellable, misresolved}.
- **`leg`** (НОВОЕ, B2) — направленная пара:
  `origin_hub, dest_hub, modes, min_price, duration_min, date_probed, latency_ms,
   checked_at, status ∈ {ok, no_route, misresolved}`. PK (origin_hub, dest_hub, date_probed).
- `hub.sellable_modes` оставить, но семантику зафиксировать как производное;
  если вводишь `reachable_from_any` — задокументируй, что это не свойство направления.
- `poi`, `cluster`, `route_cache`, `hotel_cache`, `misresolve_log` — как в §5.
- Индексы: `poi(lat, lon)`, `poi(ingredient_id)`, `leg(origin_hub, dest_hub)`.

## Час 1–2 — заморозить контракт API

`/api/places` и `/api/price` (SSE) — взять §4 mvp-spec дословно, дописать
недоопределённое:
- `rarity.rank` и порядок сортировки `places[]` — сослаться на формулу B3
  (worker-B). Зафиксировать, что список **отсортирован по cluster_score убыв.**
- SSE-события `resolved|leg|hotel|breakdown|checkout|warning|done` — payload каждого.
- Опубликовать как `openapi`/markdown в `plans/api-contract.md`. Это интерфейс
  между B/C и D — заморозить, менять только через тебя.

## Час 1–2 (параллельно) — MCP-клиент как общая lib

`lib/tutu_mcp.py`:
- `initialize` (protocolVersion `2025-06-18`), POST /mcp, парсер и `application/json`,
  и SSE `data: `.
- `call_tool(name, args)` с тайм-аутом ≥ 30 с, ретраем, семафором concurrency=4.
- **Guard §7 здесь же** (`check_resolve(meta, expected_name, expected_region)`),
  чтобы A и C не копировали. Нормализация региона = вхождение подстроки.
- Кэш «результат в БД до обработки» — обёртка, общая для проберов.
A (ингест) и C (фаза 2) импортируют это. Не разрешать двух реализаций.

## Час 2–3 — фикстуры + пустые регресс-тесты (разблокирует B/C/D)

- `fixtures/` : ответы `search_multitransport` для «Ростов», «Ростов Великий»,
  «Великий Новгород» (из проверки Stream A §5); POI-выборка по Ярославской обл.;
  несколько `leg`; ответ отеля. Формат = ровно то, что кладёт MCP-lib в БД.
- `tests/test_acceptance.py` (пустой каркас, red): эталон №1 (Ярославль→Ростов
  Великий, храм+промтуризм, Москва, окт-2026, топ-5, 4 342 ₽ ±15%) + запасной
  одноузловой бургер (B4). Плюс регресс-набор узлов из open-issues B1 п.4:
  Ярославль, Ростов Великий, Рязань, Коломна, Тула, Калуга, Владимир, Иваново.

## Дальше — ревью швов (непрерывно)

- Никто не определяет свои модели данных — только импорт из схемы.
- Guard не продублирован. MCP-клиент один.
- Проверить, что ползунок радиуса (D) ограничен порогом D2 (150 км), иначе
  матрица неполна, а UI не знает (open-issues V1).
- Следить за V3: окна дат считаются лениво, не 140 вызовов синхронно.
