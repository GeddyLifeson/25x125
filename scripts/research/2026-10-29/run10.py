import json,csv,math,statistics as st,collections,urllib.request,urllib.parse,sys
W,R=sys.argv[1],sys.argv[2]
pool=json.load(open(W+'/pool_all.json'))
def q(host,ds,p): return json.load(urllib.request.urlopen(f'https://{host}/resource/{ds}.json?'+urllib.parse.urlencode(p),timeout=90))
def dist(a,b): return math.hypot((a[0]-b[0])*69,(a[1]-b[1])*69*math.cos(math.radians(41.85)))
grp=lambda u:'2' if u==2 else ('3' if u==3 else '4-6')
yr=collections.defaultdict(list)
for c in pool:
    if c['psf']: yr[int(c['date'][:4])].append(c['psf'])
trend={y:st.median(v) for y,v in yr.items() if len(v)>=20}
def T(y): return trend.get(y) or trend[min(trend,key=lambda k:abs(k-y))]
def est(tl,u,y,ex):
    cand=[c for c in pool if not ex(c)]
    for rad,same in ((0.75,True),(1.5,True),(1.5,False),(3,False),(99,False)):
        use=[c for c in cand if dist(tl,(c['lat'],c['lon']))<=rad and (not same or grp(c['units'])==grp(u)) and abs(int(c['date'][:4])-y)<=4]
        if len(use)>=6: break
    vals=sorted((c['per_unit']*T(y)/T(int(c['date'][:4])),1/(0.2+dist(tl,(c['lat'],c['lon'])))) for c in use)
    tot=sum(w for _,w in vals)
    def pct(p):
        acc=0
        for v,w in vals:
            acc+=w
            if acc>=tot*p: return v
    return pct(.5),pct(.25),pct(.75),rad,len(use)
zd={r['district']:r for r in csv.DictReader(open(R+'/../rules/zoning_districts.csv'))}
idx={r['area']:float(r['index']) for r in csv.DictReader(open(R+'/cost_index_by_area_v2.csv'))}
fd=json.load(open(R+'/../rules/feasibility_defaults.json'))
P={k:(v['2-3'],v['4-6']) for k,v in fd['build_spec_presets'].items() if isinstance(v,dict) and '2-3' in v}
def preset(a): return 'high' if a>=1.8 else ('standard' if a>=1.3 else 'production')
def total(units,b23,b46,adj,land,lot):
    g=units*{2:1300,3:1200}.get(units,1000)*1.12
    hard=g*(b23 if units<=3 else b46)*adj; spr=g*5 if units>=4 else 0; cont=.05*hard; soft=.22*hard
    permit=max(2000 if units<=3 else 3000,g*.5*(.75 if units<=3 else 1))
    pre=land+hard+spr+cont+soft+permit
    fin=.65*pre*.08*(.55+.5)+.015*pre*1.5
    return pre+fin,g
permits={p['addr']:p for p in json.load(open(R+'/permits_2to6_clean_city.json'))}
tp=list(csv.DictReader(open(R+'/test_parcels.csv')))
names=sys.argv[3].split('|')
out=[]
for t in tp:
    if t['addr'] not in names: continue
    p=permits[t['addr'].upper()]; tl=(float(p['lat']),float(p['lon'])); u=int(t['units'])
    z=q('data.cityofchicago.org','dj47-wfun',{'$select':'zone_class','$where':f"intersects(the_geom,'POINT ({tl[1]} {tl[0]})')"})
    zc=z[0]['zone_class'] if z else '?'
    pl=q('data.cityofchicago.org','ydr8-5enu',{'$select':'pin_list','$where':f"permit_='{p['permit']}'"})
    pin=(pl[0].get('pin_list','') if pl else '').split('|')[0].strip()
    lot=None
    if pin:
        a=q('datacatalog.cookcountyil.gov','x54s-btds',{'$select':'year,char_land_sf,char_bldg_sf','$where':f"pin='{pin}0000'",'$order':'year DESC','$limit':1})
        if a: lot=float(a[0]['char_land_sf']); bsf=a[0].get('char_bldg_sf')
        else: bsf=None
    else: bsf=None
    base=zc.split('-')[0]; key=zc if zc in zd else None
    if key is None:
        for k in zd:
            if k==zc or (zc[:2] in ('B1','B2','B3','C1','C2') and k.endswith(zc[-2:]) and k[:1]==zc[:1]): key=k;break
    lapu=float(zd[key]['lot_area_per_unit_sqft']) if key else None; far=float(zd[key]['far']) if key else None
    byright=math.floor(lot/lapu) if lot and lapu else None
    a=idx.get(t['area'],1.0); ps=preset(a); b=P[ps]; adj=1+.5*(min(a,1.3)-1) if ps=='production' else 1.0
    cost,g=total(u,b[0],b[1],adj,60000,lot)
    fs=t['first_sale']; ex=lambda c: dist(tl,(c['lat'],c['lon']))<0.02 or c['date']==fs
    m,lo,hi,rad,n=est(tl,u,int(fs[:4]),ex)
    sale=m*u; net=sale*.94; profit=net-cost; resid=net/1.15-(cost-60000)
    out.append(dict(addr=t['addr'],area=t['area'],zoning=zc,lot_sf=lot,units_built=u,units_by_right=byright,far_gfa=round(lot*far) if lot and far else None,model_gfa=round(g),assessor_bldg_sf=bsf,
        preset=ps,cost_index=a,total_cost=round(cost),sale_est=round(sale),sale_range=f"{round(lo*u):,}-{round(hi*u):,}",comps=n,radius_mi=rad,actual_sale=float(t['sale_total']),
        sale_err=round(sale/float(t['sale_total'])-1,3),profit_est=round(profit),profit_at_actual=round(float(t['sale_total'])*.94-cost),residual_land=round(resid)))
json.dump(out,open(sys.argv[4],'w'),indent=1)
for o in out: print(o)
