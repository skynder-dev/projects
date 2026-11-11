"""Validate typed funding-policy/duration assertions without interpreting grant IDs."""
import re

def errors(text,cited):
    problems=[];modes={c.get('values',{}).get('cost_sharing_mode') for c in cited}-{None}
    if modes:
        permitted=[]
        for match in re.finditer(r'\b(?P<no>no\s+)?cost\s+(?:share|sharing|match)\s+(?:is\s+)?(?P<not>not\s+)?(?P<term>optional|allowed|required|mandatory|prohibited|accepted)\b',text,re.I):
            negative=bool(match['no'] or match['not']);term=match['term'].lower()
            if term in ('required','mandatory'):valid={'optional','prohibited'} if negative else {'required'}
            elif term=='optional':valid=set() if negative else {'optional'}
            elif term in ('allowed','accepted'):valid={'prohibited'} if negative else {'optional','required'}
            else:valid=set() if negative else {'prohibited'}
            permitted.append(valid)
        if re.search(r'\b(?:do not|must not)\s+include\s+cost shar(?:e|ing)\b',text,re.I):permitted.append({'prohibited'})
        if len(modes)!=1 or any(not modes.issubset(valid) for valid in permitted):problems.append('Cost-sharing assertion contradicts the typed primary-document policy')
    count_words={'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'eight':8,'nine':9,'ten':10}
    def count_value(value):return int(value) if value.isdigit() else count_words[value.lower()]
    application_limits=[]
    for claim in cited:
        if claim.get('key')=='primary_application_limit':
            match=re.search(r'\bonly\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+applications?\b',claim.get('statement',''),re.I)
            if match:application_limits.append(count_value(match[1]))
    for match in re.finditer(r'\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+(applications?|proposals?|grants?|awards?)\b',text,re.I):
        if not match[2].lower().startswith('application') and not re.match(r'\s+per\b',text[match.end():],re.I):continue
        if application_limits and any(count_value(match[1])!=limit for limit in application_limits):problems.append('Application count contradicts the cited primary-document limit')
        if application_limits and not match[2].lower().startswith('application'):problems.append('Application limit misrepresented as a different count unit')
    periods=[c['values']['typed_project_period'] for c in cited if c.get('values',{}).get('typed_project_period')]
    numbers={'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'eight':8,'nine':9,'ten':10,'eleven':11,'twelve':12}
    token=r'(\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)'
    duration=re.compile(r'\b'+token+r'(?:\s+to\s+'+token+r')?\s+(years?|months?)\b',re.I)
    for match in duration.finditer(text):
        low,high,unit=match.groups();values=[int(v) if v.isdigit() else numbers[v.lower()] for v in (low,high) if v]
        for p in periods:
            if any(not p['min_months']<=value*(12 if unit.lower().startswith('year') else 1)<=p['max_months'] for value in values):problems.append('Project duration assertion exceeds the typed primary-document period')
    return list(dict.fromkeys(problems))
