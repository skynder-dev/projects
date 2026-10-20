"""Mechanical review diagnostics only. Never changes a model verdict or proves entailment."""
import re
import contract_v3,response_diagnostics as rd

QUOTES=re.compile(r'''(?<!\w)'([^'\n]{3,240})'(?!\w)|"([^"\n]{3,240})"|“([^”\n]{3,240})”''')
def audit(contract,output):
 sources,units=contract_v3.catalog(contract['source_catalog']);annotations=set();all_refs=set();quoted=[];groups=[]
 def check_text(path,text,ids,sid):
  selected=[units[u]['fragment']['quote'] for u in ids]
  for match in QUOTES.finditer(text):
   q=next(v for v in match.groups()if v is not None)
   if any(q in s for s in selected):continue
   same=[uid for uid,u in units.items()if u['source_alias']==sid and q in u['fragment']['quote']]
   quoted.append({'record':path,'quoted_text':q,'status':'QUOTE_OUTSIDE_SELECTED_SPANS'if same else'QUOTED_TEXT_NOT_VERBATIM_SOURCE_REVIEW_REQUIRED','selected_units':list(ids),'other_matching_units_DIAGNOSTIC_ONLY':same,'verdict_changed':False})
 for sid,row in output['sources'].items():
  for n,a in enumerate(row.get('annotations',[])):
   ids=a['unit_ids'];annotations.update(ids);all_refs.update(ids)
   if len(ids)>1:groups.append({'record':sid+'/annotations/'+str(n),'units':ids,'status':'MULTI_UNIT_INTERPRETATION_REQUIRES_COVERAGE_REVIEW'})
   check_text(sid+'/annotations/'+str(n),a['AI_reading_unverified'],ids,sid)
 for atom in contract['atoms']:
  row=output['atom_checks'][atom['id']];sid=next(s for s,f in sources.items()if(f['source_id'],f['field_id'])==(atom['source_id'],atom['field_id']));all_refs.update(row['unit_ids']);check_text('atom/'+atom['id'],row['reason'],row['unit_ids'],sid)
 return {'schema':'reveng-mechanical-proposal-review-v1','decision_eligibility':'BLOCKED_PENDING_INDEPENDENT_SEMANTIC_REVIEW','source_unit_count':len(units),'annotation_units_referenced':len(annotations),'all_units_referenced':len(all_refs),'units_without_annotation':sorted(set(units)-annotations),'units_without_any_reference':sorted(set(units)-all_refs),'quoted_span_warnings':quoted,'multi_unit_groups':groups,'meaning':'Exact quote-location and coverage diagnostics only. Missing units may be routing/context; all referenced is not complete interpretation. Scare quotes and paraphrases require review. No automatic repair, guessed span, corrected verdict or semantic PASS.','semantic_PASS':False,'automatic_admission':False}

def for_row(row):
 c=row['contract']
 import contract_v4,base64
 if c.get('contract_version')==contract_v4.VERSION:
  raw=base64.b64decode(row['raw_response_base64'],validate=True);content=rd.unwrap(raw);derived=contract_v4.derive(c,content);out=rd.strict_json(content.decode('utf-8'));sources,units=contract_v3.catalog(c['source_catalog']);view={'sources':{sid:{'annotations':[]}for sid in sources},'atom_checks':out['atom_checks']}
  for uid,u in out['unit_coverage'].items():
   if u['status']=='interpretation_proposed':view['sources'][units[uid]['source_alias']]['annotations'].append({'unit_ids':[uid],'AI_reading_unverified':u['AI_reading_unverified']})
  d=audit(c,view);d['explicit_unit_accounting_unverified']=derived['result']['unit_accounting'];d['whole_proposition_checks_UNVERIFIED']=derived['result']['atom_checks'];return d
 if c.get('contract_version')!=contract_v3.VERSION:return {'decision_eligibility':'BLOCKED_PENDING_INDEPENDENT_SEMANTIC_REVIEW','semantic_PASS':False,'reason':'No mechanical unit audit for this legacy contract'}
 raw=base64.b64decode(row['raw_response_base64'],validate=True)
 content=rd.unwrap(raw);contract_v3.derive(c,content)
 return audit(c,rd.strict_json(content.decode('utf-8')))
