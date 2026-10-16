"""
Real county surplus sources.

collect_all() runs every state's fetch() and caches each state's last successful
result in data/live/<state>.json. If a state's fetch fails or returns nothing
(site down, runner IP blocked), the last good cache is used so one county
outage never empties the feed. Records are never invented.
"""

import importlib
import json
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CACHE_DIR = BASE_DIR / "data" / "live"
STATES = ["fl", "tx", "ga", "nc", "tn", "ca"]

# Records whose last successful fetch is older than this are dropped rather than
# re-sent as if current.
MAX_CACHE_AGE_DAYS = 14


def _load_cache(state):
    path = CACHE_DIR / f"{state}.json"
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        fetched = datetime.fromisoformat(payload.get("fetched_at", "1970-01-01"))
        if (datetime.now() - fetched).days > MAX_CACHE_AGE_DAYS:
            print(f"  ⚠️ {state.upper()}: cache is older than {MAX_CACHE_AGE_DAYS} days; dropping.")
            return []
        return payload.get("records", [])
    except Exception as e:
        print(f"  ⚠️ {state.upper()}: unreadable cache ({e})")
        return []


def _save_cache(state, records):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (CACHE_DIR / f"{state}.json").write_text(
        json.dumps({"fetched_at": datetime.now().isoformat(), "records": records}, indent=2),
        encoding="utf-8",
    )


def collect_all(states=None):
    all_records = []
    for st in states or STATES:
        records = []
        try:
            mod = importlib.import_module(f"scrapers.sources.{st}")
            records = mod.fetch() or []
        except Exception as e:
            print(f"  ⚠️ {st.upper()}: fetch failed ({e})")

        if records:
            _save_cache(st, records)
            print(f"  ✓ {st.upper()}: {len(records)} live records")
        else:
            records = _load_cache(st)
            print(f"  ↺ {st.upper()}: using cached records ({len(records)})")
        all_records.extend(records)
    return all_records
