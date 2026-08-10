import json, random
RATE = 1.17
random.seed(11)

# Synthetic lots for layout testing only. Prices are invented.
W = [
 # (wine, country, region, subregion, vintages, market_lo, market_hi, standout)
 ("Domaine Faiveley Gevrey-Chambertin","FR","Burgundy","Gevrey-Chambertin",[2016,2017,2018,2019],150,260,""),
 ("Domaine Robert Chevillon Nuits-St-Georges Les Vaucrains","FR","Burgundy","Nuits-Saint-Georges",[2015,2017,2019],210,340,"Benchmark 1er cru"),
 ("Joseph Drouhin Chablis Vaudésir","FR","Burgundy","Chablis",[2018,2019,2020],95,160,""),
 ("Domaine Vincent Dauvissat Chablis La Forest","FR","Burgundy","Chablis",[2017,2018],180,300,"Seldom at auction"),
 ("Château Gloria St-Julien","FR","Bordeaux","Saint-Julien",[2009,2010,2014,2016],75,135,""),
 ("Château Sociando-Mallet Haut-Médoc","FR","Bordeaux","Haut-Médoc",[2005,2009,2015],60,120,""),
 ("Château Lynch-Bages Pauillac","FR","Bordeaux","Pauillac",[2012,2014],140,230,"Benchmark 5ème cru"),
 ("Château Chasse-Spleen Moulis-en-Médoc","FR","Bordeaux","Moulis-en-Médoc",[2010,2015,2016],45,85,""),
 ("Domaine Jean-Louis Chave Sélection Offerus St-Joseph","FR","Rhône","Saint-Joseph",[2018,2019,2020],42,72,""),
 ("Domaine du Vieux Télégraphe Châteauneuf-du-Pape La Crau","FR","Rhône","Châteauneuf-du-Pape",[2016,2017,2019],95,160,"Reference CdP"),
 ("Guigal Côte-Rôtie Brune et Blonde","FR","Rhône","Côte-Rôtie",[2016,2017,2018],85,145,""),
 ("Domaine Clusel-Roch Côte-Rôtie Classique","FR","Rhône","Côte-Rôtie",[2017,2018],110,185,"Small production"),
 ("Domaine Vacheron Sancerre Les Romains","FR","Loire","Sancerre",[2019,2020,2021],60,105,""),
 ("Domaine Huet Vouvray Le Mont Sec","FR","Loire","Vouvray",[2017,2018,2020],48,88,"Bucket-list Chenin"),
 ("Charles Joguet Chinon Clos de la Dioterie","FR","Loire","Chinon",[2016,2018],52,92,""),
 ("Trimbach Riesling Cuvée Frédéric Emile","FR","Alsace","Ribeauvillé",[2013,2015,2016],95,165,"Reference Alsace Riesling"),
 ("Domaine Zind-Humbrecht Riesling Clos Windsbuhl","FR","Alsace","Hunawihr",[2016,2017],105,175,""),
 ("Produttori del Barbaresco Barbaresco","IT","Piedmont","Barbaresco",[2016,2017,2018],48,82,""),
 ("Vietti Barolo Castiglione","IT","Piedmont","Barolo",[2016,2017,2018],75,130,""),
 ("Giacomo Fenocchio Barolo Bussia","IT","Piedmont","Barolo",[2015,2016,2017],95,165,"Traditionalist Bussia"),
 ("G.D. Vajra Barolo Albe","IT","Piedmont","Barolo",[2017,2018,2019],62,105,""),
 ("Bruno Giacosa Roero Arneis","IT","Piedmont","Roero",[2020,2021],38,62,""),
 ("Massolino Barolo","IT","Piedmont","Barolo",[2016,2017],78,132,""),
 ("Felsina Chianti Classico Riserva Rancia","IT","Tuscany","Chianti Classico",[2016,2017,2018],72,125,"Benchmark Riserva"),
 ("Isole e Olena Chianti Classico","IT","Tuscany","Chianti Classico",[2018,2019,2020],40,68,""),
 ("Poggio di Sotto Rosso di Montalcino","IT","Tuscany","Montalcino",[2018,2019],95,160,"Seldom at auction"),
 ("Il Poggione Brunello di Montalcino","IT","Tuscany","Montalcino",[2015,2016,2017],105,175,""),
 ("Valdicava Rosso di Montalcino","IT","Tuscany","Montalcino",[2019,2020],62,105,""),
 ("Quintarelli Valpolicella Classico Superiore","IT","Veneto","Valpolicella",[2015,2016],120,200,"Cult producer"),
 ("Pieropan Soave Classico La Rocca","IT","Veneto","Soave",[2018,2019,2020],42,72,""),
 ("Emidio Pepe Montepulciano d'Abruzzo","IT","Abruzzo","Colline Teramane",[2015,2016],130,215,"Natural-wine landmark"),
 ("Arianna Occhipinti SP68 Rosso","IT","Sicily","Vittoria",[2020,2021],32,55,""),
 ("COS Cerasuolo di Vittoria Classico","IT","Sicily","Vittoria",[2018,2019],42,70,""),
 ("López de Heredia Viña Tondonia Reserva","ES","Rioja","Rioja Alta",[2010,2011,2012],78,135,"Benchmark traditional Rioja"),
 ("La Rioja Alta Viña Ardanza Reserva","ES","Rioja","Rioja Alta",[2014,2015,2016],52,90,""),
 ("CVNE Imperial Gran Reserva","ES","Rioja","Rioja Alta",[2014,2015],75,128,""),
 ("Remelluri Rioja Reserva","ES","Rioja","Rioja Alavesa",[2016,2017],48,82,""),
 ("Descendientes de J. Palacios Pétalos","ES","Bierzo","Bierzo",[2020,2021],26,44,""),
 ("Raúl Pérez Ultreia Saint Jacques","ES","Bierzo","Bierzo",[2019,2020],30,52,""),
 ("Alvaro Palacios Les Terrasses","ES","Priorat","Priorat",[2018,2019,2020],72,120,""),
 ("Do Ferreiro Albariño Cepas Vellas","ES","Rías Baixas","Val do Salnés",[2019,2020],62,105,"Old-vine Albariño"),
 ("Quinta do Vale Meão Meandro","PT","Douro","Douro",[2017,2018,2019],35,58,""),
 ("Niepoort Redoma Tinto","PT","Douro","Douro",[2017,2018],48,82,""),
 ("Quinta do Crasto Reserva Old Vines","PT","Douro","Douro",[2017,2018,2019],62,105,""),
 ("Luis Pato Vinha Pan Baga","PT","Bairrada","Bairrada",[2015,2017],55,95,"Rarely exported"),
 ("Soalheiro Alvarinho Primeiras Vinhas","PT","Vinho Verde","Monção e Melgaço",[2019,2020],45,78,""),
 ("F.X. Pichler Grüner Veltliner Loibner Steinertal Smaragd","AT","Wachau","Loiben",[2018,2019],85,145,""),
 ("Emmerich Knoll Riesling Loibenberg Smaragd","AT","Wachau","Loiben",[2017,2018,2019],78,132,"Reference Wachau"),
 ("Prager Riesling Wachstum Bodenstein Smaragd","AT","Wachau","Weissenkirchen",[2018,2019],92,155,""),
 ("Schloss Gobelsburg Grüner Veltliner Ried Lamm","AT","Kamptal","Langenlois",[2018,2019,2020],62,105,""),
 ("Bründlmayer Riesling Ried Heiligenstein","AT","Kamptal","Langenlois",[2017,2019],72,122,"Grand cru of Austria"),
 ("Claus Preisinger Blaufränkisch Kalkundkiesel","AT","Burgenland","Neusiedlersee",[2019,2020],34,58,""),
]
FORMATS = ["750ml"]*17 + ["1.5L","375ml","3.0L"]
COND = [""]*13 + ["Scuffed label","Bin-soiled label","Nicked capsule","Torn label, wine unaffected","Faded label"]
SRC = [("ws_vintage","Wine-Searcher average retail, vintage-specific"),
       ("ws_vintage","Wine-Searcher average retail, vintage-specific"),
       ("ws_vintage","Wine-Searcher average retail, vintage-specific"),
       ("ws_adjacent","Wine-Searcher average retail, adjacent vintage ({adj})"),
       ("ws_allvintage","Wine-Searcher all-vintage average"),
       ("ws_single_retailer","Single retailer listing (Wine-Searcher)"),
       ("auction","Recent auction hammer, comparable lot")]

deals, used, idn = [], set(), 10814600
for w in W:
    for v in random.sample(w[4], k=min(len(w[4]), random.choice([1,1,2,2,3]))):
        key=(w[0],v)
        if key in used: continue
        used.add(key)
        idn += random.randint(3,29)
        market = round(random.uniform(w[5], w[6]), 0)
        fmt = random.choice(FORMATS)
        if fmt == "1.5L": market *= 2.1
        elif fmt == "375ml": market *= 0.55
        elif fmt == "3.0L": market *= 4.4
        # target discount is now measured on the buyer price (reserve + premium)
        target = random.choice([.26,.28,.31,.34,.37,.41,.44,.47,.51,.56,.60,.64])
        reserve = round(market*(1-target)/RATE)
        if reserve > 150 or reserve < 12: continue
        buyer = round(reserve*RATE, 2)
        pb = (market-buyer)/market
        if pb < 0.25: continue
        st, ss = random.choice(SRC)
        if "{adj}" in ss: ss = ss.format(adj=v-1)
        deals.append({
          "id": idn, "wine": w[0], "vintage": v, "format": fmt,
          "region_raw": ", ".join([{"FR":"France","IT":"Italy","ES":"Spain","PT":"Portugal","AT":"Austria"}[w[1]], w[2], w[3]]),
          "region_path": [{"FR":"France","IT":"Italy","ES":"Spain","PT":"Portugal","AT":"Austria"}[w[1]], w[2], w[3]],
          "country_code": w[1], "qty": random.choice([1,1,1,2,2,3,6]),
          "reserve": float(reserve), "buyer_price": buyer,
          "market": float(market), "pct_below": round(pb,4),
          "tag": "Steal" if pb>=.55 else "Great" if pb>=.40 else "Good",
          "flag": w[7] if random.random()<.62 else "",
          "condition": random.choice(COND),
          "source": ss, "source_type": st})

unval = []
UV = [("Domaine Ponsot Morey-St-Denis Cuvée des Alouettes","FR","Burgundy","Morey-Saint-Denis",1978),
      ("Cantina Sociale di Serralunga Barolo","IT","Piedmont","Barolo",1971),
      ("Bodegas Riojanas Monte Real Gran Reserva","ES","Rioja","Rioja Alta",1970),
      ("Caves São João Frei João Reserva","PT","Bairrada","Bairrada",1985),
      ("Weingut Josef Jamek Riesling Federspiel","AT","Wachau","Joching",1979),
      ("Domaine Berthet-Bondet Château-Chalon","FR","Jura","Château-Chalon",1996),
      ("Cascina Fontana Nebbiolo d'Alba","IT","Piedmont","Alba",2004),
      ("Quinta da Pellada Primus","PT","Dão","Dão",2009)]
for i,(n,cc,rg,sr,v) in enumerate(UV):
    unval.append({"id": 10817400+i*7, "wine": n, "vintage": v, "format": "750ml",
      "region_raw": ", ".join([{"FR":"France","IT":"Italy","ES":"Spain","PT":"Portugal","AT":"Austria"}[cc], rg, sr]),
      "region_path": [{"FR":"France","IT":"Italy","ES":"Spain","PT":"Portugal","AT":"Austria"}[cc], rg, sr],
      "country_code": cc, "reserve": float(random.choice([38,45,52,66,74,88,95,120])),
      "condition": random.choice(["","Scuffed label","Bin-soiled label"])})

p = {"schema":2,"sample":True,"auction_date":"2026-08-09","premium_rate":0.17,
     "funnel":{"total":1847,"after_country":612,"after_dessert":574,"after_price":361,
               "after_condition":329,"valued":301,"unvalued":len(unval),"deals":len(deals)},
     "deals":deals,"unvalued":unval}
json.dump(p, open("sample_payload.json","w"), ensure_ascii=False, indent=1)
print("deals:",len(deals),"unvalued:",len(unval))
print("tiers:", {t:sum(1 for d in deals if d['tag']==t) for t in ["Good","Great","Steal"]})
