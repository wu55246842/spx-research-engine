# SPX Research Engine - Workflows & Deployment Guide

This guide explains the automated research pipeline you have configured and how to deploy it to GitHub.

## Status: Deployed 🚀
**Repository**: [wu55246842/spx-research-engine](https://github.com/wu55246842/spx-research-engine)
**Local Status**: Synced with correct remote.

---

## 1. Workflow Logic Explanation

You have set up a **GitOps-style automated research pipeline** consisting of two linked workflows.

### A. Scheduled Research (`spx-research-scheduled.yml`)
**Purpose**: Runs the SPX research engine automatically at key market times to generate reports.

1.  **Triggers**:
    *   **Cron Schedule**: Aligned with US Market sessions (converted to your Singapore Timezone in comments).
        *   `PRE` (Pre-market)
        *   `OPEN_CONFIRM` (Market Open)
        *   `MID` (Mid-day)
        *   `POWER_HOUR` (Last hour)
        *   `CLOSE` (Market Close)
        *   Weekend Reviews (`SAT_REVIEW`, `SUN_WEEKLY`)
    *   **Manual Dispatch**: You can manually trigger a run for any session via the GitHub Actions UI.

2.  **Job Steps**:
    *   **Session Determination**: A shell script maps the current cron time to a named session.
    *   **Execution**: Runs `python -m research.runner`.
    *   **Artifacts**: Suffixes the session name to the artifact (e.g., `spx-research-CLOSE-<id>`) and uploads the `outputs/` directory.

### B. Publish to Pages (`publish-pages.yml`)
**Purpose**: Takes the output from the research run and publishes it as a static website.

1.  **Triggers**:
    *   **`workflow_run`**: Automatically starts when the *Scheduled Research* workflow completes successfully.
    *   **Manual Dispatch**: Allows manual re-deployments.

2.  **Job Steps**:
    *   **Download Artifacts**: Retrives the `outputs/` folder from the *upstream* research run.
    *   **Build Site**: A Python script converts Markdown reports to HTML and creates an `index.html`.
    *   **Deploy**: Uploads the `site/` directory to GitHub Pages.

---

## 2. **Final Config Required** in GitHub

I have handled all the code deployment for you. There is **ONE** final step you must do in the GitHub website:

### Step 1: Enable GitHub Pages
1.  Go to your GitHub Repo -> **Settings** -> **Pages**.
2.  Under **Build and deployment** -> **Source**, change "Deploy from a branch" to **GitHub Actions**.

### Step 2: Verify
1.  Go to the **Actions** tab.
2.  Select **SPX Research Scheduled**.
3.  Click **Run workflow** (Blue button) -> "Run workflow".
4.  Once it finishes, **Publish SPX Reports** will run automatically.
5.  Your site will be live at: `https://wu55246842.github.io/spx-research-engine/`

---

## 6. Access via MCP (Claude Desktop)

You can connect **Claude Desktop** to this research engine to run analysis directly from the chat.

1.  Open your Claude Desktop config file:
    *   **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
    *   **Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`

2.  Add the research engine server:

    ```json
    {
      "mcpServers": {
        "spx-research": {
          "command": "path/to/.venv/Scripts/python",
          "args": [
            "-m",
            "research.mcp_server"
          ],
          "cwd": "path/to/spx-research-engine",
          "env": {
             "SPX_PREV_CLOSE": "6848.7",
             "SPX_LAST": "6830.0"
          }
        }
      }
    }
    ```
    *(Note: Replace `path/to` with the absolute path to your cloned repository)*

3.  Restart Claude Desktop. You will now see:
    *   **Tool**: `analyze_ticker` (Ask: "Analyze NVDA")
    *   **Resource**: `Latest Report` (Ask: "Show me the latest SPX report")

