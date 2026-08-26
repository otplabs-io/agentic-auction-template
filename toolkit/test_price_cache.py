#!/usr/bin/env python3
"""Tests for price_cache. Run: python3 test_price_cache.py"""
import datetime, os, tempfile, sys
import price_cache as pc

P = F = 0
def ok(name, cond, detail=''):
    global P, F
    if cond:
        P += 1; print(f"  PASS  {name}")
    else:
        F += 1; print(f"  FAIL  {name}" + (f"  -> {detail}" if detail else ''))

TODAY = datetime.date(2026, 8, 10)

print("\n— format normalisation —")
for raw, ml in [('750ml',750), ('750 ml',750), ('1.5L',1500), ('1.5 L',1500),
                ('1.5 Liter',1500), ('375ml',375), ('3.0L',3000), ('Magnum',1500),
                ('Half Bottle',375), ('', 750), (None,750), ('37.5cl',375)]:
    ok(f"{raw!r} -> {ml}ml", pc.norm_format(raw) == ml, str(pc.norm_format(raw)))

print("\n— wine-name folding —")
ok("accents fold", pc.norm_wine('Château Gloria') == pc.norm_wine('Chateau Gloria'))
ok("case folds", pc.norm_wine('DOMAINE HUET') == pc.norm_wine('domaine huet'))
ok("punctuation folds",
   pc.norm_wine("Jean-Louis Chave, St. Joseph") == pc.norm_wine("Jean Louis Chave St Joseph"))
ok("ampersand folds", pc.norm_wine('Brune & Blonde') == pc.norm_wine('Brune and Blonde'))
ok("whitespace collapses", pc.norm_wine('Vietti   Barolo ') == 'vietti barolo')

print("\n— names that must NOT collide —")
pairs = [
    ('Vietti Barolo Castiglione', 'Vietti Barolo Lazzarito'),
    ('Produttori del Barbaresco Barbaresco', 'Produttori del Barbaresco Barbaresco Riserva Asili'),
    ('Domaine Huet Vouvray Le Mont Sec', 'Domaine Huet Vouvray Le Haut Lieu Sec'),
    ('Guigal Cote-Rotie Brune et Blonde', 'Guigal Cote-Rotie La Mouline'),
    ('Il Poggione Rosso di Montalcino', 'Il Poggione Brunello di Montalcino'),
    ('Chateau Gloria', 'Chateau Gloria Second Wine'),
    ('Lopez de Heredia Tondonia Reserva', 'Lopez de Heredia Tondonia Gran Reserva'),
]
for a, b in pairs:
    ok(f"{a[:34]}… vs {b[:34]}…", pc.norm_wine(a) != pc.norm_wine(b))

print("\n— key composition —")
ok("vintage separates", pc.make_key('X', 2019, '750ml') != pc.make_key('X', 2018, '750ml'))
ok("format separates", pc.make_key('X', 2019, '750ml') != pc.make_key('X', 2019, '1.5L'))
ok("NV normalises", pc.make_key('X', None, '750ml') == pc.make_key('X', 'NV', '750ml'))
ok("float vintage from pandas", pc.norm_vintage(2019.0) == '2019', pc.norm_vintage(2019.0))
ok("nan vintage", pc.norm_vintage(float('nan')) == 'NV')
ok("equivalent spellings share a key",
   pc.make_key('Château Gloria', 2016, '750 ml') == pc.make_key('Chateau Gloria', '2016', '750ml'))

print("\n— TTL —")
cache = {}
k = pc.make_key('Vietti Barolo Castiglione', 2018, '750ml')
pc.put(cache, k, 92.0, 'Wine-Searcher average retail, vintage-specific', 'ws_vintage',
       today=TODAY - datetime.timedelta(days=30))
ok("30d-old price is fresh", pc.get(cache, k, TODAY) is not None)
pc.put(cache, k, 92.0, 'Wine-Searcher average retail, vintage-specific', 'ws_vintage',
       today=TODAY - datetime.timedelta(days=75))
ok("75d-old price is stale", pc.get(cache, k, TODAY) is None)

ku = pc.make_key('Obscure Cuvee', 1978, '750ml')
pc.put(cache, ku, None, 'Insufficient data', 'insufficient',
       today=TODAY - datetime.timedelta(days=15))
ok("15d-old 'insufficient' still held", pc.get(cache, ku, TODAY) is not None)
pc.put(cache, ku, None, 'Insufficient data', 'insufficient',
       today=TODAY - datetime.timedelta(days=30))
ok("30d-old 'insufficient' retried (shorter TTL)", pc.get(cache, ku, TODAY) is None)

print("\n— dedupe + planning —")
lots = [
    {'idx': 1, 'wine': 'Vietti Barolo Castiglione', 'vintage': 2018, 'format': '750ml'},
    {'idx': 2, 'wine': 'Vietti Barolo Castiglione', 'vintage': 2018, 'format': '750ml'},
    {'idx': 3, 'wine': 'Vietti Barolo Castiglione', 'vintage': 2018, 'format': '1.5L'},
    {'idx': 4, 'wine': 'Château Gloria',            'vintage': 2016, 'format': '750ml'},
    {'idx': 5, 'wine': 'Chateau Gloria',            'vintage': 2016, 'format': '750 ml'},
    {'idx': 6, 'wine': 'Massolino Barolo',          'vintage': 2017, 'format': '750ml'},
]
fresh = {}
pc.put(fresh, pc.make_key('Massolino Barolo', 2017, '750ml'), 88.0,
       'Wine-Searcher average retail, vintage-specific', 'ws_vintage',
       today=TODAY - datetime.timedelta(days=10))
plan = pc.plan(lots, fresh, TODAY)
s = plan['stats']
ok("6 lots collapse to 4 unique wines", s['unique'] == 4, str(s['unique']))
ok("duplicate lots counted", s['dedupe_saved'] == 2, str(s['dedupe_saved']))
ok("accent variants grouped together",
   len(plan['groups'][pc.make_key('Chateau Gloria', 2016, '750ml')]) == 2)
ok("magnum kept separate from 750ml",
   pc.make_key('Vietti Barolo Castiglione', 2018, '1.5L') in plan['groups'])
ok("cached wine resolved, not fetched", s['cache_hits'] == 1 and s['to_fetch'] == 3,
   f"hits={s['cache_hits']} fetch={s['to_fetch']}")
ok("lookups saved reported", s['lookups_saved'] == 3, str(s['lookups_saved']))
ok("hit counter incremented",
   int(fresh[pc.make_key('Massolino Barolo', 2017, '750ml')]['hits']) == 1)

print("\n— citation makes reuse visible —")
row = fresh[pc.make_key('Massolino Barolo', 2017, '750ml')]
c = pc.cite(row, TODAY)
ok("citation names age", 'cached' in c and '10d' in c, c)
ok("citation keeps original source", 'Wine-Searcher' in c, c)
fresh_row = dict(row); fresh_row['fetched'] = TODAY.isoformat()
ok("same-day price cites plainly", 'cached' not in pc.cite(fresh_row, TODAY))

print("\n— round-trip —")
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, 'price_cache.csv')
    pc.save(fresh, p)
    back = pc.load(p)
    ok("saved and reloaded", set(back) == set(fresh))
    ok("price survives round-trip",
       float(back[pc.make_key('Massolino Barolo', 2017, '750ml')]['price']) == 88.0)
    empty = pc.load(os.path.join(d, 'does_not_exist.csv'))
    ok("missing cache file is empty, not an error", empty == {})
    pc.save({}, p)
    ok("empty cache writes a header only", pc.load(p) == {})

print("\n" + "=" * 46)
print(f"{P} passed, {F} failed")
sys.exit(1 if F else 0)
