"""Lossless model view over a hash-bound source excerpt ledger; no consumer I/O."""
import copy
import hashlib
import json
from .source_excerpt_projection import encoded

VERSION='SOCIAL_EXCERPT_MODEL_VIEW_V2'
LEGACY_VERSION='SOCIAL_EXCERPT_MODEL_VIEW_V1'
EXCERPT_COLUMNS=['id','page','section_ref','quote']
LEGACY_COLUMNS=['id','page','section','role','quote']
OMITTED=['per-quote full ID/hash/absolute and page-relative offsets','literal_modals (all literal text remains in quotes)',
         'extractor details/raw size/normalization details','record and receipt hashes','duplicate full-input and packet copies']

def sha(value):return hashlib.sha256(encoded(value)).hexdigest()
def prompt_bytes(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')

def expanded_rows(view):
    # Lossless section/role table expansion; legacy view remains verifiable.
    if view.get('schema')==LEGACY_VERSION and view.get('excerpt_columns')==LEGACY_COLUMNS:
        return view['excerpts']
    if view.get('schema')!=VERSION or view.get('excerpt_columns')!=EXCERPT_COLUMNS:
        raise ValueError('Unknown excerpt view/column version')
    sections=view['selected_sections'];roles=view['section_roles'];role_by_index={}
    if len(sections)!=len(set(sections)) or set(roles)!={'topic','required_condition'}:
        raise ValueError('Ambiguous shared section/role table')
    for role,indices in roles.items():
        for index in indices:
            if type(index) is not int or not 0<=index<len(sections) or index in role_by_index:
                raise ValueError('Invalid/repeated shared section index')
            role_by_index[index]=role
    if set(role_by_index)!=set(range(len(sections))):raise ValueError('Incomplete section role coverage')
    result=[]
    for row in view['excerpts']:
        if len(row)!=4:raise ValueError('Excerpt shape changed')
        key,page,index,quote=row
        if type(index) is not int or index not in role_by_index:raise ValueError('Unknown section reference')
        result.append([key,page,sections[index],role_by_index[index],quote])
    return result


def compact(packet):
    """Verify every full quote hash, then bind a lossless view to the whole ledger."""
    if packet.get('schema')!='SOCIAL_SOURCE_EXCERPTS_V1':raise ValueError('Unknown ledger schema')
    ledger=copy.deepcopy(packet);ledger_hash=sha(ledger);mapping={};rows=[]
    for chunk in sorted(ledger['chunks'],key=lambda c:(c['start'],c['end'],c['id'])):
        quote=chunk['quote'];raw=quote.encode('utf-8')
        if hashlib.sha256(raw).hexdigest()!=chunk['quote_sha256']:raise ValueError('Ledger quote hash mismatch')
        if chunk['end']-chunk['start']!=len(quote) or chunk['page_end']-chunk['page_start']!=len(quote):raise ValueError('Ledger span/quote mismatch')
        short=chunk['id'][:9]
        if len(short)!=9 or short in mapping:raise ValueError('Short excerpt ID collision/invalid ID')
        mapping[short]={'ledger_excerpt_id':chunk['id'],'quote_sha256':chunk['quote_sha256'],
                        'page':chunk['page'],'start':chunk['start'],'end':chunk['end'],
                        'page_start':chunk['page_start'],'page_end':chunk['page_end']}
        rows.append([short,chunk['page'],chunk['section'],chunk['role'],quote])
    reverse={v['ledger_excerpt_id']:k for k,v in mapping.items()}
    refs=[]
    for ref in ledger['unresolved_references']:
        if ref['evidence_id'] not in reverse or ref['status']!='unresolved_no_auto_resolution':raise ValueError('Invalid/unresolved reference binding')
        refs.append([reverse[ref['evidence_id']],ref['quote'],ref['status']])
    section_roles={'topic':[],'required_condition':[]}
    for _,_,section,role,_ in rows:
        index=ledger['selected_sections'].index(section)
        if index not in section_roles[role]:section_roles[role].append(index)
    section_roles={k:sorted(v) for k,v in section_roles.items()}
    compact_rows=[[key,page,ledger['selected_sections'].index(section),quote] for key,page,section,role,quote in rows]
    d=ledger['document']
    view={'schema':VERSION,'ledger_sha256':ledger_hash,
          'source':{'id':'D1','title':ledger['intent']['source_title'],'url':d['url'],
                    'original_fetched_at':d['original_fetched_at'],'scope':'historical_organizational_source_not_current_availability'},
          'intent':copy.deepcopy(ledger['intent']),'selected_sections':copy.deepcopy(ledger['selected_sections']),
          'omitted_sections':copy.deepcopy(ledger['omitted_sections']),'coverage':ledger['coverage'],
          'coverage_scope':copy.deepcopy(ledger['coverage_scope']),
          'section_roles':section_roles,'excerpt_columns':EXCERPT_COLUMNS.copy(),'excerpts':compact_rows,
          'unresolved_reference_columns':['excerpt_id','literal_reference','status'],'unresolved_references':refs,
          'research_unknowns':copy.deepcopy(ledger['research_unknowns']),
          'claims_created':False,'source_currentness_confirmed':False,'owner_approval':False}
    binding={'schema':'SOCIAL_EXCERPT_VIEW_BINDING_V1','ledger_sha256':ledger_hash,'model_view_sha256':sha(view),
             'mapping':mapping,'omitted_from_model_view_but_retained_in_ledger':OMITTED.copy()}
    verify_view(view,binding,ledger)
    return {'view':view,'binding':binding}

def verify_view(view,binding,ledger):
    if sha(ledger)!=binding['ledger_sha256'] or view['ledger_sha256']!=binding['ledger_sha256'] or sha(view)!=binding['model_view_sha256']:
        raise ValueError('Ledger/view digest mismatch')
    rows=expanded_rows(view)
    d=ledger['document']
    expected_source={'id':'D1','title':ledger['intent']['source_title'],'url':d['url'],
                     'original_fetched_at':d['original_fetched_at'],'scope':'historical_organizational_source_not_current_availability'}
    if view['source']!=expected_source or view['intent']!=ledger['intent']:
        raise ValueError('Document/intent provenance changed')
    if view.get('claims_created') is not False or view.get('source_currentness_confirmed') is not False or view.get('owner_approval') is not False:
        raise ValueError('Projection cannot grant acceptance')
    chunks={c['id']:c for c in ledger['chunks']};seen=set()
    for row in rows:
        if len(row)!=5:raise ValueError('Excerpt shape changed')
        short,page,section,role,quote=row
        if short in seen:raise ValueError('Duplicate model excerpt')
        seen.add(short);m=binding['mapping'][short];c=chunks[m['ledger_excerpt_id']]
        if short!=c['id'][:9] or hashlib.sha256(quote.encode('utf-8')).hexdigest()!=c['quote_sha256']:
            raise ValueError('Quote/short-ID binding changed')
        if [page,section,role,quote]!=[c['page'],c['section'],c['role'],c['quote']]:raise ValueError('Lossy/reworded excerpt')
        for key in ('page','start','end','page_start','page_end','quote_sha256'):
            if m[key]!=c[key]:raise ValueError('Span/hash mapping changed')
    if {binding['mapping'][k]['ledger_excerpt_id'] for k in seen}!=set(chunks) or seen!=set(binding['mapping']):raise ValueError('Missing/extra ledger excerpt')
    reverse={v['ledger_excerpt_id']:k for k,v in binding['mapping'].items()}
    expected_refs=[[reverse[r['evidence_id']],r['quote'],r['status']] for r in ledger['unresolved_references']]
    if view['unresolved_references']!=expected_refs or view['unresolved_reference_columns']!=['excerpt_id','literal_reference','status']:
        raise ValueError('Unresolved reference lost or auto-resolved')
    if view.get('coverage_scope')!=ledger['coverage_scope']:raise ValueError('Profile/document coverage or usage boundary changed')
    if view['research_unknowns']!=ledger['research_unknowns'] or view['coverage']!=ledger['coverage'] or view['selected_sections']!=ledger['selected_sections'] or view['omitted_sections']!=ledger['omitted_sections']:
        raise ValueError('Unknown/coverage information lost')
    return {'all_quotes_reconstruct_exactly':True,'excerpt_count':len(seen),'quote_utf8_bytes':sum(len(row[4].encode('utf-8')) for row in rows)}

def build_request(packet,request_shell,context=None,*,max_request_bytes=16384):
    """Measure the exact complete request body with caller-supplied shell.

    Uses stable_json encoding matching local_editorial.request_json; prompt uses
    compact JSON. Never dispatches. Caller owns all system/schema/options fields.
    """
    if type(max_request_bytes) is not int or not 0<max_request_bytes<=16384:raise ValueError('Existing full16KiB request bound required')
    if not isinstance(request_shell,dict) or not {'model','system','format','options','stream','think','keep_alive','prompt'}<=set(request_shell):raise ValueError('Complete caller request shell required')
    context=copy.deepcopy(context or {})
    if not isinstance(context,dict) or 'source_evidence' in context:raise ValueError('Context must not replace source evidence')
    derived=compact(packet)
    before_input={**context,'source_evidence':copy.deepcopy(packet)}
    after_input={**context,'source_evidence':derived['view']}
    before=copy.deepcopy(request_shell);after=copy.deepcopy(request_shell)
    # Only the source-evidence representation changes; shell/context are intact.
    before['prompt']=prompt_bytes(before_input).decode('utf-8');after['prompt']=prompt_bytes(after_input).decode('utf-8')
    sizes={'before_evidence_pretty_bytes':len(encoded(packet)),'after_evidence_pretty_bytes':len(encoded(derived['view'])),
           'before_prompt_bytes':len(before['prompt'].encode()),'after_prompt_bytes':len(after['prompt'].encode()),
           'before_complete_request_bytes':len(encoded(before)),'after_complete_request_bytes':len(encoded(after))}
    if sizes['after_complete_request_bytes']>max_request_bytes:
        return {'state':'needs_narrower_topic','request':None,'sizes':sizes,'no_truncation':True}
    return {'state':'budget_validated_not_dispatched','request':after,'request_sha256':sha(after),'sizes':sizes,
            **derived,'consumer_integration':'deferred; budget validity is not semantic/consumer readiness'}
