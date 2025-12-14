# SPX Research Engine (Automated)

This repository is a packaged starter-kit for an automated SPX daily/weekly research pipeline designed for GitHub Actions.

## What you get
- Config validation with friendly errors (`research/config.py` + `research/tools/validate_config.py`)
- Scenario engine (Bear/Neutral/Bull) with configurable weights (`research/scenarios.py`)
- End-to-end runner (`research/runner.py`) producing:
  - `outputs/json/<run_id>.json`
  - `outputs/reports/<run_id>.md`

## Quick start (local)
```bash
pip install -r requirements.txt
python -m research.tools.validate_config --config config/spx_config.yaml
python -m research.runner --session PRE --config config/spx_config.yaml
```

## GitHub Actions
- `.github/workflows/config-lint.yml`: validates config on PR/push.
- Add your own scheduled workflow to run `research.runner` on a cron.

## Next steps
Replace the stub data fetchers in `research/fetch_data.py` with your real data providers.
