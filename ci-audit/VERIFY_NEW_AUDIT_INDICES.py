#!/usr/bin/env python3
"""Verify archived independent new-audit MBB indices against saved endpoints, not old missing registry."""
from pathlib import Path
import hashlib,json,numpy as np,pandas as pd
R=Path(__file__).resolve().parent
mapj=json.loads((R/'replay_results/NEW_AUDIT_MBB_INDICES_MAP.json').read_text())
reg=R/'replay_results'/mapj['npz_file']
assert hashlib.sha256(reg.read_bytes()).hexdigest()==mapj['npz_sha256']
D=pd.read_csv(R/'frozen_input_tables/ablation/Unlisted9_Ablation_DateLevel.csv',parse_dates=['decision_date']).sort_values('decision_date')
S=pd.read_csv(R/'frozen_input_tables/ablation/Unlisted9_Ablation_Ridge_5Week_CI.csv')
T=pd.read_csv(R/'replay_results/INDEPENDENT_BLOCK_LENGTH_SENSITIVITY_NOT_ORIGINAL.csv')
count_abl=0;count_sens=0;mx=0.;errors=[]
with np.load(reg,allow_pickle=False) as data:
 for m in mapj['arrays']:
  a=data[m['key']]
  if hashlib.sha256(a.tobytes()).hexdigest()!=m['array_sha256']:errors.append('array_hash_mismatch:'+m['key'])
  f=D[(D.specification==m['specification'])&(D.fold_family==m['fold_family'])]
  vals=f.paired_ap_difference.to_numpy(float)
  assert a.shape==(5000,len(vals))
  lo,hi=np.quantile(vals[a].mean(axis=1),[.025,.975]); m['computed_lo']=float(lo);m['computed_hi']=float(hi)
  if m['block_weeks']==5:
   r=S[(S.specification==m['specification'])&(S.fold_family==m['fold_family'])]
   if len(r)!=1:errors.append('missing_source_5wk:'+m['key']);continue
   ref_lo=float(r.iloc[0].ci95_lower);ref_hi=float(r.iloc[0].ci95_upper)
   count_abl+=1
  else:
   r=T[(T.family==m['fold_family'])&(T.block_weeks==m['block_weeks'])]
   if len(r)!=1:errors.append('missing_new_sensitivity:'+m['key']);continue
   ref_lo=float(r.iloc[0].ci95_lower);ref_hi=float(r.iloc[0].ci95_upper)
   count_sens+=1
  dif=max(abs(lo-ref_lo),abs(hi-ref_hi));mx=max(mx,dif)
  if dif>1e-12:errors.append(f'interval_mismatch:{m["key"]}:{dif}')
summary={'new_index_arrays':len(mapj['arrays']),'abl_5week_rows_checked':count_abl,'other_block_rows_checked':count_sens,'max_abs_endpoint_error':mx,'failures':errors,'passed':not errors and count_abl==18 and count_sens==8,'historical_registry_recovered':False}
(R/'replay_results/NEW_AUDIT_INDEX_VERIFICATION.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
assert summary['passed']
