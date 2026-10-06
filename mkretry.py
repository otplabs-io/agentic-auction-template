"""usage: python3 mkretry.py <tag> < lines  key|price|type|source   (key = price_cache key)"""
import json,sys,csv,subprocess
sys.path.insert(0,'toolkit'); import price_cache as pc
tag=sys.argv[1]
rows=list(csv.DictReader(open('valuations.csv',newline='',encoding='utf-8')))
meta={}
for r in rows: meta[pc.make_key(r['wine'],r['vintage'],r['format'])]=r
out=[]
for line in sys.stdin:
    line=line.strip()
    if not line: continue
    k,p,t,s=line.split('@@',3)
    if k not in meta: print('NO KEY',k); continue
    r=meta[k]
    out.append(dict(wine=r['wine'],vintage=r['vintage'],format=r['format'],price=(None if p in('','None') else float(p)),source=s,source_type=t))
f=f'retry_{tag}_results.json'; json.dump(out,open(f,'w'),indent=1)
print(subprocess.run(['python3','apply_batch.py',f],capture_output=True,text=True).stdout)
rows=list(csv.DictReader(open('valuations.csv',newline='',encoding='utf-8'))); seen={}
for r in rows: seen[r['id']]=r
with open('valuations.csv','w',newline='',encoding='utf-8') as fh:
    w=csv.DictWriter(fh,fieldnames=list(rows[0].keys())); w.writeheader(); [w.writerow(r) for r in seen.values()]
print('valuations rows',len(seen))
