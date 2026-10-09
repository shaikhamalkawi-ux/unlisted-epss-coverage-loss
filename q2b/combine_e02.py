#!/usr/bin/env python3
import json,sys,hashlib,glob
from pathlib import Path
from datetime import datetime,timezone
import numpy as np,pandas as pd
sys.path.insert(0,str(Path(__file__).parent/'code'))
import run_experiment as r
ROOT=Path(__file__).parent;BASE=ROOT/'e02_chunks';OUT=ROOT/'E02_RESULTS_COMPLETE'
E02_HASH=(ROOT/'E02_PROTOCOL_AMENDMENT_SHA256.txt').read_text().split()[0]
if hashlib.sha256((ROOT/'E02_PROTOCOL_AMENDMENT.json').read_bytes()).hexdigest()!=E02_HASH:raise SystemExit('E02 HASH HOLD')
if OUT.exists():
 import shutil;shutil.rmtree(OUT)
OUT.mkdir()
ph,folds,kev,versions,samples,req,tracen=r.verify_inputs();gate=r.raw_gate(req,ROOT/'raw/epss');gate.to_csv(OUT/'RAW_SOURCE_GATE.csv',index=False)
chunks=sorted(p for p in BASE.glob('chunk_*') if (p/'STATUS.json').exists())
metrics=pd.concat([pd.read_csv(p/'metrics.csv') for p in chunks],ignore_index=True);support=pd.concat([pd.read_csv(p/'support.csv') for p in chunks],ignore_index=True);capture=pd.concat([pd.read_csv(p/'capture_events.csv') for p in chunks],ignore_index=True);elig=pd.concat([pd.read_csv(p/'eligible_outcomes.csv') for p in chunks],ignore_index=True);seen=pd.concat([pd.read_csv(p/'seen_outcomes.csv') for p in chunks],ignore_index=True)
expected=[]
for f in folds.itertuples(index=False):expected+=samples[samples.decision_date.between(f.test_start,f.test_end)].decision_date.tolist()
models=['epss','full_logistic_replayable','fuzzy_primary','reduced_primary','fuzzy_version_aware','reduced_version_aware']
if len(support)!=102 or support.date.nunique()!=102 or sorted(support.date)!=sorted(expected) or not support.status.eq('PASS').all():raise SystemExit('102-DATE SUPPORT HOLD')
if support.full_status.eq('PREDECLARED_LINEAGE_EXCEPTION').sum()!=1 or support.loc[support.full_status.eq('PREDECLARED_LINEAGE_EXCEPTION'),'date'].iloc[0]!='2025-01-28':raise SystemExit('LINEAGE EXCEPTION ID HOLD')
if len(metrics)!=102*len(models) or metrics.groupby(['date','model']).size().ne(1).any() or set(metrics.model)!=set(models):raise SystemExit('METRIC COMPLETENESS HOLD')
support.sort_values('date').to_csv(OUT/'PANEL_REPLAY_GATE.csv',index=False);metrics.sort_values(['date','model']).to_csv(OUT/'date_level_metrics.csv',index=False)
# unique-event common-support capture from actual replayable scores only
eligible_ids=set(elig.cve.astype(str));seen_ids=set(seen.cve.astype(str));caps=[]
for (name,k,bound),g in capture.groupby(['model','k','bound']):
 ids=set(g.cve.astype(str));caps.append({'model':name,'k':int(k),'bound':bound,'test_dates':102,'common_outcome_denominator':len(eligible_ids),'common_observable_denominator':len(seen_ids),'unique_captured':len(ids),'conditional':len(ids)/len(seen_ids),'end_to_end_common_support':len(ids)/len(eligible_ids)})
pd.DataFrame(caps).sort_values(['model','k','bound']).to_csv(OUT/'common_support_event_capture.csv',index=False)
# family summaries for replayable-score models
metrics.groupby(['family','model'],as_index=False).agg(n_dates=('date','size'),AP=('AP','mean'),AUC=('AUC','mean')).to_csv(OUT/'family_summary.csv',index=False)
# legacy full AP kept separately, no inferred legacy per-CVE scores
legacy=support[['fold_id','family','date','full_logistic_ap_legacy']].rename(columns={'full_logistic_ap_legacy':'AP'});legacy.groupby('family',as_index=False).agg(n_dates=('date','size'),AP=('AP','mean')).to_csv(OUT/'legacy_full_logistic_ap_summary.csv',index=False)
# bootstrap contrasts; fuzzy-vs-legacy uses saved legacy AP only
registry={};summ=[]
for fam,g in metrics.groupby('family',sort=True):
 p=g.pivot(index='date',columns='model',values='AP').sort_index();leg=legacy[legacy.family.eq(fam)].set_index('date').AP.reindex(p.index);n=len(p)
 contrasts={'fuzzy_minus_reduced':p.fuzzy_primary-p.reduced_primary,'fuzzy_minus_epss':p.fuzzy_primary-p.epss,'fuzzy_minus_full_replayable':p.fuzzy_primary-p.full_logistic_replayable,'fuzzy_minus_full_legacy_ap':p.fuzzy_primary-leg,'fuzzy_version_effect':p.fuzzy_version_aware-p.fuzzy_primary,'reduced_version_effect':p.reduced_version_aware-p.reduced_primary}
 for block in [4,5,8,13]:
  if block>=n:
   for name,z in contrasts.items():summ.append({'family':fam,'contrast':name,'n_dates':n,'block':block,'mean_difference':float(np.nanmean(z)),'lower':None,'upper':None,'status':'UNINFORMATIVE_BLOCK_LENGTH'})
   continue
  seed=int.from_bytes(hashlib.sha256(f'20261008|E02|{fam}|{block}'.encode()).digest()[:8],'little');rng=np.random.default_rng(seed);starts=rng.integers(0,n,size=(5000,int(np.ceil(n/block))));idx=((starts[:,:,None]+np.arange(block))%n).reshape(5000,-1)[:,:n];registry[f'{fam}__b{block}']=idx
  for name,z in contrasts.items():
   arr=z.to_numpy(float);means=np.nanmean(arr[idx],axis=1);q=np.nanquantile(means,[.025,.975]);summ.append({'family':fam,'contrast':name,'n_dates':n,'block':block,'mean_difference':float(np.nanmean(arr)),'lower':float(q[0]),'upper':float(q[1]),'status':'EXPLORATORY_E02_NEW_REGISTRY'})
np.savez_compressed(OUT/'NEW_E02_BOOTSTRAP_INDICES.npz',**registry);pd.DataFrame(summ).to_csv(OUT/'paired_exploratory_intervals.csv',index=False)
# lineage sensitivity delta itself
pd.DataFrame([{'fold_id':'F03','date':'2025-01-28','legacy_full_ap':0.0005504560627005,'replayable_full_ap':0.0005503592967540049,'difference':0.0005503592967540049-0.0005504560627005,'status':'PREDECLARED_LINEAGE_EXCEPTION_PRESERVED'}]).to_csv(OUT/'F03_LINEAGE_EXCEPTION.csv',index=False)
state={'status':'E02_EXPLORATORY_EVALUATION_COMPLETE_NOT_MANUSCRIPT_APPROVAL','e02_protocol_sha256':E02_HASH,'raw_pass':int(gate.status.eq('PASS').sum()),'evaluated_dates':102,'baseline_candidate_event_epss_pass':102,'full_logistic_replay_matches_legacy':101,'predeclared_lineage_exceptions':1,'held_out_performance_computed':True,'manuscript_modified':False,'finished_utc':datetime.now(timezone.utc).isoformat()};(OUT/'RUN_STATUS.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(state,indent=2))
