"""Split a Capital One 'Combo' statement text into per-account sections and parse each section's transactions.
parse_statement(txt) -> {'period':(start,end),'sections':{acct_no:{'name','opening','closing','tx':[{date,desc,amt,bal}],'tie':bool}}}"""
import re, datetime as dt
from decimal import Decimal as D
MON={m:i+1 for i,m in enumerate('Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split())}
HDR=re.compile(r'^(\S.*?)\s+-\s+(\d{8,})\s*$')
DATE=re.compile(r'^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})\s{2,}(.*)$')
AMT=re.compile(r'([+-])\s*\$([\d,]+\.\d\d)')
BAL=re.compile(r'\$([\d,]+\.\d\d)')
def m(s): return D(s.replace(',',''))
def parse_statement(txt):
    mp=re.search(r'STATEMENT PERIOD\s*\n\s*(\w{3}) (\d+) - (\w{3}) (\d+), (\d{4})',txt)
    if not mp: mp=re.search(r'(\w{3}) (\d+) - (\w{3}) (\d+), (\d{4})',txt)
    s_mon,s_day,e_mon,e_day,yr=mp.groups(); end=dt.date(int(yr),MON[e_mon],int(e_day)); start_year=int(yr) if MON[s_mon]<=MON[e_mon] else int(yr)-1
    start=dt.date(start_year,MON[s_mon],int(s_day))
    secs={}; cur=None; blk=None
    def flush():
        nonlocal blk
        if blk and cur is not None: cur['_blocks'].append(blk)
        blk=None
    for line in txt.split('\n'):
        mh=HDR.match(line)
        if mh and not line.startswith(' '):
            flush(); cur=secs.setdefault(mh.group(2),{'name':mh.group(1).strip(),'_blocks':[]}); continue
        if cur is None: continue
        md=DATE.match(line)
        if md: flush(); blk={'mon':md.group(1),'day':int(md.group(2)),'lines':[md.group(3)]}; continue
        if blk is not None:
            if re.match(r'^\s*(Page \d+ of|DATE\s+DESCRIPTION|capitalone\.com|ORMAND|\s*STATEMENT PERIOD)',line) or not line.strip(): 
                if re.match(r'^\s*(Page \d+ of|capitalone\.com)',line): flush()
                continue
            blk['lines'].append(line.strip())
    flush()
    for no,s in secs.items():
        tx=[]; opening=closing=None; run_bal=None
        for b in s['_blocks']:
            body=' '.join(b['lines']); mo=MON[b['mon']]; y=end.year if (mo<=end.month or start.year==end.year) else end.year-1
            if mo>end.month and start.year!=end.year: y=start.year
            d=dt.date(y,mo,b['day'])
            if body.startswith('Opening Balance'): opening=m(BAL.search(body).group(1)); run_bal=opening; continue
            if body.startswith('Closing Balance'): closing=m(BAL.search(body).group(1)); continue
            ma=re.search(r'([+-])\s*(?=\$)',body)
            if not ma: continue   # e.g. 'Interest Rate Change' lines carry no amount
            sign=1 if ma.group(1)=='+' else -1
            nums=[m(x) for x in BAL.findall(body[ma.start():])]
            prev=run_bal if run_bal is not None else opening
            wrapped=bool(re.search(r'[+-]\s{2,}\$',body))
            if not nums: continue
            if wrapped and len(nums)>=2: amt,bal=sign*nums[-1],nums[0]
            else: amt=sign*nums[0]; bal=nums[1] if len(nums)>1 else None
            run_bal=prev+amt if prev is not None else None
            if bal is not None: run_bal=bal
            desc=re.sub(r'\s{2,}',' ',body[:ma.start()]).strip()
            desc=re.sub(r'\s+(Debit|Credit)\s*$','',desc)
            tx.append({'date':d.isoformat(),'desc':desc,'amt':amt,'bal':bal})
        s['opening'],s['closing'],s['tx']=opening,closing,tx
        s['tie']= (opening is not None and closing is not None and opening+sum((t['amt'] for t in tx),D(0))==closing)
        # running-balance cross-check
        run=opening; ok=True
        for t in tx:
            if run is not None: run+=t['amt']
            if t['bal'] is not None and run is not None and run!=t['bal']: ok=False
        s['run_ok']=ok
        del s['_blocks']
    return {'period':(start.isoformat(),end.isoformat()),'sections':secs}
if __name__=='__main__':
    import sys, collections
    names=collections.Counter(); bad=[]
    for k in sys.argv[1:]:
        r=parse_statement(open(f'/tmp/claude-0/capone/c_{k}.txt').read())
        for no,s in r['sections'].items():
            names[(no[-4:],s['name'])]+=1
            if not (s['tie'] and s['run_ok']): bad.append((k,no[-4:],s['name'],str(s['opening']),str(s['closing']),len(s['tx']),s['tie'],s['run_ok']))
    print('accounts seen:',sorted(names.items(),key=lambda x:-x[1])[:14]); print('sections not tying:',len(bad)); [print('  ',b) for b in bad[:12]]
