"""Container boot: optional golden seed, never overwrite a live ingest DB."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _truthy(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in ("1", "true", "yes", "on")


def seed_if_needed() -> None:
    path = Path(os.environ.get("BURGER_DB") or "data/burger.db")
    seed = _truthy("BURGER_SEED_FIXTURES")
    size = path.stat().st_size if path.is_file() else 0
    print(
        "boot: db=%s bytes=%s seed_fixtures=%s live_tutu=%s sc_price_accepted=%s"
        % (
            path,
            size,
            int(seed),
            int(_truthy("BURGER_LIVE_TUTU")),
            int(_truthy("BURGER_SC_PRICE_ACCEPTED")),
        ),
        flush=True,
    )
    if not seed:
        return
    if path.name == "burger.db" and size > 10_000:
        print("boot: refuse to seed live ingest db path=%s" % path, flush=True)
        return
    if size > 10_000:
        print("boot: using existing db", flush=True)
        return
    from lib.load_fixtures import load_golden_fixtures
    from lib.models import connect

    conn = connect(path)
    try:
        load_golden_fixtures(conn)
    finally:
        conn.close()
    print("boot: seeded golden fixtures path=%s bytes=%s" % (path, path.stat().st_size), flush=True)


def main() -> None:
    seed_if_needed()
    os.execvp(
        "uvicorn",
        ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"],
    )


if __name__ == "__main__":
    sys.exit(main())
