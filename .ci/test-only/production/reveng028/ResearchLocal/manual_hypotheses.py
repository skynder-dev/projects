"""Validate local manual drafts; no model, network, admission or buyer verification."""
import hashlib,json,re

def loads(value):
 def pairs(items):
  result={}
  for key,item in items:
   if key in result:raise ValueError('Duplicate manual JSON property')
   result[key]=item
  return result
 def invalid(value):raise ValueError('Non-finite manual JSON number')
 return json.loads(value,object_pairs_hook=pairs,parse_constant=invalid)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def unpack(wrapper):
 payload=wrapper.get('payload_json')
 if not isinstance(payload,str) or sha(payload.encode())!=wrapper.get('payload_sha256'):raise ValueError('Manual draft payload hash mismatch')
 return loads(payload)
def verify_material(source,fetch,names):
 text=source.get('text');kind=source.get('kind');bound=False;authors=set()
 if not isinstance(text,str) or not text or sha(text.encode())!=source.get('text_sha256'):raise ValueError('Manual source snapshot hash mismatch')
 for origin in source.get('origins',[]):
  name=origin['container'];field=origin['source_field']
  if not re.fullmatch(r'analysis-inputs/[0-9a-f]{64}\.json|observation-snapshots/[0-9a-f]{64}\.json|attribution-cases/[a-z0-9][a-z0-9-]{0,63}-catalog\.json',name) or name not in names:raise ValueError('Manual source container missing or unsafe')
  raw=fetch(name)
  if sha(raw)!=origin.get('container_sha256'):raise ValueError('Manual source container bytes changed')
  data=loads(raw.decode('utf-8-sig'))
  if name.startswith('attribution-cases/'):
   parent=data['sources'][origin['evidence_id']];row=parent['fields'][field];actual=row.get('text',row.get('full_text'));author=row.get('reported_author_id');url=row.get('url') or parent.get('url');stamp=row.get('captured_at') or parent.get('observed_at');expected_kind='community_answer' if field=='answer_text' else 'archived_original'
  else:
   rows=[r for r in data['observations'] if r.get('evidence_id')==origin.get('evidence_id') and r.get('observation_id')==origin.get('observation_id')]
   if len(rows)!=1:raise ValueError('Manual source origin ambiguous')
   row=rows[0];actual=row.get(field);author=row.get('answer_author_id' if field=='answer_text' else 'author_id')
   url=(row.get('answer_url') or row.get('url')) if field=='answer_text' else row.get('url');stamp=row.get('answer_observed_at') if field=='answer_text' else (row.get('context_observed_at') or row.get('observed_at')) if field=='context_text' else row.get('observed_at');expected_kind='community_answer' if field=='answer_text' else 'package_listing' if row.get('kind')=='package_listing_not_demand' else 'metadata_only' if field=='title' else 'archived_original' if row.get('content_scope') in ['question_body','original_post_only','original_ask_post'] else 'unscoped_observation'
  if actual!=text or author!=origin.get('reported_author_id'):raise ValueError('Manual source field/author binding mismatch')
  if source.get('url')!=url or origin.get('url')!=url or source.get('captured_at')!=stamp or origin.get('captured_at')!=stamp or kind!=expected_kind:raise ValueError('Manual source URL/date/role mismatch')
  authors.add('unknown' if author is None or author=='' else str(author))
  bound=True
 if authors and source.get('author')!=(next(iter(authors)) if len(authors)==1 else 'differing saved author metadata; see exact origins; identity not inferred'):raise ValueError('Manual source author display mismatch')
 if kind in ['original_post','provider_document']:
  if 'research-candidate-reviews.json' not in names:raise ValueError('Manual public source versions missing')
  state=loads(fetch('research-candidate-reviews.json').decode('utf-8-sig'));versions={w['payload_sha256']:w for item in state['items'].values() for w in item.get('research_versions',[])}
  if not source.get('version_ids'):raise ValueError('Manual public source version IDs missing')
  for id in source['version_ids']:
   if id not in versions:raise ValueError('Manual public source revision missing')
   version=unpack(versions[id]);rows=version['sources' if kind=='original_post' else 'documents']
   if not any(all(row.get(k)==source.get(k) for k in ['url','text','text_sha256','captured_at','author']) for row in rows):raise ValueError('Manual public source exact binding mismatch')
  bound=True
 if not bound:raise ValueError('Manual draft has no saved source origin')
def verify(fetch,names):
 if 'manual-hypotheses.json' not in names:return []
 state=unpack(loads(fetch('manual-hypotheses.json').decode('utf-8-sig')))
 if state.get('schema')!='reveng-manual-hypotheses-v1':raise ValueError('Unsupported manual drafts schema')
 if not isinstance(state.get('notes'),list):raise ValueError('Manual notes array missing or invalid')
 result=[];seen=set()
 for wrap in state['notes']:
  note=unpack(wrap);id=wrap['payload_sha256']
  if id in seen:raise ValueError('Duplicate manual revision')
  if note.get('schema')!='reveng-manual-hypothesis-v1' or note.get('origin')!='LOCAL_MANUAL_INPUT_NOT_MODEL_OUTPUT' or note.get('status')!='DRAFT_UNVERIFIED' or note.get('auto_admission') is not False or note.get('customer_status')!='UNVERIFIED' or note.get('demand_status')!='UNVERIFIED':raise ValueError('Manual draft cannot become automatic admission or buyer proof')
  for k in ['title','interpretation','assumptions','next_action','success','failure']:
   if not isinstance(note.get(k),str) or not note[k].strip() or len(note[k].encode('utf-16-le'))//2>(200 if k=='title' else 4000):raise ValueError('Manual draft field invalid: '+k)
  source=note['source_snapshot'];verify_material(source,fetch,names);r=note['reference'];text=source['text']
  if type(r['start']) is not int or type(r['end']) is not int or not 0<=r['start']<r['end']<=len(text) or r['end']-r['start']>1000 or r['text_sha256']!=source['text_sha256'] or text[r['start']:r['end']]!=r['quote']:raise ValueError('Manual quote/range mismatch')
  if note.get('supersedes') and note['supersedes'] not in seen:raise ValueError('Manual prior revision missing or out of order')
  seen.add(id);result.append(dict(note,id=id))
 return result
