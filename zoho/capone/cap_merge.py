"""One-off: reconcile statements k1..k2 (consecutive) of a savings account as a single period. Usage: cap_merge.py <last4> <k1> <k2> [--dry]"""
import sys, json, glob, collections, time, datetime as dt
sys.path.insert(0,'/tmp/claude-0/capone'); sys.path.insert(0,'/home/user/claude/zoho/amex')
from paths import *
from resave_lib import retry, z
from cap_parse import parse_statement
from decimal import Decimal as D
ACC={'0153':'1635470000000150082','8873':'1635470000000150117','7838':'1635470000000150110'}
no,k1,k2=sys.argv[1:4]; dry='--dry' in sys.argv; AID=ACC[no]
def ky(k): return (k[:2],k[3:])
S={}
for f in glob.glob('/tmp/claude-0/capone/c_*.txt'):
    k=f.split('c_')[1][:5]
    if ky(k1)<=ky(k)<=ky(k2):
        r=parse_statement(open(f).read())
        for n_,s in r['sections'].items():
            if n_[-4:]==no: S[k]=(r['period'],s)
ks=sorted(S,key=ky); print('statements merged:',ks)
reg={}
for st in ['uncategorized','categorized','matched']:
    page=1
    while True:
        d=retry(z.get,'banktransactions',account_id=AID,status=st,per_page=200,page=page)
        for t in d.get('banktransactions',[]): reg.setdefault(t['transaction_id'],dict(t,_st=st))
        if not d.get('page_context',{}).get('has_more_page'): break
        page+=1; time.sleep(0.3)
def days(a,b): return abs((dt.date.fromisoformat(a)-dt.date.fromisoformat(b)).days)
pool=collections.defaultdict(list)
for t in sorted(reg.values(),key=lambda t:(0 if t['_st']!='uncategorized' else 1,t['transaction_id'])): pool[(t['debit_or_credit'],round(float(t['amount']),2))].append(t)
sel=[]; miss=[]
for k in ks:
    for x in S[k][1]['tx']:
        side='debit' if x['amt']>0 else 'credit'; hit=None
        for c in sorted(pool[(side,abs(float(x['amt'])))],key=lambda c:days(c['date'],x['date'])):
            if days(c['date'],x['date'])<=3: hit=c; break
        if hit: pool[(side,abs(float(x['amt'])))].remove(hit); sel.append(hit)
        else: miss.append(x)
opening=S[ks[0]][1]['opening']; closing=S[ks[-1]][1]['closing']; start=S[ks[0]][0][0]; end=S[ks[-1]][0][1]
net=sum(((D(str(t['amount'])) if t['debit_or_credit']=='debit' else -D(str(t['amount']))) for t in sel),D(0))
unc=[t for t in sel if t['_st']=='uncategorized']
print(f'{start}..{end}: matched {len(sel)} missing {len(miss)} uncategorized {len(unc)} | open {opening} + net {net} = {opening+net} vs printed {closing}')
if dry or miss or unc or opening+net!=closing: sys.exit()
res=z.call('POST',f'bankaccounts/{AID}/reconciliations',body={"start_date":start,"end_date":end,"closing_balance":float(closing),"save_option":"reconcile","transactions_to_be_reconciled":[t['transaction_id'] for t in sel]})
print('POST ->',res.get('code'),res.get('message'))
open(ZOHO+'/manifests/2026-11-17_capone_savings_reconciliations.jsonl','a').write(json.dumps({'acct':no,'stmt':f'{k1}+{k2} merged','period':f'{start}..{end}','rows':len(sel),'closing':str(closing),'code':res.get('code'),'message':res.get('message')})+'\n')
