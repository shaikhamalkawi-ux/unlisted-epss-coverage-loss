#!/usr/bin/env python3
"""Independent stdlib EPSS/KEV historical holdout cross-check against public V5R1 release.
Does not import original experiment runner. Downloads exact Git-pinned sources, reconstructs
ranked queues and all 31 policy settings, compares 744 dated work-ledger records.
The endpoint is later CISA KEV admission, NOT exploitation onset or enterprise impact.
"""
import argparse,csv,gzip,hashlib,io,json,math,urllib.request,zipfile
from datetime import date,datetime,timezone,timedelta
from pathlib import Path
SOURCE_SHA256='fe2b6db7744b0a14f228d211b3b377145aa5a6bdcaece27eebe24048dc069ed8'
RESULT_SHA256='ab528d983de12b63f52894572ef8edd52342f0754600490602af6045e458e560'
URL='https://raw.githubusercontent.com/'
def require(x,why):
 if not x:raise RuntimeError('INDEPENDENT_SOURCE_HOLD: '+why)
def blob(data):
 return hashlib.sha1(b'blob '+str(len(data)).encode('ascii')+b'\0'+data).hexdigest()
def download(url,want,size=None):
 require(url.startswith(URL),'unexpected source host')
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'UNLISTED-V5R1-independent-raw-audit/1.0'}),timeout=120) as r:
  payload=r.read()
 require(blob(payload)==want,'Git blob digest mismatch '+url)
 if size is not None:require(len(payload)==size,'compressed file size '+url)
 return payload
def readcsv(z,name):
 return list(csv.DictReader(io.StringIO(z.read(name).decode('utf-8-sig'))))
def get_kev(raw,cutoff):
 j=json.loads(raw)
 v=j.get('vulnerabilities')
 require(isinstance(v,list),'invalid KEV JSON')
 known={}
 for r in v:
  c=r['cveID'];dt=date.fromisoformat(r['dateAdded'])
  require(c not in known and dt<=cutoff,'KEV duplicate/future entry '+c)
  known[c]=dt
 require(j.get('count')==len(known),'KEV catalog count')
 return known
def rank_snapshot(raw,day,blocked):
 with gzip.GzipFile(fileobj=io.BytesIO(raw)) as f:
  hdr=f.readline().decode('utf-8-sig','replace').strip()
  require('model_version:v2026.06.15' in hdr and 'score_date:'+str(day) in hdr,'EPSS model/date header')
  reader=csv.DictReader(io.TextIOWrapper(f,encoding='utf-8-sig',newline=''))
  require({'cve','epss'}.issubset(set(reader.fieldnames or [])),'missing EPSS columns')
  seen=set();ranked=[];n=0
  for r in reader:
   c=r['cve'];n+=1
   require(c and c not in seen,'EPSS missing/duplicate CVE')
   seen.add(c)
   v=float(r['epss'])
   require(math.isfinite(v) and 0<=v<=1,'EPSS probability invalid')
   if c not in blocked:ranked.append((-v,c))
 require(len(ranked)>=12000,'candidate prefetch insufficient')
 ranked.sort()
 return [c for _,c in ranked[:12000]],n,len(ranked)
def choose(queues,label,memory,B,lam,afford,evaldays):
 reviewed=set();last={};hits=set();weeks=[]
 for i,(day,ranked) in enumerate(queues):
  n=first=repeat=0;work=0.
  for c in ranked:
   if n==1000:break
   if i-last.get(c,-999999)<memory:continue
   price=1. if c not in reviewed or lam is None else lam
   if B is not None and work+price>B+1e-10:
    if afford=='skip':continue
    break
   n+=1;work+=price
   if c in reviewed:repeat+=1
   else:first+=1
   reviewed.add(c);last[c]=i
   if day in evaldays and c in label and 0<(label[c]-day).days<=30:hits.add(c)
  if day in evaldays:weeks.append({'date':str(day),'selected':n,'new':first,'repeat':repeat,'work':work})
 return hits,weeks
def main():
 root=Path(__file__).resolve().parent
 p=argparse.ArgumentParser()
 p.add_argument('--source',type=Path,default=root/'UNLISTED_V5R1_CorrectedHoldout_PUBLIC_SAFE_GITHUB_20261027.zip')
 p.add_argument('--results',type=Path,default=root/'UNLISTED_V5R1_HistoricalHoldout_DerivedResults_20261027.zip')
 p.add_argument('--output',type=Path,default=root/'INDEPENDENT_RAW_CROSSCHECK.json')
 a=p.parse_args()
 require(hashlib.sha256(a.source.read_bytes()).hexdigest()==SOURCE_SHA256,'source ZIP SHA256')
 require(hashlib.sha256(a.results.read_bytes()).hexdigest()==RESULT_SHA256,'derived ZIP SHA256')
 with zipfile.ZipFile(a.source) as zs,zipfile.ZipFile(a.results) as zr:
  require(zs.testzip() is None and zr.testzip() is None,'ZIP CRC')
  spec=json.loads(zs.read('provenance/V5_SOURCE_LOCK.json'))
  sr=readcsv(zr,'LOCKED_V5_SOURCE_CHECKS.csv')
  scenarios=readcsv(zr,'V5_HOLDOUT_POLICY_RESULTS.csv')
  weekly=readcsv(zr,'V5_WEEKLY_WORK.csv')
  require(len(spec['dates'])==len(sr)==15 and len(scenarios)==31 and len(weekly)==744,'source/row count')
  weekly_lookup={(r['setting'],r['policy'],r['date']):r for r in weekly}
  evaldays={date.fromisoformat(d) for d in spec['test_dates']}
  require(len(evaldays)==12,'holdout dates')
  queues=[]
  for i,pin in enumerate(spec['dates']):
   day=date.fromisoformat(pin['date'])
   require(day.weekday()==1 and (day-date(2026,6,16)).days==7*i,'unexpected Tuesday')
   for kind in ['epss','kev']:
    srcdt=datetime.fromisoformat(pin[kind+'_commit_at'].replace('Z','+00:00'))
    require(srcdt<=datetime(day.year,day.month,day.day,23,59,59,tzinfo=timezone.utc),'source clock in future')
   es=download(URL+'empiricalsec/epss_scores/'+pin['epss_commit']+'/2026/epss_scores-'+pin['date']+'.csv.gz',pin['epss_blob_sha'],pin['epss_bytes'])
   kb=download(URL+'cisagov/kev-data/'+pin['kev_commit']+'/known_exploited_vulnerabilities.json',pin['kev_blob_sha'])
   blocked=get_kev(kb,day)
   ordered,n,allowed=rank_snapshot(es,day,blocked)
   row=sr[i]
   require(row['date']==pin['date'] and row['score_blob']==pin['epss_blob_sha'] and row['kev_blob']==pin['kev_blob_sha'],'source object IDs')
   require(row['epss_sha256']==hashlib.sha256(es).hexdigest() and row['kev_sha256']==hashlib.sha256(kb).hexdigest(),'source SHA256')
   require(int(row['EPSS_candidates'])==n and int(row['eligible'])==allowed and int(row['asof_kev_count'])==len(blocked),'source row/population')
   queues.append((day,ordered))
   print('INDEPENDENT_SOURCE_PASS',i+1,pin['date'],'EPSS',n,'KEV',len(blocked),flush=True)
  frozen=spec['outcome_kev']
  labels=get_kev(download(URL+'cisagov/kev-data/'+frozen['commit']+'/known_exploited_vulnerabilities.json',frozen['blob_sha']),date(2026,10,23))
  require(len(labels)==1756 and date(2026,9,22)+timedelta(days=30)<=date(2026,10,22),'outcome size/follow-up')
  wins=ties=losses=0
  for sc in scenarios:
   name=sc['setting'];lam=None if not sc['lambda'] else float(sc['lambda'])
   B=None if not sc['budget'] else float(sc['budget'])
   mode=sc['affordability'];require(mode in ('no-budget','stop','skip'),'rule')
   lh,lw=choose(queues,labels,1,B,lam,mode,evaldays)
   rh,rw=choose(queues,labels,4,B,lam,mode,evaldays)
   for tag,hits,weeks in [('L1',lh,lw),('L4',rh,rw)]:
    require(len(weeks)==12 and len(hits)==int(sc[tag+'_captures']),'capture parity '+name+tag)
    require(sum(w['new'] for w in weeks)==int(sc[tag+'_new']),'first-review parity '+name+tag)
    require(abs(sum(w['work'] for w in weeks)-float(sc[tag+'_work']))<0.002,'total work parity '+name+tag)
    for w in weeks:
     ref=weekly_lookup[(name,tag,w['date'])]
     for key in ['selected','new','repeat']:
      require(w[key]==int(ref[key]),'weekly '+key+' mismatch '+name+tag+w['date'])
     require(abs(w['work']-float(ref['work']))<0.00002,'weekly work mismatch '+name+tag+w['date'])
   plus=len(rh-lh);minus=len(lh-rh)
   require(plus==int(sc['L4_additions']) and minus==int(sc['L4_losses']),'paired identities '+name)
   if B is None:require((len(lh),len(rh),plus,minus)==(5,7,2,0),'baseline result not reproducible')
   elif len(rh)>len(lh):wins+=1
   elif len(rh)==len(lh):ties+=1
   else:losses+=1
  require((wins,ties,losses)==(22,8,0),'modeled-budget results not reproducible')
  report={'independent_raw_reparse':'PASS','independent_implementation':True,'EPSS_original_files':15,'CISA_KEV_original_files':16,'model_header':'v2026.06.15','scenarios_compared':31,'weekly_rows_compared':744,'L1_later_KEV_captures':5,'L4_later_KEV_captures':7,'L4_additions':2,'L4_losses':0,'budget_strict_wins':22,'budget_ties':8,'budget_losses':0,'endpoint':'later KEV admission only','limits':'retrospective 12-week historical source audit; not exploitation onset, prospectively pre-registered test, or measured analyst time'}
  a.output.write_text(json.dumps(report,indent=2)+'\n')
  print(json.dumps(report,indent=2))
if __name__=='__main__':main()
