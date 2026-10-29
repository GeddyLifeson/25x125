import json,sys,urllib.parse,urllib.request,time
def q(base,ds,params,tries=4):
    url=base+ds+'.json?'+urllib.parse.urlencode(params)
    for i in range(tries):
        try:
            with urllib.request.urlopen(url,timeout=120) as r: return json.load(r)
        except Exception as e:
            err=e; time.sleep(2**i)
    raise err
CC='https://datacatalog.cookcountyil.gov/resource/'
CHI='https://data.cityofchicago.org/resource/'
def qall(base,ds,params,page=50000):
    out=[];off=0
    while True:
        p=dict(params); p['$limit']=page; p['$offset']=off
        got=q(base,ds,p); out+=got
        if len(got)<page: return out
        off+=page
