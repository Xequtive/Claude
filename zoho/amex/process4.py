import os
from paths import *
from process3 import *
PLACE='1635470000001792340'   # Uncategorized Transactions (expense)
QUEUE=ZOHO+'/amex_review_queue.jsonl'
MANI=ZOHO+'/manifests/2026-11-17_amex_missing_rows_import.jsonl'
AMEXRE=re.compile(r'AMEX|AMERICAN EXPRESS')
def qlog(**k): open(QUEUE,'a').write(json.dumps(k)+'\n')
_banks={}
def bank_pool():
    if _banks: return _banks
    accts=retry(z.get,'bankaccounts',filter_by='Status.Active',per_page=200)['bankaccounts']
    want=['CapOne: 360 Checking','Chase: OVO Checking','CapOne: Manolo Checking','BofA: Checking Account']
    for a in accts:
        if a['account_name'] not in want: continue
        rows=[]
        for st in ['uncategorized','categorized','matched']:
            page=1
            while True:
                d=retry(z.get,'banktransactions',account_id=a['account_id'],status=st,per_page=200,page=page)
                rows+=[(round(float(t['amount']),2),t['date'],t['description'].upper()) for t in d.get('banktransactions',[])]
                if not d.get('page_context',{}).get('has_more_page'): break
                page+=1; time.sleep(0.3)
        _banks[a['account_name']]=(a['account_id'],rows); print('   bank pool',a['account_name'],len(rows),flush=True)
    return _banks
def pay_source(amount,date):
    P=bank_pool(); d0=dt.date.fromisoformat(date); hits={}
    for name,(aid,rows) in P.items():
        for amt,d,desc in rows:
            if amt==round(float(amount),2) and abs((dt.date.fromisoformat(d)-d0).days)<=5: hits.setdefault(name,[]).append(bool(AMEXRE.search(desc)))
    if len(hits)==1:
        n=list(hits)[0]; return n,P[n][0],'verified: bank row found' + (' (AMEX desc)' if any(hits[n]) else ' (amount+date only)'),True
    ax=[n for n,v in hits.items() if any(v)]
    if len(ax)==1: return ax[0],P[ax[0]][0],'verified: only bank row with AMEX desc',True
    n='CapOne: 360 Checking'; return n,P[n][0],('ambiguous: bank rows in %s'%list(hits)) if hits else 'unverified: no bank row found, history default',False
def import_missing(n,missing):
    for r in missing:
        amt=abs(D(r['amt'])); d=d2(r['date']); charge=D(r['amt'])>0
        body={"account_id":A,"start_date":d,"end_date":d,"transactions":[{"transaction_id":f"STMT-{n}-{d}-{amt}","date":d,"debit_or_credit":'debit' if charge else 'credit',"amount":float(amt),"description":r['desc'].replace(' | ',' ')[:80]+' (manual add from statement)'}]}
        res=retry(z.call,'POST','bankstatements',body=body)
        open(MANI,'a').write(json.dumps({'stmt':n,'date':d,'amt':str(r['amt']),'desc':r['desc'][:60],'code':res.get('code')})+'\n')
        qlog(stmt=n,date=d,amount=str(r['amt']),desc=r['desc'],action='imported missing statement line into Books',confidence='n/a',reason='statement line not in Books')
        assert res.get('code')==0,res; time.sleep(1)
def run_many4(names):
    used,last=used_ids(); reg=load_register(); H2=build_hist2(reg)
    for n in names:
        sm,tx,sel,missing=plan(n,reg,used)
        if missing:
            print(f'== {n}: importing {len(missing)} missing statement line(s)',flush=True); import_missing(n,missing); time.sleep(2); reg=load_register(); sm,tx,sel,missing=plan(n,reg,used)
            assert not missing,missing
        fuzzy=plan.last_fuzzy; close=d2(sm['closing']); start=(dt.date.fromisoformat(last)+dt.timedelta(days=1)).isoformat()
        todo=[]
        for r,b in sel:
            if b['_st'] in ('categorized','matched'): continue
            desc=b['description'].upper(); rd=b.get('rule_details') or {}; side='charge' if b['debit_or_credit']=='credit' else 'pay'
            base=dict(stmt=n,date=b['date'],amount=str(b['amount']),desc=b['description'][:70],side=side,tid=b['transaction_id'])
            if side=='charge':
                if 'DEBIT ADJUSTMENT' in desc: todo.append(('exp',REW,'Rewards & Reimbursements (adjustment twin)',base,None))
                elif b.get('is_rule_exist') and rd.get('transaction_type')=='expense' and rd.get('offset_account_id'): todo.append(('exp',rd['offset_account_id'],rd.get('offset_account_name')+' (rule)',base,None))
                else:
                    p=pick2(H2,b['description'],'charge')
                    if p and p[0]=='expense': todo.append(('exp',p[2],f'{p[1]} (history {p[3]})',base,None))
                    else: todo.append(('exp',PLACE,'Uncategorized Transactions (placeholder)',base,'no rule and <80% history'))
            else:
                p=pick2(H2,b['description'],'pay'); is_pay=('PAYMENT' in desc and 'THANK YOU' in desc) or (p and p[0]=='card_payment')
                if is_pay and not (p and p[0] not in('card_payment',)):
                    bn,bid,why,ok=pay_source(b['amount'],b['date'])
                    todo.append(('cardpay',bid,f'card payment from {bn} ({why})',base,None if ok else why))
                elif p and p[0]=='expense_refund': todo.append(('refund',p[2],f'{p[1]} refund (history {p[3]})',base,None))
                elif p and p[0]=='transfer_fund': todo.append(('xfer',p[2],f'transfer from {p[1]} (history {p[3]})',base,None))
                else: todo.append(('refund',PLACE,'Uncategorized Transactions refund (placeholder)',base,'credit/other debit-side row, <80% sure of type'))
        print(f"== {n}: {start}..{close} rows {len(tx)} fuzzy {len(fuzzy)} to categorize {len(todo)} (flagged {sum(1 for t in todo if t[4])})",flush=True)
        for kind,acct,why,base,flag in todo:
            b=reg[base['tid']]
            try:
              if kind=='exp': res=retry(z.call,'POST',f"banktransactions/uncategorized/{base['tid']}/categorize/expenses",params={'account_id':A},body={"date":b['date'],"amount":float(b['amount']),"account_id":acct,"paid_through_account_id":A})
              else:
                ty={'cardpay':'card_payment','refund':'expense_refund','xfer':'transfer_fund'}[kind]
                body={"transaction_type":ty,"from_account_id":acct,"to_account_id":A,"amount":float(b['amount']),"date":b['date']}
                res=retry(z.call,'POST',f"banktransactions/uncategorized/{base['tid']}/categorize",params={'account_id':A},body=body)
            except SystemExit as e:
                if '108006' in str(e):
                    open(MANC,'a').write(json.dumps(dict(base,account=why,kind=kind,code='already-done-skipped'))+'\n'); print('   skip (already categorized by Books):',base['date'],base['amount'],base['desc'][:30],flush=True); continue
                raise
            open(MANC,'a').write(json.dumps(dict(base,account=why,kind=kind,code=res.get('code')))+'\n')
            assert res.get('code')==0,res
            if flag: qlog(**dict(base,action=why,confidence='<80%',reason=flag))
            time.sleep(0.8)
        if todo: reg=load_register()
        sm,tx,sel,missing=plan(n,reg,used)
        assert not missing and all(b['_st'] in ('categorized','matched') for r,b in sel),'statement not clean after categorizing'
        net=sum((D(r['amt']) for r,b in sel),D(0)); assert sm['Previous Balance']+net==sm['New Balance']
        body={"start_date":start,"end_date":close,"closing_balance":float(sm['New Balance']),"save_option":"reconcile","transactions_to_be_reconciled":[b['transaction_id'] for r,b in sel]}
        res=retry(z.call,'POST',f'bankaccounts/{A}/reconciliations',body=body); rec=res.get('reconciliation') or {}
        open(MANR,'a').write(json.dumps({'statement':n,'period':f'{start}..{close}','rows':len(sel),'fuzzy':len(fuzzy),'closing':str(sm['New Balance']),'code':res.get('code'),'message':res.get('message'),'reconciliation_id':rec.get('reconciliation_id')})+'\n')
        print('   RECONCILED' if res.get('code')==0 else '   FAILED',res.get('message'),'| open',rec.get('opening_balance'),'close',rec.get('closing_balance'),flush=True)
        if res.get('code')!=0: return
        used|={b['transaction_id'] for r,b in sel}; last=close
if __name__=='__main__': run_many4(sys.argv[1:])
