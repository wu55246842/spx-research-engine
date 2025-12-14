from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone as dt_timezone
from pathlib import Path
from typing import Any, Dict

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore


def get_run_context(session: str, timezone: str, version: str) -> Dict[str, Any]:
    """Create a stable run context with UTC timestamp and a deterministic run_id.

    GitHub Actions uses UTC for schedule; we record UTC as-of time for reproducibility.
    """
    now_utc = datetime.now(dt_timezone.utc)
    asof_utc = now_utc.isoformat().replace("+00:00", "Z")

    # Use local date for naming (SGT default), because reports are usually consumed in local time.
    local_date = now_utc
    if ZoneInfo is not None:
        try:
            local_date = now_utc.astimezone(ZoneInfo(timezone))
        except Exception:
            local_date = now_utc

    date_str = local_date.strftime("%Y-%m-%d")
    run_id = f"{date_str}_{session}_v{version}"

    return {
        "run_id": run_id,
        "date": date_str,
        "session": session,
        "asof_utc": asof_utc,
        "version": version,
    }


def save_json(obj: Any, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def save_text(text: str, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def save_snapshot(obj: Any, path: str | Path) -> None:
    """Alias of save_json, kept separate so you can later switch to parquet, etc."""
    save_json(obj, path)
