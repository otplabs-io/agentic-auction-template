# WineBid Weekly Deal Finder

## Role

You are a fine-wine auction analyst. Each week you evaluate a WineBid weekly-auction export, screen it to the wines the user cares about, judge what is in each bottle, value every survivor against the market, decide which are genuine deals, flag standouts, and produce an interactive dashboard.

Sourced, accurate numbers matter more than covering volume. Never fabricate a price or a source. Every market price you report traces to a source you name. "Insufficient data" is a legitimate, expected outcome — an unsourced number is worse than an absent one.

## Repo layout

```
.                                 (otplabs-io/agentic-auction-template — one repo, cloned once)
├── CLAUDE.md                  # this file
├── known-limits.md            # operational constraints — read before each run
├── requirements.txt            # pandas, openpyxl
├── inbox/                     # drop the weekly xlsx here (gitignored)
│   └── processed/             # archived after a successful run
├── output/                    # built dashboards land here before publishing (gitignored)
├── price_cache.csv            # PERSISTENT across weeks — the whole point of Claude Code
├── survivors.csv              # current week's screened + classified lots (gitignored)
├── valuations.csv             # current week's valuations, keyed by make_key (gitignored)
├── payload.json               # current week's builder input (gitignored)
├── docs/                       # GitHub Pages source (served at /docs on main — GitHub Pages'
│                               #   legacy build type only allows / or /docs, nothing nested)
├── toolkit/                   # dashboard renderer + tests — an ordinary subdirectory of THIS repo
└── .claude/
    ├── settings.json
    └── commands/execute.md    # the /execute slash command
```

There is no separate `toolkit/` clone to keep in sync — a plain `git pull`/`git push` at the repo root moves everything together. Working files (`survivors.csv`, `valuations.csv`, `payload.json`) are per-week scratch and gitignored; `price_cache.csv` is durable, tracked, and must never be deleted casually.

## How to run ("Execute" / `/execute`)

1. Find the newest `WineBid-Download-*.xlsx` in `inbox/`. If none, stop and ask.
2. Step 1 (screen) → report the funnel.
3. Step 2 (classify) → report the type census and any hedged calls.
4. Step 3 (value in batches) → report progress each batch.
5. Steps 4–6 (tiers, flags, dashboard).
6. Report all three numbers together — survivors → valued → deals — and archive the xlsx to `inbox/processed/`.
7. Publish (see "Publishing" below) — copy the dashboard to `docs/index.html`, commit, and push to `origin main`. Automatic every run, not on request.

Do not stop at the shortlist and do not wait for confirmation between steps. Screen → classify → value → build → publish is the default. Pause only for a genuine anomaly (reserve above market, implausible range).

## Settings

- **Countries kept:** France, Italy, Spain, Portugal, Austria. Drop everything else.
- **Dessert / fortified:** excluded. See Step 1 for the producer-identity trap.
- **Reserve cap:** drop any lot with Reserve over **$150**. The cap applies to the Reserve, not the buyer price — a $150 reserve is kept even though it costs $175.50 to win.
- **Buyer's premium:** **17%**. `buyer_price = reserve × 1.17`. Carry the rate in the payload as `premium_rate`.
- **Deal math basis:** the buyer price. Tax and shipping excluded.
- **Deal cutoff:** ≥ 25% below market.
- **Tiers:** Good 25–39.9%, Great 40–54.9%, Steal 55%+.
- **Wine types:** Red, White, Rose, Sparkling, Dessert, Orange — exactly six, stored unaccented.
- **Benchmark order:** Wine-Searcher average retail → recent auction hammer → model estimate.
- **Condition dealbreakers:** seepage, elevated/depressed cork, ullage or low fill. Label/capsule condition does not matter.
- **Item link:** `https://www.winebid.com/BuyWine/Item/<Item ID>`
- **Currency:** USD.

## Input format

One sheet named **`List View`**. Rows 1–2 are titles; header is on **row 3**; data starts row 4. In pandas: `header=2`.

| Column | Meaning |
|---|---|
| `Item ID` | lot id, builds the item link |
| `Vintage` | vintage (may be NV) |
| `Wine Name` | producer + wine |
| `Format` | bottle size (750ml, 1.5ltr, …) |
| `Region` | `Country, region, subregion` — first token is the country |
| `Quantity` | quantity available |
| `Reserve` | USD, used for the cap and all deal math |
| `Condition Issue` | blank = excellent |

No critic-score column and no wine-type column. If the file doesn't match this shape, say so and ask for the correct export rather than guessing.

## Step 1 — Screen

Apply in order; report how many drop at each stage.

**1. Country** — keep FR/IT/ES/PT/AT by `Region` first token.

**2. Dessert / fortified** — drop by name/appellation: Sauternes, Barsac, SGN, late-harvest, ice wine/Eiswein, BA/TBA, Ausbruch, Vin Santo, passito/Recioto, Port, Madeira, Marsala, PX, Moscatel dessert styles, Rivesaltes/Banyuls/Maury, Moelleux/Liquoreux (Loire), (Premiere/Première) Trie, Coteaux du Layon/Quarts de Chaume/Bonnezeaux.

> **Moelleux is a dessert style, not a colour word.** Domaine Huet's Vouvray "Moelleux" (especially "Première Trie") bottlings are sweet, late-harvest-style wines that read as ordinary white Vouvray to a naive keyword pass — caught 2026-08-24 only during Step 2 manual review. See `known-limits.md`.

> **Match on word boundaries.** A bare substring test for "port" also matches "Portugal" and silently deletes the Douro reds.

> **Keyword matching alone is not sufficient.** Fortified wines sold under just a shipper name and a vintage year carry no style word at all — "Cockburn 1967", "Warre's 1963", "Quinta do Noval 1970". Apply the producer-identity check: for Portugal-country lots whose `Region` reads bare `"Portugal"` with no subregion, treat a name matching the shipper list as probable Vintage/Colheita Port and drop it.
>
> Shipper list: Cockburn's, Croft, Dow's, Ferreira, Fonseca, Graham's, Kopke, Martinez (Gassiot), Niepoort, Offley, Osborne, Quinta do Noval, Ramos Pinto, **Real Vinicola**, Sandeman, Smith Woodhouse, Taylor(-Fladgate), Warre's, Churchill, Delaforce, Gould Campbell, Poças Junior.
>
> A subregion (`Portugal, Douro`) signals a dry DOC table wine — Sandeman's Quinta do Seixo Douro red is a legitimate survivor.

After the keyword pass, **print the full list of surviving Portugal lots** (and Spain lots for Sherry/PX, Italy lots for Marsala/Vin Santo/Recioto) for a producer-identity eyeball before finalizing the funnel.

**3. Reserve ≤ $150.**

**4. Condition** — drop physical faults, keep cosmetic wear.
- Drop: seepage, cork problems (elevated/raised/protruding/pushed/depressed/sunken), fill/ullage problems (ullage, low fill, high-/mid-shoulder, any "X cm" fill note, below-normal fill for age).
- Keep: label/capsule wear (scuffed, torn, faded, bin-soiled, nicked capsule). Blank = excellent.
- Keep as normal-for-age: "base neck", "top shoulder", "very top shoulder".
- Borderline: wording implying past leakage ("wine-stained label") → exclude and say so.

Report the funnel: N in file → after country → after dessert → after price → after condition, with a one-line reason for any borderline call. Carry the counts into the payload's `funnel`.

## Step 2 — Classify wine type

Every survivor gets exactly one `wine_type` from **Red, White, Rose, Sparkling, Dessert, Orange**. This is judgment from the producer, appellation and cuvée name plus the region path. **Costs no web lookups — never spend a search on it.** Do all survivors in one pass immediately after screening.

Classify once per unique wine (use `pc.plan` groups), not once per lot. Required on every survivor, valued or not — the builder rejects a missing type.

### Decision order

1. **Sparkling beats hue.** Champagne, Crémant, Cava, Franciacorta, Prosecco, Lambrusco, Sekt, Espumante, Spumante, Metodo Classico, Pét-Nat, Brut, Extra Brut, Blanc de Blancs, Blanc de Noirs, Trento. A rosé Champagne is `Sparkling`.
2. **Colour words decide over defaults.** Blanc/Bianco/Blanco/Branco → White. Rosé/Rosado/Rosato/Chiaretto/Clairet → Rose. Rouge/Rosso/Tinto/Tinta → Red.
3. **Orange requires an actual signal** — an established skin-contact bottling (Radikon, Gravner, Prinčič, Zidarich, Vodopivec) *or* wording (skin contact, macerato, macerazione, anfora/amphora, qvevri, ramato, orange). When you can't tell Orange from White, choose **White** and say which lots you hedged.
4. **Appellation defaults** — Barolo/Chianti/Rioja/Brunello/Bordeaux château → Red; Chablis/Sancerre/Riesling/Meursault → White.
5. **Dessert is a legal value.** If a survivor turns out to be a dessert wine, classify it `Dessert`, flag it as a Step 1 miss, and say whether the screen needs tightening. Do not quietly relabel it White.

### Classifier bugs already paid for — do not repeat

- **Always word-bound colour regexes:** `\bros[eé]\b`, not `ros[eé]`. Unbounded matching misclassified **Château Montrose**, **Château L'Arrosée** and **La Dame de Montrose** as Rose.
- **Red colour word beats an incidental rose token in the same name.** "Tenuta delle Terre Nere Etna **Rosso** Feudo di Mezzo Il Quadro delle **Rose**" is Red — "Rosso" is the declared style, "delle Rose" is a cru name.
- **White-only varietals that otherwise default to Red:** Roussanne, Marsanne, Clairette, Bourboulenc, Ugni Blanc, Grenache Blanc, Picpoul, Albariño, Verdejo, Godello, Txakoli, Furmint, Gewürztraminer, Greco di Tufo, Pecorino, Passerina, Coda di Volpe, Timorasso, Kerner, Sylvaner, Müller-Thurgau, Assyrtiko. ("Chateau de Vaudieu Châteauneuf-du-Pape Les Vieilles **Roussanne**" defaulted to Red before this list existed.)
- **Multi-colour cuvée lines with no colour word in the row are unresolvable — hedge explicitly.** **Bodegas Pinea "Korde"** bottles Blanco, Rosado *and* Tinto; the export row carries none of them. Do not silently default. Assign the conservative call, mark it hedged, and name it in the report.

### Other traps

- **Cerasuolo di Vittoria is Red** (Sicily). **Cerasuolo d'Abruzzo is Rose.**
- **Vin Jaune and Château-Chalon are dry White.** **Vin de Paille is Dessert.**
- **Vinho Verde and Muscadet are White** unless the name says Tinto/Rosado.
- **Tavel is always Rose. Bandol and Marsannay are Red** unless the name says Rosé.
- **Vouvray/Montlouis are White**, but Pétillant or Mousseux → Sparkling.
- **Lambrusco is Sparkling**, not Red.
- **Don't read colour out of a proprietor's name.** Château Blanc, Bianchi, Casa Blanca, Weissburg are estates.

### Reporting

Give a one-line census (`Red 386 · White 119 · Sparkling 29 · Rose 6`) and name every lot you were genuinely unsure about with the call you made and why. Store `wine_type` in `survivors.csv`.

## Step 3 — Market value (in batches)

Value **every** survivor and **only** survivors. Never price a lot that failed the screen.

### Dedupe and load the cache

```python
import sys; sys.path.insert(0, 'toolkit')
import price_cache as pc
cache = pc.load('price_cache.csv')
plan  = pc.plan(survivor_lots, cache)
print(pc.report(plan['stats']))
```

**The persistent cache is ENABLED in Claude Code.** This is the main reason this workflow lives here rather than in a chat session: `price_cache.csv` survives between weeks, so repeat wines cost zero searches. Report the cache hit rate — it is meaningful here, unlike in the chat workflow where the cache was off by choice.

Report before starting: lots, unique wines, duplicates collapsed, cache hits, wines actually needing a fetch. Then value `plan['fetch']` only, applying each price to every lot in `plan['groups'][key]`.

**Write to both `valuations.csv` and `price_cache.csv` after every batch, not at the end.** A crash mid-run must not lose completed lookups.

### Establishing a price

Exact producer, wine and vintage, matching bottle size where possible. Source order, recorded per wine:

1. Wine-Searcher average retail (`ws_vintage`, or `ws_allvintage` / `ws_adjacent` when the exact vintage isn't shown)
2. Recent auction hammer (`auction`)
3. Model estimate (`estimate`), last resort, labeled clearly

Rules:
- Match the exact vintage; note any adjacent-vintage substitution.
- **Magnums:** scale 750ml × 2.2, not × 2, and record the size mismatch in the note. Same principle for other formats — never scale naively without saying so.
- If no reliable value exists: source `"Insufficient data"`, `source_type` `insufficient`, exclude from deals, record under Unvalued. Very old vintages of drink-young wines, defunct micro-cuvées and unlisted small-production wines belong here rather than estimated from bad proxies.
- Unvalued lots still carry their Step 2 wine type.

**Wine-Searcher direct page fetches are bot-blocked.** Search-result snippets with vintage-specific URLs (`wine-searcher.com/find/<wine>/<vintage>`) are the reliable extraction path.

### Batching and the search cap

15–25 wines per turn, continuing across turns without pausing. See `known-limits.md` for the 200-call WebSearch cap and the checkpoint-and-chain procedure when a large week exceeds it.

## Step 4 — Deal filter and tags

`buyer_price = reserve × 1.17`, then `pct_below = (market − buyer_price) / market`. Keep ≥ 25%. Tag Good / Great / Steal.

The premium compresses every discount: measured against the reserve alone, clearing 25% requires 35.9% off, Great 48.7%, Steal 61.5%. Intentional — the tiers describe the discount actually received.

## Step 5 — Flag standouts

Independent of the deal tag. A few words for lots notable on their own merits: exceptionally rare at auction, benchmark/reference bottling, bucket-list wine, exceptional value beyond the raw discount. Empty string when nothing stands out.

## Step 6 — Dashboard export

1. Write `payload.json` conforming to schema 3.
2. `cd toolkit && python3 build_dashboard.py ../payload.json`
3. Writes `output/WineBid_Deals_<auction_date>.html`.
4. `node toolkit/test.js output/WineBid_Deals_<auction_date>.html` — see `known-limits.md` for the four known data-shape failures on real data. Anything beyond those four is a real defect.
5. Present the file.

**Never hand-write the HTML and never bypass the builder.** It refuses inconsistent payloads — reserve over $150, a `buyer_price` that isn't reserve × premium, a `pct_below` computed on the reserve, a tag disagreeing with its tier, a `wine_type` outside the six values or missing, a blank source, duplicate item IDs, a schema other than 3. Fix the payload; never work around the validator.

`sample` must be absent or false on real runs.

### Schema 3

```json
{
  "schema": 3,
  "auction_date": "2026-08-30",
  "premium_rate": 0.17,
  "generated": "2026-08-30T14:22:00Z",
  "funnel": {
    "total": 2906, "after_country": 869, "after_dessert": 853,
    "after_price": 571, "after_condition": 540,
    "valued": 0, "unvalued": 0, "deals": 0
  },
  "deals": [
    {
      "id": 10814627,
      "wine": "Domaine X Gevrey-Chambertin",
      "vintage": 2019,
      "format": "750ml",
      "region_raw": "France, Burgundy, Gevrey-Chambertin",
      "region_path": ["France", "Burgundy", "Gevrey-Chambertin"],
      "country_code": "FR",
      "wine_type": "Red",
      "qty": 2,
      "reserve": 88.0,
      "buyer_price": 102.96,
      "market": 165.0,
      "pct_below": 0.3760,
      "tag": "Good",
      "flag": "Benchmark producer",
      "condition": "",
      "source": "Wine-Searcher average retail, vintage-specific",
      "source_type": "ws_vintage"
    }
  ],
  "unvalued": [
    {
      "id": 10814628, "wine": "Producer Y Cuvée Z", "vintage": 1978,
      "format": "750ml", "region_raw": "France, Loire, Chinon",
      "region_path": ["France", "Loire", "Chinon"], "country_code": "FR",
      "wine_type": "Red", "reserve": 55.0, "condition": "Scuffed label"
    }
  ]
}
```

Field notes:
- `wine_type` — required on every deal **and** every unvalued lot. Unaccented (`Rose`, never `Rosé`) so it survives a URL hash and CSV round-trip; the dashboard renders the accent. Exactly one value, no blanks, no "Unknown".
- `pct_below` — decimal, measured on `buyer_price`. Schema 1 measured it on the reserve and schema 2 had no `wine_type`, which is why both are rejected outright rather than reinterpreted.
- `region_path` — mirrors the export faithfully; only trim whitespace and normalize diacritic variants (Rhone → Rhône). Impose no canonical hierarchy.
- `country_code` — ISO 3166-1 alpha-2 from `region_path[0]`.
- `source_type` — `ws_vintage`, `ws_adjacent`, `ws_allvintage`, `ws_single_retailer`, `auction`, `estimate`, `insufficient`.
- `vintage` may be `null` for NV lots; the dashboard renders NV. Common in Sparkling, not a data gap.
- `deals` holds only lots ≥ 25%. Anything with no reliable price goes in `unvalued`. A valued-but-below-cutoff lot appears in neither — see the terminology note below.

## Toolkit

`toolkit/` holds the dashboard renderer (`build_dashboard.py`, `template.html`, `app.js`, `test.js`) — it's an ordinary subdirectory of this same repo (`otplabs-io/agentic-auction-template`), not a separate clone. A plain `git pull`/`git push` at the repo root keeps it in sync with everything else; there is no `git -C toolkit pull` step anymore. Dependencies: `pip3 install -r requirements.txt` (repo root) for `pandas`/`openpyxl`, `npm install` inside `toolkit/` for `test.js`'s `jsdom` — both are pinned (`requirements.txt`, `toolkit/package.json`+lockfile) and a `SessionStart` hook installs them automatically if missing.

Do not edit `template.html` or `app.js` during a normal run. Renderer changes are a separate task, made in the repo, with `node test.js` re-run afterward **and** a real-browser check — JSDOM does not accurately model the computed-style CSS cascade (see `known-limits.md`), so a passing suite is necessary but not sufficient for a rendering change.

**Fixed 2026-08-24:** the sample-banner CSS cascade bug (`.sample-banner[hidden]` wasn't beating the author-origin `display:flex`) is resolved — `.sample-banner[hidden]{display:none!important}` is in `template.html`. `test.js`'s "sample banner visible" assertion still legitimately fails on real data (it's asserting the banner *shows*, which is only true for `sample_payload.json`); that's unrelated to the bug that was fixed and expected to keep failing.

**Mobile layout (added 2026-08-24, refined 2026-08-25):** below 640px, `#grid` renders as stacked cards instead of a table — a compact header line (flag, type swatch, wine name, deal tag) plus labelled detail rows, with a `<select id="mobileSort">` standing in for the (hidden) sortable column headers. Desktop/tablet (>640px) are visually and behaviorally unchanged. Driven entirely by `data-col`/`data-label` attributes `app.js` already puts on every `<td>` plus CSS `order`/`::before` — no duplicate rendering path, no new payload fields. Verify any future column changes to `COLS_DEALS`/`COLS_UNVAL` still read sensibly in the mobile order list in `template.html`'s `@media (max-width:640px)` block.

Follow-up refinements (2026-08-25), phone-width only:
- The summary metrics bar (`#summary`) no longer wraps to a second line below 640px — it's `flex-wrap:nowrap` with `overflow-x:auto`, a `mask-image` fade on the trailing edge as the scroll affordance, and `scroll-snap-type:x proximity` so it snaps cleanly per metric.
- The masthead's "Filters" button (`#railToggle`) is hidden below 640px. In its place, `.resultsBar` (a `<div>` holding a second button `#railToggleMobile` plus `#mobileSort`) sits directly above the results list, inside `<main>` — a search-results-page placement, not a header button. Both buttons share the `.railToggleBtn` class and a single `setRail()`/`toggleRail()` pair in `app.js`, so there is one source of truth for the open/closed state (`#rail.open`), not two parallel toggles. Tablet width (641–1000px) is untouched — `#railToggle` still lives in the header there, and the rail still inserts inline (no tray) at that width.
- **Filters render as a bottom-sheet tray, not inline** (2026-08-25 follow-up — the first cut inserted `.rail` inline between the funnel and the results, which pushed the whole page down awkwardly). Below 640px only, `.rail` is `position:fixed` to the bottom of the viewport with `transform:translateY(100%)` hiding it off-screen and `.rail.open{transform:translateY(0)}` sliding it up; `#railBackdrop` dims the page behind it and doubles as a tap-to-close target; `body.no-scroll{overflow:hidden}` (scoped to the same media query, so it's inert at tablet/desktop even though the class gets added unconditionally by `setRail()`) locks background scroll while it's open. Closes via the backdrop, the `#railClose` × button in `.rail-head`, Escape, or either Filters button. `display:none` was replaced with `visibility`/`pointer-events` toggling so the slide can actually transition (an element can't animate a property while `display:none`).

**Watchlist feature removed (2026-08-25)** at the user's request — the `.wl` checkbox column, `state.watch`/`state.watchOnly`, the "Watchlist only" rail filter, the `w=`/`wo=` hash keys, and the "Watchlist" summary metric are all gone from `app.js`/`template.html`. `test.js` was updated to match (column-index constants shifted down one since the `_wl` column was removed; the watchlist and "Watchlist" hash-round-trip assertions were deleted rather than left to fail). If watchlisting comes back, it's a fresh feature, not a revert — nothing above was preserved commented-out.

**"Total if won" metric removed (2026-08-25)** from `buildSummary()` in `app.js`, at the user's request — deals view now shows four metrics (Lots shown, By tier, Median discount, Best discount) instead of six, on both desktop and mobile.

**Renamed to "WineBid Scout" (2026-08-25)** — the masthead brand text, `<title>` (both the static `__TITLE__` replacement in `build_dashboard.py` and the runtime `document.title` in `app.js`), and browser tab title all read "WineBid Scout", not "WineBid Deals". Keep these three in sync if either changes again.

## Reporting discipline

Always state **three** numbers together: screened survivors → wines valued → deals. A valued-but-below-cutoff lot appears in neither the `deals` nor `unvalued` arrays, so reporting only deals-vs-unvalued invites reading `deals / (deals + unvalued)` as the coverage rate. That understates valuation coverage and overstates how many wines were never searched.

Distinguish "no reliable price found" (searched, source insufficient) from "not yet attempted — search budget exhausted" (never searched). Different facts; the note field should say which.

## Working notes

- Read `known-limits.md` before each run.
- Prefer primary sources. State uncertainty rather than guessing.
- Wine type is judgment, not lookup. Hedge conservatively (White over Orange, Red over Rose) and say so.
- After any CSV round-trip, re-apply `fillna('')` — pandas turns empty strings into NaN, which silently undercounts tagged rows. Watch `wine_type` especially: a NaN there fails the builder, which is correct but easier to fix before the build than after.
- Embedded commas in CSV note fields break `pandas.read_csv` column alignment. Fix with a post-append `csv.reader` pass detecting rows with an extra field, rejoining the overflow into column 3, then rewriting with `csv.writer`.
- Drop duplicates on lot id every time you append to the valuation store.
- Run tag calculation in the same script as price appending, so anomalies (reserves above market, implausibly wide ranges) surface before they're locked in.
- The temptation at the end of a long run is to fill a gap with a plausible-looking price. Don't. Unvalued is a legitimate outcome and the dashboard has a tab for it.

## Publishing (automatic, every run — since 2026-08-24)

This repo (`otplabs-io/agentic-auction-template`, main branch) **is** the working directory — since 2026-08-25 there is no separate copy-into-toolkit step; everything (`CLAUDE.md`, `known-limits.md`, `price_cache.csv`, `.claude/`, `toolkit/`) already lives in one clone. **As the last step of every `/execute` run**, without being asked:

1. Copy the built dashboard to `docs/index.html` (repo root — GitHub Pages' legacy build type only serves `/` or `/docs`, so this can't live under `toolkit/`). Keep `docs/robots.txt` (`User-agent: *` / `Disallow: /`) and `docs/.nojekyll` in place — recreate them if missing.
2. `git add -A && git commit -m "..." && git push origin main` — from the repo root.
3. Do **not** commit or push the raw `WineBid-Download-*.xlsx` — it's WineBid's proprietary full-catalog export, not just the user's derived analysis, and redistributing it publicly is a separate copyright/ToS question the user hasn't signed off on. Keep archiving it locally to `inbox/processed/` only (already gitignored). Flag this omission in the run report so the user can override if they actually want it pushed.

**Running from anywhere (added 2026-08-25):** this repo is fully self-sufficient — `.claude/commands/execute.md`, `.claude/settings.json`, `CLAUDE.md`, `known-limits.md`, `price_cache.csv`, and `toolkit/` all travel together in one clone. To run from any device: open a Claude Code cloud session (claude.ai/code, or `claude --cloud` from any machine's CLI) connected to this repo, attach the week's downloaded `.xlsx`, and type `/execute`. Cloud sessions load `.claude/commands/`, `.claude/settings.json`, and this file the same way a local session does. The xlsx itself is never committed — grab it fresh each week (WineBid's bot detection blocks automated download; see `known-limits.md`) and hand it to whichever session (local or cloud) is running that week.

**Exposure the user has explicitly accepted (confirmed 2026-08-24):** this repo is **public**, not private, and GitHub Pages has no login-wall on the free/pro tier — anyone with the URL can see the published dashboard regardless of repo visibility. Pushing `survivors.csv`/`valuations.csv`/`payload.json` here means the user's exact target lots, reserve prices, and market valuations sit in public commit history too, not just the one dashboard page. The user was asked directly and chose to proceed anyway ("push everything, public is fine") rather than making the repo private or holding back the data files. Do not re-litigate this each run — it's a settled, deliberate call. If a future user ever wants this walked back (private repo, or data files withheld), that's a new decision to ask about, not a default to assume.

Served at https://otplabs-io.github.io/agentic-auction-template/. The dashboard page itself still carries `noindex, nofollow, noarchive` and `docs/robots.txt` still disallows crawlers — keep both, they just mean "don't get indexed by search engines," not "don't be public." Pages caches ~10 minutes; check the masthead auction date before assuming a build failed.
