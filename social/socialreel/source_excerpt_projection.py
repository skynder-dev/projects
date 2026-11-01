"""Pure bounded OJP source quotation projection. No claims, summaries or inference."""
import copy
import datetime as dt
import hashlib
import importlib.metadata
import json
import re
from urllib.parse import urlsplit
from .source_documents import normalized_text

PROFILE = 'OJP_ORGANIZATIONAL_HEADINGS_V1'
NORMALIZATION = 'SOURCE_DOCUMENTS_PDF_V1'
VERSION = 'SOCIAL_SOURCE_EXCERPTS_V1'
HEADINGS = {
 'purpose': r'Purpose of the Funding[ \t]*$',
 'funding': r'Funding Details[ \t]*$',
 'eligible': r'Eligible Applicants[ \t]*$',
 'match': r'Cost Sharing \(Match\) Requirement:',
 'limits': r'Limit on Number of Applications:',
 'program': r'3\. PROGRAM DESCRIPTION[ \t]*$',
 'priorities': r'Agency Funding Priorities[ \t]*$',
 'exclusions': r'Unallowable Activities:',
 'goals': r'Goals and Objectives of This Funding Opportunity[ \t]*$',
 'outcomes': r'Expected Outcomes[ \t]*$',
}
SECTIONS = {'purpose':('purpose','funding'), 'eligibility':('eligible','match'),
 'match':('match','limits'), 'application_conditions':('limits','program'),
 'priorities':('priorities','exclusions'), 'exclusions':('exclusions','goals'),
 'goals':('goals','outcomes')}
TOPICS = {'program_purpose':('purpose','goals'), 'application_conditions':('application_conditions',)}
# Mandatory whole source blocks for both supported organizational topics.
DEPENDENCIES = ('eligibility','match','application_conditions','priorities','exclusions')
UNKNOWN_PATHS = ('audience_assessment.suitability','audience_assessment.domestic_eligibility_proven',
 'selection_assessment.applicant_categories.specific_viewer_eligible',
 'selection_assessment.topic_match.trend_proven')
MODALS = re.compile(r'\b(?:must|may|only|if|will|not limited to|does not require|does not guarantee|shall not|shall)\b',re.I)
REFERENCES = re.compile(r'Application Resource Guide|DOJ Grants Financial Guide|Eligible Applicants section|Post-Award Requirements(?: and Administration)?',re.I)

def encoded(value):
    return (json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode('utf-8')

def digest(data):
    return hashlib.sha256(data).hexdigest()

def _failed(state,reason,**details):
    return {'schema':VERSION,'state':state,'reason':reason,'packet':None,**details,
            'claims_created':False,'source_currentness_confirmed':False,'owner_approval':False}

def project(raw, receipt, record, intent, *, full_input=None, input_key='source_evidence',
            max_input_bytes=16384,max_packet_bytes=16384,max_quote_bytes=9000,max_blocks=24,
            expected_normalized_sha256=None):
    """Return packet+measured full input or an explicit refusal; never write/mutate.

    full_input is the exact caller-supplied envelope before this key is inserted.
    No clipping, fallback source, automatic dependency resolution or claim creation.
    """
    if not isinstance(receipt,dict) or not isinstance(record,dict):
        return _failed('invalid_input','Original receipt and record objects required')
    if not isinstance(input_key,str) or re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,63}',input_key) is None:
        return _failed('invalid_envelope','Simple explicit evidence key required')
    try: original = digest(encoded([receipt,record,intent,full_input]))
    except (TypeError,ValueError,RecursionError):
        return _failed('invalid_input','Finite JSON input objects required')
    if not isinstance(raw,bytes) or not raw.startswith(b'%PDF-') or len(raw)>2*1024**2:
        return _failed('unsupported_source','Bounded original PDF bytes required')
    if not isinstance(intent,dict) or intent.get('profile')!=PROFILE or intent.get('audience')!='organizational_applicants' or intent.get('topic') not in TOPICS:
        return _failed('unsupported_intent','Explicit supported organizational profile/topic required; no household fallback')
    if intent.get('source_title')!=record.get('title') or not record.get('title'):
        return _failed('source_mismatch','Explicit source title differs from captured record')
    if full_input is not None and (not isinstance(full_input,dict) or input_key in full_input):
        return _failed('invalid_envelope','Exact object envelope must not already contain evidence key')
    if any(type(x) is not int or x<=0 for x in (max_input_bytes,max_packet_bytes,max_quote_bytes,max_blocks)):
        return _failed('invalid_budget','Positive integer bounds required')
    try:
        u=urlsplit(receipt['url']);stamp=dt.datetime.fromisoformat(receipt['fetched_at'])
        if u.scheme!='https' or not (u.hostname=='ojp.gov' or (u.hostname or '').endswith('.ojp.gov')) or u.username or u.password or stamp.tzinfo is None:
            return _failed('source_mismatch','Original official OJP URL and timezone-aware capture date required')
        if digest(raw)!=receipt['sha256'] or ('bytes' in receipt and len(raw)!=receipt['bytes']):
            return _failed('source_mismatch','Original PDF hash/size does not match receipt')
        text=normalized_text(raw,{'normalization':NORMALIZATION,'final_url':receipt['url']})
    except Exception as error:
        return _failed('unsupported_source','Saved PDF normalization failed: '+type(error).__name__)
    normalized_title=' '.join(record['title'].split())
    title_lines=[line for line in text.splitlines() if ' '.join(line.split())==normalized_title]
    if len(title_lines)<2 or not record.get('number') or record['number'] not in text:
        return _failed('source_mismatch','PDF repeated title/opportunity number differs from captured record')
    text_hash=digest(text.encode('utf-8'))
    if expected_normalized_sha256 is not None and text_hash!=expected_normalized_sha256:
        return _failed('normalization_mismatch','Normalized hash changed; old spans not reusable')
    pages=list(re.finditer(r'^\[PAGE ([1-9][0-9]*)\]\n',text,re.M))
    if not pages or [int(m[1]) for m in pages]!=list(range(1,len(pages)+1)) or len(text)>2_000_000:
        return _failed('unsupported_profile','Unsupported normalized page index')
    anchors={}
    for key,pattern in HEADINGS.items():
        found=list(re.finditer(r'^'+pattern,text,re.M))
        if len(found)!=1:
            return _failed('unsupported_profile','Missing/ambiguous standalone heading: '+key)
        anchors[key]=found[0].start()
    spans={}
    for section,(start,end) in SECTIONS.items():
        a,b=anchors[start],anchors[end]
        if a>=b:return _failed('unsupported_profile','Heading order invalid: '+section)
        spans[section]=(a,b)
    selected=tuple(dict.fromkeys(TOPICS[intent['topic']]+DEPENDENCIES))
    chunks=[];refs=[];quote_bytes=0
    for section in selected:
        a,b=spans[section]
        for i,page in enumerate(pages):
            start=max(a,page.end());end=min(b,pages[i+1].start() if i+1<len(pages) else len(text))
            if start>=end:continue
            quote=text[start:end];quote_bytes+=len(quote.encode('utf-8'))
            qhash=digest(quote.encode('utf-8'));key='E'+digest(encoded([text_hash,section,start,end,qhash]))[:24]
            chunk={'id':key,'section':section,'role':'topic' if section in TOPICS[intent['topic']] else 'required_condition',
                   'page':int(page[1]),'start':start,'end':end,'page_start':start-page.end(),'page_end':end-page.end(),
                   'quote':quote,'quote_sha256':qhash,
                   'literal_modals':sorted({m[0] for m in MODALS.finditer(quote)})}
            chunks.append(chunk)
            for match in REFERENCES.finditer(quote):
                refs.append({'evidence_id':key,'start':start+match.start(),'end':start+match.end(),
                             'quote':match[0],'status':'unresolved_no_auto_resolution'})
    unknowns=[]
    for path in UNKNOWN_PATHS:
        value=record
        try:
            for part in path.split('.'):value=value[part]
        except (KeyError,TypeError):continue
        unknowns.append({'path':path,'value':copy.deepcopy(value),'interpretation':'Original uncertainty flag; false is not an eligibility denial'})
    for path in ('unknowns','unknown'):
        if path in record:
            unknowns.append({'path':path,'value':copy.deepcopy(record[path]),'interpretation':'Existing source record uncertainty; not resolved by projection'})
    # Detect only literal outside-profile markers; not a semantic section review.
    outside_rules=(('funding_details',r'(?m)^Funding Details[ \t]*$'),('dates_and_times',r'(?m)^Key Dates and Times[ \t]*$'),('outcomes_reporting',r'(?m)^Expected Outcomes[ \t]*$|Performance Reports'),('application_components',r'APPLICATION CONTENTS AND FORMAT|Application Contents List'),
      ('responsiveness',r'responsiveness review'),('cost_budget',r'Budget and Associated Documentation|\bcosts?\b'),
      ('evaluation',r'Project Evaluations'),('planning_implementation',r'Program Implementation Schedule|planning phase|implementation phase|Project Design and Implementation'),
      ('application_review',r'APPLICATION REVIEW INFORMATION'),('post_award',r'POST.AWARD REQUIREMENTS.*ADMINISTRATION'))
    outside=[]
    for label,pattern in outside_rules:
        found_pages=set()
        for match in re.finditer(pattern,text,re.I):
            if any(c['start']<=match.start() and match.end()<=c['end'] for c in chunks):continue
            page=next((i+1 for i,m in reversed(list(enumerate(pages))) if m.end()<=match.start()),None)
            if page is not None and page>2:found_pages.add(page)  # exclude cover/TOC label repetition
        if found_pages:outside.append([label,sorted(found_pages)])
    coverage_scope={'omitted_sections_scope':'finite_heading_profile_only; empty does not mean whole document',
      'unselected_document_pages':[i+1 for i in range(len(pages)) if i+1 not in {c['page'] for c in chunks}],
      'detected_unselected_content':outside,'detection_limit':'Non-exhaustive lexical markers outside selected spans; not semantic review',
      'usage_boundary':'Program-purpose concepts only; not complete application, budget or timeline guidance.'}
    packet={'schema':VERSION,'profile':PROFILE,'intent':copy.deepcopy(intent),
            'document':{'url':receipt['url'],'original_fetched_at':receipt['fetched_at'],'raw_sha256':digest(raw),
                        'raw_bytes':len(raw),'normalized_sha256':text_hash,'normalized_utf8_bytes':len(text.encode('utf-8')),
                        'extractor':{'module':'socialreel.source_documents.normalized_text','normalization':NORMALIZATION,
                                     'pypdf_version':importlib.metadata.version('pypdf'),'projection_version':VERSION},
                        'offset_basis':'0-based Unicode codepoints in exact normalized document with page markers; end-exclusive'},
            'record_sha256':digest(encoded(record)),'receipt_sha256':digest(encoded(receipt)),
            'selected_sections':list(selected),'omitted_sections':[s for s in SECTIONS if s not in selected],
            'chunks':chunks,'unresolved_references':refs,'research_unknowns':unknowns,
            'coverage_scope':coverage_scope,
            'coverage':'Selected whole heading blocks plus mandatory dependencies only; all cross-references remain unresolved; not full legal/eligibility review',
            'modality_policy':'Literal lexical markers only; no semantic summaries or inferred entitlement',
            'claims_created':False,'source_currentness_confirmed':False,'owner_approval':False}
    envelope=copy.deepcopy(full_input) if full_input is not None else {}
    envelope[input_key]=packet
    sizes={'blocks':len(chunks),'quote_bytes':quote_bytes,'packet_bytes':len(encoded(packet)),'full_input_bytes':len(encoded(envelope))}
    if len(chunks)>max_blocks or quote_bytes>max_quote_bytes or sizes['packet_bytes']>max_packet_bytes or sizes['full_input_bytes']>max_input_bytes:
        return _failed('needs_narrower_topic','Complete mandatory material exceeds budget; no snippets silently clipped',sizes=sizes)
    assert digest(encoded([receipt,record,intent,full_input]))==original
    return {'schema':VERSION,'state':'projected','packet':packet,'full_input':envelope,'sizes':sizes,
            'packet_sha256':digest(encoded(packet)),'full_input_sha256':digest(encoded(envelope)),
            'consumer_integration':'deferred; not a concept request or approval'}
