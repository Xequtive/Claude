import sys, json, time; sys.path.insert(0,'/home/user/claude/zoho/amex')
from paths import *
from resave_lib import retry, z
REG={'7244':'1635470000000150103','4861':'1635470000000150096','9051':'1635470000000150124','8873':'1635470000000150117','7838':'1635470000000150110','0153':'1635470000000150082'}
OWN={'8873':'1635470000000150117','7838':'1635470000000150110'}
INCOME='1635470000000369711'   # Uncategorized/No Statement Income (Net)
plan=json.load(open('/tmp/claude-0/capone/transfer_plan.json'))
MAN=ZOHO+'/manifests/2026-11-17_capone_savings_categorize.jsonl'; QUEUE=ZOHO+'/capone/review_queue.jsonl'
probe='--probe' in sys.argv; n=0
def call(m,p,**kw):
    try: return z.call(m,p,**kw)
    except SystemExit as e: return {'code':'ERR','message':str(e)[:250]}
for no,rows in plan.items():
    me=OWN[no]
    for tid,date,side,amt,desc,last,cp_tid,cp_st in rows:
        rec={'acct':no,'tid':tid,'date':date,'side':side,'amount':amt,'desc':desc,'counterpart':last,'cp_tid':cp_tid,'cp_status':cp_st}
        if last in REG and REG[last]!=me:
            other=REG[last]; frm,to=(me,other) if side=='credit' else (other,me)
            r=call('POST',f'banktransactions/uncategorized/{tid}/categorize',params={'account_id':me},body={"transaction_type":"transfer_fund","from_account_id":frm,"to_account_id":to,"amount":float(amt),"date":date})
            rec['kind']='transfer'; rec['code']=r.get('code'); rec['msg']=r.get('message'); new_tx=(r.get('banktransaction') or {}).get('transaction_id'); rec['new_tx']=new_tx
            if r.get('code')==0 and cp_tid and cp_st=='uncategorized' and new_tx:
                time.sleep(1.2)
                cand=call('GET',f'banktransactions/uncategorized/{cp_tid}/match',params={'account_id':other}); ids=[c.get('transaction_id') for c in (cand.get('matching_transactions') or cand.get('transactions') or [])]
                if new_tx in ids:
                    m=call('POST',f'banktransactions/uncategorized/{cp_tid}/match',params={'account_id':other},body={"transactions_to_be_matched":[{"transaction_id":new_tx,"transaction_type":"transfer_fund"}]}); rec['match']=m.get('code')
                else: rec['match']='not offered'
            elif r.get('code')==0 and not cp_tid:
                open(QUEUE,'a').write(json.dumps({'acct':no,'date':date,'amount':amt,'desc':desc,'action':f'categorized as transfer with {last}','confidence':'>=80% (account named)','note':'counterpart row not in the other register yet - match when that register is processed'})+'\n')
        elif last is None and 'Check Deposit' in desc:
            r=call('POST',f'banktransactions/uncategorized/{tid}/categorize',params={'account_id':me},body={"transaction_type":"deposit","from_account_id":INCOME,"to_account_id":me,"amount":float(amt),"date":date})
            rec['kind']='check deposit -> Uncategorized/No Statement Income'; rec['code']=r.get('code'); rec['msg']=r.get('message')
            open(QUEUE,'a').write(json.dumps({'acct':no,'date':date,'amount':amt,'desc':desc,'action':'deposit to Uncategorized/No Statement Income (placeholder)','confidence':'<80%','note':'payer unknown'})+'\n')
        else:
            rec['kind']='skipped'; rec['code']='skip'
            open(QUEUE,'a').write(json.dumps({'acct':no,'date':date,'amount':amt,'desc':desc,'action':'left uncategorized','confidence':'<80%','note':'counterpart account unclear'})+'\n')
        open(MAN,'a').write(json.dumps(rec)+'\n'); n+=1
        print(n,no,date,amt,rec['kind'],rec.get('code'),rec.get('match',''),flush=True)
        if probe: sys.exit()
        time.sleep(1.0)
