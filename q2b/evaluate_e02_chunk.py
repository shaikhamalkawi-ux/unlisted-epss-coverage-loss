#!/usr/bin/env python3
import argparse,json,sys,hashlib
from pathlib import Path
from datetime import date,timedelta,datetime,timezone
import numpy as np,pandas as pd
sys.path.insert(0,str(Path(__file__).parent/'code'))
import run_experiment as r
ROOT=Path(__file__).parent;RAW=ROOT/'raw/epss'
E02_HASH=(ROOT/'E02_PROTOCOL_AMENDMENT_SHA256.txt').read_text().split()[0]
EXPECTED_HASH=hashlib.sha256((ROOT/'E02_PROTOCOL_AMENDMENT.json').read_bytes()).hexdigest()
if E02_HASH!=EXPECTED_HASH:raise SystemExit('E02 protocol hash mismatch')
EXC_FOLD='F03';EXC_DATE='2025-01-28';EXC_LEGACY=0.0005504560627005;EXC_REPLAY=0.0005503592967540049

def load_models():
    out={}
    for fid in [f'F{i:02d}' for i in range(1,9)]:
        p=(ROOT/'training_checks/ALL_FOLDS/models'/f'{fid}.json') if fid in {'F01','F02','F03','F04','F05'} else (ROOT/'training_checks'/fid/'models'/f'{fid}.json')
        out[fid]=json.loads(p.read_text())
    return out

def date_index(folds,samples):
    x=[]
    for f in folds.itertuples(index=False):
        for ds in samples[samples.decision_date.between(f.test_start,f.test_end)].decision_date:x.append((f.fold_id,f.fold_family,ds))
    return x

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--start',type=int,required=True);ap.add_argument('--end',type=int,required=True);a=ap.parse_args()
    ph,folds,kev,versions,samples,req,tracen=r.verify_inputs();gate=r.raw_gate(req,RAW)
    if not gate.status.eq('PASS').all():raise SystemExit('RAW HOLD')
    idx=date_index(folds,samples);todo=idx[a.start:a.end]
    if len(idx)!=102 or not todo:raise SystemExit('DATE SUPPORT HOLD')
    out=ROOT/'e02_chunks'/f'chunk_{a.start:03d}_{a.end:03d}'
    if out.exists():
        import shutil;shutil.rmtree(out)
    out.mkdir(parents=True)
    models=load_models();orig=pd.read_csv(ROOT/'inputs/original_date_metrics.csv');orig=orig[orig.negative_sample_rate.eq(.005)].set_index(['fold_id','decision_date'])
    rows=[];support=[];capture=[];eligible=[];seen=[]
    for fid,family,ds in todo:
        d=r.panel(ds,RAW,kev,versions);y=d.outcome.to_numpy(int);old=orig.loc[(fid,ds)]
        epss=d.epss_current.to_numpy(float);full=r.full_score(d,fid);ea=r.average_precision(y,epss);fa=r.average_precision(y,full)
        base_ok=(len(d)==old.candidate_cves and int(y.sum())==old.future_kev_events and abs(ea-old.epss_average_precision)<=1e-12)
        if (fid,ds)==(EXC_FOLD,EXC_DATE):
            full_ok=(abs(old.model_average_precision-EXC_LEGACY)<=1e-15 and abs(fa-EXC_REPLAY)<=1e-15)
            full_status='PREDECLARED_LINEAGE_EXCEPTION'
        else:
            full_ok=abs(fa-old.model_average_precision)<=1e-12;full_status='PASS' if full_ok else 'HOLD'
        ok=base_ok and full_ok
        support.append({'fold_id':fid,'family':family,'date':ds,'candidates':len(d),'events':int(y.sum()),'epss_ap_replay':ea,'epss_ap_legacy':old.epss_average_precision,'full_logistic_ap_replayable':fa,'full_logistic_ap_legacy':old.model_average_precision,'full_difference_replay_minus_legacy':fa-old.model_average_precision,'full_status':full_status,'status':'PASS' if ok else 'HOLD'})
        if not ok:
            pd.DataFrame(support).to_csv(out/'support.csv',index=False);raise SystemExit(f'E02 BASELINE HOLD {fid}/{ds}')
        scores={'epss':epss,'full_logistic_replayable':full}
        for aware,label in [(False,'primary'),(True,'version_aware')]:
            x,delta,u,miss,cross=r.history_inputs(d,versions,aware)
            scores['fuzzy_'+label]=r.score_sugeno(models[fid]['fuzzy_'+label],x,delta,u)
            scores['reduced_'+label]=r.score_reduced_logistic(models[fid]['reduced_'+label],x,delta,u)
        t=date.fromisoformat(ds)
        for c in kev[kev.dateAdded.map(lambda z:t<z<=t+timedelta(days=30))].cveID:eligible.append({'date':ds,'cve':c})
        for c in d.loc[y==1,'cve']:seen.append({'date':ds,'cve':c})
        for name,s in scores.items():
            rr={'fold_id':fid,'family':family,'date':ds,'model':name,'n':len(y),'events':int(y.sum()),'AP':r.average_precision(y,s),'AUC':r.auc(y,s),'legacy_full_ap':old.model_average_precision}
            for k in [100,500,1000]:
                tb=r.topk_ties(y,s,k);rr[f'tp{k}_min']=tb['tp_min'];rr[f'tp{k}_max']=tb['tp_max']
                for bound in ['sure','possible']:
                    for c in d.loc[tb[f'event_{bound}_mask'],'cve']:capture.append({'date':ds,'model':name,'k':k,'bound':bound,'cve':c})
            rows.append(rr)
        print('E02_CHUNK_PASS',a.start,a.end,fid,ds,len(d),full_status,flush=True)
    pd.DataFrame(support).to_csv(out/'support.csv',index=False);pd.DataFrame(rows).to_csv(out/'metrics.csv',index=False)
    pd.DataFrame(capture,columns=['date','model','k','bound','cve']).to_csv(out/'capture_events.csv',index=False);pd.DataFrame(eligible,columns=['date','cve']).to_csv(out/'eligible_outcomes.csv',index=False);pd.DataFrame(seen,columns=['date','cve']).to_csv(out/'seen_outcomes.csv',index=False)
    st={'status':'E02_CHUNK_COMPLETE_NOT_REPORTABLE','start':a.start,'end':a.end,'n_dates':len(todo),'first_date':todo[0][2],'last_date':todo[-1][2],'e02_protocol_sha256':E02_HASH,'finished_utc':datetime.now(timezone.utc).isoformat()};(out/'STATUS.json').write_text(json.dumps(st,indent=2)+'\n');print(json.dumps(st))
if __name__=='__main__':main()
