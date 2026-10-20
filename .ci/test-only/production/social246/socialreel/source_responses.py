"""Existing Grants.gov response validation: unknown/incomplete is not empty or ineligible."""
from .common import PipelineError
class IncompleteSourceResponse(PipelineError):pass
def requested_id(value):
 text=str(value)
 if isinstance(value,bool) or not 1<=len(text)<=32 or not text.isascii() or not text.isdigit() or int(text)<=0:raise IncompleteSourceResponse('Invalid requested opportunity identity before source request')
 return text

def search_payload(envelope,rows,start):
 if type(rows) is not int or not 1<=rows<=1000 or type(start) is not int or start<0:raise IncompleteSourceResponse('Invalid bounded search request')
 data=envelope.get('data') if isinstance(envelope,dict) else None
 if not isinstance(data,dict) or 'oppHits' not in data or not isinstance(data['oppHits'],list):raise IncompleteSourceResponse('Grants.gov search missing/invalid oppHits; not a verified empty result')
 hits=data['oppHits']
 if len(hits)>rows:raise IncompleteSourceResponse('Search returned more hits than requested; cursor not advanced')
 for hit in hits:
  id=hit.get('id') if isinstance(hit,dict) else None
  if isinstance(id,bool) or not isinstance(id,(str,int)) or not 1<=len(str(id))<=32 or not str(id).isascii() or not str(id).isdigit() or int(id)<=0:raise IncompleteSourceResponse('Search hit lacks a valid pinned identity; page remains unconfirmed')
 paging=None
 if 'hitCount' in data:
  total=data['hitCount'];offset=data.get('startRecord')
  if type(total) is not int or total<0 or type(offset) is not int or offset!=start:raise IncompleteSourceResponse('Inconsistent search pagination metadata')
  if len(hits)>max(0,total-start) or not hits and start<total:raise IncompleteSourceResponse('Search hits conflict with reported total; not proof catalog exhausted')
  paging={'start':start,'total':total}
 return hits,paging

def detail_record(detail,opp_id):
 opp_id=requested_id(opp_id)
 if not isinstance(detail,dict) or not detail:raise IncompleteSourceResponse('Empty Grants.gov detail; keep source pending, not rejected')
 id=detail.get('id')
 if isinstance(id,bool) or not isinstance(id,(str,int)) or not 1<=len(str(id))<=32 or not str(id).isascii() or not str(id).isdigit() or int(id)<=0 or int(id)!=int(opp_id):raise IncompleteSourceResponse('Grants.gov detail identity differs from requested opportunity')
 if not isinstance(detail.get('opportunityTitle'),str) or not detail['opportunityTitle'].strip():raise IncompleteSourceResponse('Detail title missing; response incomplete')
 if not any(isinstance(detail.get(k),dict) and detail[k] for k in ['synopsis','forecast']):raise IncompleteSourceResponse('Detail has no substantive synopsis/forecast; response incomplete')
 return detail

def detail_envelope(data,opp_id):
 if not isinstance(data,dict):raise IncompleteSourceResponse('Detail envelope is not an object')
 try:code=int(data.get('errorcode',0) or 0)
 except (TypeError,ValueError):raise IncompleteSourceResponse('Detail error code invalid')
 if code:raise IncompleteSourceResponse('Saved detail reports API error; not adopted')
 return detail_record(data.get('data'),opp_id)
