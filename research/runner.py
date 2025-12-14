from __future__ import annotations

import argparse
from pathlib import Path

from research.config import load_config
from research.utils import get_run_context, save_json, save_text, save_snapshot
from research.fetch_data import fetch_all_inputs
from research.macro import analyze_macro
from research.technicals import analyze_technicals
from research.structure import analyze_market_structure
from research.scenarios import build_scenarios
from research.report import render_markdown_report


OUTPUT_DIR = Path("outputs")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--session",
        required=True,
        choices=[
            "PRE",
            "OPEN_CONFIRM",
            "MID",
            "POWER_HOUR",
            "CLOSE",
            "SAT_REVIEW",
            "SUN_WEEKLY",
        ],
    )
    parser.add_argument("--config", default="config/spx_config.yaml")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(args.config)

    ctx = get_run_context(session=args.session, timezone=config["timezone"], version=config.get("version", "1.0.0"))

    raw_inputs = fetch_all_inputs(
        symbol=config["symbols"]["spx"],
        proxy=config["symbols"]["proxy"],
        asof_utc=ctx["asof_utc"],
        session=args.session,
        config=config,
    )

    (OUTPUT_DIR / "inputs").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "json").mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "reports").mkdir(parents=True, exist_ok=True)

    save_snapshot(raw_inputs, OUTPUT_DIR / "inputs" / f"{ctx['run_id']}.json")

    macro_result = analyze_macro(
        rates=raw_inputs.get("rates", {}),
        fx=raw_inputs.get("fx", {}),
        calendar=raw_inputs.get("macro_calendar", []),
        earnings=raw_inputs.get("earnings", []),
        config=config,
    )

    technical_result = analyze_technicals(price_data=raw_inputs.get("technicals_raw", {}), config=config)

    structure_result = analyze_market_structure(
        options=raw_inputs.get("options", {}),
        vix=raw_inputs.get("vix", {}),
        price=raw_inputs.get("price", {}),
        config=config,
    )

    scenarios = build_scenarios(
        macro=macro_result,
        technicals=technical_result,
        structure=structure_result,
        price=raw_inputs.get("price", {}),
        config=config,
    )

    final_output = {
        "run_id": ctx["run_id"],
        "asof_utc": ctx["asof_utc"],
        "session": ctx["session"],
        "version": ctx["version"],
        "market": {"symbol": config["symbols"]["spx"], "proxy": config["symbols"]["proxy"]},
        "price": raw_inputs.get("price", {}),
        "macro": macro_result,
        "technical": technical_result,
        "structure": structure_result,
        "scenarios": scenarios,
        "inputs_health": raw_inputs.get("health", {}),
    }

    report_md = render_markdown_report(data=final_output, template_path="templates/report.md.jinja")

    save_json(final_output, OUTPUT_DIR / "json" / f"{ctx['run_id']}.json")
    save_text(report_md, OUTPUT_DIR / "reports" / f"{ctx['run_id']}.md")

    print(f"[OK] Generated outputs for {ctx['run_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
