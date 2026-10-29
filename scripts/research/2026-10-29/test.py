import json,collections,statistics as st,csv,math,sys
R=sys.argv[1]
comps=json.load(open('comps.json'))
for c in comps: c['kind']='building'
d=json.load(open('condo.json')); par=d['par']; um={x['pin']:x for x in d['u']}
first={}
for s in sorted(d['sales'],key=lambda s:s['sale_date']):
    x=um.get(s['pin']); p=par.get(s['pin'])
    if not x or not p or not p.get('chicago_community_area_name'): continue
    if x.get('bldg_is_mixed_use') in (True,'true'): continue
    if s.get('is_multisale') in (True,'true') or s.get('sale_filter_less_than_10k') in (True,'true') or s.get('sale_filter_deed_type') in (True,'true'): continue
    yb=int(float(x['char_yrblt'])); pr=float(s['sale_price'])
    n=int(float(x['char_building_pins']))
    if int(s['sale_date'][:4])<yb or pr<150000 or n>6: continue
    if s['pin'] in first: continue
    usf=float(x.get('char_unit_sf') or 0)
    first[s['pin']]=dict(pin=s['pin'],bldg=x['tieback_key_pin'] or x['pin10'],date=s['sale_date'][:10],price=pr,units=n,per_unit=pr,sf=usf,psf=pr/usf if usf>400 else None,yb=yb,
        area=p['chicago_community_area_name'].title(),nbhd=p['nbhd_code'],lat=float(p['lat']),lon=float(p['lon']),kind='condo')
condos=list(first.values())
print('condo unit comps',len(condos),'buildings',len(set(c['bldg'] for c in condos)),collections.Counter(c['units'] for c in condos))
pool=comps+condos
json.dump(pool,open('pool_all.json','w'))
print('total comps',len(pool),'areas with 5+',sum(1 for a,n in collections.Counter(c['area'] for c in pool).items() if n>=5),'nbhds 5+',sum(1 for a,n in collections.Counter(c['nbhd'] for c in pool).items() if n>=5))
# city trend: median per unit by year (for time adjustment)
yr=collections.defaultdict(list)
for c in pool: yr[int(c['date'][:4])].append(c['per_unit'])
trend={y:st.median(v) for y,v in yr.items() if len(v)>=20}
print('city median per unit by year',{y:round(v) for y,v in sorted(trend.items())})
def tadj(c,target):
    ys=sorted(trend); 
    a=trend.get(int(c['date'][:4])) or trend[min(ys,key=lambda y:abs(y-int(c['date'][:4])))]
    b=trend.get(target) or trend[min(ys,key=lambda y:abs(y-target))]
    return c['per_unit']*b/a
def dist(a,b): return math.hypot((a[0]-b[0])*69,(a[1]-b[1])*69*math.cos(math.radians(41.85)))
permits=json.load(open(R+'/permits_2to6_clean_city.json')); ll={p['addr'].replace('  ',' '):(float(p['lat']),float(p['lon'])) for p in permits if p.get('lat')}
tp=list(csv.DictReader(open(R+'/test_parcels.csv')))
def estimate(t_area,t_units,t_ll,t_year,exclude,pool):
    cand=[c for c in pool if not exclude(c)]
    grp=lambda u:'2' if u==2 else ('3' if u==3 else '4-6')
    near=[c for c in cand if grp(c['units'])==grp(t_units) and t_ll and dist(t_ll,(c['lat'],c['lon']))<=1.0 and abs(int(c['date'][:4])-t_year)<=3]
    if len(near)>=5: lvl='1 mi'; use=near
    else:
        use=[c for c in cand if grp(c['units'])==grp(t_units) and c['area']==t_area]; lvl='area'
        if len(use)<5:
            use=[c for c in cand if grp(c['units'])==grp(t_units) and t_ll and dist(t_ll,(c['lat'],c['lon']))<=2.5]; lvl='2.5 mi'
        if len(use)<5: use=[c for c in cand if grp(c['units'])==grp(t_units)]; lvl='city'
    if t_ll and lvl!='city':
        w=[(1/(0.25+dist(t_ll,(c['lat'],c['lon']))), tadj(c,t_year)) for c in use]
        w.sort(key=lambda z:z[1]); tot=sum(a for a,_ in w); acc=0
        for a,v in w:
            acc+=a
            if acc>=tot/2: return v,lvl,len(use)
    return st.median([tadj(c,t_year) for c in use]),lvl,len(use)
hit=0;res=[]
for t in tp:
    a=t['addr'].upper(); tl=ll.get(a)
    sale=float(t['sale_total']); fs=t['first_sale']; u=int(t['units'])
    # exclude own building: same location within 30 m or identical price/date
    ex=lambda c: (tl and dist(tl,(c['lat'],c['lon']))<0.02) or (c['date']==fs)
    est,lvl,n=estimate(t['area'],u,tl,int(fs[:4]),ex,pool)
    act=float(t['sale_per_unit']); e=est/act-1; ok=abs(e)<=0.15; hit+=ok
    res.append((t['addr'],t['area'],u,round(act),round(est),round(e*100),lvl,n,ok))
for r in res: print(r)
print('TEST SET hit within 15%:',hit,'/',len(tp),round(hit/len(tp)*100),'%')
lv=collections.Counter(r[6] for r in res); print(lv)
# LOO on whole pool (building sales only + one unit per condo bldg sample)
h=0;n=0
for c in pool:
    ex=lambda z: z is c or (c['kind']=='condo' and z.get('bldg')==c.get('bldg')) or dist((c['lat'],c['lon']),(z['lat'],z['lon']))<0.02
    est,_,_=estimate(c['area'],c['units'],(c['lat'],c['lon']),int(c['date'][:4]),ex,pool)
    n+=1; h+=abs(est/c['per_unit']-1)<=0.15
print('POOL LOO hit within 15%:',h,'/',n,round(h/n*100),'%')
