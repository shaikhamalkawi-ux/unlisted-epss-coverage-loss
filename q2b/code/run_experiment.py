#!/usr/bin/env python3
"""Run E01 in a new directory; never overwrite UNLISTED40 or inherited results.
Modes: audit, training-check, evaluate. Full-panel evaluation is fail-closed.
"""
from __future__ import annotations
import argparse,csv,gzip,hashlib,json,platform,sys,time,warnings
from pathlib import Path
from datetime import date,timedelta,datetime,timezone
from functools import lru_cache
import numpy as np
import pandas as pd
import scipy,sklearn
from scipy.special import expit
from scipy.stats import rankdata
from fuzzy_core import GateError,fit_sugeno,score_sugeno,fit_reduced_logistic,score_reduced_logistic,average_precision,topk_ties

ROOT=Path(__file__).resolve().parents[1]
FEATURES=['logit_epss_current','percentile_current','delta_logit_1w','delta_logit_4w','epss_max_4w','epss_range_4w','missing_lag_1w','missing_lag_4w']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def logit(x):
    x=np.clip(np.asarray(x,float),1e-8,1-1e-8);return np.log(x/(1-x))
def version_from_validation(v):
    return str(v).split('model_version:',1)[1].split(',',1)[0].strip()
def verify_inputs():
    ph=sha(ROOT/'PROTOCOL.json');expected=(ROOT/'PROTOCOL_SHA256.txt').read_text().split()[0]
    if ph!=expected:raise GateError('Frozen protocol hash mismatch')
    trace=pd.read_csv(ROOT/'inputs/INPUT_TRACE.csv');bad=[]
    for r in trace.itertuples():
        p=ROOT/r.package_path
        if not p.is_file() or p.stat().st_size!=r.bytes or sha(p)!=r.sha256:bad.append(r.package_path)
    if bad:raise GateError('Derived/source input integrity failures: '+str(bad))
    original=pd.read_csv(ROOT/'inputs/original_folds.csv');folds=pd.read_csv(ROOT/'inputs/folds.csv')
    pd.testing.assert_frame_equal(original[original.negative_sample_rate.eq(.005)].reset_index(drop=True),folds,check_dtype=False)
    kev=pd.read_csv(ROOT/'inputs/frozen_kev.csv');kev['dateAdded']=pd.to_datetime(kev.dateAdded).dt.date
    if len(kev)!=1637 or not kev.cveID.is_unique:raise GateError('Frozen KEV identity')
    manifest=pd.read_csv(ROOT/'inputs/original_download_manifest.csv');manifest=manifest[manifest.source.eq('FIRST_EPSS')]
    versions={r.observation_date:version_from_validation(r.validation) for r in manifest.itertuples()}
    samples=pd.read_csv(ROOT/'inputs/original_sample_manifest.csv')
    test_dates=[]
    for f in folds.itertuples():test_dates.extend(samples[samples.decision_date.between(f.test_start,f.test_end)].decision_date.tolist())
    needed=sorted({(date.fromisoformat(d)-timedelta(days=lag)).isoformat() for d in test_dates for lag in (0,7,28)})
    req=pd.read_csv(ROOT/'inputs/required_test_source_manifest.csv')
    if len(test_dates)!=102 or len(set(test_dates))!=102 or sorted(req.observation_date)!=needed or len(needed)!=106:raise GateError('Exact date-support mismatch')
    expectedreq=manifest[manifest.observation_date.isin(needed)].reset_index(drop=True)
    pd.testing.assert_frame_equal(req,expectedreq,check_dtype=False)
    return ph,folds,kev,versions,samples,req,len(trace)

def raw_gate(req,rawdir):
    rows=[]
    for r in req.itertuples():
        p=rawdir/f'epss_scores-{r.observation_date}.csv.gz';exist=p.is_file()
        actual=sha(p) if exist else None; length=p.stat().st_size if exist else None
        status='PASS' if exist and actual==r.sha256 and length==r.bytes else ('MISMATCH' if exist else 'MISSING')
        rows.append({'date':r.observation_date,'file':p.name,'expected_sha256':r.sha256,'expected_bytes':int(r.bytes),'actual_sha256':actual,'actual_bytes':length,'status':status})
    return pd.DataFrame(rows)

def load_training(fold,kev):
    k=kev.set_index('cveID').dateAdded; frames=[]
    for p in sorted((ROOT/'inputs/training_samples').glob('*.csv.gz')):
        ds=p.name[len('trajectory_sample_'):-len('.csv.gz')]
        if not fold.train_start<=ds<=fold.train_end:continue
        d=pd.read_csv(p); t=date.fromisoformat(ds)
        if not d.cve.is_unique or not d.decision_date.eq(ds).all():raise GateError('Duplicate or wrongly dated training sample')
        kd=d.cve.map(k);already=kd.notna()&(kd<=t)
        y=(kd.notna()&(kd>t)&(kd<=t+timedelta(days=30))).astype(int)
        if already.any() or not np.array_equal(y.to_numpy(),d.outcome.to_numpy()):raise GateError('Training endpoint/prior-KEV mismatch')
        d=d[d.outcome.eq(1)|d.sampling_uniform.lt(.005)].copy();frames.append(d)
    d=pd.concat(frames,ignore_index=True)
    if d.decision_date.nunique()!=fold.train_dates or len(d)!=fold.train_rows or int(d.outcome.sum())!=fold.train_events:raise GateError('Training support does not reproduce locked fold')
    if date.fromisoformat(fold.train_end)+timedelta(days=30)>=date.fromisoformat(fold.test_start):raise GateError('Embargo violation')
    d['weight']=np.where(d.outcome.eq(1),1.0,200.0)
    return d

def history_inputs(d,versions,aware=False):
    x=d.logit_epss_current.to_numpy(float);delta=d.delta_logit_1w.to_numpy(float)
    missing=d.missing_lag_1w.to_numpy(int).astype(bool)
    crossing=np.array([versions[t]!=versions[(date.fromisoformat(t)-timedelta(days=7)).isoformat()] for t in d.decision_date],bool)
    unavailable=missing|(crossing if aware else False)
    return x,np.where(unavailable,0,delta),unavailable,missing,crossing

def train_fold(f,kev,versions,ph,out):
    d=load_training(f,kev);y=d.outcome.to_numpy(int);w=d.weight.to_numpy(float)
    models={'fold':f._asdict(),'protocol_sha256':ph,'not_held_out_performance':True}
    for aware,label in [(False,'primary'),(True,'version_aware')]:
        x,delta,u,missing,cross=history_inputs(d,versions,aware)
        models['fuzzy_'+label]=fit_sugeno(x,delta,u,y,w)
        models['reduced_'+label]=fit_reduced_logistic(x,delta,u,y,w)
        models['history_'+label]={'missing_rows':int(missing.sum()),'cross_version_rows':int(cross.sum()),'unavailable_rows':int(u.sum())}
    save(out/'models'/f'{f.fold_id}.json',models)
    return models

@lru_cache(maxsize=6)
def read_raw(p):
    p=Path(p)
    with gzip.open(p,'rt') as g:header=g.readline().strip()
    if not header.startswith('#') or 'model_version:' not in header:raise GateError('Missing EPSS version header')
    v=header.split('model_version:',1)[1].split(',',1)[0].strip()
    d=pd.read_csv(p,comment='#',dtype={'cve':str,'epss':float,'percentile':float})
    if not d.cve.is_unique or not np.isfinite(d[['epss','percentile']]).all().all() or not d.epss.between(0,1).all():raise GateError('Invalid raw candidate population')
    return d,v

def panel(ds,raw,kev,versions):
    t=date.fromisoformat(ds);paths=[raw/f'epss_scores-{(t-timedelta(days=l)).isoformat()}.csv.gz' for l in (0,7,28)]
    data=[read_raw(str(p)) for p in paths]
    for p,(_,v) in zip(paths,data):
        day=p.name[len('epss_scores-'):-len('.csv.gz')]
        if v!=versions[day]:raise GateError('Raw header version mismatch')
    d=data[0][0].rename(columns={'epss':'epss_current','percentile':'percentile_current'}).copy()
    for suffix,(lag,_) in zip(['lag1','lag4'],data[1:]):d=d.merge(lag[['cve','epss']].rename(columns={'epss':'epss_'+suffix}),on='cve',how='left',validate='one_to_one')
    kd=d.cve.map(kev.set_index('cveID').dateAdded); keep=~(kd.notna()&(kd<=t));d=d[keep].copy();kd=kd[keep]
    d['outcome']=(kd.notna()&(kd>t)&(kd<=t+timedelta(days=30))).astype(int)
    d['missing_lag_1w']=d.epss_lag1.isna().astype(int);d['missing_lag_4w']=d.epss_lag4.isna().astype(int)
    p1=d.epss_lag1.fillna(d.epss_current);p4=d.epss_lag4.fillna(d.epss_current);x=logit(d.epss_current)
    d['logit_epss_current']=x;d['delta_logit_1w']=x-logit(p1);d['delta_logit_4w']=x-logit(p4)
    hist=np.column_stack((d.epss_current,p1,p4));d['epss_max_4w']=hist.max(1);d['epss_range_4w']=hist.max(1)-hist.min(1)
    d['decision_date']=ds;return d.reset_index(drop=True)

def full_score(d,fid):
    c=pd.read_csv(ROOT/'inputs/original_full_logistic_coefficients.csv');c=c[c.fold_id.eq(fid)&c.negative_sample_rate.eq(.005)].set_index('feature')
    if len(c)!=9 or not c.index.is_unique:raise GateError('Saved coefficient identity mismatch')
    z=(d[FEATURES].to_numpy(float)-c.loc[FEATURES,'standardization_mean'].to_numpy())/c.loc[FEATURES,'standardization_scale'].to_numpy()
    return expit(z@c.loc[FEATURES,'standardized_log_odds_coefficient'].to_numpy()+c.loc['INTERCEPT','standardized_log_odds_coefficient'])

def auc(y,s):
    n1=int(y.sum());n0=len(y)-n1
    return float((rankdata(s)[y==1].sum()-n1*(n1+1)/2)/(n1*n0)) if n1 and n0 else float('nan')

def evaluation(folds,kev,versions,samples,raw,out,models):
    orig=pd.read_csv(ROOT/'inputs/original_date_metrics.csv');orig=orig[orig.negative_sample_rate.eq(.005)].set_index(['fold_id','decision_date'])
    rows=[];support=[];eventsets={};seen=set();eligible_outcomes=set();alltest=[]
    for f in folds.itertuples(index=False):
        dates=samples[samples.decision_date.between(f.test_start,f.test_end)].decision_date
        for ds in dates:
            alltest.append(ds);d=panel(ds,raw,kev,versions); y=d.outcome.to_numpy(int);old=orig.loc[(f.fold_id,ds)]
            epss=d.epss_current.to_numpy(float);full=full_score(d,f.fold_id)
            passed=(len(d)==old.candidate_cves and int(y.sum())==old.future_kev_events and abs(average_precision(y,epss)-old.epss_average_precision)<=1e-12 and abs(average_precision(y,full)-old.model_average_precision)<=1e-12)
            support.append({'fold_id':f.fold_id,'date':ds,'candidates':len(d),'events':int(y.sum()),'epss_ap_replay':average_precision(y,epss),'full_logistic_ap_replay':average_precision(y,full),'full_logistic_ap_locked':old.model_average_precision,'status':'PASS' if passed else 'HOLD'})
            pd.DataFrame(support).to_csv(out/'PANEL_REPLAY_GATE.csv',index=False)
            if not passed:raise GateError(f'Full-panel baseline replay HOLD at {f.fold_id}/{ds}; no tolerance change or inherited-result replacement.')
            scores={'epss':epss,'full_logistic_locked':full}
            for aware,label in [(False,'primary'),(True,'version_aware')]:
                x,delta,u,miss,cross=history_inputs(d,versions,aware)
                scores['fuzzy_'+label]=score_sugeno(models[f.fold_id]['fuzzy_'+label],x,delta,u)
                scores['reduced_'+label]=score_reduced_logistic(models[f.fold_id]['reduced_'+label],x,delta,u)
            t=date.fromisoformat(ds);ek=kev[kev.dateAdded.map(lambda z:t<z<=t+timedelta(days=30))].cveID
            eligible_outcomes.update(ek);seen.update(d.loc[y==1,'cve'])
            for name,s in scores.items():
                r={'fold_id':f.fold_id,'family':f.fold_family,'date':ds,'model':name,'n':len(y),'events':int(y.sum()),'AP':average_precision(y,s),'AUC':auc(y,s)}
                for k in [100,500,1000]:
                    tb=topk_ties(y,s,k);r[f'tp{k}_min']=tb['tp_min'];r[f'tp{k}_max']=tb['tp_max']
                    for bound in ['sure','possible']:
                        eventsets.setdefault((name,k,bound),set()).update(d.loc[tb[f'event_{bound}_mask'],'cve'])
                rows.append(r)
            print('FULL_PANEL_PASS',f.fold_id,ds,len(d),flush=True)
    metrics=pd.DataFrame(rows);metrics.to_csv(out/'date_level_metrics.csv',index=False)
    capture=[]
    for (name,k,bound),ids in eventsets.items():
        capture.append({'model':name,'k':k,'bound':bound,'test_dates':len(alltest),'common_outcome_denominator':len(eligible_outcomes),'common_observable_denominator':len(seen),'unique_captured':len(ids),'conditional':len(ids)/len(seen),'end_to_end_common_support':len(ids)/len(eligible_outcomes)})
    pd.DataFrame(capture).to_csv(out/'common_support_event_capture.csv',index=False)
    # This new registry is explicitly NOT the missing historical bootstrap registry.
    registry={}; summaries=[]
    for fam,g in metrics.groupby('family',sort=True):
        p=g.pivot(index='date',columns='model',values='AP').sort_index();n=len(p)
        contrasts={'fuzzy_minus_reduced':p.fuzzy_primary-p.reduced_primary,'fuzzy_minus_epss':p.fuzzy_primary-p.epss,'fuzzy_minus_full':p.fuzzy_primary-p.full_logistic_locked,'fuzzy_version_effect':p.fuzzy_version_aware-p.fuzzy_primary,'reduced_version_effect':p.reduced_version_aware-p.reduced_primary}
        for block in [4,5,8,13]:
            if block>=n:
                for name,z in contrasts.items():summaries.append({'family':fam,'contrast':name,'n_dates':n,'block':block,'mean_difference':float(np.nanmean(z)),'lower':None,'upper':None,'status':'UNINFORMATIVE_BLOCK_LENGTH'})
                continue
            seed=int.from_bytes(hashlib.sha256(f'20261007|{fam}|{block}'.encode()).digest()[:8],'little')
            rng=np.random.default_rng(seed);starts=rng.integers(0,n,size=(5000,int(np.ceil(n/block))))
            idx=((starts[:,:,None]+np.arange(block))%n).reshape(5000,-1)[:,:n]
            registry[f'{fam}__b{block}']=idx
            for name,z in contrasts.items():
                arr=z.to_numpy(float);means=np.nanmean(arr[idx],axis=1);q=np.nanquantile(means,[.025,.975])
                summaries.append({'family':fam,'contrast':name,'n_dates':n,'block':block,'mean_difference':float(np.nanmean(arr)),'lower':float(q[0]),'upper':float(q[1]),'status':'EXPLORATORY_NEW_REGISTRY'})
    np.savez_compressed(out/'NEW_E01_BOOTSTRAP_INDICES.npz',**registry)
    pd.DataFrame(summaries).to_csv(out/'paired_exploratory_intervals.csv',index=False)
    metrics.groupby(['family','model'],as_index=False).agg(n_dates=('date','size'),AP=('AP','mean'),AUC=('AUC','mean')).to_csv(out/'family_summary.csv',index=False)
    return len(support)

def main():
    a=argparse.ArgumentParser();a.add_argument('mode',choices=['audit','training-check','evaluate']);a.add_argument('--raw-dir',type=Path,default=ROOT/'raw/epss');a.add_argument('--output',type=Path,required=True);a.add_argument('--fold',help='training-check only, e.g. F01; evaluate always requires all eight folds')
    args=a.parse_args();out=args.output.resolve()
    if out.exists() and any(out.iterdir()):raise SystemExit('Refusing to overwrite a nonempty output directory')
    out.mkdir(parents=True,exist_ok=True)
    state={'mode':args.mode,'started_utc':datetime.now(timezone.utc).isoformat(),'manuscript_modified':False,'held_out_performance_computed':False}
    try:
        ph,folds,kev,versions,samples,req,tracen=verify_inputs();state.update(protocol_sha256=ph,verified_traced_inputs=tracen)
        gate=raw_gate(req,args.raw_dir);gate.to_csv(out/'RAW_SOURCE_GATE.csv',index=False)
        state.update(raw_required=len(gate),raw_pass=int(gate.status.eq('PASS').sum()),raw_missing=int(gate.status.eq('MISSING').sum()),raw_mismatch=int(gate.status.eq('MISMATCH').sum()))
        save(out/'ENVIRONMENT.json',{'python':sys.version,'platform':platform.platform(),'numpy':np.__version__,'pandas':pd.__version__,'scipy':scipy.__version__,'sklearn':sklearn.__version__})
        if args.mode=='audit':state['status']='INPUTS_VERIFIED_RAW_READY' if state['raw_pass']==len(gate) else 'INPUTS_VERIFIED_RAW_HOLD'
        else:
            if args.mode=='evaluate' and state['raw_pass']!=len(gate):raise GateError('All 106 exact raw source files are required before held-out evaluation')
            if args.mode=='evaluate' and args.fold:raise GateError('Partial evaluation is disallowed')
            selected=folds if not args.fold else folds[folds.fold_id.eq(args.fold)]
            if len(selected)==0:raise GateError('Unknown training fold')
            models={}
            for f in selected.itertuples(index=False):
                models[f.fold_id]=train_fold(f,kev,versions,ph,out);print('TRAINING_CHECK_PASS',f.fold_id,flush=True)
            state['training_folds_checked']=len(models)
            if args.mode=='training-check':state['status']='TRAINING_CHECK_ONLY_NOT_PERFORMANCE'
            else:
                state['evaluated_dates']=evaluation(folds,kev,versions,samples,args.raw_dir,out,models)
                state['held_out_performance_computed']=True;state['status']='EXPLORATORY_EVALUATION_COMPLETE_NOT_MANUSCRIPT_APPROVAL'
    except Exception as e:
        state['status']='HOLD';state['error']=str(e);save(out/'RUN_STATUS.json',state);print(json.dumps(state,indent=2));return 2
    save(out/'RUN_STATUS.json',state);print(json.dumps(state,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
