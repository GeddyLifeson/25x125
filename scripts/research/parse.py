import json, re, sys, statistics as st, collections

AREAS = {'19': 'Belmont Cragin', '20': 'Hermosa', '21': 'Avondale', '22': 'Logan Square', '23': 'Humboldt Park',
         '24': 'West Town', '25': 'Austin', '26': 'West Garfield Park', '27': 'East Garfield Park',
         '28': 'Near West Side', '29': 'North Lawndale'}

d = json.load(open(sys.argv[1]))
WORDS = {'TWO': 2, 'THREE': 3, 'FOUR': 4, 'FIVE': 5, 'SIX': 6, 'SINGLE': 1, 'ONE': 1}
unit_re = re.compile(r'\b(\d{1,2}|TWO|THREE|FOUR|FIVE|SIX|SINGLE|ONE)[\s-]*(?:DWELLING\s*)?(?:UNITS?|DU|D\.U\.|FLAT|FAMILY|APARTMENTS?)\b')
story_re = re.compile(r'\b(\d|TWO|THREE|FOUR|FIVE)[\s-]*STOR(?:Y|IES)\b')
skip = re.compile(r'GARAGE|STAGE|TENT|ADDITION|DECK|PORCH|FENCE|SIGN|SHED|CANOPY|TOWER|ANTENNA|SOLAR|TRAILER|TEMPORARY|BLEACHER|COACH HOUSE|ADU|ACCESSORY')
rows = []
for r in d:
    desc = (r.get('work_description') or '').upper()
    cost = float(r.get('reported_cost') or 0)
    if not desc or cost <= 0:
        continue
    m = unit_re.search(desc)
    if not m:
        continue
    if skip.search(desc) and not re.search(r'(DWELLING|RESIDEN|FLAT|UNIT)', desc.split('GARAGE')[0]):
        continue
    u = m.group(1)
    units = WORDS.get(u, None) if not u.isdigit() else int(u)
    if not units or units < 2 or units > 6:
        continue
    if re.search(r'\bMIXED|COMMERCIAL|RETAIL|OFFICE|STORE', desc):
        kind = 'mixed'
    else:
        kind = 'res'
    s = story_re.search(desc)
    stories = (int(s.group(1)) if s.group(1).isdigit() else WORDS.get(s.group(1))) if s else None
    rows.append(dict(permit=r['permit_'], date=r['issue_date'][:10], area=AREAS.get(r['community_area'], r['community_area']),
                     addr=f"{r.get('street_number','')} {r.get('street_direction','')} {r.get('street_name','')}",
                     units=units, stories=stories, kind=kind, cost=cost, per_unit=cost / units,
                     review=r.get('review_type'), desc=desc[:160]))

json.dump(rows, open(sys.argv[2], 'w'), indent=1)
print('matched 2-6 unit permits:', len(rows))
by = collections.defaultdict(list)
for x in rows:
    if x['kind'] == 'res':
        by[(x['area'], x['units'])].append(x['per_unit'])
print(f"{'area':22} {'units':>5} {'n':>4} {'median/unit':>12} {'p25':>10} {'p75':>10}")
for (a, u), v in sorted(by.items()):
    v.sort()
    q = st.quantiles(v, n=4) if len(v) >= 4 else [v[0], st.median(v), v[-1]]
    print(f"{a:22} {u:>5} {len(v):>4} {st.median(v):>12,.0f} {q[0]:>10,.0f} {q[-1]:>10,.0f}")
allres = [x['per_unit'] for x in rows if x['kind'] == 'res']
print('ALL residential 2-6 units: n=%d median per unit %s' % (len(allres), f"{st.median(allres):,.0f}"))
for u in range(2, 7):
    v = [x['per_unit'] for x in rows if x['kind'] == 'res' and x['units'] == u]
    if v:
        print(f"  {u} units: n={len(v)} median/unit {st.median(v):,.0f}")
yr = collections.defaultdict(list)
for x in rows:
    if x['kind'] == 'res':
        yr[x['date'][:4]].append(x['per_unit'])
for y in sorted(yr):
    print('year', y, 'n', len(yr[y]), 'median/unit', f"{st.median(yr[y]):,.0f}")
