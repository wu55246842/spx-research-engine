from __future__ import annotations

import argparse
import sys
from pathlib import Path

from research.config import load_config, ConfigError


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/spx_config.yaml")
    args = ap.parse_args()

    cfg_path = Path(args.config)
    if not cfg_path.exists():
        print(f"[CONFIG-LINT] Missing config file: {cfg_path}", file=sys.stderr)
        return 2

    try:
        cfg = load_config(cfg_path)
    except ConfigError as e:
        print("[CONFIG-LINT] FAILED", file=sys.stderr)
        print(str(e), file=sys.stderr)
        return 1

    se = cfg.get("scenario_engine", {})
    print("[CONFIG-LINT] OK")
    print(f"  timezone: {cfg.get('timezone')}")
    print(f"  version: {cfg.get('version')}")
    print(f"  hold_minutes: {se.get('hold_minutes')}")
    print(f"  event_week_tilt: {se.get('event_week_tilt')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
