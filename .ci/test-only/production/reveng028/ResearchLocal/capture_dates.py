"""Application cache age only; parse/review time never renews source capture."""
from datetime import datetime
import time
def timestamp(value):
 try:
  if type(value)is not str:return None
  parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
  return None if parsed.tzinfo is None else parsed.timestamp()
 except (ValueError,OverflowError):return None
def expiry(stamp,ttl=86400,now=None):
 clock=time.time()if now is None else now;t=timestamp(stamp)
 return 0 if t is None or t>clock else t+ttl
def current(record,expiry_key='expires',ttl=86400,now=None):
 clock=time.time()if now is None else now;until=expiry(record.get('observed_at'),ttl,clock);claimed=record.get(expiry_key)
 return type(claimed)in[int,float]and claimed>clock and until>clock
