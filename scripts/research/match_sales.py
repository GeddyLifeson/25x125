import json, sys, subprocess, urllib.parse, collections, time

BASE = 'https://datacatalog.cookcountyil.gov/resource/'

def q(ds, params):
    url = BASE + ds + '.json?' + urllib.parse.urlencode(params)
    out = subprocess.run(['curl', '-s', '-m', '60', url], capture_output=True, text=True).stdout
    try:
        return json.loads(out)
    except Exception:
        return []

rows = json.load(open(sys.argv[1]))
cand = [r for r in rows if '2022-01-01' <= r['date'] <= '2024-06-30']
print('candidate permits (issued 2022 to mid-2024):', len(cand))

# latest address year available
yr = q('3723-97qp', {'$select': 'max(year) as y'})
year = yr[0]['y'] if yr else '2025'
print('address year used:', year)

results = []
addrs = sorted(set(r['addr'] for r in cand))
for i in range(0, len(addrs), 40):
    chunk = addrs[i:i + 40]
    where = ' OR '.join("prop_address_full like '%s%%'" % a.replace("'", "''") for a in chunk)
    got = q('3723-97qp', {'$select': 'pin,prop_address_full', '$where': f"year='{year}' AND ({where})", '$limit': 5000})
    for g in got:
        g['_match'] = next((a for a in chunk if g['prop_address_full'].startswith(a)), None)
    results.extend(got)
    time.sleep(0.2)
pins_by_addr = collections.defaultdict(set)
for g in results:
    if g.get('_match'):
        pins_by_addr[g['_match']].add(g['pin'])
print('addresses matched to PINs:', len(pins_by_addr))

allpins = sorted(set(p for s in pins_by_addr.values() for p in s))
sales = []
for i in range(0, len(allpins), 80):
    chunk = allpins[i:i + 80]
    inlist = ','.join("'%s'" % p for p in chunk)
    sales.extend(q('wvhk-k5uv', {'$select': 'pin,sale_date,sale_price,class,deed_type,is_multisale,num_parcels_sale,sale_filter_less_than_10k',
                                 '$where': f"pin in({inlist}) AND sale_date >= '2022-06-01'", '$limit': 5000}))
    time.sleep(0.2)
by_pin = collections.defaultdict(list)
for s in sales:
    by_pin[s['pin']].append(s)

cases = []
for r in cand:
    pins = pins_by_addr.get(r['addr'], set())
    after = []
    for p in pins:
        for s in by_pin.get(p, []):
            if s['sale_date'][:10] > r['date'] and float(s.get('sale_price') or 0) >= 100000 and not s.get('sale_filter_less_than_10k'):
                after.append(s)
    if not after:
        continue
    # condo units: one sale per unit PIN (first sale after permit); whole building: one sale
    first = {}
    for s in sorted(after, key=lambda s: s['sale_date']):
        first.setdefault(s['pin'], s)
    sold = list(first.values())
    total = sum(float(s['sale_price']) for s in sold)
    classes = sorted(set(s['class'] for s in sold))
    whole = len(sold) == 1 and classes[0].startswith('2') and classes[0] not in ('299',)
    condo = all(c == '299' for c in classes)
    if condo and len(sold) == r['units']:
        kind = 'all units sold as condos'
    elif whole:
        kind = 'whole building sold'
    else:
        kind = f'{len(sold)} of {r["units"]} unit sales' if condo else 'mixed'
    cases.append(dict(addr=r['addr'], area=r['area'], units=r['units'], permit_date=r['date'], reported_cost=r['cost'],
                      sales=len(sold), sale_total=total, kind=kind, first_sale=min(s['sale_date'][:10] for s in sold),
                      classes=classes))
json.dump(cases, open(sys.argv[2], 'w'), indent=1)
good = [c for c in cases if c['kind'] in ('all units sold as condos', 'whole building sold')]
print('permits with later sales:', len(cases), ' clean full-building cases:', len(good))
for c in sorted(good, key=lambda c: c['area'])[:60]:
    print(f"{c['area']:20} {c['addr']:28} {c['units']}u permit {c['permit_date']} cost {c['reported_cost']:>10,.0f}  sold {c['sale_total']:>11,.0f} ({c['kind']}, first {c['first_sale']})  ratio {c['sale_total']/c['reported_cost']:.2f}")
