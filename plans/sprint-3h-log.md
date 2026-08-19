# 3h local MVP sprint log

Start: 2026-08-19 ~18:26 UTC+4. Hard stop: ~21:26 UTC+4.
Do not push. No VPS deploy. Outcome: working local Docker Compose on `main`.

## Checkpoint (before first code edit)

- Branch: `main` (ahead of origin/main by 2, then +1 empty commit)
- Checkpoint commit: `f45ffdc1d0b205e433aa915b79d7cee13e8e95ef`
- Message: Checkpoint before 3h local MVP sprint.
- Parent assemble: `cdad753`
- SQLite backup: `data/backups/burger.db.checkpoint-3h` (4.0M, mtime 2026-08-19 17:46)
- Working tree at checkpoint: clean except gitignored live DB

## Worktrees / branches

| Stream | Branch | Worktree |
|---|---|---|
| Data D4/D5 | `codex/data` | sibling worktree |
| Live price | `codex/price-live` | sibling worktree |
| Frontend wow | `codex/frontend-wow` | sibling worktree |
| Integrator G10 | `main` | `/Users/ramilmustafin/Projects/tuturu_hackaton` |

One writer for `burger.db`: data stream only, on its worktree copy.

## G10 proof (local Docker through nginx :80)

Date: 2026-08-19 ~18:32 UTC+4. Compose: `docker compose up --build -d`.

- Python 3.12.13 venv at `.venv`; Node 20.20.2; `npm ci` + `npm run build` OK
- unittest guard+places+price: 29 OK
- `/healthz` 200
- `/_sse_smoke` frames at 0.06s / 1.06s / 2.06s (not buffered)
- `/api/places` etalon pair present, matched both, missing=[], ~16 ms
- `/api/places` backup single Yaroslavl ancient_temple+ruins present
- `/api/price` through nginx: resolved, then legs, breakdown, done; `fixture-confirmed`; pair cluster_id
- unknown cluster 404
- UI `/` 200
- Seeded DB: `data/burger.g10.db` (golden fixtures). Live ingest DB remains `data/burger.db`.

## Audit snapshot (do not treat TODO checkboxes as proof)

- G10 now proven through nginx compose (see above)
- D1/D2/D3 ran; D4/D5 still owned by `codex/data`
- Live OSM: Yaroslavl oblast only; 0 industrial_museum on Yaroslavl/Rostov
- Demo compose uses golden fixtures; live ingest DB is separate
- Places now persist live discs into `cluster` for `/api/price`
- Grey-card heuristic still in frontend until `codex/frontend-wow` merge
- Host Python 3.12.13 venv created; Docker backend is 3.12-slim
- Compose bind-mounts `./data` and seeds `burger.g10.db`
