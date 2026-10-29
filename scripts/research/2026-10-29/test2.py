import json,collections,statistics as st,csv,math,sys
R=sys.argv[1]; pool=json.load(open('pool_all.json'))
def dist(a,b): return math.hypot((a[0]-b[0])*69,(a[1]-b[1])*69*math.cos(math.radians(41.85)))
yr=collections.defaultdict(list)
for c in pool:
    if c['psf']: yr[int(c['date'][:4])].append(c['psf'])
trend={y:st.median(v) for y,v in yr.items() if len(v)>=20}
print('city median $/sf by year',{y:round(v) for y,v in sorted(trend.items())})
def T(y): return trend.get(y) or trend[min(trend,key=lambda k:abs(k-y))]
grp=lambda u:'2' if u==2 else ('3' if u==3 else '4-6')
SIZE={2:1300,3:1200}
def est(t_ll,t_units,t_year,ex,kinds=None,mode='psf'):
    cand=[c for c in pool if not ex(c) and (c['psf'] if mode=='psf' else True) and (kinds is None or c['kind'] in kinds)]
    sizef=lambda u:SIZE.get(u,1000)
    for rad,need,same in ((0.75,6,True),(1.5,6,True),(1.5,6,False),(3,6,False),(99,1,False)):
        use=[c for c in cand if dist(t_ll,(c['lat'],c['lon']))<=rad and (not same or grp(c['units'])==grp(t_units)) and abs(int(c['date'][:4])-t_year)<=4]
        if len(use)>=need: break
    vals=[]
    for c in use:
        v=(c['psf']*T(t_year)/T(int(c['date'][:4])))*sizef(t_units) if mode=='psf' else c['per_unit']
        w=1/(0.2+dist(t_ll,(c['lat'],c['lon'])))
        vals.append((v,w))
    vals.sort(); tot=sum(w for _,w in vals); acc=0
    for v,w in vals:
        acc+=w
        if acc>=tot/2: return v,rad,len(use)
permits=json.load(open(R+'/permits_2to6_clean_city.json')); ll={p['addr']:(float(p['lat']),float(p['lon'])) for p in permits if p.get('lat')}
tp=list(csv.DictReader(open(R+'/test_parcels.csv')))
for kinds in (None,['building'],['condo']):
  for mode in ('psf','unit'):
    hit=0;errs=[]
    for t in tp:
        tl=ll[t['addr'].upper()]; fs=t['first_sale']; u=int(t['units'])
        ex=lambda c: dist(tl,(c['lat'],c['lon']))<0.02 or c['date']==fs
        e,_,_=est(tl,u,int(fs[:4]),ex,kinds,mode); a=float(t['sale_per_unit']); errs.append(e/a-1); hit+=abs(e/a-1)<=.15
    print(kinds,mode,'test hit',hit,'/37','median abs err',round(st.median([abs(x) for x in errs])*100),'%')
# pool LOO psf mode, building sales only (whole-building comparison)
for kinds in (None,):
    h=n=0
    for c in pool:
        if not c['psf']: continue
        ex=lambda z: z is c or (c['kind']=='condo' and z.get('bldg')==c.get('bldg')) or dist((c['lat'],c['lon']),(z['lat'],z['lon']))<0.02
        e,_,_=est((c['lat'],c['lon']),c['units'],int(c['date'][:4]),ex,kinds,'psf')
        e=e/SIZE.get(c['units'],1000)  # back to psf
        n+=1; h+=abs(e/c['psf']-1)<=.15
    print('pool LOO $/sf within 15%:',h,'/',n,round(h/n*100),'%')
