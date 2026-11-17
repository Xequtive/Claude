import sys, json, re, time, collections, datetime as dt; sys.path.insert(0,'/home/user/claude/zoho/amex')
from paths import *
from resave_lib import retry, z
REG={'7244':('1635470000000150103','Manolo Checking'),'4861':('1635470000000150096','360 Checking'),'9051':('1635470000000150124','Sophie Checking'),
     '8873':('1635470000000150117','Manolo Savings'),'7838':('1635470000000150110','Sophie Savings'),'0153':('1635470000000150082','360 Perf Savings')}
def load(aid):
    out={}
    for st in ['uncategorized','categorized','matched']:
        page=1
        while True:
            d=retry(z.get,'banktransactions',account_id=aid,status=st,per_page=200,page=page)
            for t in d.get('banktransactions',[]): out.setdefault(t['transaction_id'],dict(t,_st=st))
            if not d.get('page_context',{}).get('has_more_page'): break
            page+=1; time.sleep(0.3)
        time.sleep(0.3)
    return out
cache={}
def get(no):
    p=f'/tmp/claude-0/capone/reg_{no}.json'
    try: cache[no]=json.load(open(p))
    except Exception: cache[no]=load(REG[no][0]); json.dump(cache[no],open(p,'w'))
    return cache[no]
def cp_no(desc):
    d=desc.replace('\xa0',' ')
    m=re.search(r'(?:Withdrawal to|Deposit from)\s+(.*?)\s+X+(\d{4})',d)
    if not m: return None,None
    name,last=m.group(1),m.group(2)
    if 'Capital One Checking' in name or 'Mami and Daddy' in name: last='4861'
    if 'Manolos Checking' in name or name=='MONEY': last=last if last in('7244','9051') else last
    return name,last
out={}
for no in ['8873','7838']:
    me=get(no); unc=[t for t in me.values() if t['_st']=='uncategorized']; res=collections.Counter(); rows=[]
    for t in unc:
        name,last=cp_no(t['description']); kind='no counterpart named (check deposit / other)'; cp=None
        if last in REG:
            other=get(last); want='credit' if t['debit_or_credit']=='debit' else 'debit'   # money-in here (debit) = money-out there (credit)
            c=[o for o in other.values() if abs(float(o['amount'])-float(t['amount']))<0.005 and o['debit_or_credit']==want and abs((dt.date.fromisoformat(o['date'])-dt.date.fromisoformat(t['date'])).days)<=3]
            if c:
                c.sort(key=lambda o:(0 if o['_st']=='uncategorized' else 1,abs((dt.date.fromisoformat(o['date'])-dt.date.fromisoformat(t['date'])).days)))
                cp=c[0]; kind=f"counterpart in {REG[last][1]}: {cp['_st']}"
            else: kind=f"names {REG[last][1]} but NO counterpart row found"
        res[kind]+=1; rows.append((t['transaction_id'],t['date'],t['debit_or_credit'],t['amount'],t['description'][:44],last,cp['transaction_id'] if cp else None,cp['_st'] if cp else None))
    print('==',no,len(unc),'uncategorized'); [print('   ',v,k) for k,v in res.most_common()]
    out[no]=rows
json.dump(out,open('/tmp/claude-0/capone/transfer_plan.json','w'))
