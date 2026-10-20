"""Protected owner-decision copy only; never automatic merge or authority."""
import hashlib,re
from manual_hypotheses import loads
NAME='decision-recovery-v1.json'


def verify(fetch,names):
 if NAME not in names:return 0
 raw=fetch(NAME)
 if len(raw)>8*1024*1024:raise ValueError('Decision recovery exceeds8MiB')
 wrapper=loads(raw.decode('utf-8-sig'));payload=wrapper.get('payload_json')
 if not isinstance(payload,str)or hashlib.sha256(payload.encode()).hexdigest()!=wrapper.get('payload_sha256'):raise ValueError('Decision recovery hash mismatch')
 value=loads(payload)
 if set(value)!={'schema','status','expected_primary_sha256','decisions'}or value['schema']!='reveng-decision-recovery-v1'or value['status']!='RECOVERY_COPY_NOT_CURRENT_AUTHORITY'or not isinstance(value['decisions'],dict):raise ValueError('Decision recovery is not current owner authority')
 pin=value['expected_primary_sha256']
 if pin is not None and(not isinstance(pin,str)or not re.fullmatch('[0-9a-fA-F]{64}',pin)):raise ValueError('Invalid decision recovery parent pin')
 return len(value['decisions'])
