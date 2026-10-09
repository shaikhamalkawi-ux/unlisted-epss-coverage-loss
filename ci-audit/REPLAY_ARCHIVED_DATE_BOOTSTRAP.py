#!/usr/bin/env python3
"""Audit only: replay legacy archived bootstrap outputs using archived stream seeds and saved decimal rows.

IMPORTANT: this replays the ORIGINAL `bootstrap_mean_by_date` independent per-date resampling
which is not the later 5-week moving-block interval analysis.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import json
ROOT=Path(__file__).resolve().parent/'frozen_input_tables'
OUT=Path(__file__).resolve().parent/'replay_results'
FAMS={'paired_date_block_bootstrap.csv':{'paired_ap_difference':'date_level_model_comparison.csv','paired_ap_lift_difference':'date_level_model_comparison.csv','paired_recall_difference':'budget_level_model_comparison.csv','paired_precision_difference':'budget_level_model_comparison.csv'},'sampling_rate_sensitivity_date_block_bootstrap.csv':None}
DATA={}
RESULTS=[]
for family in ['locked_results/trajectory_model','current_environment_reproduction']:
 DATA[family]={n:pd.read_csv(ROOT/family/n) for n in ['paired_date_block_bootstrap.csv','sampling_rate_sensitivity_date_block_bootstrap.csv','date_level_model_comparison.csv','budget_level_model_comparison.csv','sampling_rate_sensitivity_date_level.csv','sampling_rate_sensitivity_budget_level.csv']}
 for output in ('paired_date_block_bootstrap.csv','sampling_rate_sensitivity_date_block_bootstrap.csv'):
  archived=DATA[family][output]
  for seq,t in archived.iterrows():
   met=t.metric
   data_name=('date_level_model_comparison.csv' if met in ('paired_ap_difference','paired_ap_lift_difference') else 'budget_level_model_comparison.csv') if output.startswith('paired_') else ('sampling_rate_sensitivity_date_level.csv' if str(t.get('budget_type',''))=='nan' or pd.isna(t.get('budget_type')) else 'sampling_rate_sensitivity_budget_level.csv')
   d=DATA[family][data_name]
   conditions={c:t[c] for c in ['negative_sample_rate','alternative_negative_sample_rate','primary_negative_sample_rate','fold_family','expected_version_regime','budget_type','budget_value','budget_label'] if c in archived.columns and c in d.columns and pd.notna(t[c])}
   g=d
   for k,v in conditions.items():
    g=g[g[k]==v]
   # value source is table metric; budget group equality exact by numeric float budget_value
   if met not in g.columns:
    raise AssertionError(f'Missing {met} in {data_name} at {family} output {output} row {seq}')
   values=pd.to_numeric(g[met],errors='coerce').dropna().to_numpy(float)
   if not len(values):raise AssertionError(f'Empty source values for {output} row {seq}, conditions={conditions}')
   if len(values)!=int(t.date_blocks):raise AssertionError(f'row count difference at {output}:{seq}: {len(values)} != {t.date_blocks}')
   rng=np.random.default_rng(int(t.bootstrap_stream_seed)); mean=float(values.mean()); reps=int(t.bootstrap_replicates)
   if len(values)==1:low=high=mean
   else:
    idx=rng.integers(0,len(values),size=(reps,len(values)))
    draws=values[idx].mean(axis=1)
    low,high=map(float,np.quantile(draws,[.025,.975]))
   delta=max(abs(low-t.ci95_lower),abs(high-t.ci95_upper)); mean_delta=abs(mean-t['mean'])
   RESULTS.append({'source':family,'table':output,'original_csv_row':seq+2,'metric':met,'fold_family':t.fold_family,'negative_sample_rate':t.get('negative_sample_rate'), 'alternative_negative_sample_rate':t.get('alternative_negative_sample_rate'), 'budget_type':t.get('budget_type'),'budget_value':t.get('budget_value'),'bootstrap_stream_seed':int(t.bootstrap_stream_seed),'date_blocks':int(t.date_blocks),'bootstrap_replicates':reps,'mean_saved':float(t['mean']),'mean_replay':mean,'lower_saved':float(t.ci95_lower),'lower_replay':low,'upper_saved':float(t.ci95_upper),'upper_replay':high,'max_abs_interval_endpoint_difference':delta,'abs_mean_difference':mean_delta,'within_1e12':bool(delta<=1e-12 and mean_delta<=1e-12)})
 report=pd.DataFrame([r for r in RESULTS if r['source']==family])
 print(family,len(report),'within tol',int(report.within_1e12.sum()),'max endpoint diff',report.max_abs_interval_endpoint_difference.max(),'worst mean',report.abs_mean_difference.max(),flush=True)
all_=pd.DataFrame(RESULTS)
all_.to_csv(OUT/'ARCHIVED_BOOTSTRAP_ALL_REPLAY.csv',index=False)
status={'scope':'Archived date-resampling outputs only (not historical 5-week moving-block interval registry)','records':len(all_),'matched_at_1e-12':int(all_.within_1e12.sum()),'maximum_interval_endpoint_error':float(all_.max_abs_interval_endpoint_difference.max()),'maximum_mean_error':float(all_.abs_mean_difference.max()),'records_by_table':all_.groupby(['source','table']).size().to_dict()}
status['records_by_table']={'|'.join(k):int(v) for k,v in status['records_by_table'].items()}
(OUT/'ARCHIVED_BOOTSTRAP_ALL_REPLAY_SUMMARY.json').write_text(json.dumps(status,indent=2)+'\n')
print('STATUS',json.dumps(status))
