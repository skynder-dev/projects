"""Small auditable screen-label equivalences; never general semantic/owner approval."""
import re,hashlib
from .common import PipelineError,stable_json
POLICY='SOCIAL_CONSERVATIVE_SCREEN_RELATION_V1'
TOKEN=re.compile(r'[$€£]\s*\d[\d,]*(?:\.\d+)?|\d[\d,]*(?:\.\d+)?%?|[A-Za-z]+(?:[\x27\u2019][A-Za-z]+)?')

def _tokens(text,allow_fha_short=False):
 raw=[(m.group().lower().replace(',','').replace(' ',''),m.start(),m.end()) for m in TOKEN.finditer(text)]
 out=[];rules=[]
 for i,(word,a,b) in enumerate(raw):
  # Only the definite article is elided. Never discard a/an, not, only, if,
  # modal, recipient, currency, number, date, or program/track identifier.
  if word=='the':rules.append('definite_article');continue
  if allow_fha_short and word=='insurance' and i and i+1<len(raw) and raw[i-1][0]=='fha' and raw[i+1][0] in {'refund','refunds'}:
   rules.append('fha_insurance_refund_short_label');continue
  out.append((word,a,b))
 return out,rules

def bind(voice,headline,allow_fha_short=False):
 if not isinstance(voice,str) or not isinstance(headline,str) or not headline.strip() or len(voice)>3000 or len(headline)>200:raise PipelineError('Invalid bounded screen relation input')
 from .narrative_checks import screen_field
 if not screen_field(headline)['preparation_valid']:raise PipelineError('Screen wording/staging separation requires review')
 v,vr=_tokens(voice,allow_fha_short);h,hr=_tokens(headline,allow_fha_short);needle=[t[0] for t in h]
 if not needle:raise PipelineError('Screen meaning requires review: empty label')
 from .meaning_review import accent_issues
 matches=[]
 for i in range(len(v)-len(h)+1):
  if [t[0] for t in v[i:i+len(h)]]!=needle:continue
  if i and v[i-1][0] in {'fha','unclaimed','unpaid'} and v[i][0] in {'refund','refunds','pension','pensions','wages'}:continue
  if v[i][0] in {'insurance','refund','refunds'} and 'fha' in [x[0] for x in v[max(0,i-2):i]]:continue
  start,end=v[i][1],v[i+len(h)-1][2];reference=voice[start:end]
  issues=accent_issues(voice,reference)
  if issues:continue
  matches.append({'start_char':start,'end_char':end,'text':reference})
 if len(matches)!=1:raise PipelineError('Screen meaning requires review: no unique conservative equivalent preserving spoken qualifiers')
 reference=matches[0]
 return {'schema':POLICY,'voice_sha256':hashlib.sha256(voice.encode()).hexdigest(),'headline_sha256':hashlib.sha256(headline.encode()).hexdigest(),'spoken_reference':reference,'rules':sorted(set(vr+hr+['case_and_punctuation'])),'scope':'Conservative label correspondence only; not source entailment, general paraphrase validation or approval'}

def verify(voice,headline,proof,allow_fha_short=False):
 try:return stable_json(proof)==stable_json(bind(voice,headline,allow_fha_short))
 except (PipelineError,ValueError,TypeError):return False
