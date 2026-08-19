# Deploy / update (Docker) — Burger

Set these locally (do not commit values):

```bash
export BURGER_HOST="<host-or-ip>"
export BURGER_SSH_USER="<ssh-user>"
export BURGER_SSH_KEY="$HOME/.ssh/<key>"
export BURGER_APP_DIR="<app-dir-on-host>"
```

**Agent vs terminal:** the agent must not run deploy/SSH/`rsync`/`docker`/`ufw`.
It prints the exact commands; the human runs them (SSH key passphrase lives
in the human terminal). Before each command, explain why. SSH and `rsync -e`
must use `$BURGER_SSH_KEY` + `$BURGER_HOST`, not a personal SSH `Host` alias.

---

## Access

```bash
ssh -i "$BURGER_SSH_KEY" -o IdentitiesOnly=yes \
  "$BURGER_SSH_USER@$BURGER_HOST"
```

| Where | Value |
|-------|--------|
| SSH | `ssh -i "$BURGER_SSH_KEY" -o IdentitiesOnly=yes "$BURGER_SSH_USER@$BURGER_HOST"` |
| App dir | `$BURGER_APP_DIR` |
| Demo edge | nginx from `docker-compose.g6.yml` on host **8080** |

That compose file binds **8080**, not 80/443. Do not publish burger on host
`:80` if that port is already in use. Do not hang the demo off an unrelated
site or a gzip/redirect reverse proxy — that breaks SSE.

---

## Layout on the host

Slim sync from the laptop. Sources (`specs/`, `plans/`, etc.) can stay local.

| Path under `$BURGER_APP_DIR` | Role |
|------------------------------|------|
| `docker-compose.g6.yml` | stack: `backend` + `nginx` on **8080** |
| `backend/`, `lib/`, `schema.sql`, `data/`, `fixtures/` | image build context |
| `nginx/g6.conf` | smoke nginx (no `frontend` upstream) |
| `nginx/nginx.conf` | full local/prod-like nginx (has `frontend`) — not mounted by g6 compose |

Local laptop compose `docker-compose.yml` still publishes **`:80`** for
dev. Do not use that file on a host where 80 must stay free.

---

## G6 (SSE through nginx)

Smoke: `GET /_sse_smoke` via nginx, not direct `:8000`. Expect events one
by one (~1 s apart), not a single burst.

```bash
curl -N -s "http://$BURGER_HOST:8080/_sse_smoke"
```

Open host **8080/tcp** for the demo. Do not bind burger to host 80.

---

## First-time bring-up

1. Create `$BURGER_APP_DIR` owned by `$BURGER_SSH_USER`
2. Slim `rsync` (see update)
3. Allow **8080/tcp** on the host firewall
4. `cd "$BURGER_APP_DIR" && docker compose -f docker-compose.g6.yml up -d --build`
5. From the laptop: `curl -N` to `:8080/_sse_smoke`

---

## Update the stack

From the clone of this repository:

```bash
rsync -avz -e "ssh -i $BURGER_SSH_KEY -o IdentitiesOnly=yes" \
  docker-compose.g6.yml schema.sql \
  "$BURGER_SSH_USER@$BURGER_HOST:$BURGER_APP_DIR/"

rsync -avz -e "ssh -i $BURGER_SSH_KEY -o IdentitiesOnly=yes" \
  backend lib data fixtures nginx \
  "$BURGER_SSH_USER@$BURGER_HOST:$BURGER_APP_DIR/"
```

No `--delete` unless you intend to wipe extras.

On the host:

```bash
cd "$BURGER_APP_DIR" && docker compose -f docker-compose.g6.yml up -d --build
docker compose -f docker-compose.g6.yml ps
```

Expect host `8080->80` on nginx, **not** host `:80`.

```bash
curl -N -s "http://$BURGER_HOST:8080/_sse_smoke"
```

---

## Logs and control (after SSH)

```bash
cd "$BURGER_APP_DIR"
docker compose -f docker-compose.g6.yml ps
docker compose -f docker-compose.g6.yml logs -f nginx
docker compose -f docker-compose.g6.yml logs -f backend
```

Stop:

```bash
cd "$BURGER_APP_DIR" && docker compose -f docker-compose.g6.yml down
```

Forbidden on this host: `ports: "80:80"` for burger if 80 must stay free.

---

## Later: HTTPS

Port 8080 is HTTP on purpose. When TLS is needed: a **separate** reverse
proxy site for burger only, to the g6 nginx/backend, with response buffering
off (`flush_interval -1` or equivalent). Until then the prod-like edge is
`:8080` nginx.

---

## If something changes

| Change | What to update |
|--------|----------------|
| New host | local `BURGER_HOST` / `BURGER_APP_DIR`; SSH/`rsync`/`curl` |
| Rebuild | Docker; firewall 8080; `$BURGER_APP_DIR`; rsync + `up` |
| Host key warning | laptop: `ssh-keygen -R "$BURGER_HOST"` |
