import json, re, sys, statistics as st, collections, math, csv

CA = ["Rogers Park","West Ridge","Uptown","Lincoln Square","North Center","Lake View","Lincoln Park","Near North Side","Edison Park","Norwood Park",
"Jefferson Park","Forest Glen","North Park","Albany Park","Portage Park","Irving Park","Dunning","Montclare","Belmont Cragin","Hermosa",
"Avondale","Logan Square","Humboldt Park","West Town","Austin","West Garfield Park","East Garfield Park","Near West Side","North Lawndale","South Lawndale",
"Lower West Side","Loop","Near South Side","Armour Square","Douglas","Oakland","Fuller Park","Grand Boulevard","Kenwood","Washington Park",
"Hyde Park","Woodlawn","South Shore","Chatham","Avalon Park","South Chicago","Burnside","Calumet Heights","Roseland","Pullman",
"South Deering","East Side","West Pullman","Riverdale","Hegewisch","Garfield Ridge","Archer Heights","Brighton Park","McKinley Park","Bridgeport",
"New City","West Elsdon","Gage Park","Clearing","West Lawn","Chicago Lawn","West Englewood","Englewood","Greater Grand Crossing","Ashburn",
"Auburn Gresham","Beverly","Washington Heights","Mount Greenwood","Morgan Park","O'Hare","Edgewater"]
AREAS = {str(i + 1): n for i, n in enumerate(CA)}

WORDS = {'TWO': 2, 'THREE': 3, 'FOUR': 4, 'FIVE': 5, 'SIX': 6, 'SINGLE': 1, 'ONE': 1}
unit_re = re.compile(r'\b(\d{1,2}|TWO|THREE|FOUR|FIVE|SIX|SINGLE|ONE)[\s-]*(?:DWELLING\s*)?(?:UNITS?|DU|D\.U\.|FLAT|FAMILY|APARTMENTS?)\b')
good = re.compile(r'ERECT|NEW CONSTRUCTION|NEW \d|NEW (TWO|THREE|FOUR|FIVE|SIX)|PROPOSED|FULL BUILDING PERMIT|CONSTRUCT A NEW|BUILD A NEW|NEW .*BUILDING')
bad = re.compile(r'REPLACE|REPAIR|^\W*PORCH|REBUILD (REAR|FRONT)? ?PORCH|WRECK|DEMOLI|INTERIOR|REVISION TO|CHANGE OF CONTRACTOR|GARAGE ONLY|COACH HOUSE|\bADU\b')
mixed = re.compile(r'\bMIXED|COMMERCIAL|RETAIL|OFFICE|STORE')

d = json.load(open(sys.argv[1]))
rows = []
for r in d:
    desc = (r.get('work_description') or '').upper()
    cost = float(r.get('reported_cost') or 0)
    m = unit_re.search(desc)
    if not desc or cost < 100000 or not m or not good.search(desc) or bad.search(desc) or mixed.search(desc):
        continue
    u = m.group(1)
    units = int(u) if u.isdigit() else WORDS.get(u)
    if not units or units < 2 or units > 6:
        continue
    rows.append(dict(permit=r['permit_'], date=r['issue_date'][:10], ca=r.get('community_area'), area=AREAS.get(r.get('community_area'), '?'),
                     addr=f"{r.get('street_number','')} {r.get('street_direction','')} {r.get('street_name','')}".strip(),
                     units=units, cost=cost, per_unit=cost / units, lat=r.get('latitude'), lon=r.get('longitude'),
                     milestone=r.get('permit_milestone'), status=r.get('permit_status'), desc=desc[:200]))
json.dump(rows, open(sys.argv[2], 'w'), indent=1)
allm = st.median([x['per_unit'] for x in rows])
print('clean 2-6 unit residential new construction permits:', len(rows), ' city median per unit:', round(allm))
by = collections.defaultdict(list)
for x in rows:
    by[x['area']].append(x['per_unit'])
out = []
for a, v in by.items():
    v = sorted(v); m = st.median(v)
    if len(v) >= 4:
        q = st.quantiles(v, n=4); lo, hi = q[0], q[2]
    else:
        lo, hi = v[0], v[-1]
    out.append(dict(area=a, permits=len(v), median_per_unit=round(m), index=round(m / allm, 2), p25=round(lo), p75=round(hi),
                    thin='yes' if len(v) < 10 else 'no'))
out.sort(key=lambda t: -t['permits'])
with open(sys.argv[3], 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
for o in out:
    print(f"{o['area']:24} n={o['permits']:3} idx={o['index']:.2f} median={o['median_per_unit']:>9,}  p25={o['p25']:>9,} p75={o['p75']:>9,} thin={o['thin']}")
print('areas with permits:', len(out), ' areas with 10+:', sum(1 for o in out if o['thin'] == 'no'))
