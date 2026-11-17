import sys, json, re, collections, time, datetime as dt
sys.path.insert(0,'/tmp/claude-0/amex'); sys.path.insert(0,'/tmp/claude-0/work')
from parse_amex import *
from resave_lib import retry, z
from decimal import Decimal as D
A='1635470000000150968'
def d2(s): m,d,y=s.split('/'); return f'20{y}-{m}-{d}'
def side(t): return 'charge' if t['debit_or_credit']=='credit' else 'pay'
def load_register():
    now={}
    for st in ['uncategorized','categorized','matched']:
        page=1
        while True:
            d=retry(z.get,'banktransactions',account_id=A,status=st,per_page=200,page=page)
            for t in d.get('banktransactions',[]): now.setdefault(t['transaction_id'],dict(t,_st=st))
            if not d.get('page_context',{}).get('has_more_page'): break
            page+=1; time.sleep(0.5)
        time.sleep(0.5)
    return now
def plan(n, reg, used):
    txt=open(f'/tmp/claude-0/amex/s_{n}.txt').read(); tx,sm,by,calc=tie(txt)
    assert calc==sm['New Balance'], 'statement parse does not tie'
    pool=collections.defaultdict(list)
    for t in sorted(reg.values(), key=lambda t:t['transaction_id']):
        if t['transaction_id'] in used: continue
        pool[(t['date'],D(str(t['amount'])),side(t))].append(t)
    sel=[]; missing=[]; 
    for r in tx:
        k=(d2(r['date']),abs(D(r['amt'])),'charge' if D(r['amt'])>0 else 'pay')
        if pool[k]: sel.append((r,pool[k].pop(0)))
        else: missing.append(r)
    return sm,tx,sel,missing
