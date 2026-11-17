import sys, json, glob, collections, datetime as dt, time
sys.path.insert(0,'/tmp/claude-0/capone'); sys.path.insert(0,'/home/user/claude/zoho/amex')
from paths import *
from resave_lib import retry, z
from cap_parse import parse_statement
from decimal import Decimal as D
ACC={'0153':('1635470000000150082','360 Perf Savings'),'8873':('1635470000000150117','Manolo Savings'),'7838':('1635470000000150110','Sophie Savings')}
# parse all statements -> per account list of tx
stm=collections.defaultdict(list); periods={}
for f in sorted(glob.glob('/tmp/claude-0/capone/c_*.txt')):
    k=f.split('c_')[1][:5]; r=parse_statement(open(f).read())
    for no,s in r['sections'].items():
        if no[-4:] in ACC:
            for t in s['tx']: stm[no[-4:]].append(dict(t,stmt=k))
            periods.setdefault(no[-4:],[]).append((k,s['opening'],s['closing'],r['period']))
json.dump({a:[dict(t,amt=str(t['amt']),bal=str(t['bal'])) for t in v] for a,v in stm.items()},open('/tmp/claude-0/capone/savings_stmt_tx.json','w'))
def load(aid):
    out={}
    for st in ['uncategorized','categorized','matched']:
        page=1
        while True:
            d=retry(z.get,'banktransactions',account_id=aid,status=st,per_page=200,page=page)
            for t in d.get('banktransactions',[]): out.setdefault(t['transaction_id'],dict(t,_st=st))
            if not d.get('page_context',{}).get('has_more_page'): break
            page+=1; time.sleep(0.4)
        time.sleep(0.4)
    return out
for no,(aid,name) in ACC.items():
    reg=load(aid); json.dump(reg,open(f'/tmp/claude-0/capone/reg_{no}.json','w'))
    tx=stm[no]; lo=min(t['date'] for t in tx); hi=max(t['date'] for t in tx)
    # decide side mapping by trying both
    def run(map_in_to):
        pool=collections.defaultdict(list)
        for t in reg.values(): pool[(t['debit_or_credit'],round(float(t['amount']),2))].append(t)
        m=0
        for x in tx:
            side=map_in_to if x['amt']>0 else ('credit' if map_in_to=='debit' else 'debit')
            for c in pool[(side,abs(float(x['amt'])))]:
                if abs((dt.date.fromisoformat(c['date'])-dt.date.fromisoformat(x['date'])).days)<=3: pool[(side,abs(float(x['amt'])))].remove(c); m+=1; break
        return m
    mi,mc=run('debit'),run('credit'); inside=('debit' if mi>=mc else 'credit')
    pool=collections.defaultdict(list)
    for t in sorted(reg.values(),key=lambda t:(0 if t['_st']!='uncategorized' else 1,t['transaction_id'])): pool[(t['debit_or_credit'],round(float(t['amount']),2))].append(t)
    matched=0; missing=[]
    for x in tx:
        side=inside if x['amt']>0 else ('credit' if inside=='debit' else 'debit'); hit=None
        for c in pool[(side,abs(float(x['amt'])))]:
            if abs((dt.date.fromisoformat(c['date'])-dt.date.fromisoformat(x['date'])).days)<=3: hit=c; break
        if hit: pool[(side,abs(float(x['amt'])))].remove(hit); matched+=1
        else: missing.append(x)
    extras=[t for v in pool.values() for t in v if lo<=t['date']<=hi]
    print(f"{name} ({no}) stmts {lo}..{hi}: statement tx {len(tx)} | register rows {len(reg)} {dict(collections.Counter(t['_st'] for t in reg.values()))} | money-IN side in Books = '{inside}' | matched {matched} | MISSING in Books {len(missing)} | EXTRA in Books (not on any statement) {len(extras)} {dict(collections.Counter(t['_st'] for t in extras))}",flush=True)
    json.dump({'inside':inside,'missing':[dict(m,amt=str(m['amt']),bal=str(m['bal'])) for m in missing],'extras':[(t['transaction_id'],t['_st'],t['date'],t['debit_or_credit'],t['amount'],t['description'][:50]) for t in extras]},open(f'/tmp/claude-0/capone/cmp_{no}.json','w'))
