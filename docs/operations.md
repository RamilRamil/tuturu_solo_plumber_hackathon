# Запуск и эксплуатация

## Требования

- Docker с Compose v2 — рекомендуемый способ;
- либо Python 3.12 и Node.js 20+ для запуска без контейнеров;
- SQLite-файл и `coverage.json` в каталоге `data`;
- сеть нужна только для live Tutu, загрузки OSM, Wikidata и AI-парсинга.

## Конфигурация

Скопируйте `.env.example` в `.env` и не коммитьте секреты.

| Переменная | Default | Назначение |
|---|---|---|
| `BURGER_DB` | `data/burger.db` | путь к SQLite; в compose обычно `/app/data/burger.db` |
| `BURGER_SEED_FIXTURES` | `0` | заполнить маленькую/отсутствующую demo-БД fixtures |
| `BURGER_LIVE_TUTU` | `0` | разрешить live search-вызовы Tutu; не бронирует и не оплачивает |
| `BURGER_SC_PRICE_ACCEPTED` | `0` | разрешить статус live после приемки эталона и backup |
| `BURGER_COVERAGE` | `data/coverage.json` | путь к метаданным покрытия |
| `BURGER_PRICE_DEMO_PACE` | off | искусственные задержки между SSE-событиями для демонстрации |
| `ANTHROPIC_API_KEY` | отсутствует | включает AI-парсинг `/api/parse` |

Build argument frontend `VITE_API_MODE_DEFAULT` принимает `live` или `mock`; Dockerfile по умолчанию собирает `live`.

## Docker Compose

### Полный локальный стек

```bash
docker compose up --build
```

Открыть `http://localhost/`. Сервисы: backend без опубликованного наружу порта, static frontend и nginx на host port 80. Каталог `./data` монтируется в `/app/data`.

Проверки:

```bash
curl -s http://localhost/healthz
curl -N http://localhost/_sse_smoke
```

### Изолированная demo-конфигурация

```bash
docker compose -f docker-compose.g6.yml up --build
```

Открыть `http://localhost:8080/`. Эта конфигурация использует `burger.g10.db`, автоматически наполняет fixtures и гарантированно держит live Tutu выключенным. Она не занимает host ports 80/443.

## Запуск без Docker

Backend:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python -m backend.boot
```

Backend слушает `http://localhost:8000`. Для fixtures задайте отдельный файл, чтобы не затереть live-базу:

```bash
BURGER_DB=data/local-fixtures.db BURGER_SEED_FIXTURES=1 python -m backend.boot
```

Frontend в другом терминале:

```bash
cd frontend
npm ci
npm run dev
```

Vite dev server должен проксировать `/api` согласно `vite.config.ts`; production использует nginx.

## Проверка качества

Backend:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Frontend:

```bash
cd frontend
npm ci
npm run build
```

Критичные проверки включают: трехсоставный `probe_status`, guard региона, локальность `/api/places`, стабильный cluster ID, сохранение кластеров, производительность поиска, порядок SSE, отмену потока, кэш пассажиров и статус цены.

## Healthcheck

`GET /healthz` возвращает:

```json
{
  "ok": true,
  "db_path": "data/burger.db",
  "db_bytes": 123456,
  "data_mode": "live-data",
  "live_tutu": false,
  "sc_price_accepted": false
}
```

`ok: true` означает, что процесс отвечает; это не полная проверка целостности БД или доступности Tutu. Нулевой `db_bytes`, неожиданный `data_mode` или сочетание `live_tutu=true`/`sc_price_accepted=false` требуют внимания.

## Диагностика

| Симптом | Проверка | Вероятная причина |
|---|---|---|
| UI открывается, API 502 | `docker compose ps`, backend logs | backend не стартовал или неверный volume |
| SSE приходит одним блоком | `curl -N /_sse_smoke`, nginx config | proxy buffering включен |
| `/api/places` пуст | `/api/coverage`, число строк `poi`/`hub` | регион не загружен или БД не та |
| cluster not found при цене | сначала повторить `/api/places` | кластер не сохранен для текущей БД |
| Все цены fixture-confirmed | `/healthz` и env | live выключен либо acceptance flag не установлен |
| Город стал misresolved | `misresolve_log` | Tutu вернул одноименный город другого региона |
| AI-поле ничего не выбрало | `/api/parse/health` | нет ключа, timeout или невалидный ответ модели |
| Карта показывает меньше POI, чем счетчик | проверить `name` у POI | frontend намеренно не рисует безымянные POI |

Полезные команды:

```bash
docker compose ps
docker compose logs --tail=200 backend
docker compose logs --tail=200 nginx
sqlite3 data/burger.db 'select count(*) from hub; select count(*) from poi;'
```

## Резервное копирование

Перед ингестом или заменой данных остановите пишущие процессы и скопируйте SQLite-файл вместе с `coverage.json`. Не включайте `BURGER_SEED_FIXTURES=1` для live `burger.db`: boot дополнительно отказывается seed-ить файл с таким именем размером больше 10 КБ, но этот guard не заменяет backup.

## Развертывание

На demo-хосте используется `docker-compose.g6.yml`, публикующий nginx на 8080. Исходники синхронизируются без `--delete`, затем стек пересобирается. Детальный runbook с SSH/rsync находится в `plans/deploy-vps.md`.

Для HTTPS ставьте отдельный reverse proxy перед demo-nginx и отключайте буферизацию SSE. Не направляйте поток через конфигурацию с gzip/response buffering. После выкладки обязательно проверьте `/healthz`, `/_sse_smoke`, один `/api/places` и полный `/api/price` до `done`.

## Безопасность

- `.env`, ключи API и SSH-ключи не входят в репозиторий и Docker image.
- Tutu-интеграция выполняет только поиск; платежных операций нет.
- Публичная аутентификация и rate limiting в приложении не реализованы — их должен обеспечивать внешний edge, если сервис выходит за рамки демо.
- CORS отдельно не настроен: штатная схема предполагает same-origin через nginx.
- SQLite рассчитан на один небольшой backend и ограниченную конкурентную запись, а не на горизонтальное масштабирование.
- `mcp_cache` содержит полные ответы внешнего API; перед публикацией снимка проверяйте его на чувствительные данные.

