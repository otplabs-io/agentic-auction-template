#!/usr/bin/env python3
"""
Persistent market-price cache for the WineBid weekly run.

Two savings, both applied before any lookup happens:

  1. Deduplication -- several lots of the same wine, vintage and size need one
     price, not one price each. Free; no staleness risk.
  2. Caching -- retail averages move slowly, and the same producers recur week
     after week. A price fetched recently enough is reused instead of re-fetched.

Provenance is never lost. A reused price reports its original source plus the
date it was fetched, so a stale number is visible rather than silently assumed
current.

    import price_cache as pc
    cache   = pc.load()
    targets = pc.plan(survivors)          # dedupe + cache hits/misses
    ...fetch only targets['fetch']...
    pc.put(cache, key, price=..., source=..., source_type=...)
    pc.save(cache)
"""
import csv, os, re, unicodedata, datetime, pathlib

CACHE_PATH = os.environ.get('WINEBID_CACHE', 'price_cache.csv')

# Retail averages drift slowly; "no data" deserves a retry sooner, because an
# unlisted wine can become listed.
TTL_DAYS = 60
TTL_DAYS_UNVALUED = 21

FIELDS = ['key', 'wine_raw', 'vintage', 'format_ml', 'price',
          'source', 'source_type', 'fetched', 'hits']

# ---------------------------------------------------------------- normalizing

_SIZE_WORDS = {
    'magnum': 1500, 'double magnum': 3000, 'jeroboam': 3000, 'imperial': 6000,
    'half': 375, 'half bottle': 375, 'split': 187, 'bottle': 750,
}


def norm_format(fmt):
    """'1.5L' / '1.5 Liter' / 'Magnum' / '750ml' -> millilitres as int."""
    if fmt is None:
        return 750
    s = str(fmt).strip().lower().replace(',', '.')
    if not s:
        return 750
    for word, ml in _SIZE_WORDS.items():
        if word in s:
            return ml
    m = re.search(r'(\d+(?:\.\d+)?)\s*(ml|cl|l|liter|litre)\b', s)
    if not m:
        m2 = re.search(r'(\d+(?:\.\d+)?)', s)
        return int(round(float(m2.group(1)))) if m2 else 750
    val, unit = float(m.group(1)), m.group(2)
    if unit == 'ml':
        return int(round(val))
    if unit == 'cl':
        return int(round(val * 10))
    return int(round(val * 1000))


def norm_wine(name):
    """
    Fold case, accents and punctuation, but keep every word.

    Dropping words is what causes false matches -- 'Barolo' and 'Barolo Riserva'
    are different wines at different prices, and so are 'Castiglione' and
    'Lazzarito'. Normalising form is safe; normalising content is not.
    """
    s = unicodedata.normalize('NFD', str(name or ''))
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = s.replace('&', ' and ')
    s = re.sub(r"[^a-z0-9]+", ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def norm_vintage(v):
    if v is None:
        return 'NV'
    s = str(v).strip().upper()
    if s in ('', 'NV', 'NAN', 'NONE', 'N/V'):
        return 'NV'
    m = re.search(r'(1[89]\d{2}|20\d{2})', s)
    return m.group(1) if m else 'NV'


def make_key(wine, vintage, fmt):
    return f"{norm_wine(wine)}|{norm_vintage(vintage)}|{norm_format(fmt)}"


# ------------------------------------------------------------------ store i/o

def load(path=None):
    path = pathlib.Path(path or CACHE_PATH)
    rows = {}
    if path.exists():
        with path.open(newline='', encoding='utf-8') as f:
            for r in csv.DictReader(f):
                if r.get('key'):
                    rows[r['key']] = r
    return rows


def save(cache, path=None):
    path = pathlib.Path(path or CACHE_PATH)
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for k in sorted(cache):
            row = {fld: cache[k].get(fld, '') for fld in FIELDS}
            w.writerow(row)
    return path


def _today():
    return datetime.date.today()


def age_days(row, today=None):
    try:
        d = datetime.date.fromisoformat(str(row.get('fetched', ''))[:10])
    except Exception:
        return 10 ** 6
    return ((today or _today()) - d).days


def is_fresh(row, today=None):
    ttl = TTL_DAYS_UNVALUED if row.get('source_type') == 'insufficient' else TTL_DAYS
    return age_days(row, today) <= ttl


def get(cache, key, today=None):
    """Return a usable cache row, or None if absent or stale."""
    row = cache.get(key)
    if row and is_fresh(row, today):
        return row
    return None


def put(cache, key, price, source, source_type, wine_raw='', vintage='', format_ml='',
        today=None):
    prev = cache.get(key, {})
    cache[key] = {
        'key': key,
        'wine_raw': wine_raw or prev.get('wine_raw', ''),
        'vintage': vintage or prev.get('vintage', ''),
        'format_ml': format_ml or prev.get('format_ml', ''),
        'price': '' if price is None else price,
        'source': source,
        'source_type': source_type,
        'fetched': (today or _today()).isoformat(),
        'hits': prev.get('hits', 0),
    }
    return cache[key]


def mark_hit(cache, key):
    if key in cache:
        try:
            cache[key]['hits'] = int(cache[key].get('hits') or 0) + 1
        except (TypeError, ValueError):
            cache[key]['hits'] = 1


# -------------------------------------------------------------------- planning

def plan(lots, cache, today=None):
    """
    lots: iterable of dicts with at least wine / vintage / format, plus whatever
    lot identifier you carry (idx or id).

    Returns {'groups', 'resolved', 'fetch', 'stats'}:
      groups   key -> list of lots sharing that key
      resolved key -> cache row (reuse; do not fetch)
      fetch    list of keys still needing a lookup, in stable order
    """
    groups = {}
    for lot in lots:
        k = make_key(lot.get('wine'), lot.get('vintage'), lot.get('format'))
        groups.setdefault(k, []).append(lot)

    resolved, fetch = {}, []
    for k in groups:
        row = get(cache, k, today)
        if row:
            resolved[k] = row
            mark_hit(cache, k)
        else:
            fetch.append(k)
    fetch.sort()

    n_lots = sum(len(v) for v in groups.values())
    ages = [age_days(r, today) for r in resolved.values()]
    ages.sort()
    stats = {
        'lots': n_lots,
        'unique': len(groups),
        'dedupe_saved': n_lots - len(groups),
        'cache_hits': len(resolved),
        'to_fetch': len(fetch),
        'hit_rate': (len(resolved) / len(groups)) if groups else 0.0,
        'median_age': (ages[len(ages) // 2] if ages else None),
        'lookups_saved': (n_lots - len(fetch)),
    }
    return {'groups': groups, 'resolved': resolved, 'fetch': fetch, 'stats': stats}


def cite(row, today=None):
    """Human-readable citation that makes reuse visible."""
    src = row.get('source', '')
    a = age_days(row, today)
    if a <= 0:
        return src
    return f"{src} (cached {row.get('fetched','')[:10]}, {a}d old)"


def report(stats):
    s = stats
    line = (f"  {s['lots']} lots -> {s['unique']} unique wines "
            f"({s['dedupe_saved']} duplicate lots collapsed)\n"
            f"  cache: {s['cache_hits']} reused, {s['to_fetch']} to fetch "
            f"({s['hit_rate']:.0%} hit rate)")
    if s['median_age'] is not None:
        line += f", median age {s['median_age']}d"
    return line


if __name__ == '__main__':
    c = load()
    print(f"{CACHE_PATH}: {len(c)} entries")
    if c:
        fresh = sum(1 for r in c.values() if is_fresh(r))
        print(f"  {fresh} fresh, {len(c)-fresh} stale")
