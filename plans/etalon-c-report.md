# STREAM_REPORT (Worker C / etalon v2 price)

Branch: `codex/etalon-c-price` (worktree `.worktrees/etalon-c`). Not merged. Not pushed.

Search only. Never booked. Overall `price_status` stays `fixture-confirmed`.
Did not set `BURGER_SC_PRICE_ACCEPTED`. One live hop does not flip overall status.

## Fixture path (live off)

Happy-path SSE (resolved, leg, breakdown, done, hotels `stay_total`, recovered
return, cache day) uses backup `c:Yaroslavl|Yaroslavl oblast` and/or the
Yaroslavl-Rostov pair from `etalon_1.almost_fits_pair_id`. Not Uglich.

Etalon v2 Uglich (`fixtures/etalon_1.json`): HTTP 200 SSE, `resolved` guard ok,
warning `not_sellable` (hub `probe_status`, on-foot) plus hop `no_route` from
the golden `leg` row (Moscow->Uglich, `date_probed` 2026-09-09). No 0 RUB
fares. No empty breakdown. `done` still emitted.

Unknown cluster: HTTP 404 before SSE.

## Live Tutu (`BURGER_LIVE_TUTU=1`, search_multitransport)

Date window: first October 2026 day `2026-10-09`, return `2026-10-11`, 1 adult.
Origin query: Moscow hub. Guard: ok on origin and both dest hubs.

### 1) Etalon v2 Uglich

- Cluster: Uglich single-hub (etalon v2)
- Latency: **1672 ms** for the SSE iterator (two directed hops)
- Warning: `not_sellable` from fixture hub probe (on-foot). No fake 0 RUB.
- Live hops (partial; fixture D2 was `no_route` on 2026-09-09):
  - 2026-10-09 Moscow -> Uglich **1341 RUB** railway `source=live`
  - 2026-10-11 Uglich -> Moscow **1341 RUB** railway `source=live`
- Breakdown transport 2682 RUB, `price_status=fixture-confirmed`
- Checkout host only: `www.tutu.ru` (full decaying URLs omitted)
- `done.ok=true`, `price_status=fixture-confirmed` (not live)

### 2) Backup Yaroslavl burger

- Cluster: backup single-hub Yaroslavl (`ancient_temple`+`ruins`)
- Latency: **2648 ms**
- Live hops:
  - 2026-10-09 Moscow -> Yaroslavl **1035 RUB** bus `source=live`
  - 2026-10-11 Yaroslavl -> Moscow **987 RUB** railway `source=live`
- Breakdown transport 2022 RUB, `price_status=fixture-confirmed`
- Checkout hosts only: `mtp-deeplink.tutu.ru`, `www.tutu.ru`
- `done.ok=true`, `price_status=fixture-confirmed` (not live)

## Tests

From this worktree (venv Python; `PYTHONPATH` = worktree root):

```
python -m unittest tests.test_price tests.test_guard -v
```

Default: **30 passed, 1 skipped** (`test_live_tutu_network_optional` unless
`BURGER_LIVE_NET=1`).

With `BURGER_LIVE_NET=1`: live optional test **ok**; still no
`BURGER_SC_PRICE_ACCEPTED`; still no `price_status=live`.

## Remaining

- SC-price for both scenarios is not accepted. Live Uglich tickets in October
  do not override fixture `probe_status=not_sellable` or overall status.
- Fixture Moscow->Uglich `no_route` remains the offline honest hop; live is
  opt-in via `BURGER_LIVE_TUTU`.
- Checkout links expire; pass through host+path as returned, do not rebuild.
