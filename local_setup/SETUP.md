# Setup — read once, then delete or ignore

## Files in this drop

| File | Purpose |
|---|---|
| `CLAUDE.md` | The workflow. Auto-loaded by Claude Code every session. |
| `known-limits.md` | Operational constraints. CLAUDE.md tells Claude to read it each run. |
| `.claude/commands/execute.md` | The `/execute` slash command. |
| `SETUP.md` | This file. |

## Steps

**1. Put these files in your new folder.**

```
winebid/
├── CLAUDE.md
├── known-limits.md
└── .claude/commands/execute.md
```

**2. Create the working directories.**

```bash
cd winebid
mkdir -p inbox/processed output
```

**3. Clone the toolkit as a subfolder.**

```bash
git clone https://github.com/otplabs-io/agentic-auction-template.git toolkit
```

Keep it as `toolkit/` rather than making the project root a clone — that keeps your weekly data separate from vendored code and lets you `git -C toolkit pull` for upstream fixes.

**4. Install dependencies.**

```bash
pip install pandas openpyxl
cd toolkit && npm install jsdom --silent && cd ..
```

**5. Seed the price cache** (optional but free). If you drop `checkpoint-2026-08-30-valuations.csv` in the folder, tell Claude on the first run to seed `price_cache.csv` from it — 56 wines pre-cached, keyed by `make_key`, so they cost zero searches this week and every week after.

**6. Decide about git.** Optional. If you do init a repo, `.gitignore` the weekly scratch but **commit `price_cache.csv`** — it's the asset that accumulates value:

```
inbox/*.xlsx
inbox/processed/
output/
survivors.csv
valuations.csv
payload.json
checkpoint-*
```

## Claude Code configuration

**Permissions.** The workflow needs Bash, Read, Write, Edit, WebSearch and WebFetch. Rather than approving each one repeatedly, either run `/permissions` inside a session to allow them for the project, or launch with `--permission-mode acceptEdits`. The exact `settings.json` schema has changed across versions — check `/permissions` or the docs for your installed version rather than hand-writing it blind.

**Model.** Use `/model` to pick something with strong judgment; the valuation and classification steps are judgment-heavy, not mechanical.

**Search cap.** Optionally raise it before launching:

```bash
CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION=500 claude
```

**Optional subagent.** If you still have `.claude/agents/wine-valuer.md` from the earlier migration work, drop it in — but note it does **not** buy extra search budget (subagents share the session cap). Its value is context isolation on long valuation runs, not more searches.

**Verify the setup** by running `/help` in a session — `/execute` should appear in the list. Note that custom commands and skills have been converging in recent versions; if `.claude/commands/` doesn't register, the same content works as `.claude/skills/execute/SKILL.md`.

## The weekly ritual

1. Download the export from WineBid.
2. Drop it in `inbox/`.
3. Run `claude`, then `/execute`.

For unattended runs: `claude -p "/execute" --permission-mode acceptEdits`.

## First-run note

CLAUDE.md is written for a clean run — it screens and classifies from scratch every week, which is correct and costs no searches. The only thing worth carrying forward is the price cache.
