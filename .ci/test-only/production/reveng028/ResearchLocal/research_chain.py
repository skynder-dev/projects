"""Read-only links, never automatic semantic conditions, preference, score or decision."""
from pathlib import Path
import json,tempfile,re
import source_ledger as l,source_proposals

def build(root,comparison):
 root=Path(root).resolve();inputs={};issues=[];claims=[]
 def capture(name):
  path=root/name;inputs[name]=l.rawsha(path.read_bytes()) if path.exists() else None
 for name in ['source-ledger-catalog.json','source-ledger.json','source-model-proposals.json']:capture(name)
 if inputs['source-ledger-catalog.json'] is None:
  return {'schema':'reveng-research-chain-v1','inputs':inputs,'claims':[],'candidate_links':{},'issues':['SOURCE_CATALOG_MISSING'],'unlinked_claims':[],'coverage':'NOT_ASSESSED','semantic_PASS':False,'decision':'NO_EXPLICIT_REVISION_BOUND_DECISION','automatic_admission':False}
 cat=l.catalog(root);materials={m['id']:m for m in cat['materials']}
 for name,h in cat['inputs'].items():
  capture(name)
  if inputs[name]!=h:raise ValueError('Chain source input changed')
 for name,h in comparison['inputs'].items():
  capture(name)
  if inputs[name]!=h:raise ValueError('Comparison changed during chain capture')
 try:
  notes,_=l.notes(root);l.verify_notes(cat,notes)
  for w in notes['entries']:
   n=l.unseal(w);sid=n['source_snapshot']['id'];claims.append({'claim_id':'manual:'+w['payload_sha256'],'source_id':sid,'field_id':n['source_snapshot']['metadata'].get('source_field','text'),'category':n['category'],'quote':n['quote'],'start':n['start'],'end':n['end'],'interpretation':None,'origin':'EXPLICIT_HUMAN_SELECTION','semantic_status':'UNVERIFIED_REPORTED_CONTENT','source_status':'CURRENT_EXACT_REVISION' if sid in materials else 'HISTORICAL_NOT_CURRENTLY_RESOLVABLE','source_snapshot':n['source_snapshot']})
 except (ValueError,KeyError,TypeError) as e:issues.append('MANUAL_LEDGER_INVALID: '+str(e))
 try:
  proposals=source_proposals.load(root,cat)
  for w in proposals['entries']:
   row=l.unseal(w)
   for sid,result in row['result']['sources'].items():
    for index,e in enumerate(result.get('annotations',[])):
     c=e['citation'];claims.append({'claim_id':'model:'+w['payload_sha256']+':'+sid+':'+str(index),'source_id':sid,'field_id':materials[sid]['metadata'].get('source_field','text') if sid in materials else 'HISTORICAL_SAVED_FIELD','category':e['category'],'quote':c['quote'],'start':c['start'],'end':c['end'],'interpretation':e['AI_reading_unverified'],'origin':'SAVED_UNVERIFIED_MODEL_PROPOSAL','semantic_status':'UNVERIFIED_MODEL_PROPOSAL','source_status':'CURRENT_EXACT_REVISION' if sid in materials else 'HISTORICAL_NOT_CURRENTLY_RESOLVABLE','proposal_id':w['payload_sha256']})
 except (ValueError,KeyError,TypeError) as e:issues.append('MODEL_PROPOSALS_INVALID: '+str(e))
 linked=set();links={}
 for row in comparison['rows']:
  key=row['kind']+':'+row['id']
  # Associations use recorded exact card identities only; never URL/title/word similarity.
  mids={sid for sid,m in materials.items() if row['id'] in m['metadata'].get('card_ids',[])}
  if row['kind']=='manual_hypothesis':
   for ref in row['source_references']:
    s=ref.get('source_snapshot',{});sid=s.get('id')
    if sid in materials and l.same_manual_source_revision(cat,materials[sid],s):mids.add(sid)
  matches=[c['claim_id'] for c in claims if c['source_id'] in mids and c['source_status']=='CURRENT_EXACT_REVISION']
  linked.update(matches)
  links[key]={'source_ids':sorted(mids),'claim_ids':matches,'atomic_condition_status':'UNVERIFIED_ANNOTATIONS_ONLY' if matches else 'NO_SAVED_CONDITION_ANNOTATIONS',
              'semantic_coverage':'NOT_ASSESSED_REQUIRES_FULL_SOURCE_REVIEW','source_fields_without_annotations':sorted(mids-{c['source_id'] for c in claims if c['claim_id'] in matches}),
              'historical_status_not_approval':row.get('historical_status_not_approval'),'unverified_saved_alternatives':row.get('unverified_saved_alternatives'),'missing_evidence':row.get('missing_evidence',[]),'risks':row.get('risks',[]),'owner_decision':'NO_EXPLICIT_REVISION_BOUND_DECISION','verified_customer':'UNKNOWN','market_advantage':'UNKNOWN','automatic_admission':False}
 import research_reviews
 revisions={row['kind']+':'+row['id']:research_reviews.revision(root,comparison,cat,row['kind']+':'+row['id'],claims) for row in comparison['rows']}
 capture('research-reviews.json')
 try:reviews=research_reviews.statuses(root,revisions)
 except (ValueError,KeyError,TypeError) as e:
  issues.append('RESEARCH_REVIEW_LOG_INVALID: '+str(e));reviews={'candidates':{},'orphan_history':[],'semantic_PASS':False,'execution_authorized':False}
 for key,link in links.items():
  link['revision_review']=reviews['candidates'].get(key,{'decision':'INVALID_OR_ABSENT_REVIEW','coverage':'NOT_ASSESSED','history':[]})
  link['owner_decision']=link['revision_review']['decision']
 for name,h in inputs.items():
  p=root/name
  if (l.rawsha(p.read_bytes()) if p.exists() else None)!=h:raise ValueError('Research chain changed during capture')
 return {'schema':'reveng-research-chain-v2','inputs':inputs,'claims':claims,'candidate_links':links,'issues':issues,
         'review_revisions':revisions,'revision_reviews':reviews,'unlinked_claims':[c['claim_id'] for c in claims if c['claim_id'] not in linked],
         'coverage':'NOT_ASSESSED','semantic_PASS':False,'decision':'NO_EXPLICIT_REVISION_BOUND_DECISION','automatic_admission':False}

def verify_portable(fetch,names):
 if 'research-reviews.json' in names and 'research-chain.json' not in names:raise ValueError('Review log requires source-bound research chain in export')
 if 'research-chain.json' not in names:return
 expected=l.unseal(json.loads(fetch('research-chain.json')))
 # Recompute from bounded, already path/checksum-validated export data; never trust a new hash alone.
 with tempfile.TemporaryDirectory(prefix='reveng-chain-') as folder:
  root=Path(folder)
  for name in names:
   if (name.endswith('.json') and name!='manifest.json') or re.fullmatch(r'buyer-source-payloads/[0-9a-f]{64}\.raw',name):
    p=(root/name).resolve()
    if not p.is_relative_to(root):raise ValueError('Unsafe chain export path')
    p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(fetch(name))
  import comparison_data
  comparison=comparison_data.build(root,include_chain=False)
  actual=build(root,comparison)
  import research_reviews
  if 'research-reviews.json' in names:
   if 'revision_reviews' not in actual:raise ValueError('Review declarations require a source catalog and revision-bound chain')
   research_reviews.verify_summary(fetch,names,actual['revision_reviews'])
  if expected.get('schema')=='reveng-research-chain-v1':
   if 'research-reviews.json' in names:raise ValueError('Legacy chain cannot carry new owner review declarations')
   actual['schema']='reveng-research-chain-v1';actual.pop('review_revisions',None);actual.pop('revision_reviews',None);actual['inputs'].pop('research-reviews.json',None)
   for link in actual['candidate_links'].values():link.pop('revision_review',None)
  if actual!=expected:raise ValueError('Research chain does not match exported source/annotation revisions')

if __name__=='__main__':
 import argparse,comparison_data
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args()
 l.require_writable(a.root)
 result=build(a.root,comparison_data.build(a.root,include_chain=False));l.write(a.root/'research-chain.json',l.seal(result));print(json.dumps({'claims':len(result['claims']),'candidates':len(result['candidate_links']),'semantic_PASS':False}))
