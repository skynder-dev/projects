"""Conservative parser for complete NIH full-announcement HTML attachments."""
import datetime as dt
import re
from html.parser import HTMLParser
from .common import PipelineError, sha256_bytes, parse_date


class Node:
    def __init__(self, tag='', attrs=()):
        self.tag=tag;self.attrs=dict(attrs);self.children=[];self.parent=None
    def text(self):
        if self.tag in ('script','style'):return ''
        return re.sub(r'\s+([,.;])',r'\1',' '.join(' '.join(c.text() if isinstance(c,Node) else c for c in self.children).split()))
    def nodes(self,tag=None):
        for c in self.children:
            if isinstance(c,Node):
                if tag is None or c.tag==tag:yield c
                yield from c.nodes(tag)


class Tree(HTMLParser):
    def __init__(self):super().__init__();self.root=Node();self.stack=[self.root]
    def handle_starttag(self,tag,attrs):
        node=Node(tag,attrs);node.parent=self.stack[-1];node.parent.children.append(node)
        if tag not in ('area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'):
            if len(self.stack)>150:raise PipelineError('NIH HTML nesting exceeds bound')
            self.stack.append(node)
    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i].tag==tag:del self.stack[i:];break
    def handle_data(self,data):self.stack[-1].children.append(data)


def _date(value):
    if not re.fullmatch(r'[A-Z][a-z]+ \d{1,2}, \d{4}',value):raise PipelineError('NIH application date format unsupported: '+value[:80])
    return dt.datetime.strptime(value,'%B %d, %Y').date().isoformat()


def parse_document(raw,record):
    if len(raw)>2*1024*1024:raise PipelineError('NIH HTML exceeds bound')
    parser=Tree();parser.feed(raw.decode('utf-8'));root=parser.root;text=root.text()
    def only(nodes,label):
        values=list(nodes)
        if len(values)!=1:raise PipelineError('NIH '+label+' missing or ambiguous')
        return values[0]
    def field(label):
        node=only((n for n in root.nodes('div') if 'datalabel' in n.attrs.get('class','').split() and n.text()==label),label)
        return only((n for n in node.parent.children if isinstance(n,Node) and 'datacolumn' in n.attrs.get('class','').split()),label+' value').text()
    title=only(root.nodes('title'),'title').text();number=field('Funding Opportunity Number (FON)')
    if number!=record.get('number') or title.removeprefix(number+': ').strip()!=record.get('title','').strip():
        raise PipelineError('NIH primary title/FON differs from opportunity')
    required=('National Institutes of Health','Part 1. Overview Information','Part 2. Full Text of Announcement',
              'Section I. Notice of Funding Opportunity Description','Section II. Award Information','Section III. Eligibility Information',
              'Section IV. Application and Submission Information','Section V. Application Review Information',
              'Section VI. Award Administration Information','Section VII. Agency Contacts','Section VIII. Other Information')
    if len(text)<15000 or any(s not in text for s in required):raise PipelineError('NIH attachment lacks complete expected sections')
    headings=[n.text() for n in root.nodes('h2')]
    if any(s not in headings for s in required[3:]):raise PipelineError('NIH full section bodies missing (table of contents alone is insufficient)')
    table=only((n for n in root.nodes('table') if n.attrs.get('id')=='keyDatesContentTable'),'application schedule')
    rows=list(table.nodes('tr'));groups=[n.text() for n in rows[0].children if isinstance(n,Node) and n.tag=='th']
    headers=[n.text() for n in rows[1].children if isinstance(n,Node) and n.tag=='th']
    if groups!=['Application Due Dates','Review and Award Cycles'] or headers!=['New','Renewal / Resubmission / Revision (as allowed)','AIDS - New/Renewal/Resubmission/Revision, as allowed','Scientific Merit Review','Advisory Council Review','Earliest Start Date']:
        raise PipelineError('NIH application/review schedule column semantics unsupported')
    cycles=[]
    for row in rows[2:]:
        cells=[n for n in row.children if isinstance(n,Node) and n.tag=='td']
        if len(cells)!=6 or any(c.attrs.get('colspan','1')!='1' or c.attrs.get('rowspan','1')!='1' for c in cells):raise PipelineError('NIH schedule row ambiguous')
        dates=[None if c.text()=='Not Applicable' else _date(c.text()) for c in cells[:3]]
        cycles.append(dict(zip(('new','renewal_resubmission_revision','aids'),dates)))
    if not cycles or len(cycles)>20:raise PipelineError('NIH application cycles missing or excessive')
    budget=field('Award Budget');phases=[]
    pattern=r'\$([\d,]+) per year in direct costs for (UG3|UH3) \(Phase ([12])\)'
    for amount,mechanism,phase in re.findall(pattern,budget):
        phases.append({'mechanism':mechanism,'phase':int(phase),'annual_direct_cost_limit_usd':int(amount.replace(',',''))})
    period=field('Award Project Period')
    for p in phases:
        match=re.search(r'(\d+) years for the '+p['mechanism']+r' \(Phase '+str(p['phase'])+r'\)',period)
        if not match:raise PipelineError('NIH phase period unsupported')
        p['max_years']=int(match.group(1))
    if len(phases)!=2 or [(p['mechanism'],p['phase']) for p in phases]!=[('UG3',1),('UH3',2)]:raise PipelineError('NIH phase budget format unsupported')
    if 'All applications are due by 5:00 PM local time of applicant organization.' not in text:raise PipelineError('NIH applicant-local deadline time unsupported')
    adjustment='When a submission date falls on a weekend or Federal holiday, the application deadline is automatically extended to the next business day.'
    if adjustment not in text:raise PipelineError('NIH weekend/holiday date rule unsupported')
    return {'schema':'NIH_FULL_HTML_V1','complete':True,'number':number,'title':title,'date_adjustment_rule':adjustment,
            'content_sha256':sha256_bytes(raw),'text':text,'posted_date':_date(field('Posted Date')),
            'application_open_date':_date(field('Open Date (Earliest Submission Date)')),
            'expiration_date':_date(field('Expiration Date')),'cycles':cycles,
            'deadline_time':'17:00 applicant organization local time','budget':{'quote':budget,'phases':phases,'period_quote':period,
            'scope':'Annual direct-cost limits by phase; not total award or personal payout; UH3 transition is not promised'}}


def assess(document,record,*,today=None,min_days=10):
    today=today or dt.datetime.now(dt.timezone.utc).date()
    upcoming=sorted(c['new'] for c in document['cycles'] if c['new'] and c['new']>=today.isoformat())
    next_date=upcoming[0] if upcoming else None
    days=(dt.date.fromisoformat(next_date)-today).days if next_date else None
    all_dates=[d for c in document['cycles'] for d in c.values() if d]
    conflicts=[]
    if next_date and dt.date.fromisoformat(next_date).weekday()>=5:conflicts.append('Next nominal new deadline is a weekend; business-day adjustment needs official calendar review')
    if parse_date(record.get('close_date'))!=dt.date.fromisoformat(max(all_dates)):conflicts.append('Listing close date differs from final application deadline')
    if parse_date(record.get('open_date'))!=dt.date.fromisoformat(document['posted_date']):conflicts.append('Listing posting date differs from document')
    limits=[p['annual_direct_cost_limit_usd'] for p in document['budget']['phases']]
    if record.get('award_ceiling') not in limits:conflicts.append('Listing ceiling does not match a recognized phase annual direct-cost limit')
    expired=today.isoformat()>=document['expiration_date']
    rejected=not conflicts and (expired or next_date is None or days<min_days or document['application_open_date']>today.isoformat())
    reason=('; '.join(conflicts) if conflicts else 'NIH announcement expired' if expired else 'No future new-application deadline' if not next_date else
            f'Next new-application deadline {next_date} is in {days} days (< minimum {min_days}); later cycles are not substituted' if days<min_days else
            'NIH application submission window has not opened' if document['application_open_date']>today.isoformat() else None)
    return {'pass':not conflicts and not rejected,'selection_rejected':rejected,'rejection_kind':'application_deadline_policy' if rejected else None,
            'next_new_application_date':next_date,'days_left':days,'minimum_lead_days':min_days,'as_of':today.isoformat(),
            'listing_deadline_agreement':not conflicts,'conflicts':conflicts,'reason':reason,'cycles':document['cycles'],
            'expiration_date':document['expiration_date'],'deadline_time':document['deadline_time']}
