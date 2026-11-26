"""Conservative review of the CDMRP program-announcement PDF format, not IDs."""
import io,re,datetime as dt
from .common import PipelineError,parse_date,sha256_bytes,write_json,atomic_bytes

def parse_document(raw,record,today=None):
    from pypdf import PdfReader
    today=today or dt.datetime.now(dt.timezone.utc).date()
    reader=PdfReader(io.BytesIO(raw))
    if reader.is_encrypted or not 5<=len(reader.pages)<=150:raise PipelineError('Unsupported encrypted or unbounded CDMRP PDF')
    pages=[p.extract_text() or '' for p in reader.pages];text=' '.join(' '.join(pages).split())
    number=record.get('opportunity_number') or record.get('number')
    if not number or not re.search(r'Funding Opportunity Number:\s*'+re.escape(number)+r'\b',text):raise PipelineError('CDMRP document opportunity number does not match listing')
    if not all(s in text for s in ('General Application Instructions','Eligibility Information','Funding Details','Application Contents','Submission Requirements','Application Review Information')):raise PipelineError('Incomplete or unsupported CDMRP document structure')
    stages={};date=r'([A-Za-z]+\s+\d{1,2},\s+\d{4})'
    for label,heading in [('Pre-application',r'Pre-Application \(Preproposal\) Submission Deadline'),('Full application',r'(?<!Pre-)Application Submission Deadline'),('Verification',r'End of Application Verification Period')]:
        matches=re.findall(heading+r':\s*(\d{1,2}:\d{2})\s*([ap])\.m\.\s*(?:Eastern Time \(ET\)|ET),\s*'+date,text,re.I)
        values={(clock,period.lower(),parse_date(day)) for clock,period,day in matches}
        if len(values)!=1 or next(iter(values))[2] is None:raise PipelineError('CDMRP stage date/clock missing or ambiguous: '+label)
        clock,period,day=next(iter(values));hour,minute=map(int,clock.split(':'))
        if not 1<=hour<=12 or not 0<=minute<60:raise PipelineError('Invalid CDMRP clock')
        stages[label]={'date':day.isoformat(),'time':'%02d:%02d'%(hour%12+(12 if period=='p' else 0),minute),'timezone':'America/New_York'}
    if not stages['Pre-application']['date']<=stages['Full application']['date']<=stages['Verification']['date']:raise PipelineError('CDMRP stages out of order')
    listed=parse_date(record.get('close_date'))
    if listed is None or stages['Full application']['date']!=listed.isoformat():raise PipelineError('CDMRP full application deadline differs from listing')
    cap=re.search(r"Cost Cap: The application['’]s total costs budgeted for the entire period of performance should not exceed \$([\d,.]+)([MK]?)\.",text)
    years=re.search(r'Period of Performance: The maximum period of performance is (\d+) years\.',text)
    if not cap or not years:raise PipelineError('CDMRP whole-project total-cost units unsupported')
    amount=round(float(cap[1].replace(',',''))*{'':1,'K':1000,'M':1000000}[cap[2]])
    eligibility=re.search(r'2\.1\. Eligible Applicants (.*?) 2\.2\. Cost Sharing',text)
    recipient=re.search(r'Awards are made to eligible organizations, not to individuals\.',text)
    if not eligibility or not recipient:raise PipelineError('CDMRP organization/PI eligibility scope unsupported')
    version=re.search(r'General Application Instructions, version ([A-Za-z0-9_]+)',text)
    if not version:raise PipelineError('CDMRP required general instructions version missing')
    expired=stages['Pre-application']['date']<=today.isoformat()
    return {'schema':'SOCIAL_CDMRP_DOCUMENT_V1','complete_program_document':True,'pages':len(pages),'content_sha256':sha256_bytes(text.encode()),'document_version':sha256_bytes(raw),'opportunity_number':number,'stages':stages,
      'budget':{'usd':amount,'unit':'total_project_cost_including_indirect','max_years':int(years[1]),'quote':cap[0]},
      'eligibility':{'organization_and_PI_quote':eligibility[1],'recipient_quote':recipient[0],'specific_viewer_eligible':False},
      'required_general_instructions_version':version[1],'required_general_instructions_reviewed':False,
      'selection_rejected':expired,'rejection_kind':'mandatory_preapplication_expired' if expired else None,
      'checked':False,'editorial_approved':False,
      'reason':'Mandatory pre-application deadline already passed; final application date does not reopen entry' if expired else 'Required general application instructions not reviewed; complete eligibility cannot be confirmed'}

def review_cdmrp(record,directory,fetch=None,today=None):
    from pypdf.errors import PdfReadError
    from .grant_attachments import fetch_pdf
    descriptors=[d for d in record.get('announcement_attachments',[]) if d.get('mime_type')=='application/pdf']
    if len(descriptors)!=1:return {'checked':False,'reason':'Full announcement PDF descriptors missing or ambiguous'}
    try:
        snapshot=(record.get('_field_sources') or {}).get('announcement_attachments')
        if not snapshot:raise PipelineError('CDMRP attachment lacks official listing snapshot provenance')
        raw,meta=(fetch or fetch_pdf)(descriptors[0],snapshot,directory)
        document=parse_document(raw,record,today);report={**document,'source':{**meta,'content_sha256':document['content_sha256'],'document_version':document['document_version'],'kind':'cdmrp_pdf_announcement'},'full_conditions_confirmed':False}
        atomic_bytes(directory/('cdmrp_'+str(record['opportunity_id'])+'.txt'),'\n'.join(p.extract_text() or '' for p in __import__('pypdf').PdfReader(io.BytesIO(raw)).pages).encode())
    except (OSError,ValueError,PipelineError,PdfReadError) as error:report={'checked':False,'reason':'CDMRP official PDF review unavailable: '+str(error)[:300]}
    write_json(directory/('cdmrp_review_'+str(record['opportunity_id'])+'.json'),report)
    return report
