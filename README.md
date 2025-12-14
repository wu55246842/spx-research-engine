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


1. Where is my website?
Your website will be located here: 👉 https://wu55246842.github.io/spx-research-engine/

(Note: If you visit it right now, it might give a 404 error because no reports have been generated yet.)

2. Why isn't it running yet?
The automation is set to run on a schedule (the specific market times we defined). The next scheduled run might be effectively "tomorrow" or "later today" depending on the clock.

You don't have to wait! You can force it to run right now to see the result.

3. How to run it manually (Action Required)
Go to the Actions tab in your GitHub repository.
On the left sidebar, click on SPX Research Scheduled.
On the right side, you will see a generic listing of runs (it might be empty).
Click the grey Run workflow button.
In the dropdown, type PRE (or leave it empty, it usually defaults to PRE) and click the green Run workflow button.
What happens next:

SPX Research Scheduled will start running (takes ~30-60 seconds).
When that finishes, Publish SPX Reports to GitHub Pages will automatically start.
When that finishes (green checkmark), refresh your website URL, and you will see your first report!