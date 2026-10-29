import sys,json; sys.path.insert(0,sys.argv[1])
from soql import *
u=qall(CC,'3r7i-mrz4',{'$where':"year='2026.0' AND char_yrblt>='2014' AND char_building_pins<='8' AND char_building_pins>='2' AND is_parking_space=false AND is_common_area=false",'$select':'pin,pin10,tieback_key_pin,char_yrblt,char_unit_sf,char_building_sf,char_building_pins,bldg_is_mixed_use'})
print('condo units',len(u))
pins=sorted(set(x['pin'] for x in u)); par={}; sales=[]
for i in range(0,len(pins),150):
    c=pins[i:i+150]; inl=','.join("'%s'"%p for p in c)
    for r in q(CC,'pabr-t5kh',{'$where':f"year='2026' AND pin in({inl})",'$select':'pin,nbhd_code,chicago_community_area_name,lat,lon','$limit':5000}): par[r['pin']]=r
    sales+=q(CC,'wvhk-k5uv',{'$where':f"pin in({inl}) AND sale_date>='2015-01-01'",'$select':'pin,sale_date,sale_price,is_multisale,sale_filter_less_than_10k,sale_filter_deed_type','$limit':5000})
json.dump(dict(u=u,par=par,sales=sales),open('condo.json','w')); print('par',len(par),'sales',len(sales))
