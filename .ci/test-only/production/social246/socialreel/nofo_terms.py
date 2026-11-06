"""Typed funding terms from page-bound document rules, independent of grant IDs."""
import datetime as dt
from .common import PipelineError,parse_date

def cost_sharing(doc):
    patterns={
      'optional':r'(Cost shar(?:e|ing) is (?:allowed but not required for the [A-Za-z0-9 -]+ program|optional))\.',
      'prohibited':r'(Cost sharing is not required for this program, and it will not be accepted if voluntarily offered)\.',
      'required':r'(Cost shar(?:e|ing) is required(?:[^.]|\.(?=\d)){0,600})\.(?=\s|$)'}
    found={mode:doc.rule('cost_share_'+mode,pattern,required=False) for mode,pattern in patterns.items()};found={mode:e for mode,e in found.items() if e}
    if len(found)!=1:return {'mode':'unknown','confirmed':False,'reason':'Cost-sharing rule missing or contradictory','observed_modes':list(found)},{}
    mode,condition=next(iter(found.items()));conditions={'cost_share':condition};unknown=[]
    if mode=='optional':
        commitment=doc.rule('share_commitment',r'(If you receive an award, you must meet your cost share commitments)\.',required=False)
        if commitment:conditions['share_commitment']=commitment
        else:unknown.append('Voluntary commitment obligations are not confirmed')
    if mode=='prohibited':conditions['share_exclusion']=doc.rule('share_exclusion',r'(Applicants must not include cost share in their budgets)\.')
    if mode=='required':unknown.append('Required contribution amount/rate and denominator are not supported; do not infer them from a required flag')
    return {'mode':mode,'confirmed':not unknown,'reason':unknown[0] if unknown else None,'evidence':condition['evidence'],'required':True if mode=='required' else False,'unknowns':unknown},conditions

def project_period(doc):
    flexible=doc.rule('flexible_project_period',r'Project activities may be carried out for (one to two years)\.',required=False)
    window=doc.rule('project_window',r'Anticipated period of performance ([A-Za-z]+ \d{1,2}, \d{4})\s*[–-]\s*([A-Za-z]+ \d{1,2}, \d{4})\.',required=False)
    if not window:return {'kind':'unknown','confirmed':False,'reason':'Labelled project calendar window is missing'},{}
    start,end=map(parse_date,window['values'])
    if start is None or end is None or end<start:raise PipelineError('Invalid primary project calendar window')
    next_day=end+dt.timedelta(days=1);months=(next_day.year-start.year)*12+next_day.month-start.month
    if next_day.day!=start.day or not 1<=months<=60:raise PipelineError('Project window is not a supported exact calendar-month interval')
    begins=doc.rule('project_start',r'Projects must begin on ([A-Za-z]+ \d{1,2}, \d{4})\.')
    if parse_date(begins['values'][0])!=start:raise PipelineError('Required project start differs from performance window')
    conditions={'project_period':flexible or window,'project_window':window,'project_start':begins}
    period={'kind':'flexible_duration_with_calendar_window' if flexible else 'fixed_calendar_window','confirmed':True,'start_date':start.isoformat(),'end_date':end.isoformat(),'window_months':months,'evidence':window['evidence'],'derivation':'End date is inclusive; end+one day matches the same day of month after the stated number of calendar months'}
    if flexible:
        if months<24:raise PipelineError('Flexible maximum duration exceeds the project window')
        period.update(min_months=12,max_months=24,spoken_duration='one to two years',display_duration='One to two years')
    else:
        if months==12:voice='one year';display='One year'
        elif months%12==0:voice=str(months//12)+' years';display=voice.capitalize()
        else:voice=str(months)+' months';display=voice.capitalize()
        period.update(min_months=months,max_months=months,spoken_duration=voice,display_duration=display)
    return period,conditions
