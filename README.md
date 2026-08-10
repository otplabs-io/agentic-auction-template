# WineBid dashboard builder

Weekly use:

    python3 build_dashboard.py payload.json

Writes `/mnt/user-data/outputs/WineBid_Deals_<auction_date>.html` — one
self-contained file. Override with `-o path.html`.

## Files

| File | Purpose |
|---|---|
| `build_dashboard.py` | Validates the payload, injects everything, writes the HTML |
| `template.html` | Structure + styles. Placeholders: `__PAYLOAD__` `__APP__` `__FONT__` `__TITLE__` |
| `app.js` | Filtering, sorting, search, watchlist, CSV, URL state |
| `flags_b64.txt` | Noto Color Emoji subset (AT/ES/FR/IT/PT), base64 woff2, OFL 1.1 |
| `flags.woff2` | Same font, unencoded, kept for regeneration |
| `test.js` | 63 headless assertions (`npm install jsdom` first, then `node test.js <built.html>`) |
| `sample_payload.json` | Synthetic data for layout work — invented prices, `"sample": true` |
| `mksample.py` | Regenerates the synthetic payload |
| `price_cache.py` | Dedupe + persistent market-price cache used during valuation |
| `test_price_cache.py` | 48 assertions covering key normalisation, TTL, dedupe |
| `price_cache.csv` | The accumulated cache. Grows weekly; commit it back each run |

## Schema 2 — the buyer's premium

`pct_below` is measured on `buyer_price` (reserve + 17% premium), not on the
reserve, because the premium is what you actually pay. `premium_rate` lives in
the payload, so changing the rate is a data edit, not a code edit.

Schema 1 payloads are rejected rather than reinterpreted: the field name
`pct_below` is the same but the number means something different, and silently
re-reading an old file would overstate every discount.

## The validator refuses to build on

- `schema` != 2, missing required fields, duplicate item IDs
- a reserve over $150, a `pct_below` under 25%
- `buyer_price` that isn't `reserve x (1 + premium_rate)`
- `pct_below` that disagrees with `(market - buyer_price) / market` by more than 0.5pt
- a `tag` that disagrees with the tier thresholds
- a blank `source`, or a `source_type` outside the enum

A bad payload fails loudly and writes nothing rather than rendering a page
with wrong numbers on it.

## Regenerating the flag font

Only needed if the country list changes.

    pip install fonttools brotli
    curl -sLO https://raw.githubusercontent.com/googlefonts/noto-emoji/main/fonts/NotoColorEmoji.ttf
    # find the ligature glyph names for the regional-indicator pairs you need,
    # then subset by glyph name with --no-layout-closure, keeping ccmp,liga,rlig
    base64 -w0 flags.woff2 > flags_b64.txt

Verify by extracting the CBDT bitmaps and looking at them — a silently dropped
glyph looks identical to a CSS problem otherwise.


## Price cache

Valuation reuses recent prices instead of re-fetching every wine every week.

    import price_cache as pc
    cache = pc.load()                       # price_cache.csv
    plan  = pc.plan(survivor_lots, cache)   # dedupe + hit/miss split
    print(pc.report(plan['stats']))
    # ...look up only plan['fetch']...
    pc.put(cache, key, price, source, source_type)
    pc.save(cache)

Two independent savings. **Dedupe** collapses several lots of the same wine,
vintage and size into one lookup -- free, no staleness risk. **Caching** reuses
a price fetched within its TTL: 60 days for a real price, 21 for
`insufficient`, because an unlisted wine can become listed.

The key is `normalised wine | vintage | millilitres`. Normalisation folds case,
accents and punctuation but never drops words -- 'Tondonia Reserva' and
'Tondonia Gran Reserva' are different wines at different prices, and 750ml is
not a magnum. `test_price_cache.py` asserts those pairs stay distinct.

Reuse stays visible: `pc.cite(row)` renders
`Wine-Searcher average retail, vintage-specific (cached 2026-07-14, 27d old)`,
so a stale number is legible in the dashboard rather than silently assumed
current.

Run the tests with `python3 test_price_cache.py`.
