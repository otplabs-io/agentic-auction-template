import json
FLAGS = {
    ("Valdicava Brunello di Montalcino", 2015): "Valdicava is a benchmark Brunello producer",
    ("Valdicava Brunello di Montalcino", 2016): "Valdicava is a benchmark Brunello producer",
    ("Valdicava Madonna del Piano Brunello di Montalcino Riserva", 2013): "Valdicava's Riserva, rarely offered at auction",
    ("Domaine Didier Dagueneau Pouilly Fume Pur Sang", 2003): "Dagueneau's flagship Pouilly-Fume, mature 2003",
    ("Gravner Ribolla", 2015): "Gravner is the reference amphora-aged orange producer",
    ("Gaja Barolo Dagromis", 2010): "Gaja Barolo, 2010 benchmark vintage",
    ("Domaine Tempier Bandol Tourtine", 2023): "Domaine Tempier is the benchmark Bandol house",
    ("Nicolas Joly Savennieres Clos De La Coulee De Serrant", 2014): "Monopole Savennieres, a Loire icon",
    ("Tua Rita Redigaffi", 2003): "Tua Rita's flagship Merlot, mature 2003",
    ("Francois Cotat Sancerre La Grande Cote", 2012): "Cotat is the reference Sancerre producer; 2012 scored 103",
    ("Francois Cotat Sancerre Les Monts Damnés", 2021): "Cotat is the reference Sancerre producer",
    ("Luigi Einaudi Barolo Cannubi", 1999): "Mature 1999 Cannubi Barolo",
}
p = json.load(open('payload.json')); n = 0
for d in p['deals']:
    k = (d['wine'], d['vintage'])
    if k in FLAGS and not d.get('flag'):
        d['flag'] = FLAGS[k]; n += 1; print('flagged:', k)
json.dump(p, open('payload.json', 'w'), ensure_ascii=False, indent=1)
print(f"applied {n}")
