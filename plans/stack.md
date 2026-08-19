# Stack freeze (G8)

Five decisions, one block. Do not reopen.

1. **Backend process:** ONE FastAPI app (routers B + C in the same process), port **8000**.
2. **Frontend:** React 18 + Vite + TypeScript + MapLibre (**not** Leaflet), **npm**, Node **20**. Worker D owns the app; this repo only has a static placeholder so compose has a frontend service.
3. **Backend language:** Python **3.12**, FastAPI, SQLite.
4. **docker-compose services:** `backend`, `frontend`, `nginx`.
   - **Mac / laptop:** `docker-compose.yml` publishes nginx **:80** (G6 rehearsal through nginx, not `:8000`).
   - **Demo host:** do **not** bind `:80`/`:443` if those ports must stay free. Use `docker-compose.g6.yml` — nginx **:8080**. Runbook: `plans/deploy-vps.md`. G6 = `GET /_sse_smoke` through that nginx.
5. **Git:** `main` plus `stream-a-*` / `stream-b-*` / `stream-c-*` / `stream-d-*`. The Architect merges seam PRs (`schema.sql`, `lib/`, `plans/api-contract.md`, `fixtures/`). Streams do not redefine models or `tutu_mcp.py`.
6. **`.db` path:** `data/burger.db` on the ingest host. Transfer by **rsync/scp** or a shared Docker volume. Git tracks golden `fixtures/` only, never the live DB.

Prod-like SSE: `nginx/nginx.conf` (`proxy_buffering off`, `proxy_cache off`, `X-Accel-Buffering: no`). Smoke route: `GET /_sse_smoke` on the backend, proxied by nginx.
