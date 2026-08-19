"""Single Tutu MCP client + guard §7. Import from A and C. Do not copy."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

from lib.models import connect as connect_db

PROTOCOL_VERSION = "2025-06-18"
DEFAULT_ENDPOINT = "https://mcp.tutu.ru/mcp"
CLIENT_NAME = "burger-hackathon"
CLIENT_VERSION = "0.1.0"
CALL_TIMEOUT_S = 30
MAX_CONCURRENCY = 4
PRICE_ABSENT = 0

ALIASES_PATH = Path(__file__).resolve().parent.parent / "data" / "city_aliases.json"

SOURCE_HANDBOOK = "cities_ru.subject"
SOURCE_OSM = "osm.admin_level_4"
SOURCE_MISSING = "missing"


def normalize(text: str) -> str:
    s = text.replace("\u0451", "\u0435").replace("\u0401", "\u0415")
    s = s.casefold()
    s = " ".join(s.split())
    return s


def region_matches(got_region: str, expected_region: str) -> bool:
    if not expected_region or not got_region:
        return False
    g = normalize(got_region)
    e = normalize(expected_region)
    return e in g or g in e


def check_resolve(
    meta: dict[str, Any],
    expected_name: str,
    expected_region: str,
) -> tuple[bool, str]:
    """Guard §7: region = substring after normalize. Name is audit-only.

    Returns (ok, reason). Region mismatch => not ok. also_named is ignored.
    """
    to = _meta_to(meta)
    got_name = str(to.get("name") or "")
    got_region = str(to.get("region") or "")
    if not got_region:
        return False, "missing_region"
    if not region_matches(got_region, expected_region):
        return False, "region_mismatch"
    _ = expected_name, got_name
    return True, "ok"


def resolve_expected_region(
    in_handbook: bool,
    handbook_subject: Optional[str],
    osm_admin4_name: Optional[str],
) -> tuple[Optional[str], str]:
    """G3 freeze. See plans/g3-expected-region.md."""
    if in_handbook:
        subject = (handbook_subject or "").strip()
        if not subject:
            return None, SOURCE_MISSING
        return subject, SOURCE_HANDBOOK
    osm = (osm_admin4_name or "").strip()
    if osm:
        return osm, SOURCE_OSM
    return None, SOURCE_MISSING


def log_osm_subject_mismatch(
    conn: sqlite3.Connection,
    requested: str,
    handbook_subject: str,
    osm_admin4_name: str,
    at: Optional[str] = None,
) -> None:
    if not handbook_subject or not osm_admin4_name:
        return
    if region_matches(osm_admin4_name, handbook_subject):
        return
    _insert_misresolve(
        conn,
        requested=requested,
        got_name="",
        got_region=osm_admin4_name,
        expected_region=handbook_subject,
        expected_region_source="osm_subject_mismatch",
        at=at,
    )


def load_aliases(path: Path = ALIASES_PATH) -> dict[str, list[str]]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, list[str]] = {}
    for key, names in data.items():
        out[key] = list(names)
    return out


def alias_key(name: str, subject: str) -> str:
    return name.strip() + "|" + subject.strip()


def iter_name_attempts(
    name: str,
    subject: str,
    aliases: Optional[dict[str, list[str]]] = None,
) -> list[str]:
    """B1 order: alias -> as-is -> 'name, subject'."""
    table = aliases if aliases is not None else load_aliases()
    ordered: list[str] = []
    seen: set[str] = set()

    def add(item: str) -> None:
        q = item.strip()
        if q and q not in seen:
            seen.add(q)
            ordered.append(q)

    for alias in table.get(alias_key(name, subject), []):
        add(alias)
    add(name)
    if subject:
        add(name.strip() + ", " + subject.strip())
    return ordered


def extract_meta(payload: Any) -> dict[str, Any]:
    doc = unwrap_tool_result(payload)
    if isinstance(doc, dict):
        meta = doc.get("meta")
        if isinstance(meta, dict):
            return meta
        if "to" in doc:
            return doc
    return {}


def unwrap_tool_result(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload
    if "mcp" in payload and isinstance(payload["mcp"], dict):
        payload = payload["mcp"]
    result = payload.get("result")
    if isinstance(result, dict):
        content = result.get("content")
        if isinstance(content, list) and content:
            first = content[0]
            if isinstance(first, dict) and first.get("type") == "text":
                text = first.get("text")
                if isinstance(text, str):
                    try:
                        return json.loads(text)
                    except json.JSONDecodeError:
                        return text
        if "meta" in result:
            return result
        return result
    if "meta" in payload:
        return payload
    return payload


def parse_mcp_body(content_type: str, body: str) -> Any:
    ctype = (content_type or "").lower()
    stripped = body.lstrip()
    if "text/event-stream" in ctype or stripped.startswith("data:"):
        chunks: list[str] = []
        for line in body.splitlines():
            if line.startswith("data:"):
                chunks.append(line[5:].lstrip())
        blob = "\n".join(chunks).strip()
        if not blob:
            return {}
        try:
            return json.loads(blob)
        except json.JSONDecodeError:
            last = chunks[-1] if chunks else blob
            return json.loads(last)
    if not body.strip():
        return {}
    return json.loads(body)


def args_hash(tool: str, args: dict[str, Any]) -> str:
    blob = json.dumps({"tool": tool, "args": args}, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(blob.encode("ascii")).hexdigest()


def price_is_absent(value: Any) -> bool:
    if value is None:
        return True
    try:
        return int(value) == PRICE_ABSENT
    except (TypeError, ValueError):
        return True


def sellable_modes_from_meta(meta: dict[str, Any], offers: Optional[list[Any]] = None) -> str:
    """Modes with count>0. Price 0 RUB = absence (etrain 0 is not a fare)."""
    summary = meta.get("modes_summary") or {}
    present: list[str] = []
    offer_prices: dict[str, list[int]] = {}
    if offers:
        for off in offers:
            if not isinstance(off, dict):
                continue
            mode = str(off.get("mode") or off.get("transport") or "")
            if not mode:
                continue
            offer_prices.setdefault(mode, []).append(_offer_price_int(off))
    for mode, info in summary.items():
        count = 0
        if isinstance(info, dict):
            count = int(info.get("count") or 0)
        if count <= 0:
            continue
        if isinstance(info, dict) and "min_price" in info:
            if price_is_absent(info.get("min_price")):
                continue
        prices = offer_prices.get(mode)
        if prices is not None and prices and all(price_is_absent(p) for p in prices):
            continue
        present.append(str(mode))
    return ",".join(sorted(present))


@dataclass
class ProbeOutcome:
    status: str
    query_used: str
    resolved_name: str = ""
    resolved_region: str = ""
    tutu_geo_id: Optional[str] = None
    sellable_modes: str = ""
    min_price: Optional[int] = None
    payload: Optional[dict[str, Any]] = None
    attempts: Optional[list[str]] = None


class TutuMcp:
    def __init__(
        self,
        db_path: str | Path,
        endpoint: str = DEFAULT_ENDPOINT,
        timeout_s: int = CALL_TIMEOUT_S,
        max_concurrency: int = MAX_CONCURRENCY,
    ) -> None:
        if timeout_s < 30:
            raise ValueError("call_tool timeout must be >= 30s")
        if max_concurrency > 4:
            raise ValueError("semaphore must be <= 4")
        self.endpoint = endpoint
        self.timeout_s = timeout_s
        self._sem = threading.BoundedSemaphore(max_concurrency)
        self._init_lock = threading.Lock()
        self._initialized = False
        self._req_id = 0
        self._id_lock = threading.Lock()
        self.conn = connect_db(db_path)

    def close(self) -> None:
        self.conn.close()

    def _next_id(self) -> int:
        with self._id_lock:
            self._req_id += 1
            return self._req_id

    def initialize(self) -> Any:
        with self._init_lock:
            if self._initialized:
                return None
            payload = {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": CLIENT_NAME, "version": CLIENT_VERSION},
                },
            }
            parsed = self._post(payload)
            notify = {"jsonrpc": "2.0", "method": "notifications/initialized"}
            try:
                self._post(notify)
            except Exception:
                pass
            self._initialized = True
            return parsed

    def call_tool(self, name: str, args: dict[str, Any]) -> Any:
        """POST /mcp tools/call. Cache to mcp_cache BEFORE guard/business processing."""
        digest = args_hash(name, args)
        cached = self._cache_get(name, digest)
        if cached is not None:
            return cached
        self.initialize()
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": name, "arguments": args},
        }
        with self._sem:
            parsed = self._post(payload)
        self._cache_put(name, digest, args, parsed)
        return parsed

    def probe_destination(
        self,
        origin: str,
        name: str,
        subject: str,
        expected_region: str,
        departure_date: str,
        adults: int = 1,
    ) -> ProbeOutcome:
        """B1 retry. misresolved is not collapsed into not_sellable."""
        attempts = iter_name_attempts(name, subject)
        saw_misresolve = False
        last_query = attempts[-1] if attempts else name
        last_to: dict[str, Any] = {}
        last_payload: Any = None
        for query in attempts:
            last_query = query
            raw = self.call_tool(
                "search_multitransport",
                {
                    "origin": origin,
                    "destination": query,
                    "departure_date": departure_date,
                    "adults": adults,
                    "page_size": 1,
                },
            )
            last_payload = unwrap_tool_result(raw)
            meta = extract_meta(raw)
            to = _meta_to(meta)
            last_to = to
            ok, _reason = check_resolve(meta, name, expected_region)
            if not ok:
                saw_misresolve = True
                _insert_misresolve(
                    self.conn,
                    requested=query,
                    got_name=str(to.get("name") or ""),
                    got_region=str(to.get("region") or ""),
                    expected_region=expected_region,
                    expected_region_source=None,
                    at=_now(),
                )
                continue
            doc = last_payload if isinstance(last_payload, dict) else {}
            offers = doc.get("offers") if isinstance(doc, dict) else None
            modes = sellable_modes_from_meta(meta, offers if isinstance(offers, list) else None)
            min_price = _min_positive_price(offers if isinstance(offers, list) else None)
            status = "sellable" if modes else "not_sellable"
            return ProbeOutcome(
                status=status,
                query_used=query,
                resolved_name=str(to.get("name") or ""),
                resolved_region=str(to.get("region") or ""),
                tutu_geo_id=to.get("geo_id"),
                sellable_modes=modes,
                min_price=min_price,
                payload=doc if isinstance(doc, dict) else None,
                attempts=attempts,
            )
        status = "misresolved" if saw_misresolve else "not_sellable"
        return ProbeOutcome(
            status=status,
            query_used=last_query,
            resolved_name=str(last_to.get("name") or ""),
            resolved_region=str(last_to.get("region") or ""),
            tutu_geo_id=last_to.get("geo_id"),
            sellable_modes="",
            min_price=None,
            payload=last_payload if isinstance(last_payload, dict) else None,
            attempts=attempts,
        )

    def _post(self, payload: dict[str, Any]) -> Any:
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                raw = resp.read().decode("utf-8")
                ctype = resp.headers.get("Content-Type") or ""
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8") if exc.fp else ""
            ctype = exc.headers.get("Content-Type") if exc.headers else ""
            if exc.code >= 400 and not raw:
                raise
        except urllib.error.URLError:
            raise
        return parse_mcp_body(ctype, raw)

    def _cache_get(self, tool: str, digest: str) -> Optional[Any]:
        row = self.conn.execute(
            "SELECT payload_json FROM mcp_cache WHERE tool = ? AND args_hash = ?",
            (tool, digest),
        ).fetchone()
        if row is None:
            return None
        return json.loads(row["payload_json"])

    def _cache_put(self, tool: str, digest: str, args: dict[str, Any], parsed: Any) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO mcp_cache(tool, args_hash, args_json, payload_json, fetched_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                tool,
                digest,
                json.dumps(args, ensure_ascii=True),
                json.dumps(parsed, ensure_ascii=True),
                _now(),
            ),
        )
        self.conn.commit()


def _meta_to(meta: dict[str, Any]) -> dict[str, Any]:
    to = meta.get("to")
    if isinstance(to, dict):
        return to
    return {}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _insert_misresolve(
    conn: sqlite3.Connection,
    requested: str,
    got_name: str,
    got_region: str,
    expected_region: Optional[str],
    expected_region_source: Optional[str],
    at: Optional[str],
) -> None:
    conn.execute(
        """
        INSERT INTO misresolve_log(
          requested, got_name, got_region, expected_region, expected_region_source, at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (requested, got_name, got_region, expected_region, expected_region_source, at or _now()),
    )
    conn.commit()


def _offer_price_int(off: dict[str, Any]) -> int:
    p = off.get("price")
    if isinstance(p, dict):
        p = p.get("amount")
    try:
        return int(float(p))
    except (TypeError, ValueError):
        return 0


def _min_positive_price(offers: Optional[list[Any]]) -> Optional[int]:
    if not offers:
        return None
    prices: list[int] = []
    for off in offers:
        if not isinstance(off, dict):
            continue
        p = _offer_price_int(off)
        if not price_is_absent(p):
            prices.append(p)
    return min(prices) if prices else None
