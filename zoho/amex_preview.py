import sys; sys.path.insert(0,'/tmp/claude-0/amex')
from process import *
names=sys.argv[1:]
used,last=used_ids(); reg=load_register()
for n in names:
    sm,tx,sel,missing=plan(n,reg,used); fz=plan.last_fuzzy
    holds=[]; auto=0
    for r,b in sel:
        if b['_st']=='categorized': continue
        rd=b.get('rule_details') or {}
        if ('DEBIT ADJUSTMENT' in b['description'].upper() and b['debit_or_credit']=='credit') or (b['debit_or_credit']=='credit' and b.get('is_rule_exist') and rd.get('transaction_type')=='expense'): auto+=1
        else: holds.append(b)
    print(f"== {n} close {sm['closing']} rows {len(tx)} matched {len(sel)} fuzzy {len(fz)} missing {len(missing)} auto-cat {auto} holds {len(holds)}")
    for r in missing: print('   MISSING in books:',r['date'],r['amt'],r['desc'][:40])
    for b in holds: print('   HOLD:',b['date'],b['debit_or_credit'],b['amount'],b['description'][:46],'| rule' ,(b.get('rule_details') or {}).get('rule_name'))
    used|={b['transaction_id'] for r,b in sel}
