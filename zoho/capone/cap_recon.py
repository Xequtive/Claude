"""Reconcile a Capital One savings register statement by statement from the parsed combo statements.
Usage: python3 cap_recon.py <last4: 0153|8873|7838>  [--dry]"""
import sys, json, glob, collections, time, datetime as dt
sys.path.insert(0,'/tmp/claude-0/capone'); sys.path.insert(0,'/home/user/claude/zoho/amex')
from paths import *
from resave_lib import retry, z
from cap_parse import parse_statement
from decimal import Decimal as D
ACC={'0153':('1635470000000150082','360 Perf Savings'),'8873':('1635470000000150117','Manolo Savings'),'7838':('1635470000000150110','Sophie Savings')}
no=sys.argv[1]; dry='--dry' in sys.argv; AID,NAME=ACC[no]
MAN=ZOHO+'/manifests/2026-11-17_capone_savings_reconciliations.jsonl'
stm={}
for f in glob.glob('/tmp/claude-0/capone/c_*.txt'):
    k=f.split('c_')[1][:5]; r=parse_statement(open(f).read())
    for n_,s in r['sections'].items():
        if n_[-4:]==no and s['opening'] is not None and s['closing'] is not None: stm[k]=(r['period'],s)
keys=sorted(stm,key=lambda k:(k[:2],k[3:]))
def load():
    out={}
    for st in ['uncategorized','categorized','matched']:
        page=1
        while True:
            d=retry(z.get,'banktransactions',account_id=AID,status=st,per_page=200,page=page)
            for t in d.get('banktransactions',[]): out.setdefault(t['transaction_id'],dict(t,_st=st))
            if not d.get('page_context',{}).get('has_more_page'): break
            page+=1; time.sleep(0.4)
        time.sleep(0.4)
    return out
recs=sorted(retry(z.get,f'bankaccounts/{AID}/reconciliations',per_page=200)['reconciliations'],key=lambda r:r['end_date'])
used=set(); last_end=None
for r in recs:
    try: d=retry(z.get,f"bankaccounts/{AID}/reconciliations/{r['reconciliation_id']}")['reconciliation']; used|={t['transaction_id'] for t in d.get('transactions',[])}
    except SystemExit: print('   (skipping unreadable empty reconciliation shell',r['reconciliation_id'],r['end_date'],')')
    last_end=r['end_date']; time.sleep(0.5)
reg=load()
def days(a,b): return abs((dt.date.fromisoformat(a)-dt.date.fromisoformat(b)).days)
IN='debit'; OUT='credit'
prev_close=None
if recs: prev_close=D(str(recs[-1]['closing_balance'])) if recs[-1].get('closing_balance') is not None else None
done=0; pending_gap=None
for i,k in enumerate(keys):
    period,s=stm[k]; pend,send=period
    if last_end and send<=last_end: continue
    start=(dt.date.fromisoformat(last_end)+dt.timedelta(days=1)).isoformat() if last_end else pend
    # gap: previous statement month missing -> fold the missing month into this period
    gap_rows=[]
    if last_end and start<pend:
        gap_rows=[t for t in reg.values() if start<=t['date']<pend and t['transaction_id'] not in used]
    pool=collections.defaultdict(list)
    for t in sorted(reg.values(),key=lambda t:(0 if t['_st']!='uncategorized' else 1,t['transaction_id'])):
        if t['transaction_id'] in used: continue
        pool[(t['debit_or_credit'],round(float(t['amount']),2))].append(t)
    sel=[]; missing=[]
    for x in s['tx']:
        side=IN if x['amt']>0 else OUT; hit=None
        for c in sorted(pool[(side,abs(float(x['amt'])))],key=lambda c:days(c['date'],x['date'])):
            if days(c['date'],x['date'])<=3: hit=c; break
        if hit: pool[(side,abs(float(x['amt'])))].remove(hit); sel.append(hit)
        else: missing.append(x)
    sel+= gap_rows
    if not sel and not missing and s['opening']==s['closing']:
        print(f"{k} {start}..{send}: no activity (balance {s['closing']}) - nothing to reconcile, folded into the next period",flush=True); continue
    unc=[t for t in sel if t['_st']=='uncategorized']
    net=sum(((D(str(t['amount'])) if t['debit_or_credit']==IN else -D(str(t['amount']))) for t in sel),D(0))
    opening=prev_close if prev_close is not None else s['opening']
    ok= not missing and not unc and (opening+net==s['closing'])
    print(f"{k} {start}..{send}: stmt tx {len(s['tx'])} matched {len(sel)-len(gap_rows)} gap-rows {len(gap_rows)} missing {len(missing)} uncategorized {len(unc)} | open {opening} + net {net} = {opening+net} vs printed {s['closing']} -> {'OK' if ok else 'HOLD'}",flush=True)
    if not ok:
        for m_ in missing[:4]: print('   MISSING in Books:',m_['date'],m_['amt'],m_['desc'][:40])
        for t in unc[:4]: print('   UNCATEGORIZED:',t['date'],t['debit_or_credit'],t['amount'],t['description'][:40])
        break
    if dry: break
    body={"start_date":start,"end_date":send,"closing_balance":float(s['closing']),"save_option":"reconcile","transactions_to_be_reconciled":[t['transaction_id'] for t in sel]}
    import http.client, urllib.error
    res=None
    for attempt in range(4):
        try: res=z.call('POST',f'bankaccounts/{AID}/reconciliations',body=body); break
        except SystemExit as e: res={'code':'ERR','message':str(e)[:300]}; break
        except (http.client.HTTPException, urllib.error.URLError, ConnectionError, TimeoutError):
            time.sleep(5*(attempt+1))
            have=retry(z.get,f'bankaccounts/{AID}/reconciliations',per_page=200)['reconciliations']   # did the dropped POST actually land?
            if any(r['end_date']==send for r in have): res={'code':0,'message':'landed despite dropped connection'}; break
    if res is None: res={'code':'ERR','message':'network retries exhausted'}
    open(MAN,'a').write(json.dumps({'acct':NAME,'stmt':k,'period':f'{start}..{send}','rows':len(sel),'closing':str(s['closing']),'code':res.get('code'),'message':res.get('message')})+'\n')
    if res.get('code')!=0:
        print('   FAILED',res.get('message'))
        ids=[t['transaction_id'] for t in sel]; fresh=load(); gone=[i for i in ids if i not in fresh]
        print('   selected ids no longer in register:',len(gone),gone[:5],'| selected',len(ids))
        for t in sel[:0]: pass
        break
    used|={t['transaction_id'] for t in sel}; last_end=send; prev_close=s['closing']; done+=1; time.sleep(1)
print('reconciled this run:',done,'| last end',last_end)
