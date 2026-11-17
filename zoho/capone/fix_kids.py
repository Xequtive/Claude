import sys, json, time, datetime as dt; sys.path.insert(0,'/home/user/claude/zoho/amex')
from paths import *
from resave_lib import retry, z
M='1635470000000150117'; S='1635470000000150110'
MAN=ZOHO+'/manifests/2026-11-17_capone_savings_categorize.jsonl'
rows=[('8873',M,S,'1635470000000361117','2022-12-01','credit',89.0),('7838',S,M,'1635470000000352166','2024-10-12','debit',10.0)]
def call(m,p,**kw):
    try: return z.call(m,p,**kw)
    except SystemExit as e: return {'code':'ERR','message':str(e)[:250]}
for no,me,other,tid,date,side,amt in rows:
    frm,to=(me,other) if side=='credit' else (other,me)
    r=call('POST',f'banktransactions/uncategorized/{tid}/categorize',params={'account_id':me},body={"transaction_type":"transfer_fund","from_account_id":frm,"to_account_id":to,"amount":amt,"date":date})
    new=(r.get('banktransaction') or {}).get('transaction_id'); rec={'acct':no,'tid':tid,'date':date,'amount':amt,'kind':'transfer (other kids savings account)','code':r.get('code'),'msg':r.get('message'),'new_tx':new}
    print(no,date,amt,r.get('code'),r.get('message'))
    if r.get('code')==0 and new:
        other_reg=json.load(open('/tmp/claude-0/capone/reg_'+('7838' if no=='8873' else '8873')+'.json'))
        want='debit' if side=='credit' else 'credit'
        c=[o for o in other_reg.values() if o['_st']=='uncategorized' and abs(float(o['amount'])-amt)<0.005 and o['debit_or_credit']==want and abs((dt.date.fromisoformat(o['date'])-dt.date.fromisoformat(date)).days)<=3]
        rec['cp_candidates']=[o['transaction_id'] for o in c]
        if len(c)==1:
            time.sleep(1.2); cand=call('GET',f"banktransactions/uncategorized/{c[0]['transaction_id']}/match",params={'account_id':other}); ids=[x.get('transaction_id') for x in (cand.get('matching_transactions') or cand.get('transactions') or [])]
            if new in ids:
                mm=call('POST',f"banktransactions/uncategorized/{c[0]['transaction_id']}/match",params={'account_id':other},body={"transactions_to_be_matched":[{"transaction_id":new,"transaction_type":"transfer_fund"}]}); rec['match']=mm.get('code'); print('  matched counterpart:',mm.get('code'))
            else: rec['match']='not offered'
    open(MAN,'a').write(json.dumps(rec)+'\n'); time.sleep(1.5)
