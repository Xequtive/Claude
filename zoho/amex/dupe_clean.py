"""Remove duplicate copies in RECONCILED Amex periods: a row not in any reconciliation that has a reconciled twin
(same side+amount, <=3 days, same description start) and is dated >=5 days before the last reconciled closing.
Categorized copy -> uncategorize, then exclude. Usage: python3 dupe_clean.py [--probe] [--limit N]"""
from paths import *
import subprocess, json, sys, time
from process import retry, z, A
MAN=ZOHO+'/manifests/2026-11-17_amex_dupe_cleanup.jsonl'
probe='--probe' in sys.argv; lim=int(sys.argv[sys.argv.index('--limit')+1]) if '--limit' in sys.argv else 10**9
subprocess.run([sys.executable,os.path.join(HERE,'dupe_scan.py')],check=True)
cands=json.load(open('/tmp/claude-0/amex/dupe_cands.json'))[: (1 if probe else lim)]
def call(m,p,**params):
    try: return z.call(m,p,params=params)
    except SystemExit as e: return {'code':'ERR','message':str(e)[:300]}
for c in cands:
    rec={'tid':c['tid'],'date':c['date'],'amount':c['amount'],'desc':c['desc'],'status':c['status'],'twin':c['twin_reconciled']}
    fid=c['tid']
    if c['status']!='uncategorized':
        r=call('POST',f"banktransactions/{c['tid']}/uncategorize",account_id=A); rec['uncat']=r.get('code'); rec['uncat_msg']=r.get('message')
        if r.get('code')!=0: open(MAN,'a').write(json.dumps(rec)+'\n'); print('uncategorize failed',rec); break
        time.sleep(1.5)
        # find the feed row again (same date/amount/side, uncategorized)
        hits=[]; page=1
        while True:
            d=retry(z.get,'banktransactions',account_id=A,status='uncategorized',per_page=200,page=page)
            rows=d.get('banktransactions',[])
            hits+=[t for t in rows if t['date']==c['date'] and abs(float(t['amount'])-float(c['amount']))<0.005 and t['debit_or_credit']==c['side']]
            if not d.get('page_context',{}).get('has_more_page') or (rows and rows[-1]['date']<c['date']): break
            page+=1; time.sleep(0.4)
        if len(hits)!=1: rec['note']=f'feed row not uniquely found after uncategorize ({len(hits)})'; open(MAN,'a').write(json.dumps(rec)+'\n'); print(rec); break
        fid=hits[0]['transaction_id']
    r=call('POST',f"banktransactions/uncategorized/{fid}/exclude",account_id=A); rec['feed_id']=fid; rec['exclude']=r.get('code'); rec['exclude_msg']=r.get('message')
    open(MAN,'a').write(json.dumps(rec)+'\n'); print(rec['date'],rec['amount'],rec['desc'][:30],'->',rec.get('uncat','-'),rec['exclude'],rec['exclude_msg'],flush=True)
    if r.get('code')!=0: break
    time.sleep(1)
