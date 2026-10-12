"""usage: python3 mk1012.py <batchN> < lines idx|price|type|source"""
import json,sys,csv,subprocess
bn=sys.argv[1]; L=json.load(open('fetch_plan_1012_full.json')); out=[]
for line in sys.stdin:
    line=line.strip()
    if not line: continue
    i,p,t,s=line.split('|',3); w=L[int(i)]
    out.append(dict(wine=w['wine'],vintage=w['vintage'],format=w['format'],price=(None if p in('','None') else float(p)),source=s,source_type=t))
f=f'w1012_batch{bn}_results.json'; json.dump(out,open(f,'w'),indent=1)
print(subprocess.run(['python3','apply_batch.py',f],capture_output=True,text=True).stdout)
rows=list(csv.DictReader(open('valuations.csv',newline='',encoding='utf-8'))); seen={}
for r in rows: seen[r['id']]=r
with open('valuations.csv','w',newline='',encoding='utf-8') as fh:
    w=csv.DictWriter(fh,fieldnames=list(rows[0].keys())); w.writeheader(); [w.writerow(r) for r in seen.values()]
print('valuations rows',len(seen))
