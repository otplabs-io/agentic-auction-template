import json, random
RATE = 1.17
random.seed(11)

# Synthetic lots for layout testing only. Prices are invented.
W = [
 # (wine, country, region, subregion, vintages, market_lo, market_hi, standout, wine_type)
 ("Domaine Faiveley Gevrey-Chambertin","FR","Burgundy","Gevrey-Chambertin",[2016,2017,2018,2019],150,260,"","Red"),
 ("Domaine Robert Chevillon Nuits-St-Georges Les Vaucrains","FR","Burgundy","Nuits-Saint-Georges",[2015,2017,2019],210,340,"Benchmark 1er cru","Red"),
 ("Joseph Drouhin Chablis Vaudésir","FR","Burgundy","Chablis",[2018,2019,2020],95,160,"","White"),
 ("Domaine Vincent Dauvissat Chablis La Forest","FR","Burgundy","Chablis",[2017,2018],180,300,"Seldom at auction","White"),
 ("Château Gloria St-Julien","FR","Bordeaux","Saint-Julien",[2009,2010,2014,2016],75,135,"","Red"),
 ("Château Sociando-Mallet Haut-Médoc","FR","Bordeaux","Haut-Médoc",[2005,2009,2015],60,120,"","Red"),
 ("Château Lynch-Bages Pauillac","FR","Bordeaux","Pauillac",[2012,2014],140,230,"Benchmark 5ème cru","Red"),
 ("Château Chasse-Spleen Moulis-en-Médoc","FR","Bordeaux","Moulis-en-Médoc",[2010,2015,2016],45,85,"","Red"),
 ("Domaine Jean-Louis Chave Sélection Offerus St-Joseph","FR","Rhône","Saint-Joseph",[2018,2019,2020],42,72,"","Red"),
 ("Domaine du Vieux Télégraphe Châteauneuf-du-Pape La Crau","FR","Rhône","Châteauneuf-du-Pape",[2016,2017,2019],95,160,"Reference CdP","Red"),
 ("Guigal Côte-Rôtie Brune et Blonde","FR","Rhône","Côte-Rôtie",[2016,2017,2018],85,145,"","Red"),
 ("Domaine Clusel-Roch Côte-Rôtie Classique","FR","Rhône","Côte-Rôtie",[2017,2018],110,185,"Small production","Red"),
 ("Domaine Vacheron Sancerre Les Romains","FR","Loire","Sancerre",[2019,2020,2021],60,105,"","White"),
 ("Domaine Huet Vouvray Le Mont Sec","FR","Loire","Vouvray",[2017,2018,2020],48,88,"Bucket-list Chenin","White"),
 ("Charles Joguet Chinon Clos de la Dioterie","FR","Loire","Chinon",[2016,2018],52,92,"","Red"),
 ("Trimbach Riesling Cuvée Frédéric Emile","FR","Alsace","Ribeauvillé",[2013,2015,2016],95,165,"Reference Alsace Riesling","White"),
 ("Domaine Zind-Humbrecht Riesling Clos Windsbuhl","FR","Alsace","Hunawihr",[2016,2017],105,175,"","White"),
 ("Produttori del Barbaresco Barbaresco","IT","Piedmont","Barbaresco",[2016,2017,2018],48,82,"","Red"),
 ("Vietti Barolo Castiglione","IT","Piedmont","Barolo",[2016,2017,2018],75,130,"","Red"),
 ("Giacomo Fenocchio Barolo Bussia","IT","Piedmont","Barolo",[2015,2016,2017],95,165,"Traditionalist Bussia","Red"),
 ("G.D. Vajra Barolo Albe","IT","Piedmont","Barolo",[2017,2018,2019],62,105,"","Red"),
 ("Bruno Giacosa Roero Arneis","IT","Piedmont","Roero",[2020,2021],38,62,"","White"),
 ("Massolino Barolo","IT","Piedmont","Barolo",[2016,2017],78,132,"","Red"),
 ("Felsina Chianti Classico Riserva Rancia","IT","Tuscany","Chianti Classico",[2016,2017,2018],72,125,"Benchmark Riserva","Red"),
 ("Isole e Olena Chianti Classico","IT","Tuscany","Chianti Classico",[2018,2019,2020],40,68,"","Red"),
 ("Poggio di Sotto Rosso di Montalcino","IT","Tuscany","Montalcino",[2018,2019],95,160,"Seldom at auction","Red"),
 ("Il Poggione Brunello di Montalcino","IT","Tuscany","Montalcino",[2015,2016,2017],105,175,"","Red"),
 ("Valdicava Rosso di Montalcino","IT","Tuscany","Montalcino",[2019,2020],62,105,"","Red"),
 ("Quintarelli Valpolicella Classico Superiore","IT","Veneto","Valpolicella",[2015,2016],120,200,"Cult producer","Red"),
 ("Pieropan Soave Classico La Rocca","IT","Veneto","Soave",[2018,2019,2020],42,72,"","White"),
 ("Emidio Pepe Montepulciano d'Abruzzo","IT","Abruzzo","Colline Teramane",[2015,2016],130,215,"Natural-wine landmark","Red"),
 ("Arianna Occhipinti SP68 Rosso","IT","Sicily","Vittoria",[2020,2021],32,55,"","Red"),
 ("COS Cerasuolo di Vittoria Classico","IT","Sicily","Vittoria",[2018,2019],42,70,"","Red"),
 ("López de Heredia Viña Tondonia Reserva","ES","Rioja","Rioja Alta",[2010,2011,2012],78,135,"Benchmark traditional Rioja","Red"),
 ("La Rioja Alta Viña Ardanza Reserva","ES","Rioja","Rioja Alta",[2014,2015,2016],52,90,"","Red"),
 ("CVNE Imperial Gran Reserva","ES","Rioja","Rioja Alta",[2014,2015],75,128,"","Red"),
 ("Remelluri Rioja Reserva","ES","Rioja","Rioja Alavesa",[2016,2017],48,82,"","Red"),
 ("Descendientes de J. Palacios Pétalos","ES","Bierzo","Bierzo",[2020,2021],26,44,"","Red"),
 ("Raúl Pérez Ultreia Saint Jacques","ES","Bierzo","Bierzo",[2019,2020],30,52,"","Red"),
 ("Alvaro Palacios Les Terrasses","ES","Priorat","Priorat",[2018,2019,2020],72,120,"","Red"),
 ("Do Ferreiro Albariño Cepas Vellas","ES","Rías Baixas","Val do Salnés",[2019,2020],62,105,"Old-vine Albariño","White"),
 ("Quinta do Vale Meão Meandro","PT","Douro","Douro",[2017,2018,2019],35,58,"","Red"),
 ("Niepoort Redoma Tinto","PT","Douro","Douro",[2017,2018],48,82,"","Red"),
 ("Quinta do Crasto Reserva Old Vines","PT","Douro","Douro",[2017,2018,2019],62,105,"","Red"),
 ("Luis Pato Vinha Pan Baga","PT","Bairrada","Bairrada",[2015,2017],55,95,"Rarely exported","Red"),
 ("Soalheiro Alvarinho Primeiras Vinhas","PT","Vinho Verde","Monção e Melgaço",[2019,2020],45,78,"","White"),
 ("F.X. Pichler Grüner Veltliner Loibner Steinertal Smaragd","AT","Wachau","Loiben",[2018,2019],85,145,"","White"),
 ("Emmerich Knoll Riesling Loibenberg Smaragd","AT","Wachau","Loiben",[2017,2018,2019],78,132,"Reference Wachau","White"),
 ("Prager Riesling Wachstum Bodenstein Smaragd","AT","Wachau","Weissenkirchen",[2018,2019],92,155,"","White"),
 ("Schloss Gobelsburg Grüner Veltliner Ried Lamm","AT","Kamptal","Langenlois",[2018,2019,2020],62,105,"","White"),
 ("Bründlmayer Riesling Ried Heiligenstein","AT","Kamptal","Langenlois",[2017,2019],72,122,"Grand cru of Austria","White"),
 ("Claus Preisinger Blaufränkisch Kalkundkiesel","AT","Burgenland","Neusiedlersee",[2019,2020],34,58,"","Red"),
 # The still-red/white core above never reaches four of the six types, so the
 # swatch column would go untested. These exist to exercise it. The Sauternes
 # would screen out on a real week -- dessert wines never survive Step 1 -- and
 # is here only so the brown chip renders somewhere.
 ("Pierre Péters Cuvée de Réserve Blanc de Blancs Grand Cru","FR","Champagne","Le Mesnil-sur-Oger",[None],62,105,"Grower benchmark","Sparkling"),
 ("Bérêche & Fils Brut Réserve","FR","Champagne","Ludes",[None],55,92,"","Sparkling"),
 ("Raventós i Blanc L'Hereu Reserva Brut","ES","Conca del Riu Anoia","Sant Sadurní d'Anoia",[2019,2020],26,44,"",  "Sparkling"),
 ("Domaine Tempier Bandol Rosé","FR","Provence","Bandol",[2021,2022],52,88,"Reference Provence rosé","Rose"),
 ("Château Simone Palette Rosé","FR","Provence","Palette",[2019,2020,2021],68,115,"","Rose"),
 ("Radikon Ribolla Gialla","IT","Friuli-Venezia Giulia","Collio",[2015,2016],95,160,"Skin-contact landmark","Orange"),
 ("Paraschos Amphoreus Ribolla Gialla","IT","Friuli-Venezia Giulia","Collio",[2016,2018],58,98,"","Orange"),
 ("Château Doisy-Daëne Barsac","FR","Bordeaux","Barsac",[2011,2015],48,82,"","Dessert"),
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
          "source": ss, "source_type": st, "wine_type": w[8]})

unval = []
UV = [("Domaine Ponsot Morey-St-Denis Cuvée des Alouettes","FR","Burgundy","Morey-Saint-Denis",1978,"Red"),
      ("Cantina Sociale di Serralunga Barolo","IT","Piedmont","Barolo",1971,"Red"),
      ("Bodegas Riojanas Monte Real Gran Reserva","ES","Rioja","Rioja Alta",1970,"Red"),
      ("Caves São João Frei João Reserva","PT","Bairrada","Bairrada",1985,"Red"),
      ("Weingut Josef Jamek Riesling Federspiel","AT","Wachau","Joching",1979,"White"),
      # Château-Chalon is vin jaune: oxidative, but a dry white, not a dessert wine.
      ("Domaine Berthet-Bondet Château-Chalon","FR","Jura","Château-Chalon",1996,"White"),
      ("Cascina Fontana Nebbiolo d'Alba","IT","Piedmont","Alba",2004,"Red"),
      ("Quinta da Pellada Primus","PT","Dão","Dão",2009,"Red")]
for i,(n,cc,rg,sr,v,wt) in enumerate(UV):
    unval.append({"id": 10817400+i*7, "wine": n, "vintage": v, "format": "750ml",
      "region_raw": ", ".join([{"FR":"France","IT":"Italy","ES":"Spain","PT":"Portugal","AT":"Austria"}[cc], rg, sr]),
      "region_path": [{"FR":"France","IT":"Italy","ES":"Spain","PT":"Portugal","AT":"Austria"}[cc], rg, sr],
      "country_code": cc, "reserve": float(random.choice([38,45,52,66,74,88,95,120])),
      "wine_type": wt,
      "condition": random.choice(["","Scuffed label","Bin-soiled label"])})

p = {"schema":3,"sample":True,"auction_date":"2026-08-09","premium_rate":0.17,
     "funnel":{"total":1847,"after_country":612,"after_dessert":574,"after_price":361,
               "after_condition":329,"valued":301,"unvalued":len(unval),"deals":len(deals)},
     "deals":deals,"unvalued":unval}
json.dump(p, open("sample_payload.json","w"), ensure_ascii=False, indent=1)
print("deals:",len(deals),"unvalued:",len(unval))
print("tiers:", {t:sum(1 for d in deals if d['tag']==t) for t in ["Good","Great","Steal"]})
print("types:", {t:sum(1 for d in deals if d['wine_type']==t)
                 for t in ["Red","Rose","Orange","White","Sparkling","Dessert"]})
