"""Narrow source-exact NSF proposer restrictions; no inferred eligibility."""
import re


def proposer_conditions(document):
    text=re.sub(r'\s+',' ',document['text'])
    blocks=list(re.finditer(r'IV\. Eligibility Information\s+Who May Submit Proposals:\s*(.*?)\s+Who May Serve as PI:',text,re.S))
    if len(blocks)!=1:return None
    paragraph=blocks[0].group(1).strip()
    policy='The categories of proposers eligible to submit proposals to the National Science Foundation are identified in the NSF Proposal & Award Policies & Procedures Guide (PAPPG), Chapter I.E.'
    exclusion='Unaffiliated individuals are not eligible to submit proposals in response to this solicitation.'
    if paragraph!=policy+' '+exclusion:return None
    section=text[blocks[0].start():].split('V. Proposal Preparation And Submission Instructions')[0]
    caps=list(re.finditer(r'Limit on Number of Proposals per PI or co-PI:\s*1\s*(An individual may serve as PI, co-PI, or other senior personnel on only one Pilot or Implementation proposal submitted to the CyberTraining program per competition\.)',section))
    return {'unaffiliated_individuals_eligible':False,'restriction_quote':exclusion,'policy_reference_quote':policy,
            'proposal_cap_quote':caps[0].group(1) if len(caps)==1 else None,
            'eligibility_defined_in_linked_policy':True,'linked_policy_reviewed':False,
            'scope':'Explicit full-document proposer exclusion and policy dependency; no complete eligibility/individual qualification determination'}


def project_budgets(document):
    text=re.sub(r'\s+',' ',document['text'])
    pilot=list(re.finditer(r'Pilot projects, with total budgets of up to \$([\d,]+) and with durations of up to (two) years, are exploratory activities that may lead to Implementation projects\.',text))
    implementation=list(re.finditer(r'Implementation projects can be either Small \(with total budgets of up to \$([\d,]+)\) or Medium \(with total budgets of up to \$([\d,]+)\) for durations of up to (four) years\.',text))
    if len(pilot)!=1 or len(implementation)!=1:return None
    a,b=pilot[0],implementation[0]
    return {'classes':[{'name':'Pilot','total_project_budget_usd':int(a[1].replace(',','')),'max_years':2},
                       {'name':'Small Implementation','total_project_budget_usd':int(b[1].replace(',','')),'max_years':4},
                       {'name':'Medium Implementation','total_project_budget_usd':int(b[2].replace(',','')),'max_years':4}],
            'source_quotes':[a[0],b[0]],'scope':'Total project budget by class; not annual cost, individual payment, or amount promised to every applicant'}
