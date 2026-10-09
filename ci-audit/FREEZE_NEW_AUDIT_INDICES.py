#!/usr/bin/env python3
"""Freeze NEW audit 5,000-replicate circular moving-block draw indices.

This is NOT recovery of the original historical registry. New arrays dated 2026-10-09.
"""
from pathlib import Path
import hashlib,math,json,re
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parent
src=pd.read_csv(ROOT/'frozen_input_tables/ablation/Unlisted9_Ablation_DateLevel.csv',parse_dates=['decision_date']).sort_values('decision_date')
reg={};map_rows=[]
def append(spec,fam,b,x):
 n=len(x);k=math.ceil(n/b);di=hashlib.sha256(f'{260711}|{b}|{n}|'.encode()+np.ascontiguousarray(x,dtype=np.float64).tobytes()).digest();seed=int.from_bytes(di[:8],'big')%(2**32)
 rng=np.random.default_rng(seed)
 starts=rng.integers(0,n,size=(5000,k))
 indices=((starts[:,:,None]+np.arange(b)[None,None,:])%n).reshape(5000,-1)[:,:n].astype('<i4')
 key=f"{spec}__{fam}__b{b}";key=re.sub(r'[^A-Za-z0-9_]', '_', key)
 if key in reg:raise AssertionError('duplicate key')
 reg[key]=indices
 map_rows.append({'key':key,'specification':spec,'fold_family':fam,'block_weeks':b,'date_count':n,'seed':seed,'replicates':5000,'array_sha256':hashlib.sha256(indices.tobytes()).hexdigest()})
for (spec,fam),g in src.groupby(['specification','fold_family'],sort=True):
 x=g.paired_ap_difference.to_numpy(float)
 append(spec,fam,5,x)
 if spec=='A5_full_trajectory':
  for b in (4,8,13):
   if b>=len(x):continue
   append(spec,fam,b,x)
p=np.array(list(reg.keys()))
out=ROOT/'replay_results/NEW_AUDIT_MBB_INDICES_20261009.npz';out.parent.mkdir(exist_ok=True)
np.savez_compressed(out,**reg)
(ROOT/'replay_results/NEW_AUDIT_MBB_INDICES_MAP.json').write_text(json.dumps({'warning':'NEW audit-generated indices; NOT recovered 2026 historical bootstrap registry','expected_missing_historical_registry_sha256':'3518700e8779bdcf4ce8745ffc0c3aa87f58515cfbb991729ffb5a5bd604226b','npz_file':out.name,'npz_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'arrays':map_rows},indent=2)+'\n')
assert len(map_rows)==26, len(map_rows)
check=np.load(out,allow_pickle=False)
for meta in map_rows:
 assert hashlib.sha256(check[meta['key']].tobytes()).hexdigest()==meta['array_sha256']
print('SAVED_NEW_AUDIT_REGISTRY',len(reg),'arrays','zip_bytes',out.stat().st_size,'sha256',hashlib.sha256(out.read_bytes()).hexdigest())
