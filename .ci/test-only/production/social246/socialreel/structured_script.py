"""Informational script from typed primary conditions, never viewer qualification."""
from .common import money,PipelineError,human_date,parse_date

def claims(record):
    document=record['primary_conditions'];meta=record['announcement_source'];result=[]
    for key,condition in document['conditions'].items():
        evidence=condition['evidence'];values={'quoted_values':condition['values']}
        if key in ('cost_share','share_commitment','share_exclusion') and document.get('cost_sharing_policy'):values['cost_sharing_mode']=document['cost_sharing_policy']['mode']
        if key in ('project_period','project_window','project_start') and document.get('project_period'):
            values['typed_project_period']={k:document['project_period'][k] for k in ('kind','start_date','end_date','min_months','max_months')}
        result.append({'key':'primary_'+key,'statement':evidence[0]['quote'],'values':values,
          'source':{'url':meta['url'],'snapshot_file':meta['file'],'snapshot_sha256':meta['sha256'],'fields':['Primary NOFO '+key], 'page_evidence':evidence}})
    return result

def script(record,ledger):
    document=record['primary_conditions'];budget=document['budget'];date=human_date(parse_date(document['deadline']['date']));clock=document['deadline']['time']+' p.m.'
    policy=document.get('cost_sharing_policy');period=document.get('project_period')
    if document.get('schema')=='SOCIAL_STRUCTURED_NOFO_V1':
        source_quote=document.get('conditions',{}).get('cost_share',{}).get('evidence',[{}])[0].get('quote','').lower()
        duration_quote=document.get('conditions',{}).get('project_period',{}).get('evidence',[{}])[0].get('quote','').lower()
        if 'cost share is allowed but not required' in source_quote:policy={'mode':'optional'}
        if 'one to two years' in duration_quote:period={'spoken_duration':'one to two years','display_duration':'One to two years'}
    if not policy or not period:raise PipelineError('Typed share/period unknown; no inheritance from another program')
    if policy['mode']=='optional':
        share_voice='Cost share is optional; commitments must be met.';share_keys=['primary_cost_share','primary_share_commitment']
    elif policy['mode']=='prohibited':
        share_voice='Do not include cost share in the budget.';share_keys=['primary_cost_share','primary_share_exclusion']
    else:raise PipelineError('Required or unknown cost-sharing details are not supported for generation')
    period_voice=period['spoken_duration']
    period_sub='Availability of funds and agency discretion apply'
    if period.get('start_date') and period.get('end_date'):
        period_sub='Project window: '+human_date(parse_date(period['start_date']))+' to '+human_date(parse_date(period['end_date']))+' • Subject to funds/agency discretion'
        if period.get('kind')=='fixed_calendar_window':period_voice+=', starting '+human_date(parse_date(period['start_date']))
    rows=[
      ('hook','title','Library-service funding for eligible Native Community organizations.',{'kicker':'LIBRARY SERVICES','headline':'For eligible Native Community organizations','sub':'Organization eligibility must be verified'},['primary_applicant']),
      ('money','stat',f"Total federal requests: {money(budget['min_usd'])} to {money(budget['max_usd'])} for {period_voice}.",{'kicker':'TOTAL PROJECT REQUEST','big':money(budget['min_usd'])+'\nTO '+money(budget['max_usd']),'headline':period['display_duration'],'sub':period_sub},['primary_budget','primary_project_period','primary_funding_conditional']+(['primary_project_window','primary_project_start'] if document.get('schema')=='SOCIAL_STRUCTURED_NOFO_V2' else [])),
      ('who','title','Applicants must be federally recognized Native Communities offering library or archival services. Individual membership does not establish organizational eligibility.',{'kicker':'ORGANIZATION REQUIREMENTS','headline':'Federally recognized + library/archive services','sub':'Individual membership does not qualify an organization'},['primary_applicant']),
      ('rules','title','One application per Tribe. The Tribe must lead partnerships. Active awards cannot be renewed or receive added funding.',{'kicker':'APPLICATION RESTRICTIONS','headline':'One application per Tribe','sub':'Tribe leads partnerships; no active-award renewal or additions'},['primary_application_limit','primary_lead_applicant','primary_no_renewal']),
      ('when','deadline',f'Apply by {date}, {clock} U.S. Eastern.',{'kicker':'APPLICATION DEADLINE','headline':date,'sub':clock+' U.S. Eastern • Grants.gov'},['primary_deadline']),
      ('cta','source',share_voice+' Verify your organization and all official funding notice conditions on Grants.gov.',{'kicker':'VERIFY BEFORE APPLYING','headline':record['number'],'sub':('Grants.gov • Cost share is prohibited' if policy['mode']=='prohibited' else 'Grants.gov • Organization eligibility must be verified')},share_keys+['primary_applicant','identity'])]
    if 'purpose' in document['conditions']:
        role,visual,voice,screen,keys=rows[0];rows[0]=(role,visual,'Sustain and improve library services in eligible Native Communities.',{**screen,'headline':'Sustain and improve library services'},['primary_purpose','primary_applicant'])
    rows.sort(key=lambda row:['hook','who','money','rules','when','cta'].index(row[0]))
    role,visual,voice,screen,keys=rows[-1]
    rows[-1]=(role,visual,voice,{**screen,'headline':__import__('re').sub(r' Grants?$','',__import__('re').sub(r'^Native American\s+','',__import__('re').sub(r'\s*\(\d{4}\)$','',record['title']))),'sub':record['number']+' | Grants.gov\nCheck eligibility + full notice'},keys)
    segments=[{'id':'s'+str(i),'role':role,'visual':visual,'voiceover':voice,'on_screen':screen,'claim_keys':keys} for i,(role,visual,voice,screen,keys) in enumerate(rows,1)]
    # Match the existing script envelope rather than introduce a new presentation system.
    details=[{'claim_key':c['key'],'text':c['statement'],'source':c['source']} for c in ledger if c['key'].startswith('primary_')]
    if not details:raise PipelineError('Primary conditions must remain available in the full description')
    description='Source-bound conditions excerpt; verify the full official notice and organizational eligibility.\n\n'+'\n\n'.join(d['text'] for d in details)
    return {'writer':'primary_conditions_template_v3','description_detail_policy':'all_primary_claims_v1','description_details':details,'hook':segments[0]['voiceover'],'segments':segments,'description':description,'source_note':'Full official NOFO and page citations are linked in the claim ledger. Verify program conditions.','title':record['title']}
