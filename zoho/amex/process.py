import os
from paths import *
from recon_stmt import *
REW='1635470000000373577'
MANC=ZOHO+'/manifests/2026-11-17_amex_categorize.jsonl'
MANR=ZOHO+'/manifests/2026-11-17_amex_reconciliations.jsonl'
def used_ids():
    recs=retry(z.get,f'bankaccounts/{A}/reconciliations',per_page=200)['reconciliations']
    used=set(); last=None
    for r in sorted(recs,key=lambda r:r['end_date']):
        d=retry(z.get,f'bankaccounts/{A}/reconciliations/{r["reconciliation_id"]}')['reconciliation']
        used|={t['transaction_id'] for t in d.get('transactions',[])}; last=r['end_date']; time.sleep(0.7)
    return used,last
def run(n, execute=True):
    used,last=used_ids()
    reg=load_register()
    sm,tx,sel,missing=plan(n,reg,used); fuzzy=plan.last_fuzzy
    close=d2(sm['closing']); start=(dt.date.fromisoformat(last)+dt.timedelta(days=1)).isoformat()
    print(f"== {n}: {start}..{close} | rows {len(tx)} matched {len(sel)} (fuzzy {len(fuzzy)}) missing {len(missing)} | prev {sm['Previous Balance']} new {sm['New Balance']}")
    for r,b,g in fuzzy: print(f"   fuzzy +-{g}d: stmt {r['date']} {r['amt']} {r['desc'][:30]} <-> books {b['date']} {b['description'][:30]}")
    holds=[]; todo=[]
    for r,b in sel:
        if b['_st']=='categorized': continue
        desc=b['description'].upper()
        rd=b.get('rule_details') or {}
        if 'DEBIT ADJUSTMENT' in desc and b['debit_or_credit']=='credit': todo.append((b,REW,'Rewards & Reimbursements (adjustment twin)'))
        elif b['debit_or_credit']=='credit' and b.get('is_rule_exist') and rd.get('transaction_type')=='expense' and rd.get('offset_account_id'): todo.append((b,rd['offset_account_id'],rd.get('offset_account_name')+' (rule '+rd.get('rule_name','')+')'))
        else: holds.append((r,b))
    for r in missing: holds.append((r,None))
    print(f"   to categorize: {len(todo)} | holds: {len(holds)}")
    for b,acct,why in todo: print(f"     CAT {b['date']} {b['amount']} {b['description'][:34]} -> {why}")
    for r,b in holds: print(f"     HOLD {'books '+b['date']+' '+b['debit_or_credit']+' '+str(b['amount'])+' '+b['description'][:40] if b else 'MISSING in books: '+r['date']+' '+r['amt']+' '+r['desc'][:40]}")
    if not execute: return 'dry'
    for b,acct,why in todo:
        res=retry(z.call,'POST',f"banktransactions/uncategorized/{b['transaction_id']}/categorize/expenses",params={'account_id':A},body={"date":b['date'],"amount":float(b['amount']),"account_id":acct,"paid_through_account_id":A})
        open(MANC,'a').write(json.dumps({'stmt':n,'tid':b['transaction_id'],'date':b['date'],'amt':b['amount'],'desc':b['description'][:60],'account':why,'expense_id':(res.get('expense') or {}).get('expense_id'),'code':res.get('code')})+'\n')
        assert res.get('code')==0,res
        time.sleep(0.8)
    if holds: print('   -> NOT reconciling: holds above'); return 'hold'
    if todo: reg=load_register(); used,_=used_ids(); sm,tx,sel,missing=plan(n,reg,used)
    assert not missing and all(b['_st']=='categorized' for r,b in sel)
    net=sum((D(r['amt']) for r,b in sel),D(0)); assert sm['Previous Balance']+net==sm['New Balance']
    body={"start_date":start,"end_date":close,"closing_balance":float(sm['New Balance']),"save_option":"reconcile","transactions_to_be_reconciled":[b['transaction_id'] for r,b in sel]}
    res=retry(z.call,'POST',f'bankaccounts/{A}/reconciliations',body=body)
    rec=res.get('reconciliation') or {}
    open(MANR,'a').write(json.dumps({'statement':n,'period':f'{start}..{close}','rows':len(sel),'fuzzy':len(fuzzy),'closing':str(sm['New Balance']),'code':res.get('code'),'message':res.get('message'),'reconciliation_id':rec.get('reconciliation_id')})+'\n')
    print('   RECONCILED' if res.get('code')==0 else '   FAILED', res.get('message'),'| open',rec.get('opening_balance'),'close',rec.get('closing_balance'))
    return 'ok'
if __name__=='__main__':
    run(sys.argv[1], execute=('--dry' not in sys.argv))
