"""Source-scoped concise script for the fully recognized NSF project-class case."""
from .common import human_date,money,parse_date,PipelineError


def compact_project_script(base,record,claims):
    by={c['key']:c for c in claims}
    required={'project_budget','proposer_restriction','proposer_policy','proposal_cap','full_proposal_deadline','cost_sharing','purpose_quote','agency','identity'}
    if not required.issubset(by):return base
    classes=by['project_budget']['values']['classes']
    if [c['name'] for c in classes]!=['Pilot','Small Implementation','Medium Implementation']:return base
    if classes[1]['max_years']!=classes[2]['max_years']:return base
    if not by['proposal_cap']['statement'].startswith('An individual may serve as PI, co-PI, or other senior personnel on only one Pilot or Implementation proposal'):return base
    time=by['full_proposal_deadline']['values']
    if time.get('time')!='17:00' or time.get('basis')!="submitter's local time":return base
    old={s['role']:s for s in base['segments']};segments=[]
    def add(role,voice,keys,screen=None):
        import copy
        segment=copy.deepcopy(old[role]);segment.update(voiceover=voice,claim_keys=keys)
        if screen is not None:segment['on_screen']=screen
        segments.append(segment)
    add('hook','The National Science Foundation supports training to create, use and support advanced cyberinfrastructure.',
        ['purpose_quote','agency','identity'],{'kicker':'NATIONAL SCIENCE FOUNDATION','headline':'Train the research workforce','sub':'Advanced cyberinfrastructure\nOpportunity '+str(record['number'])})
    pilot,small,medium=classes
    budget=(f"Project budget caps: Pilot, {money(pilot['total_project_budget_usd'])} over up to {pilot['max_years']} years; "
            f"Small Implementation, {money(small['total_project_budget_usd'])}; Medium Implementation, {money(medium['total_project_budget_usd'])}. "
            f"Implementation projects: up to {small['max_years']} years.")
    add('money',budget,['project_budget'])
    add('who','Unaffiliated individuals are not eligible. Check proposer categories in the official policy onscreen.',
        ['proposer_restriction','proposer_policy'],{'kicker':'CHECK PROPOSER ELIGIBILITY','headline':'Unaffiliated individuals cannot apply','sub':'NSF Proposal & Award Policies & Procedures Guide\nChapter I.E.'})
    segments[-1]['visual']='title'
    add('restriction','One Pilot or Implementation proposal per person per competition, across principal investigator, co-principal investigator and other senior roles.', ['proposal_cap'])
    segments[-1]['visual']='title';segments[-1]['on_screen']={'kicker':'ONE PROPOSAL PER COMPETITION','headline':'Across PI, co-PI and other senior roles','sub':'One Pilot or Implementation proposal per person'}
    date=human_date(parse_date(time['date']));matching=by['cost_sharing']['values']['cost_sharing_required']
    add('deadline',f'Proposals: {date}, by 5 PM, submitter-local time. '+('Cost match required.' if matching else 'No cost match required.'),
        ['full_proposal_deadline','cost_sharing'],{'kicker':'FULL PROPOSAL DEADLINE','big':parse_date(time['date']).strftime('%b ')+str(parse_date(time['date']).day),'headline':str(parse_date(time['date']).year),'sub':'5 PM submitter-local time\n'+('Cost match required' if matching else 'No cost match required')})
    add('cta','Find CyberTraining on Grants.gov; verify the notice number and conditions.', ['identity','proposal_cap'],{'kicker':'FIND THE OFFICIAL PROGRAM','headline':'CyberTraining','sub':'NSF '+str(record['number'])+' | Grants.gov\nVerify all proposer categories and conditions'})
    segments.sort(key=lambda segment:['hook','who','money','restriction','deadline','cta'].index(segment['role']))
    for i,segment in enumerate(segments,1):segment['id']='s'+str(i)
    result={**base,'writer':'template_compact_project_v2','segments':segments,'hook':segments[0]['voiceover'],
            'composition_scope':'Shorter narration; exact source quotes remain in linked claims and on-screen restrictions; no speed/time manipulation or editorial approval'}
    return result
