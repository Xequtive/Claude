"""Exclude every Amex row that is NOT in any reconciliation and is dated on/before the last statement closing.
(Owner instruction: if it is not on a statement, remove it.) Feed rows cannot be deleted in Books, only excluded.
Categorized rows are uncategorized first (via imported_transaction_id), then excluded. Matched rows are skipped and reported.
Usage: python3 offstatement_clean.py [--dry] [--probe]"""
from paths import *
import sys, json, time, collections, http.client, urllib.error
from recon_stmt import load_register
from process import retry, z, A
MAN=ZOHO+'/manifests/2026-11-17_amex_offstatement_cleanup.jsonl'
LASTCLOSE='2026-10-21'
def call(m,p,**params):
    for i in range(6):
        try: return z.call(m,p,params=params)
        except SystemExit as e: return {'code':'ERR','message':str(e)[:300]}
        except (http.client.HTTPException, urllib.error.URLError, ConnectionError, TimeoutError): time.sleep(3*(i+1))
    return {'code':'ERR','message':'network retries exhausted'}
recs=retry(z.get,f'bankaccounts/{A}/reconciliations',per_page=200)['reconciliations']
assert len(recs)==36, len(recs)
recset=set()
for r in recs:
    d=retry(z.get,f"bankaccounts/{A}/reconciliations/{r['reconciliation_id']}")['reconciliation']
    recset|={t['transaction_id'] for t in d.get('transactions',[])}
reg=load_register()
done={json.loads(l).get('tid') for l in open(MAN)} if os.path.exists(MAN) else set()
cands=[t for t in reg.values() if t['transaction_id'] not in recset and t['date']<=LASTCLOSE and t['_st'] in('uncategorized','categorized')]
skipped=[t for t in reg.values() if t['transaction_id'] not in recset and t['date']<=LASTCLOSE and t['_st']=='matched']
noitid=[t for t in cands if t['_st']=='categorized' and not t.get('imported_transaction_id')]
cands=[t for t in cands if t not in noitid and t['transaction_id'] not in done]
print(f"in {len(recset)} reconciled txns | to remove: {len(cands)} {dict(collections.Counter(t['_st'] for t in cands))} | matched rows skipped: {len(skipped)} | categorized without feed id (skipped): {len(noitid)}",flush=True)
print('by month:',sorted(collections.Counter(t['date'][:7] for t in cands).items())[-8:],flush=True)
json.dump({'skipped_matched':[(t['transaction_id'],t['date'],t['amount'],t['description'][:40]) for t in skipped],'skipped_noitid':[(t['transaction_id'],t['date'],t['amount'],t['description'][:40]) for t in noitid]},open('/tmp/claude-0/amex/offstatement_skipped.json','w'))
if '--dry' in sys.argv: sys.exit()
if '--probe' in sys.argv: cands=cands[:1]
n=0
for t in cands:
    rec={'tid':t['transaction_id'],'date':t['date'],'amount':t['amount'],'side':t['debit_or_credit'],'desc':t['description'][:60],'status':t['_st']}
    fid=t['transaction_id']
    if t['_st']=='categorized':
        r=call('POST','banktransactions/uncategorize',account_id=A,imported_transaction_ids=t['imported_transaction_id']); rec['uncat']=r.get('code')
        if r.get('code')!=0: rec['msg']=r.get('message'); open(MAN,'a').write(json.dumps(rec)+'\n'); print('uncategorize failed',rec,flush=True); continue
        fid=t['imported_transaction_id']; time.sleep(1.2)
    r=call('POST',f'banktransactions/uncategorized/{fid}/exclude',account_id=A); rec['exclude']=r.get('code'); rec['msg']=r.get('message'); rec['feed_id']=fid
    open(MAN,'a').write(json.dumps(rec)+'\n'); n+= r.get('code')==0
    if r.get('code')!=0: print('exclude failed',rec,flush=True)
    elif n%25==0: print('excluded',n,'of',len(cands),flush=True)
    time.sleep(0.9)
print('done: excluded',n,'of',len(cands),flush=True)
