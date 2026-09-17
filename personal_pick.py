#!/usr/bin/env python3
"""
Step 6 -- Personalized picks.

Marks payload.json deals and unvalued lots with a star (`personal_pick`)
when they match the user's own taste history, read from two durable
reference files:

    preferences/cellar.csv          -- CellarTracker "My Cellar" export
    preferences/tasting_notes.csv   -- CellarTracker "My Tasting Notes" export

These are NOT per-week scratch -- they persist like price_cache.csv and get
refreshed by dropping a newer export in preferences/ (see CLAUDE.md Step 6).

Three independent signals, any one of which stars a lot:
  1. Producer match  -- you've rated this producer >=90 avg (>=1 tasting), or
     you own >=2 bottles of it, or you own it and it averages >=93 CScore.
  2. Region match     -- you've rated >=2 wines from the same region/subregion
     averaging >=92.
  3. Varietal match   -- the varietal name appears in the wine's name, and
     you've rated >=3 wines of that varietal averaging >=92.

Matching is deliberately conservative (minimum sample sizes, exact producer-
name-as-prefix matching) -- a missed star is a minor annoyance, a false one
undermines the whole feature. See known-limits.md for the matching caveats.

    python3 personal_pick.py payload.json
"""
import csv, json, re, sys, unicodedata
from collections import defaultdict

PREF_DIR = 'preferences'


def norm(s):
    if not s:
        return ''
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = s.lower()
    s = re.sub(r"[^\w\s]", ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def norm_region(s):
    s = norm(s)
    s = re.sub(r'\bvalley\b', '', s).strip()
    return s


def load_rows(path):
    with open(path, encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def region_parts(locale):
    return [p.strip() for p in (locale or '').split(',')]


def build_profile():
    """Aggregate producer / region / varietal stats from both reference files."""
    producer = defaultdict(lambda: {'ratings': [], 'cscores': [], 'n_cellar': 0, 'display': ''})
    region = defaultdict(lambda: {'ratings': [], 'display': ''})
    varietal = defaultdict(lambda: {'ratings': [], 'display': ''})

    cellar = load_rows(f'{PREF_DIR}/cellar.csv')
    notes = load_rows(f'{PREF_DIR}/tasting_notes.csv')

    for r in cellar:
        p = r.get('Producer', '').strip()
        if p:
            key = norm(p)
            producer[key]['n_cellar'] += 1
            producer[key]['display'] = p
            cs = r.get('CScore', '')
            if cs:
                try:
                    producer[key]['cscores'].append(float(cs))
                except ValueError:
                    pass
        rp = region_parts(r.get('Locale', ''))
        if len(rp) >= 2:
            rkey = (norm_region(rp[0]), norm_region(rp[1]), norm_region(rp[2]) if len(rp) > 2 else '')
            region[rkey]['display'] = ' > '.join(x for x in rp[:3] if x)

    for r in notes:
        if r.get('Defective') == 'True':
            continue  # a corked/defective bottle says nothing about taste
        rating = r.get('Rating', '')
        try:
            rating = float(rating)
        except ValueError:
            continue
        if rating <= 0:
            continue
        p = r.get('Producer', '').strip()
        if p:
            key = norm(p)
            producer[key]['ratings'].append(rating)
            producer[key]['display'] = producer[key]['display'] or p
        rp = region_parts(r.get('Locale', ''))
        if len(rp) >= 3:
            # Appellation-level only (country, region, subregion) -- "France >
            # Burgundy" alone matched nearly everything on a first pass, since
            # this user's tastings skew toward exactly the countries/regions
            # this auction already screens to. A bare region match isn't a
            # personalization signal here; it's just "wine this auction kept."
            rkey = (norm_region(rp[0]), norm_region(rp[1]), norm_region(rp[2]))
            region[rkey]['ratings'].append(rating)
            region[rkey]['display'] = region[rkey]['display'] or ' > '.join(x for x in rp[:3] if x)
        v = r.get('Varietal', '').strip()
        if v:
            vkey = norm(v)
            varietal[vkey]['ratings'].append(rating)
            varietal[vkey]['display'] = varietal[vkey]['display'] or v

    # sort producer keys longest-first so a specific producer name is tried
    # before a shorter one that happens to be its own substring/prefix
    producer_keys = sorted(producer.keys(), key=len, reverse=True)
    varietal_keys = sorted(varietal.keys(), key=len, reverse=True)
    return producer, producer_keys, region, varietal, varietal_keys


def avg(xs):
    return sum(xs) / len(xs) if xs else None


def match_producer(wine_norm, producer, producer_keys):
    for key in producer_keys:
        if len(key) < 6:
            continue
        if wine_norm.startswith(key):
            return key, producer[key]
    return None, None


def match_region(region_path, region):
    parts = [norm_region(x) for x in (region_path or [])]
    if len(parts) < 3:
        return None, None
    key = (parts[0], parts[1], parts[2])
    if key in region and region[key]['ratings']:
        return key, region[key]
    return None, None


def match_varietal(wine_norm, varietal, varietal_keys):
    for key in varietal_keys:
        if len(key) < 4:
            continue
        if re.search(r'\b' + re.escape(key) + r'\b', wine_norm):
            return key, varietal[key]
    return None, None


def score(wine, region_path, producer, producer_keys, region, varietal, varietal_keys):
    wn = norm(wine)

    pkey, pstat = match_producer(wn, producer, producer_keys)
    if pstat:
        r = pstat['ratings']
        if len(r) >= 1 and avg(r) >= 90:
            return True, f"You've rated {pstat['display']} {len(r)}x averaging {avg(r):.0f}/100"
        if not r and pstat['n_cellar'] >= 2:
            return True, f"You own {pstat['n_cellar']} bottles of {pstat['display']} in your cellar"
        if not r and pstat['n_cellar'] >= 1 and avg(pstat['cscores']) is not None and avg(pstat['cscores']) >= 93:
            return True, f"{pstat['display']} averages {avg(pstat['cscores']):.1f}/100 and you already collect it"

    rkey, rstat = match_region(region_path, region)
    if rstat:
        r = rstat['ratings']
        if len(r) >= 2 and avg(r) >= 93:
            return True, f"Your {rstat['display']} wines have averaged {avg(r):.0f}/100 across {len(r)} tastings"

    vkey, vstat = match_varietal(wn, varietal, varietal_keys)
    if vstat:
        r = vstat['ratings']
        if len(r) >= 3 and avg(r) >= 92:
            return True, f"Your {vstat['display']} wines have averaged {avg(r):.0f}/100 across {len(r)} tastings"

    return False, ''


def main():
    if len(sys.argv) != 2:
        print('usage: python3 personal_pick.py payload.json', file=sys.stderr)
        sys.exit(1)
    path = sys.argv[1]
    p = json.loads(open(path, encoding='utf-8').read())

    producer, producer_keys, region, varietal, varietal_keys = build_profile()

    n_starred = 0
    for bucket in ('deals', 'unvalued'):
        for r in p.get(bucket, []):
            starred, reason = score(r['wine'], r.get('region_path'), producer, producer_keys, region, varietal, varietal_keys)
            r['personal_pick'] = starred
            r['pick_reason'] = reason
            if starred:
                n_starred += 1

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(p, f, indent=1, ensure_ascii=False)
    total = len(p.get('deals', [])) + len(p.get('unvalued', []))
    print(f"personal_pick: {n_starred} of {total} lots starred "
          f"({len(p.get('deals', []))} deals, {len(p.get('unvalued', []))} unvalued)")


if __name__ == '__main__':
    main()
