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
| `price_cache.py` | Deduplication during valuation (persistent cache present but disabled) |
| `test_price_cache.py` | 48 assertions covering key normalisation, TTL, dedupe |
| `price_cache.csv` | Empty seed for the cache. Unused while the cache is disabled |

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


## Price cache — currently disabled

Only the deduplication half of `price_cache.py` is in use. The persistent cache
is off, because the CSV would have to be committed back to this repo every week
for it to survive.

    import price_cache as pc
    plan = pc.plan(survivor_lots, {})     # empty dict: dedupe only
    print(pc.report(plan['stats']).splitlines()[0])

Dedupe collapses several lots of the same wine, vintage and size into one
lookup. It is arithmetic on the current export, so it carries no staleness risk
and needs no stored state. Passing `{}` means `price_cache.csv` is never read or
written.

`pc.report` prints a second line about cache hit rate; drop it while the cache
is off, since a permanent "0% hit rate" is noise.

**Re-enabling** is one line -- `pc.load('price_cache.csv')` instead of `{}`,
plus `pc.put`/`pc.save` as prices are found. Prices are then reused within their
TTL (60 days; 21 for `insufficient`) and cited with their fetch date via
`pc.cite(row)`, so reuse stays visible. The tradeoff is that `price_cache.csv`
must be committed after every run or the cache silently starts empty.

The key is `normalised wine | vintage | millilitres`. Normalisation folds case,
accents and punctuation but never drops words -- 'Tondonia Reserva' and
'Tondonia Gran Reserva' are different wines at different prices, and 750ml is
not a magnum. `test_price_cache.py` asserts those pairs stay distinct.

Run the tests with `python3 test_price_cache.py`.
