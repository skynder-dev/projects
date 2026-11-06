"""Official publisher status cross-check; no assumption that POSTED means open."""
import ssl
import urllib.request
from urllib.parse import urlsplit
from html.parser import HTMLParser
from .common import PipelineError,atomic_bytes,write_json,sha256_bytes,utc_now

class Alerts(HTMLParser):
    def __init__(self):super().__init__();self.stack=[];self.alerts=[];self.active=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs);inside=any(self.active) or 'usa-alert' in attrs.get('class','')
        if tag not in ('area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'):
            self.stack.append(tag);self.active.append(inside)
    def handle_endtag(self,tag):
        if tag in self.stack:
            index=len(self.stack)-1-self.stack[::-1].index(tag)
            del self.stack[index:];del self.active[index:]
    def handle_data(self,text):
        if any(self.active) and not any(t in ('script','style') for t in self.stack):self.alerts.append(text)

def publisher_status(raw):
    parser=Alerts();parser.feed(raw.decode('utf-8',errors='replace'))
    text=' '.join(' '.join(parser.alerts).split())
    import re
    closed=bool(re.search(r'not currently accepting proposals|awaiting a new solicitation|no longer accepting proposals',text,re.I))
    return {'explicitly_closed':closed,'publisher_status_quote':text[:1200] if closed else None,
            'scope':'Explicit NSF publisher alert only; absence is not proof of full conditions/current acceptance'}

def nsf_page(record,directory):
    url=urlsplit(record.get('full_announcement_url') or '')._replace(scheme='https').geturl()
    def allowed(value):
        p=urlsplit(value)
        return p.scheme=='https' and not p.username and p.port in (None,443) and (p.hostname=='nsf.gov' or (p.hostname or '').endswith('.nsf.gov'))
    if not allowed(url):raise PipelineError('NSF source URL outside supported official scope')
    class Redirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,request,fp,code,msg,headers,newurl):
            if not allowed(newurl):raise PipelineError('NSF source redirected outside official HTTPS scope')
            return super().redirect_request(request,fp,code,msg,headers,newurl)
    try:
        import truststore
        context=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except ImportError:context=ssl.create_default_context()
    opener=urllib.request.build_opener(Redirect(),urllib.request.HTTPSHandler(context=context))
    request=urllib.request.Request(url,headers={'User-Agent':'SocialReels/1.0 official-source-status'})
    with opener.open(request,timeout=15) as response:
        raw=response.read(2*1024*1024+1);final=response.url;status=response.status;content_type=response.headers.get('Content-Type','')
    if len(raw)>2*1024*1024:raise PipelineError('NSF source exceeds bounded2MiB read')
    filename='announcement_'+str(record['opportunity_id'])+'.html'
    atomic_bytes(directory/filename,raw)
    return raw,{'url':url,'final_url':final,'http_status':status,'content_type':content_type,'file':'source/'+filename,'sha256':sha256_bytes(raw),'bytes':len(raw),'fetched_at':utc_now().isoformat()}

def review_source(record,directory,fetch=None):
    if record.get("agency_code")=="IMLS" and record.get("announcement_attachments"):
        from .structured_nofo import review
        return review(record,directory,fetch=fetch)
    if str(record.get("agency_code") or "").startswith("DOD-") and any(d.get("mime_type")=="application/pdf" for d in record.get("announcement_attachments",[])):
        from .cdmrp_document import review_cdmrp
        return review_cdmrp(record,directory,fetch=fetch)
    if record.get('announcement_attachments') and str(record.get('agency_code') or '').startswith('HHS-NIH'):
        from .nih_review import review_nih
        return review_nih(record,directory,fetch=fetch)
    url=record.get('full_announcement_url') or '';host=(urlsplit(url).hostname or '').lower()
    if host=='nsf.gov' or host.endswith('.nsf.gov'):
        try:
            raw,meta=(fetch or nsf_page)(record,directory)
            from .nsf_document import parse_solicitation,deadline_agreement
            document=parse_solicitation(raw,meta.get('final_url') or meta['url'])
            import re
            number=re.fullmatch(r'(?:NSF\s*)?(\d{2}-\d{3})',str(record.get('number') or ''),re.I)
            if not number or number[1]!=document.get('document_version'):
                record['source_conditions_unconfirmed']=True
                report={'checked':False,'document_complete':document['complete'],'primary_article_captured':document['complete'],'identity_agreement':False,'explicitly_closed':document.get('explicitly_closed',False),'source':meta,'reason':'Primary solicitation version does not match the listed opportunity number; no primary conditions adopted'}
                write_json(directory/('announcement_check_'+str(record['opportunity_id'])+'.json'),report)
                return report

            agreement=deadline_agreement(document,record.get('close_date'))
            meta={**meta,'kind':'nsf_html_solicitation','content_sha256':document['content_sha256'],
                  'document_version':document['document_version'],'canonical_schema':document['schema']}
            report={'checked':document['complete'] and agreement['pass'] and not document['explicitly_closed'],
                    'source':meta,'document_complete':document['complete'],'deadline_agreement':agreement,
                    'explicitly_closed':document['explicitly_closed'],'publisher_status_quote':document['publisher_status_quote'],
                    'editorial_approved':False,'review_level':'Full document captured, deadline coherence and publisher alert; not applicant qualification or narrative quality',
                    'reason':('Publisher explicitly not accepting proposals' if document['explicitly_closed'] else
                              document['reason'] or agreement.get('reason') or (None if agreement['pass'] else 'Publisher/listing deadlines disagree'))}
            if document['complete']:
                record['announcement_source']=meta
                import re
                clock=re.search(r"due by 5 p\.m\. submitter's local time",agreement.get('header_excerpt',''),re.I)
                if agreement['pass'] and clock:
                    record['publisher_deadline']={'date':agreement['listing_date'],'time':'17:00','basis':"submitter's local time",'clock_quote':clock[0],'date_basis':agreement['basis']}
                from .nsf_conditions import proposer_conditions,project_budgets
                budgets=project_budgets(document)
                if budgets:
                    record['project_budget_scope']=budgets
                    report['project_budget_scope']=budgets
                    if record.get('award_ceiling')!=max(c['total_project_budget_usd'] for c in budgets['classes']):
                        report['checked']=False;report['reason']='Listing ceiling differs from primary project-class total budget'
                elif 'PILOT Projects' in document['text'] and 'IMPLEMENTATION Projects' in document['text']:
                    record['project_budget_unconfirmed']=True
                    report['checked']=False;report['reason']='Project-class budget units/durations unsupported; review required'
                conditions=proposer_conditions(document)
                if conditions:
                    record['publisher_eligibility']=conditions
                    report['publisher_eligibility']=conditions
                if conditions is None or budgets is None or not conditions.get('proposal_cap_quote'):
                    record['source_conditions_unconfirmed']=True
                    report['checked']=False
                    report['reason']='Primary document captured, but proposer/budget/track conditions are unsupported; only a restricted overview draft may be prepared'
                    report['unresolved_conditions']=['proposer eligibility','funding scope and project classes','track-specific submission conditions']
                from .nsf_tracks import parse as parse_tracks
                track_data=parse_tracks(document,meta)
                if track_data:
                    record['track_conditions']=track_data
                    record['source_conditions_unconfirmed']=True
                    report['track_conditions']=track_data
                    report['checked']=False
                    report['reason']='Track-specific facts extracted; remaining linked-policy/DCL conditions are not established'
                    report['unresolved_conditions']=track_data['unresolved_conditions']
                    write_json(directory/('track_conditions_'+str(record['opportunity_id'])+'.json'),track_data)
                atomic_bytes(directory/('announcement_'+str(record['opportunity_id'])+'.txt'),document['text'].encode())
                if track_data:
                    from .source_dependencies import apply as apply_dependencies
                    apply_dependencies(record,report,directory)
                    write_json(directory/('track_conditions_'+str(record['opportunity_id'])+'.json'),record['track_conditions'])
        except (OSError,ValueError,PipelineError) as error:
            report={'checked':False,'explicitly_closed':False,'reason':'NSF publisher status unavailable: '+str(error)[:250]}
        write_json(directory/('announcement_check_'+str(record['opportunity_id'])+'.json'),report)
        return report
    from .nofo import check_nofo
    return check_nofo(record,directory)

class SourceSelectionExhausted(PipelineError):
    """Explicit bounded semantic/source outcome; not synchronization failure."""
    pass


def select_source_candidate(good,directory,review=None,audience="general_us",max_review_candidates=3):
    from .audience_selection import assess
    audience_deferred=[];format_deferred=[]
    rejected=[];deferred=[];fallback=None;supported=[]
    if type(max_review_candidates) is not int or not 1<=max_review_candidates<=10:raise PipelineError('Source review budget must be1..10')
    unreviewed=list(good[max_review_candidates:])
    deferred.extend({'opportunity_id':r.get('opportunity_id'),'outcome':'review_budget_remaining','reason':'Not reviewed in this bounded pass; preserve for continuation'} for score,r,snap in unreviewed)
    def selected(candidate,report):
        score,record,snapshot=candidate
        report={**report,'selection_deferrals':list(deferred),'audience_deferrals':list(audience_deferred),'format_deferrals':list(format_deferred)}
        return score,record,snapshot,report,list(rejected)
    for candidate in good[:max_review_candidates]:
        score,record,snapshot=candidate
        try:
            report=(review or review_source)(record,directory)
            if not isinstance(report,dict):raise ValueError('Source review returned no structured report')
        except (OSError,ValueError,PipelineError) as error:
            report={'checked':False,'explicitly_closed':False,'reason':'Official source review unavailable: '+str(error)[:300],
                    'error_type':type(error).__name__}
        if report.get('selection_rejected') is True:
            rejected.append({'opportunity_id':record['opportunity_id'],'reason':report.get('reason'),'kind':report.get('rejection_kind'),'source_review':report})
            continue
        if report.get('explicitly_closed') is True:
            rejected.append({'opportunity_id':record['opportunity_id'],'reason':'Official publisher is not accepting proposals',
                             'source_review':report})
            continue
        if report.get('checked') is True:
            from .source_brief import adapt
            try:record=adapt(record,snapshot,audience)
            except (PipelineError,ValueError,TypeError,KeyError) as error:
                deferred.append({'opportunity_id':record.get('opportunity_id'),'outcome':'source_adaptation_unconfirmed','reason':str(error)[:400]})
                continue
            candidate=(score,record,snapshot)
            fit=assess(record,audience)
            if not fit['suitable']:
                audience_deferred.append({'opportunity_id':record['opportunity_id'],**fit,'source_brief':record.get('editorial_source_brief')})
                continue
            # Pure CPU/template check only. Source/audience relevance does not
            # prove this installed editor can express it as a short story.
            try:
                from .claims import build_claims
                from .writer import write_script
                from .common import utc_now
                ledger=build_claims(record,snapshot,utc_now().date())
                draft,_=write_script(record,ledger,{'writer':'template','selection':{'audience':audience}})
            except (PipelineError,ValueError,TypeError,KeyError) as error:
                format_deferred.append({'opportunity_id':record.get('opportunity_id'),'outcome':'short_format_unavailable','reason':str(error)[:400],'facts_preserved':True})
                continue
            report['audience_fit']=fit
            report['editorial_format_preflight']={'pass':True,'contract':draft.get('editorial_contract'),'scene_count':len(draft['segments']),'model_started':False}
            from .editorial import ranking_evidence
            rank=ranking_evidence(record,score,[],snapshot,audience=audience,as_of=utc_now().date());record['ranking_evidence']=rank
            supported.append(((rank['score'],record,snapshot),report))
            continue
        deferred.append({'opportunity_id':record['opportunity_id'],'outcome':'source_unconfirmed',
                         'reason':report.get('reason'),'error_type':report.get('error_type')})
        if fallback is None or (report.get('document_complete') is True and report.get('identity_agreement') is not False and (fallback[1].get('document_complete') is not True or fallback[1].get('identity_agreement') is False)):fallback=(candidate,report)
    if supported:
        supported.sort(key=lambda x:(-x[0][0],str(x[0][1].get('opportunity_id',''))))
        candidate,report=supported[0];report['reviewed_candidate_ranking']=[{'opportunity_id':r[1]['opportunity_id'],'score':r[0],'components':r[1]['ranking_evidence']['components']} for r,p in supported]
        return selected(candidate,report)
    # Unconfirmed source is never a suitable-topic fallback.
    selection_status='no_supported_format' if format_deferred else 'no_suitable_topic' if audience_deferred else 'source_review_unavailable' if deferred else 'publisher_rejected' if rejected else 'no_candidates_in_bounded_pass'
    write_json(directory/'audience_selection.json',{'status':selection_status,'audience':audience,'deferred':audience_deferred,'format_deferred':format_deferred,'source_deferred':deferred,'preserve_specialized_candidates':True})
    write_json(directory/'publisher_rejections.json',{'rejected':rejected})
    if format_deferred:raise SourceSelectionExhausted('Audience-matching facts retained, but no supported short editorial format remains')
    if audience_deferred:raise SourceSelectionExhausted('No suitable topic for configured audience; specialized sources retained')
    write_json(directory/'publisher_rejections.json',{'rejected':rejected})
    if deferred:raise SourceSelectionExhausted('Source review unavailable/incomplete in this bounded pass; candidates remain unconfirmed, not publisher-rejected')
    if not rejected:raise SourceSelectionExhausted('No candidates in this bounded pass; not proof no topics exist')
    raise SourceSelectionExhausted('No candidate remains after official publisher closure/application-deadline policy checks')
