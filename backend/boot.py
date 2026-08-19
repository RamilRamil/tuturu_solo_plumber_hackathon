"""Container boot: seed golden fixtures if the target DB is empty, then serve."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def seed_if_needed() -> None:
    flag = (os.environ.get("BURGER_SEED_FIXTURES") or "1").strip().lower()
    if flag not in ("1", "true", "yes", "on"):
        return
    path = Path(os.environ.get("BURGER_DB") or "data/burger.g10.db")
    if path.exists() and path.stat().st_size > 10_000:
        print("boot: using existing db bytes=%s path=%s" % (path.stat().st_size, path), flush=True)
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
