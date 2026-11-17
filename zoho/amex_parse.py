import re, sys, json
from decimal import Decimal as D
AMT=r'(-?\$[\d,]+\.\d\d)'
LINE=re.compile(r'^\s*(\d\d/\d\d/\d\d)(\*?)\s+(.*?)\s+'+AMT+r'(?:\s+[t⧫]+)?\s*$')
def money(s): return D(s.replace('$','').replace(',','').replace('+','').replace('=','').strip())
def parse(txt):
    out=[]; sec=None; lines=txt.split('\n')
    for i,l in enumerate(lines):
        s=l.strip()
        if re.match(r'^Payments\s+Amount$',s): sec='payment'; continue
        if re.match(r'^Credits\s+Amount$',s): sec='credit'; continue
        if re.match(r'^New Charges\s*$',s): sec='charge'; continue
        if re.match(r'^Fees\b.*(t - denotes|Amount)?',s) and re.match(r'^Fees\s*(t - denotes.*)?$|^Fees\s+Amount$',s): sec='fee'; continue
        if re.match(r'^Interest Charged\b',s) and 'Amount' in s: sec='interest'; continue
        if re.match(r'^(Total Fees for this Period|Total Interest Charged for this Period|About Trailing Interest|Interest Charge Calculation|Important Notices|IMPORTANT NOTICES)',s): sec=None; continue
        m=LINE.match(l)
        if not m and sec:
            md=re.match(r'^\s*(\d\d/\d\d/\d\d)(\*?)\s+(.*\S)\s*$',l)
            if md:
                for j in range(i+1,min(i+8,len(lines))):
                    ma=re.match(r'^\s*'+AMT+r'(?:\s+[t⧫]+)?\s*$',lines[j])
                    if ma:
                        m=re.match(r'^\s*(\d\d/\d\d/\d\d)(\*?)\s+(.*?)\s+'+AMT+r'$', md.group(0)+'  '+ma.group(1)); break
                    if re.match(r'^\s*\d\d/\d\d/\d\d',lines[j]): break
        if m and sec:
            d,star,desc,amt=m.groups()
            out.append({'sec':sec,'date':d,'posting':bool(star),'desc':re.sub(r'\s{2,}',' | ',desc.strip()),'amt':str(money(amt)),'line':i})
    return out
def summary(txt):
    lines=txt.split('\n'); res={}
    start=next(i for i,l in enumerate(lines) if re.search(r'Account Total\s*$',l))
    for l in lines[start+1:start+14]:
        m=re.search(r'(Previous Balance|Payments/Credits|New Charges|New Cash Advances|Fees|Interest Charged|New Balance|Minimum Payment Due)\s+([=+-]?\s*-?\+?\$[\d,]+\.\d\d)\s*$',l)
        if m: res[m.group(1)]=money(m.group(2))
    res['closing']=re.search(r'Closing Date (\d\d/\d\d/\d\d)',txt).group(1)
    return res
def tie(txt):
    tx=parse(txt); sm=summary(txt); by={}
    for t in tx: by[t['sec']]=by.get(t['sec'],D(0))+D(t['amt'])
    calc=sm['Previous Balance']+sum(by.values(),D(0))
    return tx,sm,by,calc
if __name__=='__main__':
    for n in sys.argv[1:]:
        txt=open(f'/tmp/claude-0/amex/s_{n}.txt').read()
        tx,sm,by,calc=tie(txt)
        print(n,'closing',sm['closing'],'prev',sm['Previous Balance'],'printed new',sm['New Balance'],'| printed pay',sm['Payments/Credits'],'chg',sm['New Charges'],'fees',sm['Fees'],'int',sm['Interest Charged'])
        print('   parsed',{k:str(v) for k,v in by.items()},'rows',len(tx),'| prev+parsed',calc,'TIE' if calc==sm['New Balance'] else 'MISMATCH')
