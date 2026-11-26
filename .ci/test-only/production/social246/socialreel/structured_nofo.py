"""Page-bound evidence rules for structured NOFO families; never opportunity IDs."""
import io,re,datetime as dt
from pathlib import Path
from .common import PipelineError,sha256_bytes,parse_date,read_json,write_json,atomic_bytes,utc_now

class Document:
    def __init__(self,raw):
        from pypdf import PdfReader
        if len(raw)>2*1024*1024 or not raw.startswith(b'%PDF-'):raise PipelineError('Unsupported bounded PDF')
        reader=PdfReader(io.BytesIO(raw))
        if reader.is_encrypted or not 5<=len(reader.pages)<=100:raise PipelineError('Unsupported encrypted PDF or page count')
        self.pages=[' '.join((p.extract_text() or '').split()) for p in reader.pages]
        if sum(map(len,self.pages))>2_000_000:raise PipelineError('PDF extracted text exceeds bound')
        self.sha=sha256_bytes(raw)
    def rule(self,key,pattern,required=True):
        observations=[]
        for page,text in enumerate(self.pages,1):
            for match in re.finditer(pattern,text,re.I):
                observations.append({'page':page,'quote':match[0],'start':match.start(),'end':match.end(),'groups':list(match.groups()),'pdf_sha256':self.sha,'basis':'Offsets in whitespace-normalized extracted page; raw PDF retained'})
        if not observations:
            if not required:return None
            raise PipelineError('Unsupported or missing primary condition: '+key)
        values={tuple(e['groups']) for e in observations}
        if len(values)!=1:raise PipelineError('Ambiguous primary condition: '+key)
        return {'values':list(next(iter(values))),'evidence':observations}

def parse(raw,record):
    doc=Document(raw);number=record.get('number') or ''
    doc.rule('document identity',r'Funding Opportunity Number\s*:?\s*('+re.escape(number)+r')\b')
    whole=' '.join(doc.pages)
    if re.search(r'\b(?:pre[- ]application|preliminary proposal|letter of intent)\b',whole,re.I):raise PipelineError('Additional application stage mentioned; its requirements/deadline are unsupported')
    for heading in ('Eligible Applicants','Cost Share Requirements','Application Limits','Submission Requirements and Deadlines','Funding Details','Post-Award Requirements'):
        if heading not in whole:raise PipelineError('Unsupported NOFO structure: '+heading)
    rules={
      'applicant':r'To be eligible for an award under the [A-Za-z0-9 -]+ program, your Native Community must be (Federally recognized and offer library and/or archival services to the community)\.',
      'application_limit':r'((?:Your Tribe|You) may submit only one application under this announcement)\.',
      'lead_applicant':r'(the Tribe must meet all eligibility requirements, serve as the lead applicant, and administer the award on behalf of the other\(s\))\.',
      'no_renewal':r'(We will not consider applications proposing to renew or add funding to active IMLS awards)\.',
      'budget':r'The total (?:federal )?funding request on your IMLS Budget Form must be between \$([\d,]+)\s*-\s*\$([\d,]+)\.',
      'deadline':r'Applications are due by (\d{1,2}:\d{2}) p\.m\. U\.S\. Eastern Time on ([A-Za-z]+ \d{1,2}, \d{4})\.',
      'instrument':r'Type of assistance instrument\s+(Grant)\b',
      'registrations':r'(Your Tribe must have an active SAM\.gov account and a Unique Entity Identifier \(UEI\) before you apply)\.',
      'funding_conditional':r'(The funding in the above Award Overview is subject to the availability of funds and the Institute of Museum and Library Services[’\x27] \(IMLS[’\x27]s\) discretion)\.'}
    # Publisher typography varies; the source quote, not reconstructed wording, is retained.
    rules['funding_conditional']=r'(The funding in the above Award Overview is subject to the availability of funds and the Institute of Museum and Library Services.*?discretion)\.'
    conditions={k:doc.rule(k,p) for k,p in rules.items()}
    purpose=doc.rule('purpose',r'((?:The [A-Za-z -]+ Grants program \([A-Z]{2,8}\) assists eligible Native Communities in sustaining and improving library services with their communities|The Native American Basic Grants \(NAB\) program assists eligible Native Communities in establishing, sustaining, and improving library services and operations with their communities))\.',required=False)
    if purpose:conditions['purpose']=purpose
    from .nofo_terms import cost_sharing,project_period
    share,share_conditions=cost_sharing(doc);period,period_conditions=project_period(doc);conditions.update(share_conditions);conditions.update(period_conditions)
    lo,hi=[int(v.replace(',','')) for v in conditions['budget']['values']]
    if (lo,hi)!=(record.get('award_floor'),record.get('award_ceiling')):raise PipelineError('Primary total request range differs from listing')
    clock,date=conditions['deadline']['values'];date=parse_date(date)
    hour,minute=map(int,clock.split(':'))
    if not 1<=hour<=12 or not 0<=minute<60:raise PipelineError('Invalid primary deadline clock')
    if not 0<lo<=hi:raise PipelineError('Invalid primary total request range')
    if record.get('funding_instruments')!=['Grant']:raise PipelineError('Primary grant instrument differs from listing or is ambiguous')
    if date is None or date!=parse_date(record.get('close_date')):raise PipelineError('Primary application date differs from listing')
    if share['mode']!='unknown' and record.get('cost_sharing') is not share['required']:raise PipelineError('Primary cost-sharing requirement differs from listing or listing is unknown')
    return {'schema':'SOCIAL_STRUCTURED_NOFO_V2','profile':'imls_native_library_organization_v2','pdf_sha256':doc.sha,'pages':len(doc.pages),'opportunity_number':number,'conditions':conditions,
      'budget':{'min_usd':lo,'max_usd':hi,'unit':'total_project_federal_request','period':period.get('spoken_duration')},
      'cost_sharing_policy':share,'project_period':period,'generation_ready':share['confirmed'] and period['confirmed'],
      'deadline':{'date':date.isoformat(),'time':clock,'timezone':'America/New_York','clock_period':'pm'},
      'applicant_scope':'Federally recognized Native Community providing library/archive services; organization-level conditions, not an individual group identity',
      'unknowns':['Specific applicant organization identity, federal recognition and services have not been verified','Allowable costs and compliance with referenced federal policies require applicant-specific review','Award selection and availability of funds are not guaranteed']+share.get('unknowns',[])+([period['reason']] if not period['confirmed'] else []),
      'editorial_approved':False,'publication_authorized':False}

def review(record,directory,fetch=None):
    try:from pypdf.errors import PdfReadError
    except ImportError:
        report={'checked':False,'reason':'Required local PDF parser unavailable; no download or source request attempted'}
        write_json(Path(directory)/('announcement_check_'+record['opportunity_id']+'.json'),report)
        return report
    from .grant_attachments import fetch_pdf
    try:
        descriptors=record.get('announcement_attachments') or []
        if len(descriptors)!=1:raise PipelineError('Full-announcement attachment missing or ambiguous')
        snapshot=(record.get('_field_sources') or {}).get('announcement_attachments')
        if not snapshot:raise PipelineError('Full-announcement listing provenance missing')
        raw,meta=(fetch or fetch_pdf)(descriptors[0],snapshot,directory)
        if sha256_bytes(raw)!=meta['sha256']:raise PipelineError('Full-announcement hash differs')
        document=parse(raw,record);meta={**meta,'kind':'structured_pdf_nofo','document_version':meta['sha256'],'canonical_schema':document['schema']}
        record['announcement_source']=meta
        if document['generation_ready']:record['primary_conditions']=document
        else:record['unconfirmed_primary_conditions']=document
        report={'checked':document['generation_ready'],'source':meta,'document_complete':True,'conditions':document,'editorial_approved':False,'reason':share_reason(document),'review_level':'Primary claimed conditions with page quotes; applicant-specific qualification and external policy compliance remain unknown'}
        write_json(Path(directory)/('conditions_'+record['opportunity_id']+'.json'),document)
    except (PipelineError,OSError,ValueError,KeyError,TypeError,PdfReadError) as error:report={'checked':False,'reason':'Structured official NOFO unconfirmed: '+str(error)[:350]}
    write_json(Path(directory)/('announcement_check_'+record['opportunity_id']+'.json'),report)
    return report

def document_check(root,current,detail,evidence,fetch=None):
    try:from pypdf.errors import PdfReadError
    except ImportError:return {'kind':'structured_pdf_nofo','current_content_confirmed':False,'changed':False,'differences':[],'error':'Required local PDF parser unavailable; no automatic download or current-source claim'}
    from .grant_attachments import discover_pdf,fetch_pdf
    root=Path(root).resolve();evidence=Path(evidence);result={'kind':'structured_pdf_nofo','current_content_confirmed':False,'changed':False,'differences':[]}
    try:
        saved=read_json(root/'topic.json')['selected'];previous=saved['announcement_source'];old=(root/previous['file']).resolve()
        if not old.is_relative_to(root) or sha256_bytes(old.read_bytes())!=previous['sha256']:raise PipelineError('Saved primary PDF missing or changed')
        olddoc=parse(old.read_bytes(),saved)
        previous_conditions=saved['primary_conditions']
        if previous_conditions.get('schema')=='SOCIAL_STRUCTURED_NOFO_V1':
            if any(olddoc['conditions'].get(k)!=v for k,v in previous_conditions['conditions'].items()):raise PipelineError('Saved primary conditions need rematerialization under current parser')
        elif {**olddoc,'conditions':{k:v for k,v in olddoc['conditions'].items() if k!='purpose' or k in previous_conditions['conditions']}}!=previous_conditions:raise PipelineError('Saved primary conditions need rematerialization under current parser')
        descriptors=discover_pdf(detail,current['opportunity_id'])
        if descriptors!=[previous['descriptor']]:
            return {**result,'changed':True,'differences':[{'kind':'announcement_attachment_membership','before':[previous['descriptor']],'after':descriptors}],'reason':'Primary attachment association or version metadata changed'}
        snapshot=current.get('_detail_snapshot')
        if not snapshot:raise PipelineError('Fresh official snapshot provenance missing')
        evidence.mkdir(parents=True,exist_ok=True);api=evidence.parent/('opportunity_'+current['opportunity_id']+'.json');atomic_bytes(evidence/api.name,api.read_bytes())
        raw,meta=(fetch or fetch_pdf)(descriptors[0],snapshot,evidence)
        stamp=dt.datetime.fromisoformat(meta['fetched_at'])
        if stamp.tzinfo is None or not -300<=(utc_now()-stamp).total_seconds()<=300 or sha256_bytes(raw)!=meta['sha256']:raise PipelineError('Current PDF hash or observation time unconfirmed')
        result['current_document']=meta
        if meta['sha256']!=previous['sha256']:
            result['differences'].append({'kind':'document_bytes','before_sha256':previous['sha256'],'after_sha256':meta['sha256']});result['changed']=True
        document=parse(raw,current)
        result['typed_terms']={'cost_sharing_policy':document['cost_sharing_policy'],'project_period':document['project_period']}
        for field in ('cost_sharing_policy','project_period'):
            if olddoc[field]!=document[field]:result['differences'].append({'kind':'typed_'+field,'before':olddoc[field],'after':document[field]})

        if document!=olddoc:result['differences'].append({'kind':'primary_conditions','before':olddoc,'after':document})
        result['changed']=bool(result['differences']);result['current_content_confirmed']=not result['changed'] and document['generation_ready'];result['deadline_agreement']={'pass':True,'deadline':document['deadline']};result['reason']=None if not result['changed'] else 'Changed primary document requires a rebuilt draft and review'
    except (PipelineError,OSError,ValueError,KeyError,TypeError,PdfReadError) as error:result['error']=type(error).__name__+': '+str(error)[:350]
    return result


def share_reason(document):
    return document["cost_sharing_policy"].get("reason") or document["project_period"].get("reason")
