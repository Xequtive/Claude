import sys; sys.path.insert(0,'/tmp/claude-0/amex')
from process import *
import re, collections
RULES=json.load(open('/home/user/claude/zoho/manifests/2026-11-17_rules_pre_resave_backup.json'))
ACCT={d['account_name']:d['account_id'] for d in RULES.values()}
def mkey(desc):
    toks=re.findall(r'[A-Z]{2,}',desc.upper()); return ' '.join(toks[:2]) if len(toks)>=2 else None
def build_hist(reg):
    h=collections.defaultdict(collections.Counter)
    for t in reg.values():
        if t['_st']=='categorized' and t['debit_or_credit']=='credit' and t.get('transaction_type')=='expense' and t.get('offset_account_name'):
            k=mkey(t['description']); 
            if k: h[k][t['offset_account_name']]+=1
    return h
def hist_pick(h,desc):
    k=mkey(desc)
    if not k or k not in h: return None
    name,n=h[k].most_common(1)[0]; tot=sum(h[k].values())
    if tot>=5 and n/tot>=0.95 and name in ACCT: return name,ACCT[name],f'{n}/{tot}'
    return None
def run_many(names):
    used,last=used_ids(); reg=load_register(); H=build_hist(reg)
    for n in names:
        sm,tx,sel,missing=plan(n,reg,used); fuzzy=plan.last_fuzzy
        close=d2(sm['closing']); start=(dt.date.fromisoformat(last)+dt.timedelta(days=1)).isoformat()
        holds=[]; todo=[]
        for r,b in sel:
            if b['_st']=='categorized': continue
            desc=b['description'].upper(); rd=b.get('rule_details') or {}
            if 'DEBIT ADJUSTMENT' in desc and b['debit_or_credit']=='credit': todo.append((b,REW,'Rewards & Reimbursements (adjustment twin)'))
            elif b['debit_or_credit']=='credit' and b.get('is_rule_exist') and rd.get('transaction_type')=='expense' and rd.get('offset_account_id'): todo.append((b,rd['offset_account_id'],rd.get('offset_account_name')+' (rule '+rd.get('rule_name','')+')'))
            elif b['debit_or_credit']=='credit' and not b.get('is_rule_exist') and hist_pick(H,b['description']):
                nm,aid,ev=hist_pick(H,b['description']); todo.append((b,aid,f'{nm} (history {ev})'))
            else: holds.append((r,b))
        for r in missing: holds.append((r,None))
        print(f"== {n}: {start}..{close} rows {len(tx)} matched {len(sel)} fuzzy {len(fuzzy)} missing {len(missing)} cat {len(todo)} holds {len(holds)}",flush=True)
        for r,b,g in fuzzy[:5]: print(f"   fuzzy +-{g}d: stmt {r['date']} {r['amt']} {r['desc'][:28]} <-> books {b['date']}")
        if holds:
            for r,b in holds[:12]: print('   HOLD', (b['date']+' '+b['debit_or_credit']+' '+str(b['amount'])+' '+b['description'][:40]) if b else 'MISSING '+r['date']+' '+r['amt']+' '+r['desc'][:40])
            print('   -> stopping: holds'); return
        for b,acct,why in todo:
            res=retry(z.call,'POST',f"banktransactions/uncategorized/{b['transaction_id']}/categorize/expenses",params={'account_id':A},body={"date":b['date'],"amount":float(b['amount']),"account_id":acct,"paid_through_account_id":A})
            open(MANC,'a').write(json.dumps({'stmt':n,'tid':b['transaction_id'],'date':b['date'],'amt':b['amount'],'desc':b['description'][:60],'account':why,'expense_id':(res.get('expense') or {}).get('expense_id'),'code':res.get('code')})+'\n')
            assert res.get('code')==0,res; time.sleep(0.8)
        if todo:
            reg=load_register(); sm,tx,sel,missing=plan(n,reg,used)
        assert not missing and all(b['_st']=='categorized' for r,b in sel)
        net=sum((D(r['amt']) for r,b in sel),D(0)); assert sm['Previous Balance']+net==sm['New Balance']
        body={"start_date":start,"end_date":close,"closing_balance":float(sm['New Balance']),"save_option":"reconcile","transactions_to_be_reconciled":[b['transaction_id'] for r,b in sel]}
        res=retry(z.call,'POST',f'bankaccounts/{A}/reconciliations',body=body); rec=res.get('reconciliation') or {}
        open(MANR,'a').write(json.dumps({'statement':n,'period':f'{start}..{close}','rows':len(sel),'fuzzy':len(fuzzy),'closing':str(sm['New Balance']),'code':res.get('code'),'message':res.get('message'),'reconciliation_id':rec.get('reconciliation_id')})+'\n')
        print('   RECONCILED' if res.get('code')==0 else '   FAILED',res.get('message'),'| open',rec.get('opening_balance'),'close',rec.get('closing_balance'),flush=True)
        if res.get('code')!=0: return
        used|={b['transaction_id'] for r,b in sel}; last=close
if __name__=='__main__': run_many(sys.argv[1:])
