"""Offline official-page parsers. Parsed content is not a live observation."""
from html.parser import HTMLParser
from urllib.parse import urlsplit,urljoin
import re,hashlib,json
from .common import PipelineError

class Page(HTMLParser):
 def __init__(self):super().__init__();self.parts=[];self.rows=[];self.row=None;self.links=[];self.href=None;self.anchor=[];self.hidden=0;self.headings=[];self.heading=None;self.normalized_length=0;self.item=None;self.item_count=0
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag in ('script','style'):self.hidden+=1
  if tag in ('h1','h2','h3') and not self.hidden:
   if len(self.headings)>=128:raise PipelineError('Official page exceeds bounded heading input')
   self.heading=(tag,len(self.parts),self.normalized_length)
  if tag=='tr':
   if len(self.rows)>=256:raise PipelineError('Official page exceeds bounded table-row input')
   self.row={'parts':[],'links':[]}
  if tag=='li' and self.row is not None:
   self.item_count+=1
   if self.item_count>256:raise PipelineError('Official page exceeds bounded list-item input')
   if self.item is not None:raise PipelineError('Nested table list needs explicit source review')
   self.item={'parts':[],'links':[]}
  if tag=='a':self.href=a.get('href');self.anchor=[]
 def handle_data(self,data):
  if self.hidden:return
  self.parts.append(data)
  normalized=' '.join(data.split())
  if normalized:self.normalized_length+=len(normalized)+(1 if self.normalized_length else 0)
  if self.row is not None:self.row['parts'].append(data)
  if self.item is not None:self.item['parts'].append(data)
  if self.href:self.anchor.append(data)
 def handle_endtag(self,tag):
  if tag in ('script','style'):self.hidden=max(0,self.hidden-1)
  if self.heading and tag==self.heading[0]:
   kind,index,before=self.heading;title=' '.join(' '.join(self.parts[index:]).split())
   self.headings.append({'tag':kind,'text':title,'start':before+(1 if before else 0)});self.heading=None
  if tag=='a' and self.href:
   if len(self.links)>=512:raise PipelineError('Official page exceeds bounded link input')
   link={'text':' '.join(' '.join(self.anchor).split()),'url':self.href};self.links.append(link)
   if self.row is not None:self.row['links'].append(link)
   if self.item is not None:self.item['links'].append(link)
   self.href=None
  if tag=='li' and self.item is not None:
   self.item['text']=' '.join(' '.join(self.item.pop('parts')).split());self.row.setdefault('items',[]).append(self.item);self.item=None
  if tag=='tr' and self.row is not None:
   self.row['text']=' '.join(' '.join(self.row.pop('parts')).split());self.rows.append(self.row);self.row=None
 @property
 def text(self):return ' '.join(' '.join(self.parts).split())

URLS={'unclaimed':'https://www.usa.gov/unclaimed-money','wages':'https://webapps.dol.gov/wow','energy':'https://www.usa.gov/help-with-energy-bills'}
def sha(text):return hashlib.sha256(text.encode()).hexdigest()

def parse(content,url,*,reconstructed=False,fetched_at=None,content_type='html',snapshot_file=None):
 if not isinstance(content,str) or not content.strip():raise PipelineError('Supplied page content must be nonempty decoded HTML/text')
 if len(content)>2*1024*1024 or len(content.encode('utf-8'))>2*1024*1024:raise PipelineError('Supplied page exceeds2MiB offline parse budget')
 if not isinstance(url,str):raise PipelineError('Official source URL is required')
 canonical=url.rstrip('/');kind=next((k for k,v in URLS.items() if v==canonical),None)
 if not kind:raise PipelineError('Unsupported official public-money page')
 page=Page()
 if content_type=='html':page.feed(content);text=page.text
 elif content_type=='text':text=' '.join(content.split())
 else:raise PipelineError('Only supplied HTML/text accepted')
 base={'schema':'SOCIAL_PUBLIC_MONEY_SOURCE_V1','kind':kind,'source_url':url,'content_sha256':sha(content),'snapshot_file':snapshot_file,'normalized_text_sha256':sha(text),'reconstructed':bool(reconstructed),'fetched_at':None if reconstructed else fetched_at,'source_updated':None,'live_verified':False,'amount':None,'deadline':None,'fields':{},'excluded':[],'unknown':[],'source_status':'reconstructed_research_fixture' if reconstructed else 'supplied_content_not_live_verified'}
 lookup_start=0;lookup_end=len(text)
 def evidence(quote):
  start=text.find(quote,lookup_start,lookup_end)
  if start<0:raise PipelineError('Required official text not found: '+quote)
  return {'url':url,'snapshot_file':snapshot_file,'quote':quote,'excerpt':quote,'excerpt_sha256':sha(quote),'locator':'normalized visible text','start':start,'end':start+len(quote),'content_sha256':sha(content),'normalized_text_sha256':sha(text),'offset_basis':'whitespace-normalized visible text; not raw HTML','reconstructed':bool(reconstructed)}
 def field(name,value,quote):base['fields'][name]={'value':value,'source':evidence(quote)};return value
 updated=re.search(r'(?:LAST UPDATED|Last updated)\s*:?\s*(\d{4}-\d{2}-\d{2}|[A-Za-z]+\s+\d{1,2},\s+\d{4})',text)
 if updated:base['source_updated']=updated[1]
 if kind=='unclaimed':
  field('benefit_kind','return_of_owned_money','Find unclaimed funds held by the government that might be owed to you.')
  field('state_search',True,'Search by state');field('other_databases',True,'Search other databases')
  base.update(audience='individuals_or_legal_heirs',geography='US_information_directory',amount_scope='individual_balance',status='information_available')
  active=[]
  for row in [item for row in page.rows for item in (row.get('items') or [row])]:
   t=row['text'];links=[{**l,'url':urljoin(url,l['url'])} for l in row['links']]
   if re.search(r'economic impact payments|stimulus',t,re.I):
    base['excluded'].append({'text':t,'reason':'Economic Impact Payments deadline ended; never a current opportunity','links':links,'source':evidence(t)});continue
   categories=[('unpaid wages','DOL','dol.gov'),('pensions','PBGC','pbgc.gov'),('FHA insurance refunds','HUD','hud.gov'),('bank failures','FDIC','fdic.gov'),('savings bonds','TreasuryDirect','treasurydirect.gov')]
   matched=[x for x in categories if x[0].casefold() in t.casefold()]
   if matched:
    if len(matched)!=1 or not links:
     base['excluded'].append({'text':t,'reason':'Missing/ambiguous evidenced category or route'});continue
    category,agency,domain=matched[0]
    if any(urlsplit(l['url']).scheme!='https' or not ((urlsplit(l['url']).hostname or '')==domain or (urlsplit(l['url']).hostname or '').endswith('.'+domain)) for l in links):
     base['excluded'].append({'text':t,'reason':'Database route does not match its stated agency/category; needs source review'});continue
    active.append({'text':t,'category':category,'agency':agency,'links':links,'source':evidence(t)})
  base['databases']=active
  base['state_directories']=[{**l,'url':urljoin(url,l['url']),'government_domain':(urlsplit(urljoin(url,l['url'])).hostname or '').endswith('.gov')} for l in page.links if 'unclaimed.org' in l['url']]
  base['unknown']=['individual_balance','individual entitlement/identity','claim-specific deadlines and evidence']
 elif kind=='wages':
  field('identity','Workers Owed Wages','Workers Owed Wages')
  purpose=next((q for q in ('When the Wage and Hour Division finds labor law violations, we often get unpaid wages on behalf of workers.',) if q in text),None)
  if purpose is None:raise PipelineError('DOL already-recovered wage context missing')
  field('purpose','already_recovered_wages',purpose)
  if 'Search for your employer' in text:field('employer_search',True,'Search for your employer')
  field('agency','DOL_WHD','Workers Owed Wages')
  base['fields']['agency']['source']['authority_basis']='Known DOL WHD landing identity from supplied research and exact allowed URL; not a quoted department-name string'
  hold=re.search(r'After (?:three|3) years, if we remain unable to find the person owed back wages, we are required to send the money to the U\.S\. Treasury\.',text,re.I)
  if not hold:raise PipelineError('Wage holding period not established')
  field('holding_period_years',3,hold[0]);base.update(audience='workers_matching_recovered_funds',amount_scope='individual_balance',status='information_available',holding_period_is_calendar_deadline=False)
  base['unknown']=['source_updated','individual_balance','matching employer/worker','case-specific holding-period start']
 else:
  title='Find out if you are eligible for LIHEAP and apply'
  if content_type=='html':
   headings=[h for h in page.headings if h['tag']=='h2' and h['text']==title]
   if len(headings)!=1:raise PipelineError('LIHEAP section heading missing or ambiguous')
   lookup_start=headings[0]['start'];lookup_end=next((h['start'] for h in page.headings if h['tag'] in ('h1','h2') and h['start']>lookup_start),len(text))
  else:
   lookup_start=text.find(title)
   if lookup_start<0:raise PipelineError('LIHEAP section not established')
   boundary=re.search(r'\bWAP\b',text[lookup_start+len(title):]);lookup_end=lookup_start+len(title)+boundary.start() if boundary else len(text)
  region=text[lookup_start:lookup_end]
  field('identity','LIHEAP','Find out if you are eligible for LIHEAP and apply')
  field('eligibility_basis','income','Eligibility for LIHEAP is based on your income.')
  local=next((q for q in ('local rules','However, every state and territory has its own requirements.') if q in region),None)
  if local:field('local_rules',True,local)
  services=next((q for q in ('heating, cooling, and energy crisis','The Low Income Home Energy Assistance Program (LIHEAP) can help you pay your heating or cooling bills or get emergency services during an energy crisis.') if q in region),None)
  if services is None:raise PipelineError('LIHEAP service scope not established inside its section')
  field('services',['heating','cooling','energy_crisis'],services)
  base.update(audience='households_subject_to_income_and_local_rules',amount_scope='local_program_determined',status='national_information_available',local_application_open=None)
  base['excluded']=[{'program':'WAP','reason':'Separate weatherization program; never merged into LIHEAP'}]
  base['unknown']=['local_application_open','local amount','local income/rules','local deadline']
 return base

def unclaimed_record(parsed):
 if parsed['kind']!='unclaimed':raise PipelineError('Unclaimed script requires the unclaimed-money source')
 if not parsed['fields'].get('benefit_kind'):raise PipelineError('Missing conditional owed-money evidence')
 basis=parsed['fields'];claims=[]
 def add(key,text,accent,field):
  source={**basis[field]['source'],'origin_field':field,'rule':'usa_gov_unclaimed_conditional_v1','snapshot_sha256':parsed['content_sha256']}
  claims.append({'key':key,'statement':text,'accent':accent,'source':source,'values':{},'must_disclose':True,'reviewed_statement_sha256':sha(text)})
 # Choose only examples actually extracted from non-expired source rows.
 choices=[('unpaid wages','unpaid wages','DOL'),('pensions','unclaimed pensions','PBGC'),('FHA insurance refunds','FHA insurance refunds','HUD')]
 examples=[]
 for category,spoken,agency in choices:
  row=next((x for x in parsed.get('databases',[]) if x.get('category')==category and x.get('agency')==agency),None)
  if row:examples.append({'spoken':spoken,'category':category,'agency':agency,'source':row['source'],'links':row['links']})
 if len(examples)<2:raise PipelineError('Insufficient evidenced money examples; do not replace with generic search filler')
 phrases=[e['spoken'] for e in examples]
 example_text=(phrases[0]+' or '+phrases[1] if len(phrases)==2 else ', '.join(phrases[:-1])+', or '+phrases[-1])+'.'
 example_text=example_text[0].upper()+example_text[1:]
 add('money_hook','You might have money waiting in your name.','might have money waiting','benefit_kind')
 add('concrete_examples',example_text,example_text.rstrip('.'),'other_databases')
 pieces=[e['source']['quote'] for e in examples];combined='\n'.join(pieces)
 claims[-1]['source'].update(quote=combined,excerpt=combined,excerpt_sha256=sha(combined),example_sources=examples,rule='usa_gov_unclaimed_examples_v4_exact_scopes')
 claims[-1]['source'].pop('start',None);claims[-1]['source'].pop('end',None)
 claims[-1]['source'].update(locator='multiple normalized visible-text spans; see example_sources[].source',span_kind='multiple_disjoint_source_spans')
 add('guide',"The government's guide shows where to check.",'where to check','other_databases')
 add('one_action','Start with your state, then the other databases.','your state, then the other databases','state_search')
 claims[-1]['source']['supporting_sources']=[basis['other_databases']['source']]
 add('cta','Links are in the description.','Links are in the description','benefit_kind')
 add('owned_money_scope','This guide concerns money already owed, not a new grant.','money already owed','benefit_kind')
 add('individual_unknown','Your individual balance and claim entitlement are not established here.','individual balance','benefit_kind')
 # Keep the actual route conditions in the description, not just category labels.
 for example in examples:
  key,accent={'DOL':('wages_scope','Unpaid wages'),'PBGC':('pension_scope','Pensions from former employers'),'HUD':('insurance_scope','FHA insurance refunds')}[example['agency']]
  statement=('FHA insurance refunds: if you had a mortgage insured by the Federal Housing Administration (FHA), search HUD to check refund eligibility.' if example['agency']=='HUD' else example['source']['quote'])
  add(key,statement,accent,'other_databases')
  claims[-1]['source']={**example['source'],'snapshot_sha256':parsed['content_sha256'],'origin_field':example['category'],'rule':'usa_gov_unclaimed_description_v2_exact_scope'}
 expired=next((x for x in parsed.get('excluded',[]) if x.get('source') and re.search(r'ended|expired|passed|no longer',x['text'],re.I)),None)
 if expired:
  add('expired_route','Economic Impact Payments are excluded because their claim deadline has ended.','claim deadline has ended','other_databases')
  claims[-1]['source']={**expired['source'],'snapshot_sha256':parsed['content_sha256'],'origin_field':'excluded Economic Impact Payments','rule':'usa_gov_unclaimed_description_v1'}
 roles=('money_hook','concrete_examples','guide','one_action','cta')
 brief={'schema':'SOCIAL_EDITORIAL_BRIEF_V1','synthetic':False,'live_verified':False,'reconstructed_source':parsed['reconstructed'],'category':'personal_money','audience_description':'People checking whether money is already owed to them; no individual match established','concrete_use':'Find official searches for money already owed; not a new grant','money_benefit':{'kind':'return_of_owned_money','scope':'individual_balance','amount':None,'limit_claim_key':'money_hook'},'review':{'reviewer':'local finite parser/template based on supplied official-source research; not live ingest','scope':'facts_and_plain_language_entailment'},'claims':claims,'main_facts':dict(zip(roles,roles)),'description_claim_keys':[c['key'] for c in claims]}
 r={'title':'Find money that might already be owed to you','opportunity_id':'USA-GOV-UNCLAIMED-MONEY','source_url':parsed['source_url'],'public_money_source':parsed,'editorial_brief':brief}
 r['_local_reviewed_brief_sha256']=sha(json.dumps(brief,sort_keys=True));return r


def energy_record(parsed):
 if parsed['kind']!='energy':raise PipelineError('Energy story requires LIHEAP source, never WAP fields')
 fields=parsed['fields'];claims=[]
 if 'local_rules' not in fields:raise PipelineError('Local-rule evidence missing; no inferred LIHEAP qualification')
 def add(key,text,accent,field):
  source={**fields[field]['source'],'origin_field':field,'rule':'usa_gov_liheap_information_v1','snapshot_sha256':parsed['content_sha256']}
  claims.append({'key':key,'statement':text,'accent':accent,'source':source,'values':{},'must_disclose':True,'reviewed_statement_sha256':sha(text)})
 add('money_hook','Need help with heating or cooling bills?','heating or cooling bills','services')
 add('use_case','Energy assistance may help cover those costs.','Energy assistance may help','services')
 add('key_caveat','Eligibility depends on income and local rules.','income and local rules','eligibility_basis')
 claims[-1]['source']['supporting_sources']=[fields['local_rules']['source']]
 add('one_action',"Start with the government's energy-bill guide.",'energy-bill guide','identity')
 add('cta','The official link is in the description.','official link is in the description','identity')
 add('program_identity','This draft concerns LIHEAP energy assistance.','LIHEAP','identity')
 add('local_unknown','Local intake status, assistance amounts and local application deadlines have not been established.','Local intake status','eligibility_basis')
 roles=('money_hook','use_case','key_caveat','one_action','cta')
 b={'schema':'SOCIAL_EDITORIAL_BRIEF_V1','synthetic':False,'live_verified':False,'reconstructed_source':parsed['reconstructed'],'category':'personal_money','audience_description':'US households seeking information about energy-cost assistance; local and income rules apply','concrete_use':'Heating/cooling bills and energy crisis assistance; local availability unknown','money_benefit':{'kind':'energy_assistance_information','scope':'local_program_determined','amount':None,'limit_claim_key':'money_hook'},'review':{'reviewer':'finite source-bound LIHEAP information template; not a local eligibility assessment','scope':'facts_and_plain_language_entailment'},'claims':claims,'main_facts':dict(zip(roles,roles)),'description_claim_keys':[c['key'] for c in claims]}
 r={'title':'Help with home energy bills: where to start','opportunity_id':'USA-GOV-ENERGY-BILLS','source_url':parsed['source_url'],'public_money_source':parsed,'editorial_brief':b};r['_local_reviewed_brief_sha256']=sha(json.dumps(b,sort_keys=True));return r


def wages_record(parsed):
 if parsed['kind']!='wages':raise PipelineError('Wage story requires the official DOL WOW landing')
 fields=parsed['fields']
 if not fields.get('employer_search'):raise PipelineError('Employer-search evidence missing; do not invent a search step')
 claims=[]
 def add(key,text,accent,field,values=None):
  claims.append({'key':key,'statement':text,'accent':accent,'values':values or {},'must_disclose':True,'reviewed_statement_sha256':sha(text),'source':{**fields[field]['source'],'origin_field':field,'rule':'dol_wow_recovered_wages_v1','snapshot_sha256':parsed['content_sha256']}})
 add('money_hook','Could you be owed unpaid wages?','unpaid wages','identity')
 add('recovered_funds','The Labor Department has already recovered money from employers.','already recovered money','purpose')
 claims[-1]['source']['supporting_sources']=[fields['agency']['source'],fields['employer_search']['source']]
 add('one_action','Search Workers Owed Wages for your employer.','Workers Owed Wages','employer_search')
 add('holding_period','The agency holds funds for 3 years.','3 years','holding_period_years',{'holding_period_years':3,'scope':'agency holding period, not a calendar deadline'})
 add('cta','The official link is in the description.','official link is in the description','identity')
 add('individual_unknown','An employer/worker match and individual balance have not been established.','individual balance','employer_search')
 add('period_scope','The holding period is not a new deadline counted from this video.','not a new deadline','holding_period_years')
 roles=('money_hook','recovered_funds','one_action','holding_period','cta')
 b={'schema':'SOCIAL_EDITORIAL_BRIEF_V1','synthetic':False,'live_verified':False,'reconstructed_source':parsed['reconstructed'],'category':'personal_money','audience_description':'Workers checking whether they match wages already recovered by DOL; no individual match inferred','concrete_use':'Find the official employer lookup for already recovered wages; no people searched','money_benefit':{'kind':'return_of_recovered_wages','scope':'individual_balance','amount':None,'limit_claim_key':'money_hook','holding_period_years':3,'calendar_deadline':None},'review':{'reviewer':'finite DOL WOW template based on supplied research; no individual lookup','scope':'facts_and_plain_language_entailment'},'claims':claims,'main_facts':dict(zip(roles,roles)),'description_claim_keys':[c['key'] for c in claims]}
 r={'title':'Could unpaid wages already be waiting for you?','opportunity_id':'DOL-WORKERS-OWED-WAGES','source_url':parsed['source_url'],'public_money_source':parsed,'editorial_brief':b};r['_local_reviewed_brief_sha256']=sha(json.dumps(b,sort_keys=True));return r
