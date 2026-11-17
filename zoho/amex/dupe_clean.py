"""Remove duplicate copies in RECONCILED Amex periods: a row not in any reconciliation that has a reconciled twin
(same side+amount, <=3 days, same description start) and is dated >=5 days before the last reconciled closing.
Categorized copy -> uncategorize, then exclude. Usage: python3 dupe_clean.py [--probe] [--limit N]"""
from paths import *
import subprocess, json, sys, time
from process import retry, z, A
MAN=ZOHO+'/manifests/2026-11-17_amex_dupe_cleanup.jsonl'
probe='--probe' in sys.argv; lim=int(sys.argv[sys.argv.index('--limit')+1]) if '--limit' in sys.argv else 10**9
subprocess.run([sys.executable,os.path.join(HERE,'dupe_scan.py')],check=True)
cands=json.load(open('/tmp/claude-0/amex/dupe_cands.json'))
if '--categorized' in sys.argv: cands=[x for x in cands if x['status']!='uncategorized']
cands=cands[: (1 if probe else lim)]
import http.client, urllib.error
def call(m,p,**params):
    for i in range(5):
        try: return z.call(m,p,params=params)
        except SystemExit as e: return {'code':'ERR','message':str(e)[:300]}
        except (http.client.HTTPException, urllib.error.URLError, ConnectionError, TimeoutError):
            time.sleep(3*(i+1))
    return {'code':'ERR','message':'network retries exhausted'}
for c in cands:
    rec={'tid':c['tid'],'date':c['date'],'amount':c['amount'],'desc':c['desc'],'status':c['status'],'twin':c['twin_reconciled']}
    fid=c['tid']
    if c['status']!='uncategorized':
        if not c.get('itid'): rec['note']='no imported_transaction_id'; open(MAN,'a').write(json.dumps(rec)+'\n'); print(rec); continue
        r=call('POST','banktransactions/uncategorize',account_id=A,imported_transaction_ids=c['itid']); rec['uncat']=r.get('code'); rec['uncat_msg']=r.get('message')
        if r.get('code')!=0: open(MAN,'a').write(json.dumps(rec)+'\n'); print('uncategorize failed',rec); break
        time.sleep(1.5); fid=c['itid']
    r=call('POST',f"banktransactions/uncategorized/{fid}/exclude",account_id=A); rec['feed_id']=fid; rec['exclude']=r.get('code'); rec['exclude_msg']=r.get('message')
    open(MAN,'a').write(json.dumps(rec)+'\n'); print(rec['date'],rec['amount'],rec['desc'][:30],'->',rec.get('uncat','-'),rec['exclude'],rec['exclude_msg'],flush=True)
    if r.get('code')!=0: break
    time.sleep(1)
