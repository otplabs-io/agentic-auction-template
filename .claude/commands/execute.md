---
description: Run the weekly WineBid deal-finder pipeline end to end
---

Run the weekly WineBid analysis. Follow CLAUDE.md exactly and read known-limits.md first.

1. Find the newest `WineBid-Download-*.xlsx` in `inbox/`. If there isn't one, stop and ask for it. Verify the sheet is `List View` with the header on row 3 (`header=2`); if the shape is wrong, say so rather than guessing.

2. **Screen** (Step 1). Include the Port-shipper producer-identity check, and print the surviving Portugal / Spain / Italy lots for a fortified-wine eyeball before finalizing. Report the full funnel.

3. **Classify** (Step 2) every survivor's `wine_type`. No web searches. Report the type census and name every hedged call. Write `survivors.csv`.

4. **Value** (Step 3). Load `price_cache.csv`, dedupe with `pc.plan`, and report lots / unique wines / duplicates collapsed / cache hits / wines actually needing a fetch. Value only the uncached ones in batches of 15–25, writing to `valuations.csv` **and** `price_cache.csv` after every batch. Continue across turns without pausing unless a genuine anomaly appears. If the 200-call cap hits, follow the checkpoint-and-chain procedure in known-limits.md.

5. **Tiers and flags** (Steps 4–5), then build the payload as schema 3, run `build_dashboard.py`, and run `test.js`. Expect the four known data-shape failures documented in known-limits.md; investigate anything beyond those.

6. **Report** survivors → valued → deals as three distinct numbers, present the dashboard from `output/`, and archive the processed xlsx to `inbox/processed/`.

7. **Publish.** Copy the dashboard to `docs/index.html` (repo root), then `git add -A && git commit && git push origin main` from the repo root. Automatic every run — see CLAUDE.md's "Publishing" section for the exposure caveat already settled with the user. Do not commit or push the raw xlsx.

$ARGUMENTS
