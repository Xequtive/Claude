"""Post-last-statement cleanup from the owner's Amex activity export (Oct 22 - Nov 20 2026):
1) exclude Books rows dated after 10/21/26 that are NOT on the export; 2) categorize the matched export rows still uncategorized."""
from paths import *
import json, time, http.client, urllib.error, sys
from process4 import *
MAN=ZOHO+'/manifests/2026-11-17_amex_poststatement_cleanup.jsonl'
def call(m,p,**params):
    for i in range(6):
        try: return z.call(m,p,params=params)
        except SystemExit as e: return {'code':'ERR','message':str(e)[:300]}
        except (http.client.HTTPException, urllib.error.URLError, ConnectionError, TimeoutError): time.sleep(3*(i+1))
    return {'code':'ERR','message':'network retries exhausted'}
late=json.load(open('/tmp/claude-0/amex/late_extras.json')); n=0
for tid,st,date,side,amt,desc,itid in late:
    rec={'tid':tid,'date':date,'amount':amt,'side':side,'desc':desc,'status':st}; fid=tid
    if st=='categorized':
        if not itid: rec['note']='no feed id'; open(MAN,'a').write(json.dumps(rec)+'\n'); continue
        r=call('POST','banktransactions/uncategorize',account_id=A,imported_transaction_ids=itid); rec['uncat']=r.get('code')
        if r.get('code')!=0: rec['msg']=r.get('message'); open(MAN,'a').write(json.dumps(rec)+'\n'); continue
        fid=itid; time.sleep(1.2)
    r=call('POST',f'banktransactions/uncategorized/{fid}/exclude',account_id=A); rec['exclude']=r.get('code'); rec['msg']=r.get('message')
    open(MAN,'a').write(json.dumps(rec)+'\n'); n+=r.get('code')==0; time.sleep(0.9)
print('excluded',n,'of',len(late),flush=True)
# categorize matched-but-uncategorized export rows with the standard policy
plan=json.load(open('/tmp/claude-0/amex/post_stmt_plan.json')); reg=load_register(); H2=build_hist2(reg); c=0
for x,tid,st in plan['matched']:
    if st!='uncategorized' or tid not in reg or reg[tid]['_st']!='uncategorized': continue
    b=reg[tid]; desc=b['description'].upper(); rd=b.get('rule_details') or {}
    if b['debit_or_credit']=='credit':
        if b.get('is_rule_exist') and rd.get('transaction_type')=='expense' and rd.get('offset_account_id'): acct,why,flag=rd['offset_account_id'],rd.get('offset_account_name')+' (rule)',None
        else:
            p=pick2(H2,b['description'],'charge')
            acct,why,flag=(p[2],f'{p[1]} (history {p[3]})',None) if p and p[0]=='expense' else (PLACE,'Uncategorized Transactions (placeholder)','no rule and <80% history')
        res=call('POST',f"banktransactions/uncategorized/{tid}/categorize/expenses",account_id=A) if False else None
        try: res=z.call('POST',f"banktransactions/uncategorized/{tid}/categorize/expenses",params={'account_id':A},body={"date":b['date'],"amount":float(b['amount']),"account_id":acct,"paid_through_account_id":A})
        except SystemExit as e: res={'code':'ERR','message':str(e)[:200]}
    else:
        p=pick2(H2,b['description'],'pay'); flag=None
        if ('PAYMENT' in desc and 'THANK YOU' in desc) or (p and p[0]=='card_payment'):
            bn,bid,why2,ok=pay_source(b['amount'],b['date']); acct,ty,why,flag=bid,'card_payment',f'card payment from {bn} ({why2})',None if ok else why2
        elif p and p[0]=='expense_refund': acct,ty,why=p[2],'expense_refund',f'{p[1]} refund (history {p[3]})'
        else: acct,ty,why,flag=PLACE,'expense_refund','Uncategorized Transactions refund (placeholder)','credit/other debit-side row, <80% sure'
        try: res=z.call('POST',f"banktransactions/uncategorized/{tid}/categorize",params={'account_id':A},body={"transaction_type":ty,"from_account_id":acct,"to_account_id":A,"amount":float(b['amount']),"date":b['date']})
        except SystemExit as e: res={'code':'ERR','message':str(e)[:200]}
    open(MAN,'a').write(json.dumps({'tid':tid,'date':b['date'],'amount':b['amount'],'desc':b['description'][:50],'categorized_as':why,'code':res.get('code'),'msg':res.get('message')})+'\n')
    if flag: qlog(stmt='post-10/21 export',date=b['date'],amount=str(b['amount']),desc=b['description'][:70],action=why,confidence='<80%',reason=flag)
    c+= res.get('code')==0; time.sleep(0.9)
print('categorized',c,flush=True)
