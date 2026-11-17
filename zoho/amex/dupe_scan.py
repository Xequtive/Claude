"""Read-only: verify reconciliations contain no duplicate pairs, and list duplicate candidates
(unreconciled rows that have a reconciled twin: same side+amount, <=3 days apart, same description start)."""
from paths import *
from process import used_ids, load_register, retry, z, A
import re, json, collections, datetime as dt
recs=sorted(retry(z.get,f'bankaccounts/{A}/reconciliations',per_page=200)['reconciliations'],key=lambda r:r['end_date'])
recset={}; per={}
for r in recs:
    d=retry(z.get,f"bankaccounts/{A}/reconciliations/{r['reconciliation_id']}")['reconciliation']
    ids=[t['transaction_id'] for t in d.get('transactions',[])]; per[r['end_date']]=ids
    for i in ids: recset[i]=r['end_date']
last=recs[-1]['end_date']
reg=load_register()
def key(t): return (t['debit_or_credit'],round(float(t['amount']),2),re.sub(r'[^A-Z0-9]','',t['description'].upper())[:6])
# 1) any reconciliation holding two copies of the same charge with a third copy left out? (i.e. dupes inside a rec)
inside=0
for end,ids in per.items():
    c=collections.Counter(key(reg[i]) for i in ids if i in reg)
    # same key twice inside one rec is fine if the statement printed it twice; flag only if an UNreconciled twin also exists
    inside+=sum(1 for k,v in c.items() if v>1)
cut=(dt.date.fromisoformat(last)-dt.timedelta(days=5)).isoformat()
rec_by=collections.defaultdict(list)
for i,end in recset.items():
    if i in reg: rec_by[key(reg[i])].append(reg[i])
cands=[]
for t in reg.values():
    if t['transaction_id'] in recset or t['date']>cut: continue
    for s in rec_by.get(key(t),[]):
        if abs((dt.date.fromisoformat(s['date'])-dt.date.fromisoformat(t['date'])).days)<=3:
            cands.append({'tid':t['transaction_id'],'status':t['_st'],'date':t['date'],'side':t['debit_or_credit'],'amount':t['amount'],'desc':t['description'][:50],'twin_reconciled':s['transaction_id'],'itid':t.get('imported_transaction_id') or '','twin_date':s['date']}); break
json.dump(cands,open('/tmp/claude-0/amex/dupe_cands.json','w'),indent=0)
print(f'reconciliations: {len(recs)} (through {last}); txns in them: {len(recset)}')
print(f'keys appearing 2+ times inside one reconciliation (legit repeats like 2x$25 airline credits): {inside}')
print(f'duplicate candidates dated <= {cut}: {len(cands)} by status {dict(collections.Counter(c["status"] for c in cands))}')
print('by month:',sorted(collections.Counter(c['date'][:7] for c in cands).items()))
for c in cands[:5]: print('  ',c['date'],c['status'],c['side'],c['amount'],c['desc'][:36],'| reconciled twin',c['twin_date'])
