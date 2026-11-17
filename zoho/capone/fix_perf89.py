import sys, json, time; sys.path.insert(0,'/home/user/claude/zoho')
import zoho_client as z
P='1635470000000150082'; TA='1635470000002177287'
LOG='/home/user/claude/zoho/manifests/2026-11-17_capone_savings_unwind.jsonl'
def log(**k): open(LOG,'a').write(json.dumps(k)+'\n'); print(k,flush=True)
def recs(): return sorted(z.get(f'bankaccounts/{P}/reconciliations',per_page=200)['reconciliations'],key=lambda r:(r['end_date'],r['reconciliation_id']))
n=0
while True:
    rs=recs()
    if not rs or rs[-1]['end_date']<'2022-12-01': break
    r=rs[-1]; res=z.call('DELETE',f'bankaccounts/{P}/reconciliations/{r["reconciliation_id"]}')
    if res.get('code')!=0: log(acct='360 Perf',error=res.get('message'),at=r['end_date']); raise SystemExit
    n+=1; time.sleep(0.8)
log(acct='360 Perf',unwound=n,through=recs()[-1]['end_date'])
feed=None; page=1
while True:
    d=z.get('banktransactions',account_id=P,status='categorized',per_page=200,page=page)
    for t in d['banktransactions']:
        if t['date']=='2022-12-01' and abs(float(t['amount'])-89)<0.005 and t['debit_or_credit']=='debit' and t.get('transaction_id')!=TA: feed=t
    if not d['page_context'].get('has_more_page') or feed: break
    page+=1
log(acct='360 Perf',step='duplicate transfer feed row',tid=feed and feed['transaction_id'],imported=feed and feed.get('imported_transaction_id'),offset=feed and feed.get('offset_account_name'))
itid=feed['imported_transaction_id']
r=z.call('POST','banktransactions/uncategorize',params={'account_id':P,'imported_transaction_ids':itid}); log(acct='360 Perf',step='uncategorize duplicate transfer',code=r.get('code'),msg=r.get('message'))
time.sleep(2)
cand=z.call('GET',f'banktransactions/uncategorized/{itid}/match',params={'account_id':P}); ids=[(c.get('transaction_id'),c.get('transaction_type'),c.get('amount')) for c in (cand.get('matching_transactions') or cand.get('transactions') or [])]
log(acct='360 Perf',step='candidates',ids=ids)
if any(i[0]==TA for i in ids):
    m=z.call('POST',f'banktransactions/uncategorized/{itid}/match',params={'account_id':P},body={"transactions_to_be_matched":[{"transaction_id":TA,"transaction_type":"transfer_fund"}]}); log(acct='360 Perf',step='matched feed row to corrected transfer',code=m.get('code'),msg=m.get('message'))
else: log(acct='360 Perf',error='corrected transfer not offered; feed row left uncategorized')
