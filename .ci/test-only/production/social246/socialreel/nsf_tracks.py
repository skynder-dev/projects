"""Source-span track adapter. Signature is declared track structure, never opportunity ID."""
import re,calendar,datetime as dt
from .common import sha256_bytes,parse_date

class Spans:
 def __init__(self,document,source):self.text=document['text'];self.source=source;self.content_sha=document['content_sha256']
 def find(self,pattern,section=None,flags=0):
  text=self.text;base=0
  if section:
   blocks=list(re.finditer(section,text,re.M|re.S))
   if len(blocks)!=1:return {'state':'unknown','reason':'Section identity ambiguous or absent','evidence':[]}
   base=blocks[0].start(1);text=blocks[0].group(1)
  matches=list(re.finditer(pattern,text,flags))
  evidence=[{'start':base+m.start(),'end':base+m.end(),'quote':m[0],'basis':'Exact character offsets in canonical extracted document.text','raw_sha256':self.source['sha256'],'content_sha256':self.content_sha,'normalized_text_sha256':sha256_bytes(self.text.encode())} for m in matches]
  signatures={tuple(m.groups()) if m.groups() else (m[0],) for m in matches}
  if not matches or len(signatures)!=1:return {'state':'unknown','reason':'Missing or contradictory source values','evidence':evidence}
  return {'state':'known','groups':list(matches[0].groups()),'evidence':evidence}

AWARD=r'^III\. Award Information\n(.*?)^IV\. Eligibility Information\n'
ELIG=r'^IV\. Eligibility Information\n(.*?)^V\. Proposal Preparation and Submission Instructions\n'

def parse(document,source):
 e=Spans(document,source);text=document['text']
 aliases=list(re.finditer(r'(NSF [A-Z0-9]+)-(Explore|Translate|Partner) \((NSF [A-Z0-9]+-[ETP])\)',text))
 mapping={m[2]:m[3] for m in aliases}
 prefixes={m[1] for m in aliases}
 if set(mapping)!={'Explore','Translate','Partner'} or len(prefixes)!=1:return None
 prefix=next(iter(prefixes))
 if any(m[3]!=prefix+'-'+{'Explore':'E','Translate':'T','Partner':'P'}[m[2]] for m in aliases):return None
 if mapping!={name:prefix+'-'+letter for name,letter in [('Explore','E'),('Translate','T'),('Partner','P')]}:return None
 q=re.escape(prefix);tracks={}
 for name,label in mapping.items():
  row=e.find(r'^'+re.escape(label)+r' (?:projects|awards) ([^\n]+)',AWARD,re.M)
  budget={'state':'unknown','reason':'Unrecognized per-award units/qualification','evidence':row['evidence']}
  if row['state']=='known':
   value=row['groups'][0]
   match=re.search(r'(estimated at approximately|up to) \$([\d,]+) per award for up to (\d+) months\.',value)
   if match:budget={'state':'known','amount_usd':int(match[2].replace(',','')),'amount_kind':'approximate_award_estimate' if match[1]=='estimated at approximately' else 'maximum_per_award','duration_max_months':int(match[3]),'evidence':row['evidence']}
  tracks[label]={'name':name,'budget':budget,'declaration':e.find(re.escape(prefix+'-'+name+' ('+label+')'))}
 # Cross-check independently repeated maximum-budget instructions; do not merge tracks.
 caps=e.find(r'The maximum budget must not exceed \$([\d,]+) for '+q+r'-T proposals, and \$([\d,]+) for '+q+r'-P proposals\.')
 if caps['state']=='known':
  for letter,amount in zip(['T','P'],caps['groups']):
   b=tracks[prefix+'-'+letter]['budget'];b['evidence']+=caps['evidence']
   if b.get('amount_usd')!=int(amount.replace(',','')):b.update(state='unknown',reason='Award section and budget instructions disagree')
 else:
  for letter in ['T','P']:tracks[prefix+'-'+letter]['budget'].update(state='unknown',reason='Independent maximum-budget instructions unavailable',evidence=tracks[prefix+'-'+letter]['budget']['evidence']+caps['evidence'])
 shared={
  'external_policy_reference':e.find(r'You must prepare your proposal according to Chapter[^\n]+'),
  'direct_partner_reference':e.find(r'It is critical that PIs review the TTP-related Dear Colleague Letters[^\n]+Terms and Conditions related to these partnerships\.'),
  'track_order':e.find(r'The NSF TTP tracks are not required to be accessed in any specific order; that is, one track is not a pre-requisite for another\.[^\n]+'),
  'availability':e.find(r'Estimated program budget, number of awards, and average award size/duration are subject to the availability of funds\.',AWARD),
  'lead_organizations':e.find(r'Who May Submit Proposals:\n(.*?)(?=\nWho May Serve as PI:)',ELIG,re.S),
  'PI_appointments':e.find(r'Who May Serve as PI:\n(.*?)(?=\nThe '+q+r'-E track requires)',ELIG,re.S),
  'proposal_limit':e.find(r'A PI \(or Co-PI\) may submit only one '+q+r' proposal \('+q+r'-E, '+q+r'-T, or '+q+r'-P\) at a time\.\nPIs \(or Co-PIs\) must wait for a determination \(award or decline recommendation\) on their current TTP proposal before submitting another TTP proposal\.',ELIG),
  'single_institution':e.find(r'All '+q+r' proposals must be submitted by a single institution\. Simultaneous proposal submissions[^\n]+returned without review \.'),
  'cost_sharing':e.find(r'Inclusion of voluntary committed cost sharing is prohibited\.'),
  'partnership_optional_required':e.find(r'While TTP-E and TTP-T tracks may include NSF-Catalyzed Partnerships, the TTP-P track requires an NSF-Catalyzed Partnership and strongly prioritizes a non-academic partner\.'),
  'TP_prior_funding':e.find(r''+q+r'-T and TTP-P proposals may be based upon NSF or other federally-funded research discoveries and innovations; however, prior federal funding is not a requirement for submission \.'),
  'TP_training':e.find(r''+q+r'-T and '+q+r'-P recipients are required to complete NSF Innovation Corps[^\n]+requirement may be waived\.[^\n]*'),
  'TP_training_budget':e.find(r'For '+q+r'-T and TTP-P tracks: The budget must include \$([\d,]+) for required I-Corps Teams training in Year 1,[^\n]+'),
 }
 tracks[prefix+'-E'].update(eligibility=e.find(r'The '+q+r'-E track requires the proposers[^\n]+before submission of an '+q+r'-E proposal\.',ELIG),submission=e.find(r'If approval is provided via email by the cognizant NSF PO,[^\n]+must be returned without review\.'),schedule=e.find(r'For '+q+r'-E: Proposals may be submitted anytime\.'))
 tracks[prefix+'-P']['partner_personnel']=e.find(r'For the '+q+r'-P track, in addition to the PI,[^\n]+',ELIG)
 partner=tracks[prefix+'-P']['partner_personnel']
 if partner['state']=='known' and 'proposals must include a co-PI or Senior/Key Personnel who is a member or employee of an NSF-Catalyzed Partner' not in partner['evidence'][0]['quote']:partner.update(state='unknown',reason='Required partner personnel relation unsupported')
 for track in tracks.values():
  b=track['budget']
  if b['state']=='known' and not (0<b['amount_usd']<=10**12 and 1<=b['duration_max_months']<=1200):b.update(state='unknown',reason='Unsupported amount or duration bounds')
 training=shared['TP_training_budget']
 if training['state']=='known':
  allocation=re.search(r'listed as \$([\d,]+)[^\n]+?and \$([\d,]+) added to the indirect costs',training['evidence'][0]['quote'])
  if not allocation or sum(int(v.replace(',','')) for v in allocation.groups())!=int(training['groups'][0].replace(',','')):training.update(state='unknown',reason='Training total and direct/indirect allocation disagree')
  else:training.update(direct_cost_usd=int(allocation[1].replace(',','')),indirect_cost_usd=int(allocation[2].replace(',','')),included_in_track_budget=True)
 lead=shared['lead_organizations']
 if lead['state']=='known' and not ('Institutions of Higher Education (IHEs)' in lead['groups'][0] and 'accredited in, and having a campus located in the U.S.' in lead['groups'][0] and 'Non-profit, non-academic organizations:' in lead['groups'][0] and 'directly associated with educational or research activities' in lead['groups'][0]):lead.update(state='unknown',reason='Lead-organization classes/qualifications are unsupported')
 pi=shared['PI_appointments']
 if pi['state']=='known' and not ('tenured or tenure-track position' in pi['groups'][0] and 'primary, full-time, paid appointment in a research or teaching position' in pi['groups'][0]):pi.update(state='unknown',reason='PI appointment alternatives unsupported')
 eligibility=tracks[prefix+'-E']['eligibility']
 if eligibility['state']=='known':
  body=eligibility['evidence'][0]['quote'];years=re.search(r'should have at least (one|two|[0-9]+) year',body);reports=re.search(r'should have submitted \(and had approved\) ([0-9]+)-([0-9]+) annual reports',body);excluded=re.search(r'As part of this track, (.*?) awards are not eligible',body);pages=re.search(r'MUST provide a ([0-9]+)- to ([0-9]+)-page description',body)
  if not all([years,reports,excluded,pages]) or 'active, eligible, NSF research award' not in body or 'gain their approval via email, before submission' not in body:eligibility.update(state='unknown',reason='One or more Explore eligibility modalities/limits unrecognized')
  else:eligibility.update(details={'active_eligible_NSF_award_required':True,'remaining_award_years_min':{'one':1,'two':2}.get(years[1],int(years[1]) if years[1].isdigit() else 0),'remaining_years_modality':'should','approved_annual_reports_range':[int(reports[1]),int(reports[2])],'reports_modality':'should','excluded_award_types':[v.strip() for v in re.split(r',|\bor\b',excluded[1]) if v.strip()],'description_pages_range':[int(pages[1]),int(pages[2])],'prior_email_approval_required':True})
 submission=tracks[prefix+'-E']['submission']
 if submission['state']=='known' and not all(v in submission['evidence'][0]['quote'] for v in ['Supplemental Funding Request','Research.gov','Authorized Organizational Representative','emailed invitation','must be returned without review']):submission.update(state='unknown',reason='Explore submission method/invitation requirements unsupported')
 if tracks[prefix+'-E']['schedule']['state']=='known':tracks[prefix+'-E']['schedule']['kind']='anytime'
 dates=e.find(r'For '+q+r'-T and '+q+r'-P:\n([A-Za-z]+ \d{1,2}, \d{4})\n([A-Za-z]+ \d{1,2}, \d{4})\n(First|Second|Third|Fourth|Last) (Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday) in ([A-Za-z]+), and ([A-Za-z]+), Annually Thereafter\.')
 clock=e.find(r"Full Proposal Deadline\(s\) \(due by (\d+) p\.m\. submitting organization's local time\):")
 if clock['state']=='known' and not 1<=int(clock['groups'][0])<=12:clock.update(state='unknown',reason='Unsupported clock')
 if dates['state']=='known' and clock['state']=='known':
  observed=dt.datetime.fromisoformat(source['fetched_at']).astimezone(dt.timezone.utc).date();a,b,ordinal,weekday,ma,mb=dates['groups'];months={v:i for i,v in enumerate(calendar.month_name) if v};order={'First':0,'Second':1,'Third':2,'Fourth':3,'Last':-1};wd=list(calendar.day_name).index(weekday)
  if ma not in months or mb not in months:dates.update(state='unknown',reason='Unknown month in recurrence')
  else:
   candidates=[]
   for year in [observed.year,observed.year+1]:
    for month in [months[ma],months[mb]]:
     days=[week[wd] for week in calendar.monthcalendar(year,month) if week[wd]];day=dt.date(year,month,days[order[ordinal]])
     if day>=observed:candidates.append(day)
   explicit=[parse_date(a),parse_date(b)]
   if any(d is None or d.month not in [months[ma],months[mb]] or d.weekday()!=wd or d.day!=[w[wd] for w in calendar.monthcalendar(d.year,d.month) if w[wd]][order[ordinal]] for d in explicit):dates.update(state='unknown',reason='Explicit dates contradict recurrence')
   else:dates.update(kind='recurring',next_date=min(candidates).isoformat(),as_of=observed.isoformat(),recurrence={'ordinal':ordinal,'weekday':weekday,'months':[ma,mb]},clock_hour_12=int(clock['groups'][0]),time=f'{int(clock["groups"][0])%12+12:02}:00',timezone_basis="submitting organization's local time",evidence=dates['evidence']+clock['evidence'],derivation='Calendar evaluation of explicit recurring rule as of the original observation; not a new source observation')
 else:dates.update(state='unknown',reason='Track-specific recurrence/clock unsupported')
 for letter in ['T','P']:tracks[prefix+'-'+letter]['schedule']=dates
 unresolved=['Linked PAPPG/application-guide conditions are referenced but not captured in this pinned document','NSF-Direct partner DCL terms may add conditions; linked DCLs were not fetched']
 for label,t in tracks.items():
  for key,value in t.items():
   if isinstance(value,dict) and value.get('state')=='unknown':unresolved.append(label+': '+key+' unresolved')
 for key,v in shared.items():
  if v['state']=='unknown':unresolved.append('Shared: '+key+' unresolved')
 return {'schema':'SOURCE_TRACK_CONDITIONS_V1','prefix':prefix,'tracks':tracks,'shared':shared,'source':source,'normalized_text_sha256':sha256_bytes(text.encode()),'unresolved_conditions':unresolved,'all_conditions_established':False,'individual_eligibility_assessed':False,'scope':'Track-specific transcription with exact canonical text spans; linked policies/individual qualification remain unknown'}
