import sys, time, numpy as np, pandas as pd
from sklearn.model_selection import GroupKFold
from sklearn.ensemble import RandomForestRegressor
from sklearn.ensemble import HistGradientBoostingRegressor as HGBR
D=sys.argv[1]
cols=['unit','cycle','os1','os2','os3']+[f's{i}' for i in range(1,22)]
def load(fn):
    df=pd.read_csv(fn,sep=r'\s+',header=None); df.columns=cols; return df
def nasa_score(d):
    d=np.asarray(d,float); return float(np.sum(np.where(d<0,np.exp(-d/13)-1,np.exp(d/10)-1)))
def feats(df,W=20):
    df=df.sort_values(['unit','cycle']).copy()
    sens=[c for c in cols if c.startswith('s')]
    g=df.groupby('unit')
    out=[df[['unit','cycle','os1','os2','os3']+sens]]
    for name,fn in [('rm',lambda x:x.rolling(W,min_periods=1).mean()),('rs',lambda x:x.rolling(W,min_periods=1).std().fillna(0))]:
        r=g[sens].transform(fn); r.columns=[f'{c}_{name}' for c in sens]; out.append(r)
    # slope over window (trend)
    def slope(x):
        return x.rolling(W,min_periods=2).apply(lambda v: np.polyfit(np.arange(len(v)),v,1)[0] if len(v)>1 else 0.0, raw=True).fillna(0)
    r=g[sens].transform(slope); r.columns=[f'{c}_slope' for c in sens]; out.append(r)
    return pd.concat(out,axis=1)
t0=time.time()
tr=load(f'{D}/train_FD{sys.argv[2]}.txt'); te=load(f'{D}/test_FD{sys.argv[2]}.txt'); rul=pd.read_csv(f'{D}/RUL_FD{sys.argv[2]}.txt',header=None)[0].values
print('subset',sys.argv[2],'train rows',len(tr),'units',tr.unit.nunique(),'test rows',len(te),'units',te.unit.nunique(),'RUL vec',len(rul))
CAP=125
mx=tr.groupby('unit').cycle.transform('max'); tr['RUL']=np.minimum(mx-tr.cycle,CAP)
Xtr=feats(tr); Xte=feats(te)
fcols=[c for c in Xtr.columns if c not in ('unit','RUL')]
# unit-wise CV
gkf=GroupKFold(n_splits=5); cv=[]
for a,b in gkf.split(Xtr,tr.RUL,groups=tr.unit):
    m=HGBR(max_iter=400,learning_rate=0.05,max_leaf_nodes=31,random_state=0).fit(Xtr.iloc[a][fcols],tr.RUL.iloc[a])
    # evaluate on last cycle of each held-out unit (mimics test protocol) AND on all rows
    p=m.predict(Xtr.iloc[b][fcols]); y=tr.RUL.iloc[b].values
    last=Xtr.iloc[b].groupby('unit').cycle.transform('max')==Xtr.iloc[b].cycle
    cv.append((np.sqrt(np.mean((p-y)**2)), np.sqrt(np.mean((p[last.values]-y[last.values])**2))))
print('unit-wise 5-fold CV RMSE all-rows / last-cycle:',np.round(np.mean(cv,axis=0),2))
m=HGBR(max_iter=400,learning_rate=0.05,max_leaf_nodes=31,random_state=0).fit(Xtr[fcols],tr.RUL)
last=Xte.groupby('unit').cycle.transform('max')==Xte.cycle
p=m.predict(Xte[last][fcols]); yt=np.minimum(rul,CAP); yraw=rul
d=p-yt
print(f'TEST last-cycle HGBR: RMSE(capped truth)={np.sqrt(np.mean(d**2)):.2f}  RMSE(raw truth)={np.sqrt(np.mean((p-yraw)**2)):.2f}  NASA score={nasa_score(d):.1f}  n={len(p)}')
rf=RandomForestRegressor(n_estimators=200,min_samples_leaf=5,n_jobs=-1,random_state=0).fit(Xtr[fcols],tr.RUL)
p2=rf.predict(Xte[last][fcols]); d2=p2-yt
print(f'TEST last-cycle RF:   RMSE(capped truth)={np.sqrt(np.mean(d2**2)):.2f}  NASA score={nasa_score(d2):.1f}')
# naive baseline: predict mean capped RUL of training
pn=np.full(len(yt),tr.RUL.mean()); print(f'NAIVE mean-RUL baseline RMSE={np.sqrt(np.mean((pn-yt)**2)):.2f} NASA={nasa_score(pn-yt):.1f}')
print('elapsed s',round(time.time()-t0,1))
