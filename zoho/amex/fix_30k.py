import sys, json, time; sys.path.insert(0,'/home/user/claude/zoho/amex')
from paths import *
from process import retry, z, A
LOG=ZOHO+'/manifests/2026-11-17_amex_30k_fix.jsonl'
def log(**k): open(LOG,'a').write(json.dumps(k)+'\n'); print(k,flush=True)
def recs(): return sorted(retry(z.get,f'bankaccounts/{A}/reconciliations',per_page=200)['reconciliations'],key=lambda r:(r['end_date'],r['reconciliation_id']))
n=0
while True:
    rs=recs()
    if rs[-1]['end_date']<'2026-04-20': break
    r=rs[-1]; res=z.call('DELETE',f'bankaccounts/{A}/reconciliations/{r["reconciliation_id"]}')
    if res.get('code')!=0: log(error=res.get('message'),at=r['end_date']); raise SystemExit
    n+=1; log(unwound=r['end_date'],id=r['reconciliation_id']); time.sleep(1)
log(unwound_total=n,remaining=len(recs()))
FEED='1635470000001759483'
r=z.call('POST','banktransactions/uncategorize',params={'account_id':A,'imported_transaction_ids':FEED}); log(step='uncategorize wrong refund copy',code=r.get('code'),msg=r.get('message'))
if r.get('code')!=0: raise SystemExit
time.sleep(2)
e=z.call('POST',f'banktransactions/uncategorized/{FEED}/exclude',params={'account_id':A}); log(step='exclude duplicate feed row',code=e.get('code'),msg=e.get('message'))
