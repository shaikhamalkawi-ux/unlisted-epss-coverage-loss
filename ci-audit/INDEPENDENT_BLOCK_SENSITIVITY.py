#!/usr/bin/env python3
"""Exploratory verification only: new deterministic 4/5/8/13-week circular moving-block intervals.
Not the missing historical 18/30 saved-output lineage; do not backfill UNLISTED42.
"""
from pathlib import Path
import pandas as pd,numpy as np,hashlib,math,json
R=Path(__file__).resolve().parent
D=pd.read_csv(R/'frozen_input_tables/ablation/Unlisted9_Ablation_DateLevel.csv',parse_dates=['decision_date']).sort_values('decision_date')
D=D[D.specification.eq('A5_full_trajectory')]
rows=[]
for fam,g in D.groupby('fold_family'):
 x=g.paired_ap_difference.to_numpy(dtype=float)
 for weeks in [4,5,8,13]:
  if weeks>=len(x):
   rows.append(dict(family=fam,block_weeks=weeks,dates=len(x),mean=x.mean(),ci95_lower=None,ci95_upper=None,classification='UNINFORMATIVE_BLOCK_SPANS_WINDOW',new_audit=True))
   continue
  b=min(weeks,len(x));k=math.ceil(len(x)/b)
  digest=hashlib.sha256(f'{260711}|{b}|{len(x)}|'.encode()+np.ascontiguousarray(x,dtype=np.float64).tobytes()).digest()
  rng=np.random.default_rng(int.from_bytes(digest[:8],'big')%(2**32))
  starts=rng.integers(0,len(x),size=(5000,k))
  idx=(starts[:,:,None]+np.arange(b)[None,None,:])%len(x)
  draws=x[idx.reshape(5000,-1)[:,:len(x)]].mean(axis=1)
  lo,hi=map(float,np.quantile(draws,[.025,.975]))
  clas='POSITIVE_INTERVAL' if lo>0 else ('NEGATIVE_INTERVAL' if hi<0 else 'CROSSES_ZERO')
  rows.append(dict(family=fam,block_weeks=weeks,dates=len(x),mean=x.mean(),ci95_lower=lo,ci95_upper=hi,classification=clas,new_audit=True))
pd.DataFrame(rows).to_csv(R/'replay_results/INDEPENDENT_BLOCK_LENGTH_SENSITIVITY_NOT_ORIGINAL.csv',index=False)
print(pd.DataFrame(rows).to_string(index=False))
