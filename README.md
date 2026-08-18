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
| `test.js` | 88 headless assertions (`npm install jsdom` first, then `node test.js <built.html>`) |
| `sample_payload.json` | Synthetic data for layout work — invented prices, `"sample": true` |
| `mksample.py` | Regenerates the synthetic payload |
| `price_cache.py` | Deduplication during valuation (persistent cache present but disabled) |
| `test_price_cache.py` | 48 assertions covering key normalisation, TTL, dedupe |
| `price_cache.csv` | Empty seed for the cache. Unused while the cache is disabled |

## Schema 3 — wine type

Every lot carries `wine_type`: one of `Red`, `White`, `Rose`, `Sparkling`,
`Dessert`, `Orange`. It is a judgment call, not a column in the WineBid export
— the export has no such field — so it is made upstream, per lot, from the
producer, appellation and cuvée name.

It is **required**, on valued and unvalued lots alike. A type is derived from
the wine's name, not from its price, so a lot with no market price has no
excuse for having no type. Making it optional would let a week where the
classification was skipped ship a column of blanks that looks like data.

`Rose` is stored unaccented so it survives a URL hash and a CSV round-trip
intact; the dashboard renders it as *Rosé*.

The dashboard shows it as a colour swatch beside the country flag, with the
type name on hover and as the screen-reader label:

| Type | Swatch | Hex |
|---|---|---|
| Red | burgundy | `#6B1B2E` |
| White | cream | `#EFE0B0` |
| Rosé | pink | `#F2A5B6` |
| Sparkling | white | `#FFFFFF` |
| Dessert | brown | `#7A4A21` |
| Orange | orange | `#E08A2E` |

Cream and white would read as an empty cell against a white row, so both carry
a darker ring. The column sorts in shelf order — Red, Rosé, Orange, White,
Sparkling, Dessert — rather than alphabetically, and the filter rail lists the
types in that same order with a swatch beside each name.

Dessert is a legal value even though dessert wines are screened out upstream:
the screen is heuristic, and a survivor that turns out to be dessert should be
visible as one rather than mislabelled.

Schema 2 payloads are rejected rather than defaulted, for the same reason
blanks are: a missing type is a gap in the work, not a rendering problem.

## Schema 2 — the buyer's premium

`pct_below` is measured on `buyer_price` (reserve + 17% premium), not on the
reserve, because the premium is what you actually pay. `premium_rate` lives in
the payload, so changing the rate is a data edit, not a code edit.

Schema 1 payloads are rejected rather than reinterpreted: the field name
`pct_below` is the same but the number means something different, and silently
re-reading an old file would overstate every discount.

## The validator refuses to build on

- `schema` != 3, missing required fields, duplicate item IDs
- a `wine_type` outside the six allowed values, on a valued or unvalued lot
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
