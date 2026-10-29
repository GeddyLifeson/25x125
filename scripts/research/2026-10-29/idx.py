import json,collections,statistics as st,csv,sys
R=sys.argv[1]
d=json.load(open(R+'/permits_2to6_clean_city.json'))
# clean: drop cancelled, dedupe by address keeping latest
d=[x for x in d if x['status']!='CANCELLED']
by={}
for x in sorted(d,key=lambda x:x['date']): by[x['addr']]=x
d=list(by.values()); print('clean permits',len(d))
grp=lambda u:'2' if u==2 else ('3' if u==3 else '4-6')
city={g:st.median([x['per_unit'] for x in d if grp(x['units'])==g]) for g in ('2','3','4-6')}
print('city median per unit by group',{k:round(v) for k,v in city.items()})
areas=collections.defaultdict(list)
for x in d: areas[x['area']].append(x['per_unit']/city[grp(x['units'])])
rows=[]
for a,v in areas.items():
    m=st.median(v); q=st.quantiles(v,n=4) if len(v)>=4 else [min(v),m,max(v)]
    rows.append(dict(area=a,permits=len(v),index=round(m,2),p25=round(q[0],2),p75=round(q[-1],2),thin='yes' if len(v)<10 else 'no'))
rows.sort(key=lambda r:-r['permits'])
old={r['area']:float(r['index']) for r in csv.DictReader(open(R+'/cost_index_by_area.csv'))}
for r in rows[:22]: print(f"{r['area']:20} n={r['permits']:3} new={r['index']:.2f} old={old.get(r['area'])}")
with open('cost_index_by_area_v2.csv','w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
json.dump({'city_median_per_unit_by_units':{k:round(v) for k,v in city.items()},'permits_used':len(d)},open('idx_meta.json','w'))
