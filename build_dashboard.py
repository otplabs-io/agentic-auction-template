#!/usr/bin/env python3
"""
Build the WineBid dashboard: one self-contained HTML file.

Schema 2: pct_below is measured on buyer_price (reserve + buyer's premium),
not on the reserve. A v1 payload will be rejected rather than silently
reinterpreted, because the same field name means a different number.

    python3 build_dashboard.py payload.json [-o output.html]

Reads a schema-1 payload, injects it plus the app JS and the flag font subset
into template.html, and writes a single file. Validates the payload first --
a malformed payload should fail here, loudly, rather than render a broken page.
"""
import json, sys, argparse, datetime, pathlib

HERE = pathlib.Path(__file__).resolve().parent

DEAL_REQ = ['id','wine','vintage','format','region_path','country_code',
            'reserve','buyer_price','market','pct_below','tag','source','source_type']
UNVAL_REQ = ['id','wine','vintage','format','region_path','country_code','reserve']
TAGS = {'Good','Great','Steal'}
SRC_TYPES = {'ws_vintage','ws_adjacent','ws_allvintage','ws_single_retailer','auction','estimate'}


def validate(p):
    errs, warns = [], []
    if p.get('schema') != 2:
        errs.append(f"schema must be 2, got {p.get('schema')!r} "
                    f"(v1 measured pct_below on the reserve, not the buyer price)")
    rate = p.get('premium_rate')
    if not isinstance(rate, (int, float)) or not (0 <= rate < 1):
        errs.append(f"premium_rate must be a fraction such as 0.17, got {rate!r}")
        rate = 0.17
    if not p.get('auction_date'):
        warns.append("no auction_date -- the header and CSV filename will be vague")

    for i, r in enumerate(p.get('deals', [])):
        where = f"deals[{i}] (id={r.get('id')})"
        for k in DEAL_REQ:
            if k not in r:
                errs.append(f"{where}: missing {k}")
        if r.get('tag') not in TAGS:
            errs.append(f"{where}: tag {r.get('tag')!r} not in {sorted(TAGS)}")
        if r.get('source_type') not in SRC_TYPES:
            errs.append(f"{where}: source_type {r.get('source_type')!r} not recognised")
        rp = r.get('region_path')
        if not isinstance(rp, list) or not rp:
            errs.append(f"{where}: region_path must be a non-empty list")
        res, buy = r.get('reserve'), r.get('buyer_price')
        mkt, pb = r.get('market'), r.get('pct_below')
        if isinstance(res, (int, float)) and res > 150:
            errs.append(f"{where}: reserve {res} exceeds the $150 cap")
        if all(isinstance(x, (int, float)) for x in (res, buy)):
            expect = res * (1 + rate)
            if abs(expect - buy) > 0.01:
                errs.append(f"{where}: buyer_price {buy} != reserve {res} "
                            f"+ {rate:.0%} premium ({expect:.2f})")
        if all(isinstance(x, (int, float)) for x in (buy, mkt, pb)) and mkt:
            calc = (mkt - buy) / mkt
            if abs(calc - pb) > 0.005:
                errs.append(f"{where}: pct_below {pb:.4f} != computed {calc:.4f} "
                            f"(must be measured on buyer_price, not reserve)")
            if pb < 0.25:
                errs.append(f"{where}: pct_below {pb:.3f} is under the 25% cutoff")
            tier = 'Steal' if pb >= 0.55 else 'Great' if pb >= 0.40 else 'Good'
            if r.get('tag') != tier:
                errs.append(f"{where}: tag {r.get('tag')!r} should be {tier!r} at {pb:.1%}")
        if not str(r.get('source', '')).strip():
            errs.append(f"{where}: source is blank -- every price must name its origin")

    for i, r in enumerate(p.get('unvalued', [])):
        for k in UNVAL_REQ:
            if k not in r:
                errs.append(f"unvalued[{i}] (id={r.get('id')}): missing {k}")

    ids = [r['id'] for r in p.get('deals', []) + p.get('unvalued', []) if 'id' in r]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        errs.append(f"duplicate item ids: {sorted(dupes)}")
    return errs, warns


def build(payload_path, out_path):
    p = json.loads(pathlib.Path(payload_path).read_text())
    errs, warns = validate(p)
    for w in warns:
        print(f"  warn: {w}")
    if errs:
        print(f"\n{len(errs)} problem(s) -- nothing written:\n", file=sys.stderr)
        for e in errs[:40]:
            print(f"  {e}", file=sys.stderr)
        if len(errs) > 40:
            print(f"  ... and {len(errs)-40} more", file=sys.stderr)
        sys.exit(1)

    p.setdefault('generated', datetime.datetime.now(datetime.timezone.utc)
                 .replace(microsecond=0).isoformat().replace('+00:00', 'Z'))

    html = (HERE / 'template.html').read_text()
    app = (HERE / 'app.js').read_text()
    font = (HERE / 'flags_b64.txt').read_text().strip()

    # </script> inside the JSON island would close the tag early
    data = json.dumps(p, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')

    html = html.replace('__TITLE__', 'WineBid Deals')
    html = html.replace('__FONT__', font)
    html = html.replace('__PAYLOAD__', data)
    html = html.replace('__APP__', app)

    out = pathlib.Path(out_path)
    out.write_text(html, encoding='utf-8')
    kb = out.stat().st_size / 1024
    print(f"  {out}  ({kb:.0f} KB, {len(p.get('deals',[]))} deals, "
          f"{len(p.get('unvalued',[]))} unvalued)")
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('payload')
    ap.add_argument('-o', '--out', default=None)
    a = ap.parse_args()
    p = json.loads(pathlib.Path(a.payload).read_text())
    default = f"/mnt/user-data/outputs/WineBid_Deals_{p.get('auction_date','undated')}.html"
    build(a.payload, a.out or default)
