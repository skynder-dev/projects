"""Isolated discussion example. Not a Social protocol, integration or publishing tool."""
import hashlib,json,os,sys
from pathlib import Path

def preview(comparison,candidate_key,source_catalog):
 import research_reviews
 row=next(r for r in comparison['rows'] if r['kind']+':'+r['id']==candidate_key)
 chain=comparison['research_chain'];link=chain['candidate_links'][candidate_key]
 materials={m['id']:m for m in source_catalog['materials']};byclaim={c['claim_id']:c for c in chain['claims']}
 refs=[]
 source_fields=[]
 for sid in link['source_ids']:
  m=materials[sid]
  source_fields.append({'binding':'EXACT_SAVED_MATERIAL','source_id':sid,'text':m['text'],'text_sha256':m['text_sha256'],'metadata':m['metadata'],'meaning':'Source text only; not an atomic condition or verified fact'})
 # Legacy candidates can have exact container-scoped fields without a source-ledger join.
 # Keep their locator and uncertainty; never invent a global source id or author link.
 candidates=iter(research_reviews.candidate_field_materials(row))
 for field in row['source_texts']:
  if 'source_snapshot' in field:
   snapshot=field['source_snapshot'];source_fields.append({'binding':'MANUAL_HYPOTHESIS_SNAPSHOT','snapshot':snapshot,'reference':field['reference'],'meaning':'Unverified saved manual interpretation context'})
  else:
   if hashlib.sha256(field['text'].encode()).hexdigest()!=field['field_sha256']:raise ValueError('Saved candidate field text/hash differ')
   material=next(candidates)
   source_fields.append({'binding':'CONTAINER_SCOPED_CANDIDATE_FIELD','review_source_id':material['id'],'reference':{k:v for k,v in field.items() if k!='text'},'text':field['text'],'meaning':'Exact historical candidate input field; role, truncation and author uncertainty retained'})
 for id in link['claim_ids']:
  c=byclaim[id];m=materials[c['source_id']];meta=m['metadata']
  refs.append({'claim_id':id,'source_id':m['id'],'field_id':meta.get('source_field','text'),'source_text_sha256':m['text_sha256'],'quote':c['quote'],'start':c['start'],'end':c['end'],'reported_author':meta.get('author'),'url':meta.get('url'),'captured_at':meta.get('captured_at'),'epistemic_status':meta.get('epistemic_status'),'semantic_status':c['semantic_status']})
 return {'schema':'ISOLATED_IDEA_EXPORT_DISCUSSION_ONLY_NOT_PROTOCOL','candidate_key':candidate_key,'workspace_scope':comparison.get('workspace_scope','UNSPECIFIED_INPUT'),'archive_sha256':comparison.get('archive_sha256'),
         'idea_hypotheses':{k:row.get(k) for k in ['title','buyer_hypothesis','problem_hypothesis','solution_hypothesis']},
         'audience':{'status':'UNVERIFIED_HYPOTHESIS' if row.get('buyer_hypothesis') else 'UNKNOWN','value':row.get('buyer_hypothesis')},
         'hook':{'status':'NOT_GENERATED','value':None,'reason':'No model run or approved editorial draft; source report is not a marketing promise'},
         'revision_sha256':chain['review_revisions'][candidate_key]['revision_sha256'],'source_fields':source_fields,'source_references':refs,
         'historical_qualification':{'model_output_review':row.get('model_review'),'assistant_source_review':row.get('assistant_source_review'),'historical_status_not_approval':row.get('historical_status_not_approval'),'semantic_PASS_not_established':True,'saved_manual_plan_not_execution':{'status':row.get('plan_status'),'assessment':row.get('current_manual_plan')},'saved_assistant_alternative_assessments':comparison.get('saved_alternative_assessments',{}).get(candidate_key,[])},
         'missing_data':{'condition_annotations':not bool(refs),'ledger_source_links':not bool(link['source_ids']),'editorial_hook':True,'verified_audience':True,'semantic_entailment':True,'market_validation':True},
         'revision_review':link.get('revision_review'),'limitations':{'semantic_coverage':'NOT_ASSESSED','known_missing_evidence':link['missing_evidence'],'risks':link['risks'],'unverified_saved_alternatives':link.get('unverified_saved_alternatives'),'market_advantage':'UNKNOWN','verified_customer':'UNKNOWN'},
         'credibility':'UNVERIFIED_RESEARCH_HYPOTHESIS_ONLY','ready_for_social':False,'publication_authorized':False,'owner_decision':link['owner_decision']}

def validate(value,comparison,catalog):
 # Full equality with a deterministic projection protects provenance/status, not semantic quality.
 expected=preview(comparison,value['candidate_key'],catalog)
 if value!=expected:raise ValueError('Discussion preview differs from exact research snapshot or overclaims readiness')
 return {'status':'PROVENANCE_ONLY','semantic_PASS':False,'ready_for_social':False,'publication_authorized':False}

def export_local(root,key,output,expected_revision_sha256=None):
 import comparison_data,source_ledger,research_export
 root=Path(root).resolve();output=Path(output).resolve()
 if not output.is_relative_to((root/'exports').resolve()) or output.suffix!='.json':raise ValueError('Discussion preview must be JSON inside local exports')
 data=comparison_data.build(root);catalog=source_ledger.catalog(root);value=preview(data,key,catalog);validate(value,data,catalog)
 if expected_revision_sha256 is not None and value['revision_sha256']!=expected_revision_sha256:raise ValueError('Displayed research revision is stale; refresh and review before exporting the idea')
 research_export.scan(value,'isolated-discussion-preview')
 current=comparison_data.build(root)
 if preview(current,key,source_ledger.catalog(root))!=value:raise ValueError('Research changed while preparing discussion preview')
 output.parent.mkdir(parents=True,exist_ok=True)
 with output.open('xb') as stream:
  stream.write(json.dumps(value,ensure_ascii=False,indent=2).encode());stream.flush();os.fsync(stream.fileno())
 return {'status':'LOCAL_DISCUSSION_EXAMPLE_ONLY','path':str(output),'ready_for_social':False,'publication_authorized':False}

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--candidate',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--expected-revision');a=p.parse_args()
 print(json.dumps(export_local(a.root,a.candidate,a.output,a.expected_revision)))
