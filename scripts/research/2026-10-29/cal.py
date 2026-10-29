import csv,statistics as st,sys
R=sys.argv[1]
idx={r['area']:float(r['index']) for r in csv.DictReader(open('cost_index_by_area_v2.csv'))}
tp=list(csv.DictReader(open(R+'/test_parcels.csv')))
def total(units,base23,base46,adj,land,lot=3125,far=1.2):
    g=min(lot*far,units*{2:1300,3:1200}.get(units,1000)*1.12)
    base=base23 if units<=3 else base46
    hard=g*base*adj; spr=g*5 if units>=4 else 0; cont=.05*hard; soft=.22*hard
    permit=max(2000 if units<=3 else 3000,g*.5*(.75 if units<=3 else 1))
    pre=land+hard+spr+cont+soft+permit
    fin=.65*pre*.08*(12/12*.55+6/12)+.015*pre*18/12
    return pre+fin, pre+fin-land
for b23,b46 in ((235,250),(185,200),(175,190),(165,180),(155,170)):
    rocs=[]
    for t in tp:
        u=int(t['units']); a=idx.get(t['area'],1.0); adj=1+.5*(a-1)
        tot,_=total(u,b23,b46,adj,60000)
        rocs.append(float(t['sale_total'])*.94/tot-1)
    mm,ex=total(3,b23,b46,1.0,0)
    print(f"base {b23}/{b46}: profit>=0 on {sum(r>=0 for r in rocs)}/37, median ROC {st.median(rocs)*100:.1f}%, std 3-flat ex-land per unit ${ex/3:,.0f}, with $60k land ${(ex+60000)/3:,.0f}")
P={'production':(165,170),'standard':(200,215),'high':(250,265)}
def preset(a): return 'high' if a>=1.8 else ('standard' if a>=1.3 else 'production')
rocs=[]
for t in tp:
    u=int(t['units']); a=idx.get(t['area'],1.0); b=P[preset(a)]
    tot,_=total(u,b[0],b[1],1+.5*(min(a,1.3)-1) if preset(a)=='production' else 1.0,60000)
    rocs.append(float(t['sale_total'])*.94/tot-1)
print('presets: profit>=0',sum(r>=0 for r in rocs),'/37 median ROC',round(st.median(rocs)*100,1))
mm,ex=total(3,165,170,1.0,0); print('production 3-flat ex land per unit',round(ex/3))
