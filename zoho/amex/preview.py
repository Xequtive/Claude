import os
from paths import *
from process3 import *
names=sys.argv[1:]
used,last=used_ids(); reg=load_register(); H2=build_hist2(reg)
tot_hold=collections.Counter(); allholds=[]
for n in names:
    sm,tx,sel,missing=plan(n,reg,used); fz=plan.last_fuzzy; holds=[]; auto=0
    for r,b in sel:
        if b['_st']=='categorized': continue
        rd=b.get('rule_details') or {}
        if ('DEBIT ADJUSTMENT' in b['description'].upper() and b['debit_or_credit']=='credit') or (b['debit_or_credit']=='credit' and b.get('is_rule_exist') and rd.get('transaction_type')=='expense'): auto+=1; continue
        side='charge' if b['debit_or_credit']=='credit' else 'pay'; p=pick2(H2,b['description'],side)
        if p and ((side=='charge' and p[0]=='expense') or (side=='pay' and p[0] in('expense_refund','card_payment'))): auto+=1
        else: holds.append(b)
    print(f"== {n} rows {len(tx)} fuzzy {len(fz)} missing {len(missing)} auto {auto} holds {len(holds)}")
    for r in missing: print('   MISSING',r['date'],r['amt'],r['desc'][:40])
    for b in holds: allholds.append((n,b)); print('   HOLD',b['date'],b['debit_or_credit'],b['amount'],repr(b['description'][:44]))
    used|={b['transaction_id'] for r,b in sel}
