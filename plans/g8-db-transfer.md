# G8 — путь .db (сторона Worker A)

Не второй FastAPI, не второй git-ритуал. Пакет решений заморожен архитектором в `plans/stack.md`.

## Канон

- Файл ингеста A: `data/burger.db`
- В контейнере бэка: `BURGER_DB=/app/data/burger.db` (том `burger-data` в `docker-compose.yml`)
- В git: только золотой срез `fixtures/`, живую `.db` не коммитить

## Как доезжает до бэка

1. Ингест пишет `data/burger.db` на хосте сбора.
2. Передача: `rsync -av data/burger.db user@backend-host:data/burger.db` (или `scp`).
3. Либо общий Docker volume / bind-mount `./data:/app/data` на той же машине — тогда rsync не нужен.
4. После копии бэк не мигрирует схему сам: источник схемы — `schema.sql` (архитектор).

## Compose с стороны A

Локальный `docker-compose.yml`: `backend`, `frontend`, `nginx:80`.
Демо-край: `docker-compose.g6.yml` (nginx **8080**, не host 80). G6 = `GET /_sse_smoke` через этот nginx. Канон выкладки: `plans/deploy-vps.md`.
