"""Full NSF HTML solicitation identity and conservative header-deadline agreement."""
import calendar
import datetime as dt
import json
import re
from html.parser import HTMLParser
from urllib.parse import urlsplit
from .common import parse_date,sha256_bytes

VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
BLOCK={'p','li','h1','h2','h3','h4','div','section','tr','td','br'}
class Solicitation(HTMLParser):
    def __init__(self):
        super().__init__();self.stack=[];self.owner=None;self.count=0;self.tokens=[];self.text=[];self.anchors=[]
    def handle_starttag(self,tag,attrs):
        values=dict(attrs)
        if tag=='article' and 'node--type-solicitation' in values.get('class','').split():
            self.count+=1;self.owner=len(self.stack)
        active=self.owner is not None
        skipped=tag in ('script','style') or any(t in ('script','style') for t in self.stack)
        if active and not skipped:
            self.tokens.append(['start',tag,sorted((k,v or '') for k,v in attrs)])
            for key in ('id','name'):
                if values.get(key):self.anchors.append(values[key].lower())
            if tag in BLOCK:self.text.append('\n')
        if tag not in VOID:self.stack.append(tag)
    def handle_endtag(self,tag):
        active=self.owner is not None
        skipped=tag in ('script','style') or any(t in ('script','style') for t in self.stack)
        if active and not skipped:
            self.tokens.append(['end',tag])
            if tag in BLOCK:self.text.append('\n')
        if tag in self.stack:
            index=len(self.stack)-1-self.stack[::-1].index(tag)
            if self.owner is not None and index<=self.owner:self.owner=None
            del self.stack[index:]
    def handle_data(self,data):
        if self.owner is not None and not any(t in ('script','style') for t in self.stack):
            text=' '.join(data.split())
            if text:self.tokens.append(['text',text]);self.text.append(text+' ')

def parse_solicitation(raw,final_url):
    from .announcements import Alerts,publisher_status
    decoded=raw.decode('utf-8');parser=Solicitation();parser.feed(decoded)
    lines=[' '.join(line.split()) for line in ''.join(parser.text).splitlines() if line.strip()]
    text='\n'.join(lines);flat=' '.join(lines)
    alerts=Alerts();alerts.feed(decoded);alert_text=' '.join(' '.join(alerts.alerts).split())
    versions=re.findall(r'\bNSF\s+(\d{2}-\d{3})\b',flat,re.I)
    match=re.search(r'/nsf(\d{2}-\d{3})/solicitation/?$',urlsplit(final_url).path,re.I)
    version=match.group(1) if match else (versions[0] if versions else None)
    required=[r'III\.\s*Award Information',r'IV\.\s*Eligibility Information',r'V\.\s*Proposal Preparation']
    sections=all(re.search(pattern,flat,re.I) for pattern in required)
    targets=all(any(term in anchor for anchor in parser.anchors) for term in ('award','elig','prep'))
    complete=parser.count==1 and len(flat)>8000 and sections and targets and version in versions
    identity={'schema':'NSF_SOLICITATION_HTML_V1','article_tokens':parser.tokens,'publisher_alerts':alert_text}
    return {'schema':'NSF_SOLICITATION_HTML_V1','complete':bool(complete),'document_version':version,
            'content_sha256':sha256_bytes(json.dumps(identity,ensure_ascii=False,sort_keys=True).encode()),
            'text':text,'article_count':parser.count,'section_targets_present':targets,
            **publisher_status(raw),
            'reason':None if complete else 'Complete unique NSF solicitation article/version/sections not established'}

def deadline_agreement(document,listing_date):
    day=parse_date(listing_date);text=' '.join(document['text'].split())
    result={'pass':False,'listing_date':day.isoformat() if day else None,'scope':'Full-proposal header only; no applicant qualification or all linked policy review'}
    match=re.search(r'Full Proposal Deadline\(s\)',text,re.I)
    if not match or not day:return {**result,'reason':'Full proposal header/listing date unrecognized'}
    header=text[match.end():match.end()+2200]
    stop=re.search(r'Important Information|Summary Of Program Requirements',header,re.I)
    if stop:header=header[:stop.start()]
    months='January February March April May June July August September October November December'.split()
    date_pattern=r'\b(?:'+'|'.join(months)+r')\s+\d{1,2},?\s+\d{4}\b'
    explicit=[parse_date(m.group(0)) for m in re.finditer(date_pattern,header,re.I)]
    explicit=[d for d in explicit if d]
    if day in explicit:return {**result,'pass':True,'basis':{'kind':'explicit_date','date':day.isoformat()},'header_excerpt':header[:1200]}
    rule=re.search(r'(First|Second|Third|Fourth|Last)\s+(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+in\s+('+'|'.join(months)+r'),?\s+Annually Thereafter',header,re.I)
    if rule and explicit and day.year>max(d.year for d in explicit):
        ordinal={'first':0,'second':1,'third':2,'fourth':3,'last':-1}[rule[1].lower()]
        weekday=['monday','tuesday','wednesday','thursday','friday','saturday','sunday'].index(rule[2].lower())
        month=[m.lower() for m in months].index(rule[3].lower())+1
        dates=[week[weekday] for week in calendar.monthcalendar(day.year,month) if week[weekday]]
        computed=dt.date(day.year,month,dates[ordinal])
        return {**result,'pass':computed==day,'basis':{'kind':'annual_rule','rule':rule[0],'computed_date':computed.isoformat(),'anchor_last_explicit_year':max(d.year for d in explicit)},'header_excerpt':header[:1200]}
    return {**result,'reason':'No unambiguous matching explicit date or supported annual rule','header_excerpt':header[:1200]}
