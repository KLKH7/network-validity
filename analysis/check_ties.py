import sys, pandas as pd, numpy as np
d=sys.argv[1]
n=pd.read_csv(d+'/NetWorkSurvey.csv', low_memory=False)
b=pd.read_csv(d+'/BasicSurvey.csv', low_memory=False)
print('net rows',len(n),'cols',len(n.columns)); print(list(n.columns)[:45])
print('egos',n.egoid.nunique(),'alters',n.alterid.nunique())
egos=set(b.egoid)
n['instudy']=n.alterid.isin(egos)
print('basic survey egos',len(egos))
print(n.groupby('wave').agg(rows=('egoid','size'),egos=('egoid','nunique'),instudy=('instudy','sum'),friend=('friend','sum')))
print('friend values',n.friend.value_counts(dropna=False).to_dict())
print('reltypecat',n.reltypecat.value_counts(dropna=False).head(8).to_dict())
bf=[c for c in b.columns if c.startswith('BigFive_1_')]
print('BFI waves:',bf)
for w in [1,2,3,4,5,6,7,8]:
    c=f'BigFive_1_{w}'
    if c in b: print(w, b[c].notna().sum())
