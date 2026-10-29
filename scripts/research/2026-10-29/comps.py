import json,collections,statistics as st,csv,sys
d=json.load(open('pool.json'))
b={x['pin']:x for x in d['b']}; par=d['par']
comps=[]
for s in d['sales']:
    x=b.get(s['pin']); p=par.get(s['pin'])
    if not x or not p or not p.get('chicago_community_area_name'): continue
    if s.get('is_multisale') in (True,'true') or s.get('sale_filter_less_than_10k') in (True,'true') or s.get('sale_filter_deed_type') in (True,'true'): continue
    yb=int(float(x['char_yrblt'])); price=float(s['sale_price'])
    if int(s['sale_date'][:4])<yb or price<200000: continue
    apts=x.get('char_apts') or ''
    units={'Two':2,'Three':3,'Four':4,'Five':5,'Six':6}.get(apts)
    if not units:
        try: units=int(float(apts))
        except: units=None
    if not units or units<2 or units>6: continue
    sf=float(x.get('char_bldg_sf') or 0)
    comps.append(dict(pin=s['pin'],date=s['sale_date'][:10],price=price,units=units,per_unit=price/units,sf=sf,psf=price/sf if sf>500 else None,yb=yb,
                      area=p['chicago_community_area_name'].title(),nbhd=p['nbhd_code'],lat=float(p['lat']),lon=float(p['lon']),land=float(x.get('char_land_sf') or 0)))
# keep first sale after build per pin
first={}
for c in sorted(comps,key=lambda c:c['date']): first.setdefault(c['pin'],c)
comps=list(first.values())
print('comps',len(comps), collections.Counter(c['units'] for c in comps), collections.Counter(c['date'][:4] for c in comps))
print('apts values',collections.Counter(x.get('char_apts') for x in d['b']).most_common(8))
json.dump(comps,open('comps.json','w'))
sfv=[c['sf'] for c in comps if c['sf']>500]; print('bldg sf median by units',{u:st.median([c['sf'] for c in comps if c['units']==u and c['sf']>500]) for u in (2,3,4,5,6) if any(c['units']==u and c['sf']>500 for c in comps)})
print('per-unit median by units',{u:round(st.median([c['per_unit'] for c in comps if c['units']==u])) for u in (2,3,4,5,6) if any(c['units']==u for c in comps)})
print('areas with 5+ comps',sum(1 for a,n in collections.Counter(c['area'] for c in comps).items() if n>=5), 'nbhds 5+',sum(1 for a,n in collections.Counter(c['nbhd'] for c in comps).items() if n>=5))
