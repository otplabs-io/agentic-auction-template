# Known Limits

Operational constraints discovered while running the weekly WineBid workflow. Read before an Execute run to set expectations on coverage.

## WebSearch session cap

The session's WebSearch tool has a hard cap of **200 calls** (`CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION`). The cap is per-session and **shared with any subagents spawned inside it** — a subagent hits the same "200 of 200" exhaustion immediately, so spawning `wine-valuer` does not buy extra budget.

There is no in-session workaround. Alternate search engines (Bing, DuckDuckGo HTML) are blocked by their own robots.txt via WebFetch, and Wine-Searcher returns 403 to WebFetch. WebFetch itself does **not** share the cap and keeps working once a URL is known.

**Practical effect:** roughly one WebSearch call per uncached unique wine. Observed weeks: 119 unique wines (2026-08-09, finished in one session), 469 (2026-08-24), 502 (2026-08-17, needed chaining). With the cache enabled, only the *delta* costs searches, so this cap should stop binding after the first few weeks.

You can raise the cap for a session by setting the env var before launching.

### Procedure when the cap is hit mid-run

1. Persist everything gathered so far to `valuations.csv` **and** `price_cache.csv` immediately — don't wait for the batch to end.
2. Save checkpoints: `checkpoint-<auction_date>-survivors.csv` (must include `wine_type`), `-valuations.csv` (keyed by `make_key`), `-remaining.json` (still-unpriced entries from the fetch plan).
3. Route never-attempted wines to Unvalued with a note distinguishing **"no reliable price found"** (searched, source insufficient) from **"not yet attempted — search budget exhausted"** (never searched).
4. Build and deliver the dashboard with partial coverage rather than blocking. State exact coverage (X of Y unique wines attempted) and keep the three numbers distinct.
5. Continue automatically in a fresh session via `create_trigger`/`fire_trigger` rather than waiting for the user to ask. The new session gets its own 200-call budget. Its prompt must be fully self-contained and must tell it to read the checkpoints instead of re-screening, resume from `remaining.json` only, never re-search a wine already in `valuations.csv`, repeat this handoff if it hits the cap again, and rebuild + re-deliver the completed dashboard in place of the partial one.

## Checkpoint reuse works even across a full re-screen

On the 2026-08-23 run, Step 1 was redone from scratch rather than trusting the prior checkpoint's survivor list. Re-screening produced 544 survivors / 491 unique keys, and **491/491 matched** the checkpoint's `valuations.csv` by `make_key` — zero new searches needed.

This works because valuations are keyed on **wine identity** (wine/vintage/format), not lot id. Always key that way. The 9 checkpoint rows that matched nothing were exactly the fortified/dessert lots the fixed screen now correctly drops — a useful cross-check that the re-screen and the valuation-era screen agree.

## Dessert/fortified screen misses producer-identified fortified wines

Keyword matching catches wines that name their style ("Taylor-Fladgate LBV", "Ruby Port"). It does **not** catch Vintage/Colheita/single-quinta Port sold under just the shipper's name and a vintage year — "Cockburn 1967", "Warre's 1963", "Quinta do Noval 1970", "Ferreira 1975", "Taylor-Fladgate 2016" — where no style word appears anywhere in the row.

Word-boundary matching on "port" prevents the *false positive* (matching "Portugal") but does nothing for these *true negatives*.

**Useful signal:** for Portugal lots, WineBid's `Region` reads bare `"Portugal"` (no subregion) for fortified Port, versus `"Portugal, Douro"` / `"Portugal, Alentejo"` for dry DOC table wines. Sandeman's dry Quinta do Seixo Douro red correctly showed `Portugal, Douro` at ~$80 retail.

This is a heuristic, not a substitute for recognizing shipper names outright. Full list in CLAUDE.md Step 1. **Real Vinicola** was added 2026-08-18 after "Real Vinicola Quinta do Sibio" 1960/1963 bare-Portugal lots appeared — same pattern, new name, so expect the list to keep growing.

On 2026-08-23 this caught 11 lots that had survived to the deals list; three (Smith Woodhouse, Warre's, Quinta do Noval) had been valued and tagged **Steal** before the miss was caught by user review post-delivery.

**Process fix:** after the keyword pass, print all surviving Portugal lots (and Spain for Sherry/PX, Italy for Marsala/Vin Santo/Recioto) for a producer-identity check before finalizing the funnel.

## test.js failures that are data-shape, not defects

`test.js` is calibrated to `sample_payload.json`'s synthetic values. Four assertions legitimately fail on real data:

1. **Sample banner visible** — real runs have `sample` absent/false, so no banner.
2. **Bare region "Rhône"** — real French regions read "Rhône Valley". This one *crashes* the suite partway through, leaving everything after it unverified.
3. **"Sample exercises all six swatches"** — fails whenever a week has no lots of some type.
4. **"Every judged type is offered as a filter"** — the filter rail is data-driven and correctly omits zero-count types.

Confirmed sound by rebuilding `sample_payload.json` and rerunning: 63/63 pass. On the 2026-08-23 real build, patching a throwaway copy (`s/Rhône/Rhône Valley/g`, never committed) to get past the crash gave **84/88 passing**, with only these four failing.

**Recommended:** when `test.js` crashes on the region-cascade test against real data, patch a throwaway copy and rerun the full suite rather than stopping at the crash — otherwise buyer-premium math, range filters, watchlist, URL hash round-trip, CSV export and self-containment all go unverified.

## price_cache.py didn't recognize the "ltr" format suffix

`norm_format` matched `ml|cl|l|liter|litre` but WineBid's export spells magnums and
imperials as `"1.5ltr"` / `"6.0ltr"`. That suffix hit the digit-only fallback,
silently returning `2` and `6` (round of the bare "1.5"/"6.0") instead of `1500`
and `6000` — corrupting the cache key and the magnum/imperial scaling logic for
every non-standard-size lot. Fixed 2026-08-24 by adding `ltr` to the unit
alternation; the existing 48-test suite in `test_price_cache.py` still passes
(it never exercised this spelling). Re-check this if WineBid ever changes its
format-string convention again.

## Vouvray/Loire "Moelleux" is a dessert style the keyword screen misses

The dessert/fortified keyword list (Sauternes, Barsac, SGN, late-harvest, Vin
Santo, etc.) has no French-Loire-specific sweet-style terms. Domaine Huet's
Vouvray **Moelleux** bottlings — especially "Première Trie" (first selective
botrytis-pass harvest) — are sweet, late-harvest-style dessert wines that read
as ordinary white Vouvray to the Step 1 keyword pass. Caught on 2026-08-24 (5
lots, all Domaine Huet) only via manual review during classification; correctly
re-tagged `Dessert` per Step 2 Rule 5 rather than dropped retroactively.

**Process fix:** add `moelleux`, `liquoreux`, and `(premiere|première) trie` to
the Step 1 dessert keyword list so these get caught at the screen stage instead
of surviving to classification. Coteaux du Layon, Quarts de Chaume, and
Bonnezeaux are already appellation-level dessert AOCs worth adding too, though
none appeared in the 2026-08-24 data.

## Classifier bugs already found and fixed

Documented in CLAUDE.md Step 2. Summary of the takeaway: **proprietor and cru names routinely embed colour-word-looking substrings** (Montrose, Arrosée, "delle Rose"). Always word-bound colour regexes, and re-check red-vs-rose precedence when both fire on one name.

New 2026-08-24: **Bodegas Pinea "Korde"** bottles Blanco, Rosado and Tinto under one cuvée name with no colour word in the export row — genuinely unresolvable from the name. Hedge explicitly rather than defaulting silently.

## Terminology pitfall when reporting progress

"Valued" (got a real market price from any source tier) and "deals" (valued AND ≥25% below market) are different numbers. A valued-but-not-a-deal lot appears in **neither** the `deals` nor `unvalued` arrays — correctly priced but simply not shown in the dashboard UI.

Reporting only deals and unvalued invites reading `deals / (deals + unvalued)` as the coverage rate, which understates valuation coverage and overstates how many wines were never searched. Always state all three: screened survivors → attempted/valued → deals.

## Environment notes

- **JSDOM does not accurately model computed-style CSS cascade.** Author-origin rules can override UA `[hidden]` behavior in ways JSDOM won't catch. Rendered browser output is the final verification. (This is how the sample-banner bug survived a passing test suite — fixed 2026-08-24 with an explicit `.sample-banner[hidden]{display:none!important}` rule. The general lesson stands for any future rendering change: run `test.js`, then also check a real browser.)
- **Embedded commas in CSV note fields** consistently break `pandas.read_csv` column alignment. Reliable fix: post-append `csv.reader` pass detecting rows with an extra field, rejoining the overflow into column 3, rewriting with `csv.writer`.
- **`exec(open('value_add.py').read().split('batch1 =')[0])`** loads function definitions from a script without executing any example batch in the body.
