import sys, json, time; sys.path.insert(0,'/home/user/claude/zoho/amex')
from paths import *
from resave_lib import retry, z
AID='1635470000000150082'; EMJ='1635470000000275087'
MAN=ZOHO+'/manifests/2026-11-17_capone_savings_pairing.jsonl'
pairs=[('1635470000002172178','1635470000000372649','2019-11-16',5.14),('1635470000002163241','1635470000000372647','2019-10-02',188427.30)]
for new_feed,emj_feed,date,amt in pairs:
    r=z.call('POST',f'banktransactions/uncategorized/{new_feed}/categorize',params={'account_id':AID},body={"transaction_type":"transfer_fund","from_account_id":EMJ,"to_account_id":AID,"amount":amt,"date":date})
    new_tx=(r.get('banktransaction') or {}).get('transaction_id'); print('categorize',amt,r.get('code'),r.get('message'),'->',new_tx)
    time.sleep(1.5)
    cand=z.call('GET',f'banktransactions/uncategorized/{emj_feed}/match',params={'account_id':EMJ})
    ids=[(c.get('transaction_id'),c.get('transaction_type'),c.get('amount'),c.get('date')) for c in (cand.get('matching_transactions') or cand.get('transactions') or [])]
    print('  match candidates offered:',ids[:5])
    rec={'amt':amt,'date':date,'new_feed':new_feed,'new_tx':new_tx,'emj_feed':emj_feed,'cat_code':r.get('code'),'candidates':[i[0] for i in ids]}
    if new_tx and any(i[0]==new_tx for i in ids):
        m=z.call('POST',f'banktransactions/uncategorized/{emj_feed}/match',params={'account_id':EMJ},body={"transactions_to_be_matched":[{"transaction_id":new_tx,"transaction_type":"transfer_fund"}]})
        rec['match_code']=m.get('code'); rec['match_msg']=m.get('message'); print('  match:',m.get('code'),m.get('message'))
    else: rec['match']='new transaction not offered - NOT matched'; print('  NOT matched: new transaction not among candidates')
    open(MAN,'a').write(json.dumps(rec)+'\n'); time.sleep(1.5)
