#!/usr/bin/env python3
"""Acquire only 106 exact E01 files. A different hash is never admitted.
Network-enabled execution required. No credentials, API pagination or current scores.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,urllib.request,urllib.parse
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
ALLOWED={'epss.empiricalsecurity.com','raw.githubusercontent.com'}

def acquire(row,out):
    day=row['observation_date'];name=f'epss_scores-{day}.csv.gz';dest=out/name
    expected=int(row['bytes']);want=row['sha256'];logs=[]
    if dest.exists():
        h=hashlib.sha256(dest.read_bytes()).hexdigest()
        return {'date':day,'status':'PASS_EXISTING' if h==want and dest.stat().st_size==expected else 'HOLD_EXISTING_MISMATCH','sha256':h,'attempts':logs}
    urls=[row['url'],f'https://raw.githubusercontent.com/empiricalsec/epss_scores/main/{day[:4]}/{name}']
    for url in urls:
        if urllib.parse.urlparse(url).hostname not in ALLOWED:raise ValueError('Unapproved source host')
        tmp=out/(name+'.partial')
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'UNLISTED-Q2b-E01-academic-hash-verification'})
            h=hashlib.sha256();total=0
            with urllib.request.urlopen(req,timeout=60) as response, tmp.open('xb') as f:
                while True:
                    chunk=response.read(65536)
                    if not chunk:break
                    total+=len(chunk)
                    if total>expected:raise ValueError('Body exceeds exact recorded source length')
                    h.update(chunk);f.write(chunk)
                final_url=response.geturl()
            actual=h.hexdigest()
            if total!=expected or actual!=want:raise ValueError(f'Exact-source mismatch: bytes={total},sha256={actual}')
            tmp.replace(dest)
            logs.append({'url':url,'resolved_url':final_url,'status':'PASS_EXACT_BYTES'})
            return {'date':day,'status':'PASS_DOWNLOADED','bytes':total,'sha256':actual,'attempts':logs}
        except Exception as e:
            logs.append({'url':url,'status':'FAILED','error':str(e)})
            if tmp.exists():tmp.unlink()
    return {'date':day,'status':'HOLD_NOT_ACQUIRED','attempts':logs}

def main():
    a=argparse.ArgumentParser();a.add_argument('--output-dir',type=Path,default=ROOT/'raw/epss');a.add_argument('--report',type=Path,required=True);a.add_argument('--only-date',help='Acquisition diagnostic only; never sufficient for evaluation')
    args=a.parse_args()
    if args.report.exists():raise SystemExit('Refusing to overwrite an acquisition report')
    args.output_dir.mkdir(parents=True,exist_ok=True)
    rows=list(csv.DictReader((ROOT/'inputs/required_test_source_manifest.csv').open()))
    if args.only_date:rows=[r for r in rows if r['observation_date']==args.only_date]
    if not rows:raise SystemExit('Requested date not in the frozen required source set')
    reports=[]
    for row in rows:
        r=acquire(row,args.output_dir);reports.append(r);print(row['observation_date'],r['status'],flush=True)
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps({'utc':datetime.now(timezone.utc).isoformat(),'required_for_full_evaluation':106,'attempted_dates':len(reports),'records':reports},indent=2)+'\n')
    return 0 if all(r['status'].startswith('PASS_') for r in reports) else 2
if __name__=='__main__':raise SystemExit(main())
