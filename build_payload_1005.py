import csv, json, re

AUCTION_DATE = "2026-10-11"
PREMIUM = 0.17

survivors = list(csv.DictReader(open('survivors.csv', newline='', encoding='utf-8')))
valuations = list(csv.DictReader(open('valuations.csv', newline='', encoding='utf-8')))
val_by_id = {}
for r in valuations:
    val_by_id[r['id']] = r

COUNTRY_CODE = {'France':'FR','Italy':'IT','Spain':'ES','Portugal':'PT','Austria':'AT'}

deals = []
unvalued = []
n_valued = 0
n_est = 0
n_unvalued = 0

for s in survivors:
    sid = s['id']
    wine = s['wine']
    vintage_raw = s['vintage']
    vintage = None if str(vintage_raw).strip().upper() in ('NV','', 'NAN') else int(float(vintage_raw))
    fmt = s['format']
    region_raw = s['Region']
    region_path = [p.strip() for p in region_raw.split(',')]
    country_code = s.get('country_code') or COUNTRY_CODE.get(region_path[0], '')
    wine_type = s['wine_type']
    qty = s['Quantity']
    reserve = float(s['Reserve'])
    condition = s.get('Condition Issue') or ''
    buyer_price = round(reserve * (1 + PREMIUM), 2)

    v = val_by_id.get(sid)
    if v is None:
        unvalued.append({
            "id": int(sid), "wine": wine, "vintage": vintage, "format": fmt,
            "region_raw": region_raw, "region_path": region_path,
            "country_code": country_code, "wine_type": wine_type,
            "reserve": reserve, "condition": condition,
            "note": "not yet attempted -- search budget exhausted this session"
        })
        n_unvalued += 1
        continue

    market_raw = v.get('market', '')
    if market_raw in (None, ''):
        unvalued.append({
            "id": int(sid), "wine": wine, "vintage": vintage, "format": fmt,
            "region_raw": region_raw, "region_path": region_path,
            "country_code": country_code, "wine_type": wine_type,
            "reserve": reserve, "condition": condition,
            "note": "no reliable price found -- searched (single-pass query), no vintage-specific USD retail price; stage 2 not run"
        })
        n_unvalued += 1
        continue

    market = float(market_raw)
    n_valued += 1
    if v.get('source_type')=='estimate': n_est += 1
    pct_below = round((market - buyer_price) / market, 4)
    if pct_below < 0.25:
        continue
    tag = 'Steal' if pct_below >= 0.5500 else 'Great' if pct_below >= 0.4000 else 'Good'
    deals.append({
        "id": int(sid), "wine": wine, "vintage": vintage, "format": fmt,
        "region_raw": region_raw, "region_path": region_path,
        "country_code": country_code, "wine_type": wine_type,
        "qty": int(float(qty)) if qty not in (None, '') else 1,
        "reserve": reserve, "buyer_price": buyer_price, "market": market,
        "pct_below": round(pct_below, 4), "tag": tag, "flag": "",
        "condition": condition,
        "source": v.get('source',''), "source_type": v.get('source_type','')
    })

payload = {
    "schema": 4,
    "auction_date": AUCTION_DATE,
    "premium_rate": PREMIUM,
    "generated": "2026-10-05T00:00:00Z",
    "funnel": {
        "total": 1976, "after_country": 849, "after_dessert": 771,
        "after_price": 536, "after_condition": 508,
        "valued": n_valued, "unvalued": n_unvalued, "deals": len(deals),
        "estimated_lots": n_est, "estimated_deals": sum(1 for d in deals if d["source_type"]=="estimate")
    },
    "deals": deals,
    "unvalued": unvalued
}

json.dump(payload, open('payload.json', 'w'), ensure_ascii=False, indent=1)
print(f"survivors={len(survivors)} valued={n_valued} unvalued={n_unvalued} deals={len(deals)}")
never_attempted = sum(1 for u in unvalued if 'budget exhausted' in u['note'])
no_price = sum(1 for u in unvalued if u['note'].startswith('no reliable price'))
print(f"unvalued breakdown: never_attempted={never_attempted} no_reliable_price={no_price}")
