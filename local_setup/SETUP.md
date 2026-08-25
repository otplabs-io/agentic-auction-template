# Setup — Claude Code in the desktop app

Read once, then ignore. Written for the **Code tab in Claude Desktop**, not the CLI.

## Files in this drop

| File | Purpose |
|---|---|
| `CLAUDE.md` | The workflow. Auto-loaded every session. |
| `known-limits.md` | Operational constraints. `CLAUDE.md` tells Claude to read it each run. |
| `.claude/commands/execute.md` | The `/execute` slash command. |
| `.claude/settings.json` | Permissions and the search-cap env var. |
| `SETUP.md` | This file. |

Desktop runs the same engine as the CLI and reads the same configuration — `CLAUDE.md`, slash commands, skills, settings, hooks, MCP servers. Nothing here is desktop-specific except how you launch it.

## Steps

**1. Create the folder and put these files in it.**

```
winebid/
├── CLAUDE.md
├── known-limits.md
├── SETUP.md
└── .claude/
    ├── settings.json
    └── commands/execute.md
```

On macOS, `.claude` is hidden in Finder — press `Cmd+Shift+.` to show dotfiles, or create it from the desktop app's file editor once you're in the project.

**2. Point the Code tab at it.**

Open Claude Desktop → **Code** tab → environment **Local** → **Select folder** → pick `winebid/`.

Windows only: Git must be installed for local sessions to work. Most Macs already have it.

**3. Let Claude do the rest of the setup.** You don't need a terminal for this — start a session and paste:

> Set up this project: create `inbox/processed/` and `output/`, clone
> https://github.com/otplabs-io/agentic-auction-template.git into `toolkit/`,
> then install pandas and openpyxl for Python and jsdom inside `toolkit/`.
> Confirm `python3 -c "import pandas, openpyxl"` and `node -e "require('jsdom')"`
> both succeed, and tell me if anything is missing from my machine.

Python 3 and Node need to already exist on your machine — the desktop app bundles Claude Code, not those. If either is missing, Claude will tell you at this step and you can install them before continuing.

The app has an integrated terminal if you'd rather run the commands yourself, but there's no need.

**4. Seed the price cache** (optional, free). Drop `checkpoint-2026-08-30-valuations.csv` in the folder and tell Claude on the first run to seed `price_cache.csv` from it — 56 wines pre-cached, keyed by wine identity, so they cost zero searches this week and every week after.

**5. Decide about git.** Optional. If you init a repo, gitignore the weekly scratch but **commit `price_cache.csv`** — it's the asset that accumulates value:

```
inbox/*.xlsx
inbox/processed/
output/
survivors.csv
valuations.csv
payload.json
checkpoint-*
```

## Configuration

### Permissions

The Code tab defaults to **Ask** mode: Claude proposes each change and waits for approval in a diff view. That's sensible for a one-off, but this workflow makes hundreds of tool calls in a run and you'd spend the whole time clicking.

`.claude/settings.json` in this drop pre-allows what the pipeline needs — Python, Node, git, the file tools, WebSearch and WebFetch — while leaving everything else on ask. Adjust it with `/permissions` inside a session rather than hand-editing, or use the **always allow** button on any prompt to grow the list from real usage.

You can also switch the session's permission mode in the app if you want to loosen it for a long run. Avoid bypass mode — the pipeline writes files and runs git on your own disk, so keep the guardrails.

### The search cap

There's no launch flag in the desktop app, so the cap goes in `settings.json` under `env`, which injects it into every session in this project:

```json
"env": { "CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION": "500" }
```

Worth verifying it took effect on the first big run — if searches still stop at 200, the setting isn't being read and you'll need the checkpoint-and-chain procedure in `known-limits.md` instead. That procedure works either way; a raised cap just makes it unnecessary.

### Model

Pick from the dropdown next to the send button. Classification and valuation are judgment-heavy, not mechanical — this is not the place to economize.

### Verify

Type `/` in a session. `/execute` should appear. If it doesn't, the same content works as `.claude/skills/execute/SKILL.md` — custom commands and skills have been converging across recent versions, and `/help` will show what yours supports.

## The weekly ritual

1. Download the export from WineBid.
2. Drop it in `inbox/`.
3. Open the Code tab on this project and run `/execute`.

Because the run is long, two desktop features are worth knowing:

- **Send it to the cloud** if you'd rather not keep the app open — cloud sessions continue after you close it. The tradeoff is that a cloud session works on a copy, so confirm where the dashboard and the updated `price_cache.csv` land before relying on it.
- **Side chat** lets you ask a question mid-run without derailing the main thread. Useful for sanity-checking a borderline classification while valuation keeps going.

### Making it recurring

The xlsx download is manual, so full automation isn't possible — but the desktop app supports scheduled tasks, and a weekly nudge that checks the folder is genuinely useful:

> Create a recurring task for this project, Monday mornings: check `inbox/`
> for a new `WineBid-Download-*.xlsx`. If one is there, run `/execute`. If not,
> just tell me it's waiting on the download.

That way the run starts itself on the weeks you remember to drop the file, and reminds you on the weeks you don't.

## First-run note

`CLAUDE.md` is written for a clean run — it screens and classifies from scratch every week, which is correct and costs no searches. The only thing worth carrying forward between weeks is `price_cache.csv`.
