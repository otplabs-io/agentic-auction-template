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

## prep_valuation.py's cache-hit path never writes to valuations.csv

`prep_valuation.py` calls `pc.plan()` and writes `fetch_plan.json` from `plan['fetch']` only — the wines that *need* a search. Wines `pc.plan()` resolves as cache hits (already priced from a prior week, still within TTL) are correctly excluded from the fetch plan, but nothing ever writes their cached price into `valuations.csv`. `apply_batch.py` only ever processes wines that appear in a batch results file, so a pure cache hit — one that never gets searched this week because it doesn't need to be — silently never gets a `valuations.csv` row either.

Caught 2026-09-20: 7 unique wines (9 lots, exactly matching the run's reported "7 cache hits") were missing from `valuations.csv` even after `fetch_plan.json` reached 0. `build_payload.py` would have miscounted them as "not yet attempted" despite having a perfectly good cached price sitting in `price_cache.csv`.

**Fix applied this week (should be folded into `prep_valuation.py` itself, not repeated by hand):** for every key in `plan['groups']` that is *not* in `plan['fetch']` (i.e. every cache hit), look up its price/source/source_type in the loaded cache and append a `valuations.csv` row for every lot in that group — same shape `apply_batch.py` writes — right there in `prep_valuation.py`, before `fetch_plan.json` is even written. Until that change lands, re-run the backfill check manually after `fetch_plan.json` hits 0: `set(survivors.id) - set(valuations.id)` should be empty; any leftover ids are cache hits that need this same manual backfill from `price_cache.csv`.

## WebSearch's synthesized answer is non-deterministic -- re-reading it changes the outcome

Caught 2026-09-20 via user report: **Altesino Brunello di Montalcino Montosoli 1997** was marked `insufficient` during the normal valuation pass. The user searched Wine-Searcher directly and got a clean $190 average price on the first try. Re-running the *identical* `site:wine-searcher.com` query in-session reproduced the miss initially, then on a subsequent call returned "average price (ex-tax) of €136" in the synthesized answer text -- the price was there, just not in every call's summary.

WebSearch returns a links list plus an LLM-synthesized prose summary of a subset of results. That summary is not a stable function of the query: identical queries across calls can yield a richer or thinner paragraph, and a price genuinely present in the underlying page can be missing, present, or phrased differently call to call. A valuation pass that reads the summary once and moves on when no price appears will systematically under-report.

**Scale of the problem, measured 2026-09-20:** a random sample of 15 wines already marked `insufficient` was re-searched with the identical query; 2 (13%) came back with a clean, usable price on retry, plus 2 more borderline all-vintage cases. Extrapolated across a full re-check of ~145 wines, 35 (24%) were recovered with a real sourced price. This is not a rounding error -- it moved a week's `deals` count from 95 to 112.

**Process fix -- apply this discipline during Step 3, not just when a user flags a miss:**

1. **Read the full narrative answer, not just the links list.** A price is often stated in prose ("average price of $X", "priced at $X", "listed at $X") even when no individual link's title shows it.
2. **Before marking `insufficient`, ask whether the price you found is actually for the row you're valuing** -- the two most common false matches:
   - A different **tier/cuvée** of the same producer (Riserva vs. base bottling, single-vineyard vs. generic, a named special cuvée vs. the plain wine). Fenocchio's Villero and Riserva-labeled Brunellos are frequent examples this week.
   - A price with no vintage tie ("current listings", "recent vintages", "average across vintages") applied to an old back vintage. Acceptable only for genuinely stable, low-variance basic bottlings (see the `ws_allvintage` convention already in use) -- never for anything Bordeaux-classified-growth-tier or older than ~10 years, where vintage materially moves price.
   - **The auction's own WineBid listing cited back as "the market price."** If a search result's number is exactly `reserve × 1.17` (this auction's own buyer-price formula) or is sourced to winebid.com, it is not independent market data -- discard it. Caught twice this week (E. Guigal Hermitage 2001, Giovanna Ciacci Brunello 2001).
3. **If the first call's summary shows nothing, it is legitimate to re-run the identical query once** before concluding `insufficient` -- this is not wasted budget chasing a coin flip; the underlying page didn't change, but the synthesis sampling did, and this session's data shows a meaningful fraction resolve on retry.
4. Genuinely insufficient stays insufficient. Most `insufficient` calls hold up under this discipline (in the 2026-09-20 sample, ~75-85% did) -- the fix is catching the minority that don't, not second-guessing every call.

This is not yet enforced by any script -- it is judgment applied during the valuation loop, easy to skip under batch-processing pressure. Re-read this section at the start of Step 3 each week rather than assuming last week's diligence carries over.

## Wine-Searcher direct access is CAPTCHA-gated, not just 403 -- and a location-shaped token changes what WebSearch surfaces

Re-confirmed 2026-09-21 while investigating the insufficient-marking problem above. Two things were tested. Note up front: `WebSearch`'s schema is just `query`, `allowed_domains`, `blocked_domains` -- there is no location/region parameter, and the tool's own description states web search "is only available in the US" as a fixed, non-configurable fact. Nothing below runs a search *from* California; it's query-text pattern matching against Wine-Searcher's own URL vocabulary, confirmed by checking the actual tool schema on 2026-09-21 rather than assumed.

1. **Direct access is a real bot-detection challenge, not a soft block.** Navigating to a `wine-searcher.com/find/...` URL in the browser tool returns a Cloudflare "Press & Hold to confirm you are a human" page, not a static 403. `WebFetch` on the same URL returns a hard HTTP 403. Both are explicit bot detection and are not to be worked around (no proxies, no simulating the press-and-hold, no alternate user agents) -- this is a hard boundary, not an engineering puzzle. Practical consequence: Wine-Searcher's *own* live DOM (the per-vintage price table, "Featured offer" merchant card, critic-score badge visible in a real browser) is permanently unreachable by this workflow. That specific gap is what the stage-2 fetch below works around -- not by defeating the block, but by reading the underlying retailer data through a different, unblocked door.

2. **Appending the literal token `usa-ca-y` to the query measurably changes results, not just re-running the query.** Controlled test, same day, same wine (Château Bourgneuf-Vayron 1998, already marked `insufficient` from an earlier pass): `site:wine-searcher.com Chateau Bourgneuf-Vayron 1998` returned nothing but tasting-note sites, no price. `site:wine-searcher.com Chateau Bourgneuf-Vayron 1998 usa-ca-y` returned "The 1998 Château Bourgneuf received a score of 89/100 with an average price of $90" plus a results link showing an actual `.../usa-ca` Wine-Searcher URL in the list -- confirming the token maps to something real and indexed on the site, not a no-op. This is one paired test, not a large-sample study; treat the practice as "worth doing, cheap, empirically justified" rather than "guaranteed to help every time."
   - **Use the raw token `usa-ca-y`, never the spelled-out word "California."** A query with the word "California" in it gets misread by the search synthesis as a question about the wine's origin ("this wine is from Tuscany, not California") and the answer goes sideways -- tested and confirmed unhelpful the same day.
   - This does not mean the returned number is verified to be California-specific pricing -- `WebSearch` is not literally navigating to the localized page, it's a text search that happens to retrieve better results when this token is present. Cite it the same way as any other `ws_vintage`/`ws_allvintage` pull; don't invent a new source_type for it.

## Stage-2 direct retailer fetch: WebFetch works fine on retailers even though Wine-Searcher itself blocks it

The insight that closes most of the remaining gap from the two findings above: the CAPTCHA/403 block is specific to `wine-searcher.com`, not to the web in general, and Wine-Searcher itself is just an aggregator of the same retailers (wine.com, K&L, J.J. Buckley, Saratoga Wine, Total Wine, CellarTracker, etc.) that already turn up constantly in `WebSearch` results. Those retailer sites are not behind any bot wall `WebFetch` has hit. So when stage-1 `WebSearch` synthesis doesn't yield a confident price, the fix isn't to keep re-querying the same black box -- it's to find a specific retailer product page for the exact wine/vintage in the results and `WebFetch` it directly for a hard, deterministic number instead of a probabilistic summary.

Full procedure is in `CLAUDE.md`'s "Establishing a price" section (stage 2). Validated 2026-09-21 on three real cases from that week's still-unvalued list, chosen to cover the success, the graceful near-miss, and the graceful failure:

- **Success:** Domaine Charles Audoin Marsannay Clos de Jeu 2019. Stage 1 only produced a vague "$76 average" with no vintage tie. An unrestricted second search ("Domaine Charles Audoin" Marsannay "Le Clos de Jeu" 2019 price 750ml) surfaced `jjbuckley.com/wine/2019-domaine-charles-audoin-marsannay-clos-de-jeu/...`, an exact vintage/wine/size match. `WebFetch` on that URL returned a clean **$59.94**, vintage and bottle size confirmed on the page itself (the listing was out of stock, which doesn't matter -- the price was still shown).
- **Correctly rejected, not force-fit:** Beni di Batasiolo Barolo 2001. The best retailer candidate found (Saratoga Wine) was for the same producer's *NV* bottling, out of stock, with no price displayed at all. Rejected rather than substituted -- an out-of-stock listing with a real price on it is usable (see above); one with no price field is not, regardless of how close the match otherwise looks.
- **Correctly failed clean:** Alois Kracher Grande Cuvée Trockenbeerenauslese #12 1995. No retailer candidate for this exact bottling number existed at all -- the closest hits were different Kracher bottling numbers (#9, #14) and one foreign-currency auction-house estimate for a mismatched wine. No fetch was attempted; this stays `insufficient` (or falls to Step 4's all-vintage rule if applicable) rather than being propped up with an unrelated number.

Rules for this stage:
- Never target `wine-searcher.com` itself in the fetch (guaranteed 403) or `winebid.com` (this auction's own platform -- citing our own listing back as "market" is circular, same failure mode as the WineBid-citation trap documented above).
- A candidate's *title* must show the exact target vintage before it's worth fetching -- don't fetch a generic NV or "current vintage" product page hoping it happens to match.
- "Out of stock" is fine if a price is still shown; "no price field at all" is not a wine to substitute with a nearby one.
- Record the result as `ws_single_retailer`, name the retailer, and note it was fetched directly -- this is higher-confidence data than a `WebSearch` synthesis, not lower, and the source note should say so.
- Cost: at most one extra `WebSearch` call (the unrestricted retailer-oriented query) plus one or two `WebFetch` calls, only for wines stage 1 misses. `WebFetch` does not count against the 200-call `WebSearch` session cap, so this is close to free reliability.

## Producer-name collisions: a WebSearch synthesis will confidently price the wrong producer

Distinct from the cuvée/tier mismatch trap (same producer, wrong bottling) documented above — this is *different, unrelated producers with confusingly similar names*, common enough in Piedmont that it's worth naming explicitly. Caught across the 2026-09-20 stage-2 pass:

- **"Vietto Barolo Ravera"** (a small, independent producer) → search returned **Vietti**'s (a much larger, more famous, completely unrelated producer) price for their own Ravera cru bottling. One letter apart in the name, same cru name coincidentally, wrong wine entirely.
- **"Ronchi di Giancarlo Rocca Barbaresco Ronchi"** → first search returned **Bruno Rocca**'s unrelated Rabajà bottling (matched on the shared surname "Rocca"); a corrected retry returned **Albino Rocca**'s similarly-named "Ronchi" cru bottling instead (matched on the shared cru name "Ronchi"). Three distinct Rocca-adjacent producers, three different wines, none the target.

Both were caught only because the producer name was re-checked against the search result's actual producer before accepting the price — the wine name / cru name alone was not enough to catch it, since those matched exactly. **Rule:** when a producer name is a common surname, a partial match, or differs by even one letter/word from what the search result actually names, treat it as a miss and re-search with the full producer name in quotes rather than accepting the substitution. This is now folded into `CLAUDE.md`'s extraction-discipline section.

## `build_dashboard.py`'s default output path assumes a different (cloud) environment

Running `python3 build_dashboard.py ../payload.json` with no `-o` flag crashes with `FileNotFoundError: [Errno 2] No such file or directory: '/mnt/user-data/outputs/WineBid_Deals_<date>.html'` on a local checkout — the script's hardcoded default (`toolkit/build_dashboard.py` line ~147) assumes a `/mnt/user-data/outputs/` path that only exists in some cloud sandbox environments. Not fixed at the script level (a local default could just as easily break a cloud session that *does* have that path) — instead, `CLAUDE.md` Step 6 now always passes `-o ../output/WineBid_Deals_<auction_date>.html` explicitly. Caught 2026-09-20 rebuilding the dashboard after the stage-2 valuation pass.

## Personal-pick region matching: a bare region is not a personalization signal for this user

`personal_pick.py`'s first cut matched taste-history region at (country, region) grain -- e.g. "France > Burgundy". Against this user's actual tasting notes, that starred **222 of 327 lots** in the first real run: this user's ratings already skew almost entirely toward the same countries/regions this auction's Step 1 screens to (France/Italy/Spain/Portugal/Austria, heavy Burgundy/Bordeaux/Tuscany/Piedmont), so "you've rated Burgundy highly" is true of nearly everything and personalizes nothing. Fixed by requiring the full (country, region, subregion/appellation) triple to match -- e.g. "France > Burgundy > Meursault", not just "France > Burgundy" -- which dropped the real run to 18 of 327 starred, all individually defensible. If this ever needs loosening again, loosen the rating/count thresholds first, not the match grain -- the grain is what was actually broken.

## CellarTracker CSV exports are cp1252, not UTF-8

Both `My Cellar` and `My Tasting Notes` exports came in as Windows-1252 (`chardet` reports ISO-8859-1 with low confidence, but cp1252 is what CellarTracker's Windows-side export actually uses, and it round-trips the accented producer names correctly -- e.g. "Bodegas y Viñedos Alión", "Domaine Jean-Marc / Thomas Bouley Bourgogne-Aligoté"). Reading them as UTF-8 raises a decode error; reading as plain Latin-1 works for the common accented Latin characters in this data but is the wrong encoding in general (would mangle curly quotes/em-dashes if the free-text tasting notes ever contain them). `preferences/cellar.csv` and `preferences/tasting_notes.csv` are stored as UTF-8 in the repo -- when refreshing either from a new CellarTracker export, decode the incoming file as cp1252 and re-save as UTF-8 rather than copying it verbatim.

## Environment notes

- **JSDOM does not accurately model computed-style CSS cascade.** Author-origin rules can override UA `[hidden]` behavior in ways JSDOM won't catch. Rendered browser output is the final verification. (This is how the sample-banner bug survived a passing test suite — fixed 2026-08-24 with an explicit `.sample-banner[hidden]{display:none!important}` rule. The general lesson stands for any future rendering change: run `test.js`, then also check a real browser.)
- **Embedded commas in CSV note fields** consistently break `pandas.read_csv` column alignment. Reliable fix: post-append `csv.reader` pass detecting rows with an extra field, rejoining the overflow into column 3, rewriting with `csv.writer`.
- **`exec(open('value_add.py').read().split('batch1 =')[0])`** loads function definitions from a script without executing any example batch in the body.
