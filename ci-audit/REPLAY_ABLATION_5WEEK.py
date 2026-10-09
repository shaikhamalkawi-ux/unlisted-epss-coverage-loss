#!/usr/bin/env python3
"""Independent replay of the 18 saved 5-week ablation rows from frozen derived values."""
from pathlib import Path
import numpy as np, pandas as pd, hashlib, math, json
R=Path(__file__).resolve().parent
source=pd.read_csv(R/'frozen_input_tables/ablation/Unlisted9_Ablation_DateLevel.csv',parse_dates=['decision_date']).sort_values('decision_date')
target=pd.read_csv(R/'frozen_input_tables/ablation/Unlisted9_Ablation_Ridge_5Week_CI.csv')
rows=[]
for (spec,fam),group in source.groupby(['specification','fold_family'],sort=True):
    x=group.paired_ap_difference.to_numpy(float)
    b=min(5,len(x)); k=math.ceil(len(x)/b)
    digest=hashlib.sha256(f'{260711}|{b}|{len(x)}|'.encode()+np.ascontiguousarray(x,dtype=np.float64).tobytes()).digest()
    rng=np.random.default_rng(int.from_bytes(digest[:8],'big')%(2**32))
    starts=rng.integers(0,len(x),size=(5000,k))
    idx=(starts[:,:,None]+np.arange(b)[None,None,:])%len(x)
    lo,hi=np.quantile(x[idx.reshape(5000,-1)[:,:len(x)]].mean(axis=1),[.025,.975])
    rows.append(dict(specification=spec,fold_family=fam,date_count=len(x),mean=x.mean(),ci95_lower=float(lo),ci95_upper=float(hi),block_weeks=5,replicates=5000,seed=260711))
current=pd.DataFrame(rows).sort_values(['specification','fold_family']).reset_index(drop=True)
original=target.sort_values(['specification','fold_family']).reset_index(drop=True)
assert len(current)==18 and len(original)==18
check=current[['specification','fold_family']].copy()
for c in ['date_count','mean','ci95_lower','ci95_upper','block_weeks','replicates','seed']:
 check[c+'_saved']=original[c]
 check[c+'_replay']=current[c]
 if pd.api.types.is_numeric_dtype(current[c]):check[c+'_absolute_error']=(original[c]-current[c]).abs()
 else:check[c+'_matched']=original[c]==current[c]
check['matched_tol_1e-12']=(check['ci95_lower_absolute_error']<=1e-12)&(check['ci95_upper_absolute_error']<=1e-12)&(check['mean_absolute_error']<=1e-12)&(check['date_count_saved']==check['date_count_replay'])
out=R/'replay_results';out.mkdir(exist_ok=True)
check.to_csv(out/'ABLATION_5WEEK_EXACT_REPLAY.csv',index=False)
summary={'archive_5week_ablation_rows':18,'matched_1e-12':int(check.matched_tol_1e_12.sum()) if hasattr(check,'matched_tol_1e_12') else int(check['matched_tol_1e-12'].sum()),'max_abs_endpoint_error':float(max(check['ci95_lower_absolute_error'].max(),check['ci95_upper_absolute_error'].max())),'resampling':'5-week circular moving-block bootstrap','seed':260711,'replicates':5000}
(out/'ABLATION_5WEEK_EXACT_REPLAY_SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
print('ABLATION',json.dumps(summary))
assert summary['matched_1e-12']==18
