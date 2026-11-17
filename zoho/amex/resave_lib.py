import sys, json, time, urllib.error, http.client
from paths import *
import zoho_client as z
def retry(f,*a,**k):
    for i in range(5):
        try: return f(*a,**k)
        except (http.client.IncompleteRead, http.client.RemoteDisconnected, urllib.error.URLError, ConnectionError, TimeoutError):
            time.sleep(3*(i+1))
    raise RuntimeError('gave up')
BODY_KEYS=['rule_name','rule_category','apply_to','criteria_type','record_as','account_id','auto_categorize','reference_number']
def body_of(d):
    b={k:d[k] for k in BODY_KEYS if k in d}
    b['criterion']=[{k:c[k] for k in ('field','comparator','value')} for c in d['criterion']]
    return b
def norm(d):
    b=body_of(d); b['criterion']=sorted(json.dumps(c,sort_keys=True) for c in b['criterion']); return b
