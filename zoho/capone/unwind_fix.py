import sys, json, time; sys.path.insert(0,'/home/user/claude/zoho')
import zoho_client as z
M='1635470000000150117'; S='1635470000000150110'
LOG='/home/user/claude/zoho/manifests/2026-11-17_capone_savings_unwind.jsonl'
def log(**k): open(LOG,'a').write(json.dumps(k)+'\n'); print(k,flush=True)
def recs(a): return sorted(z.get(f'bankaccounts/{a}/reconciliations',per_page=200)['reconciliations'],key=lambda r:(r['end_date'],r['reconciliation_id']))
def unwind(aid,name,row_date):
    n=0
    while True:
        rs=recs(aid)
        if not rs or rs[-1]['end_date']<row_date: break
        r=rs[-1]; res=z.call('DELETE',f'bankaccounts/{aid}/reconciliations/{r["reconciliation_id"]}')
        if res.get('code')!=0: log(acct=name,error=res.get('message')); raise SystemExit
        n+=1; time.sleep(0.8)
    log(acct=name,unwound=n,remaining=len(recs(aid)),through=(recs(aid)[-1]['end_date'] if recs(aid) else None))
def fix(aid,name,feed_id,leg_id,amt,date,side):
    r=z.call('POST','banktransactions/uncategorize',params={'account_id':aid,'imported_transaction_ids':feed_id}); log(acct=name,step='uncategorize wrong transfer',code=r.get('code'),msg=r.get('message'))
    if r.get('code')!=0: raise SystemExit
    time.sleep(2)
    cand=z.call('GET',f'banktransactions/uncategorized/{feed_id}/match',params={'account_id':aid}); ids=[(c.get('transaction_id'),c.get('transaction_type'),c.get('amount')) for c in (cand.get('matching_transactions') or cand.get('transactions') or [])]
    log(acct=name,step='candidates',ids=ids)
    if not any(i[0]==leg_id for i in ids): log(acct=name,error='existing 360 Perf leg not offered; NOT matched - feed row left uncategorized'); raise SystemExit
    m=z.call('POST',f'banktransactions/uncategorized/{feed_id}/match',params={'account_id':aid},body={"transactions_to_be_matched":[{"transaction_id":leg_id,"transaction_type":"transfer_fund"}]})
    log(acct=name,step='matched to 360 Perf leg',code=m.get('code'),msg=m.get('message'))
unwind(S,'Sophie Savings','2024-10-12'); fix(S,'Sophie Savings','1635470000000352166','1635470000002084817',10.0,'2024-10-12','debit')
unwind(M,'Manolo Savings','2022-12-01'); fix(M,'Manolo Savings','1635470000000361117','1635470000002084520',89.0,'2022-12-01','credit')
print('DONE')
