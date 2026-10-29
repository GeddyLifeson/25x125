import sys,json; sys.path.insert(0,sys.argv[1])
from soql import *
b=qall(CC,'x54s-btds',{'$where':"class='211' AND year='2026.0' AND char_yrblt>='2014'",'$select':'pin,char_yrblt,char_apts,char_bldg_sf,char_land_sf,char_cnst_qlty,char_ext_wall,pin_num_cards,card'})
print('bldgs',len(b))
pins=sorted(set(x['pin'] for x in b))
par={};sales=[]
for i in range(0,len(pins),150):
    c=pins[i:i+150]; inl=','.join("'%s'"%p for p in c)
    for r in q(CC,'pabr-t5kh',{'$where':f"year='2026' AND pin in({inl})",'$select':'pin,nbhd_code,chicago_community_area_name,ward_num,lat,lon,census_tract_geoid','$limit':5000}): par[r['pin']]=r
    sales+=q(CC,'wvhk-k5uv',{'$where':f"pin in({inl}) AND sale_date>='2015-01-01'",'$select':'pin,sale_date,sale_price,class,deed_type,is_multisale,num_parcels_sale,sale_filter_less_than_10k,sale_filter_deed_type,sale_filter_same_sale_within_365','$limit':5000})
json.dump(dict(b=b,par=par,sales=sales),open('pool.json','w'))
print('parcels',len(par),'sales',len(sales))
