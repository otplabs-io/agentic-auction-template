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
  1. Producer + cuvee match -- you've rated THIS SPECIFIC BOTTLING (not just
     the producer) >=90 avg, or own >=2 bottles of it, or own it and it
     averages >=93 CScore.
  2. Region match     -- you've rated >=2 wines from the same region/subregion
     averaging >=92.
  3. Varietal match   -- the varietal name appears in the wine's name, and
     you've rated >=3 wines of that varietal averaging >=92.

Matching is deliberately conservative (minimum sample sizes, exact producer-
name-as-prefix matching, and -- critically -- a cuvee-identity check, not
just a producer-name match) -- a missed star is a minor annoyance, a false
one undermines the whole feature. See known-limits.md for the matching
caveats, including the 2026-09-24 incident this cuvee check was added for:
producer-only matching starred "Bibi Graetz/Testamatta Grilli Del Testamatta"
(a ~$25, poorly-rated bottling) off a 93-point tasting note for Bibi Graetz's
actual flagship "Testamatta" -- a different wine that merely shares a name.
The same bug also matched Casanova di Neri's plain Brunello off a Tenuta
Nuova (single-vineyard) rating, Beaucastel's red off a Beaucastel Blanc
tasting note, and others -- roughly half of the producer-based stars in that
run were wrong once checked. A producer match now only counts a rated or
owned bottle whose OWN cuvee name (the wine's name minus the producer
prefix) is the same wine, not just the same house.

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


# Generic legal/appellation-designation boilerplate that carries no cuvee-
# identity information, so it's ignored when deciding whether two wines from
# the same producer are actually the same bottling. Deliberately does NOT
# include words that distinguish a tier or a specific vineyard/cru (riserva,
# gran, reserva, 1er, cru, grand, blanc, rosso, bianco...) -- those are
# exactly the words that need to cause a mismatch, e.g. Beaucastel's red vs.
# Beaucastel "Blanc" is white and Sangiovese Grosso red are two different
# products.
CUVEE_FILLER = {'igt', 'igp', 'doc', 'docg', 'doca', 'vdt', 'vino', 'da', 'tavola', 'di', 'de', 'del', 'della'}


def cuvee_tokens(wine_norm, producer_key):
    """The wine's name minus its producer prefix, as a filtered token set --
    what actually identifies WHICH bottling this is, not just which house."""
    rest = wine_norm[len(producer_key):].strip() if wine_norm.startswith(producer_key) else wine_norm
    return {t for t in rest.split() if t not in CUVEE_FILLER}


def region_words_of(locale_or_path):
    """Normalized single-word tokens from a region string/path, e.g. Toscana
    IGT's ["Italy","Tuscany","Toscana IGT"] -> {italy,tuscany,toscana,igt}."""
    parts = locale_or_path if isinstance(locale_or_path, list) else region_parts(locale_or_path)
    words = set()
    for p in parts:
        words.update(norm(p).split())
    return words


def same_cuvee(a, a_region_words, b, b_region_words):
    """True only when neither side names something the other doesn't -- so a
    plain base wine matches a plain base wine, and a named single-vineyard/
    second-wine/different-color bottling does NOT silently stand in for it in
    either direction. Word order doesn't matter (CellarTracker and WineBid
    export the same wine's name in different orders often enough that this
    has to be a set comparison, not a string comparison).

    A word that's extra on one side is forgiven if it's just that side's own
    region/appellation boilerplate (e.g. "Toscana" from a Toscana IGT wine,
    or "Chateauneuf"/"du"/"Pape" when CellarTracker's own Locale already
    files the wine under a 4-level "...,Southern Rhone,Chateauneuf-du-Pape"
    path). Forgiving it via each side's OWN region words in the *difference*
    -- not by stripping region words out of both token sets up front -- is
    what keeps this from over-forgiving: subtracting from both sets first
    quietly zeroed out an entire cuvee name when only ONE side's metadata
    happened to also list it as a region level, breaking otherwise-identical
    matches (Clos des Papes' and Domaine de la Janasse's plain Chateauneuf-
    du-Pape bottlings, caught while fixing the Toscana case above)."""
    extra_a = (a - b) - a_region_words
    extra_b = (b - a) - b_region_words
    return not extra_a and not extra_b


def load_rows(path):
    with open(path, encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def region_parts(locale):
    return [p.strip() for p in (locale or '').split(',')]


def build_profile():
    """Index producer items individually (not pre-aggregated -- aggregating
    before matching is exactly what let a Tenuta Nuova rating get applied to
    a plain Brunello); aggregate region / varietal stats as before, since
    those don't carry a cuvee-identity claim in the same way."""
    producer = defaultdict(list)   # producer_key -> [{'tokens','rating','cscore','is_cellar','display'}]
    region = defaultdict(lambda: {'ratings': [], 'display': ''})
    varietal = defaultdict(lambda: {'ratings': [], 'display': ''})

    cellar = load_rows(f'{PREF_DIR}/cellar.csv')
    notes = load_rows(f'{PREF_DIR}/tasting_notes.csv')

    for r in cellar:
        p = r.get('Producer', '').strip()
        wine = r.get('Wine', '').strip()
        if p and wine:
            key = norm(p)
            cs = None
            if r.get('CScore', ''):
                try:
                    cs = float(r['CScore'])
                except ValueError:
                    pass
            producer[key].append({
                'tokens': cuvee_tokens(norm(wine), key), 'region_words': region_words_of(r.get('Locale', '')),
                'rating': None, 'cscore': cs, 'is_cellar': True, 'display': wine,
            })
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
        wine = r.get('Wine', '').strip()
        if p and wine:
            key = norm(p)
            producer[key].append({
                'tokens': cuvee_tokens(norm(wine), key), 'region_words': region_words_of(r.get('Locale', '')),
                'rating': rating, 'cscore': None, 'is_cellar': False, 'display': wine,
            })
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


def match_producer(wine_norm, region_path, producer, producer_keys):
    """Find the producer, then keep only the items that are the SAME cuvee as
    this deal -- not just the same producer. Returns None if the producer
    matches but every rated/owned bottling on file is a different, more (or
    less) specific wine (different vineyard, different color, a Riserva
    standing in for a base wine, etc.)."""
    deal_region_words = region_words_of(region_path or [])
    for key in producer_keys:
        if len(key) < 6:
            continue
        if wine_norm.startswith(key):
            deal_tokens = cuvee_tokens(wine_norm, key)
            items = [it for it in producer[key]
                     if same_cuvee(deal_tokens, deal_region_words, it['tokens'], it['region_words'])]
            if items:
                return key, items
            return key, None  # producer matched, but no item is the same wine
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

    pkey, items = match_producer(wn, region_path, producer, producer_keys)
    if items:
        display = items[0]['display']
        ratings = [it['rating'] for it in items if it['rating'] is not None]
        cscores = [it['cscore'] for it in items if it['cscore'] is not None]
        n_cellar = sum(1 for it in items if it['is_cellar'])
        if len(ratings) >= 1 and avg(ratings) >= 90:
            return True, f"You've rated {display} {len(ratings)}x averaging {avg(ratings):.0f}/100"
        if not ratings and n_cellar >= 2:
            return True, f"You own {n_cellar} bottles of {display} in your cellar"
        if not ratings and n_cellar >= 1 and avg(cscores) is not None and avg(cscores) >= 93:
            return True, f"{display} averages {avg(cscores):.1f}/100 and you already collect it"

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
