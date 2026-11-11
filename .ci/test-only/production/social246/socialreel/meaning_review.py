"""Conservative emphasis checks. Lexical review signals, never semantic fact approval."""
import re

MODAL=r'\b(?:might|could|may|possibly|perhaps)\b'
NEGATIVE=r'\b(?:not|never|cannot|no|without|unknown|unconfirmed|unverified)\b|\b\w+n.t\b'
LIMIT=r'\b(?:up to|at most|at least|more than|less than|maximum|minimum|approximately|about)\b'
CONDITION=r'\b(?:only|eligible|qualifying|if|unless)\b'
NUMBER=r'(?:[$\u20ac\u00a3]\s*)?\b\d[\d,]*(?:\.\d+)?(?:\s*%)?\b'
NUMBER_WORD=r'\b(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|billion)\b'
DATE=r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|before|after|until|through|deadline)\b'

def signals(text):
 return {name:[m.group(0) for m in re.finditer(pattern,text,re.I)] for name,pattern in [('numbers',NUMBER),('number_words',NUMBER_WORD),('currencies',r'[$€£]|\b(?:USD|EUR|GBP|dollars?|euros?|pounds?)\b'),('dates_and_bounds',DATE),('probability',MODAL),('negation_or_unknown',NEGATIVE),('limits',LIMIT),('conditions',CONDITION)]}

def accent_issues(voice,headline):
 if not headline:return []
 start=voice.find(headline)
 if start<0:return ['Screen emphasis does not occur in current narration']
 # Sentence/semicolon boundaries isolate unrelated thoughts; decimal dots do not split.
 left=list(re.finditer(r'[!?;]|(?<!\d)\.(?!\d)',voice[:start]));a=left[-1].end() if left else 0
 right=re.search(r'[!?;]|(?<!\d)\.(?!\d)',voice[start+len(headline):]);b=start+len(headline)+right.start() if right else len(voice)
 clause=voice[a:b];source=signals(clause);screen=signals(headline);issues=[]
 numeric=bool(screen['numbers'] or screen['number_words'])
 assertion=bool(re.search(r'\b(?:get|gets|receive|receives|qualify|qualifies|claim|claims|owed|pays?|refund|eligible)\b|money\s+(?:is\s+)?waiting',headline,re.I))
 # A neutral CTA/accent can stay short; a monetary/date/eligibility assertion needs its own qualifiers.
 for key in ['probability','negation_or_unknown','limits','conditions']:
  required=(numeric or assertion) or (key=='negation_or_unknown' and len(headline.split())>1)
  if required and source[key] and [x.casefold() for x in source[key]]!=[x.casefold() for x in screen[key]]:
   issues.append('Screen emphasis drops or changes '+key.replace('_',' ')+' from its spoken clause')
 if numeric and source['currencies'] and [x.casefold() for x in source['currencies']]!=[x.casefold() for x in screen['currencies']]:issues.append('Screen amount loses its spoken currency')
 if numeric and source['dates_and_bounds'] and [x.casefold() for x in source['dates_and_bounds']]!=[x.casefold() for x in screen['dates_and_bounds']]:issues.append('Screen number/date loses its spoken date or boundary')
 return issues

def change_review(before,after):
 old=signals(before);new=signals(after)
 changed=[key for key in old if [x.casefold() for x in old[key]]!=[x.casefold() for x in new[key]]]
 return {'critical_fields_changed':changed,'before':old,'after':new,'text_changed':before!=after,'semantic_equivalence_verified':False,'factual_approval_implied':False}