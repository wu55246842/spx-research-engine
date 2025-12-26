from mcp.server.fastmcp import FastMCP, Context
import yaml
from pathlib import Path
from typing import Optional

# Import Research Engine Components
from research.config import load_config
from research.utils import get_run_context
from research.fetch_data import fetch_all_inputs
from research.macro import analyze_macro
from research.technicals import analyze_technicals
from research.structure import analyze_market_structure
from research.scenarios import build_scenarios
from research.report import render_markdown_report

ROOT_DIR = Path(__file__).parent.parent


def create_server() -> FastMCP:
    """Create a FastMCP server without side effects at import time."""
    mcp = FastMCP("SPX Research Engine")

    @mcp.tool()
    def analyze_ticker(symbol: str = "SPX", session: str = "PRE") -> str:
        """Run a full research analysis on a ticker symbol (e.g., NVDA, SPX, BTC-USD).

        Args:
            symbol: The ticker symbol to analyze (default: SPX).
            session: The trading session context (PRE, MID, CLOSE).

        Returns:
            A markdown formatted research report.
        """
        config_path = ROOT_DIR / "config/spx_config.yaml"
        if not config_path.exists():
            return f"Error: Config not found at {config_path}"

        config = load_config(str(config_path))

        # 1. Context & Inputs
        ctx = get_run_context(session=session, timezone=config["timezone"], version=config.get("version", "1.0.0"))

        try:
            raw_inputs = fetch_all_inputs(
                symbol=symbol,
                proxy=config["symbols"]["proxy"],
                asof_utc=ctx["asof_utc"],
                session=session,
                config=config,
            )
        except Exception as e:
            return f"Error fetching data for {symbol}: {str(e)}"

        # 2. Analysis
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

        # 3. Report Generation
        final_output = {
            "run_id": ctx["run_id"],
            "asof_utc": ctx["asof_utc"],
            "session": ctx["session"],
            "version": ctx["version"],
            "market": {"symbol": symbol, "proxy": config["symbols"]["proxy"]},
            "price": {k: v for k, v in raw_inputs.get("price", {}).items() if k != "history"},
            "macro": macro_result,
            "technical": technical_result,
            "structure": structure_result,
            "scenarios": scenarios,
            "inputs_health": raw_inputs.get("health", {}),
        }

        report_md = render_markdown_report(data=final_output, template_path=str(ROOT_DIR / "templates/report.md.jinja"))

        # Save a copy locally as well (optional, but good for history)
        output_path = ROOT_DIR / "outputs/reports" / f"{ctx['run_id']}.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report_md, encoding="utf-8")

        return report_md

    @mcp.resource("spx://reports/latest")
    def get_latest_report() -> str:
        """Retrieve the content of the most recently generated research report."""
        report_dir = ROOT_DIR / "outputs/reports"
        if not report_dir.exists():
            return "No reports found."

        reports = list(report_dir.glob("*.md"))
        if not reports:
            return "No reports found."

        latest_report = max(reports, key=lambda p: p.stat().st_mtime)
        return latest_report.read_text(encoding="utf-8")

    return mcp


def main() -> None:
    server = create_server()
    server.run()


if __name__ == "__main__":
    main()
