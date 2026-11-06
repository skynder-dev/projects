"""Narrow checks of program output facts, never external-source entailment."""
import hashlib,re
from .common import PipelineError
from .source_urls import https_url,official_url

VERSION='SOCIAL_PROGRAM_DESCRIPTION_LINK_PRESENCE_V1'

def verify_cta(narration,claim_keys,artifact,expected_text=None,model_review=None,expected_fact_version=None):
 if claim_keys!=['cta']:raise PipelineError('Program CTA proof requires only the dedicated cta claim')
 if artifact.get('kind')!='PROGRAM_RENDERED_DESCRIPTION_NOT_EXTERNAL_SOURCE':raise PipelineError('Program description artifact kind missing')
 text=artifact.get('complete_original_text')
 if not isinstance(text,str) or not text or hashlib.sha256(text.encode('utf-8')).hexdigest()!=artifact.get('text_sha256'):raise PipelineError('Program description bytes/hash differ')
 if expected_text is not None and text!=expected_text:raise PipelineError('Actual rendered description differs from the reviewed program artifact')
 if not re.fullmatch('[a-f0-9]{64}',artifact.get('fact_version','')):raise PipelineError('Program artifact fact version missing')
 if expected_fact_version is not None and artifact['fact_version']!=expected_fact_version:raise PipelineError('Program artifact belongs to a different fact version')
 urls=[];official=[]
 spans=artifact.get('literal_link_excerpts')
 if not isinstance(spans,list) or not spans:raise PipelineError('No actual description link spans')
 for span in spans:
  a,b=span.get('start'),span.get('end');quote=span.get('quote')
  if type(a)is not int or type(b)is not int or not 0<=a<b<=len(text) or text[a:b]!=quote:raise PipelineError('Description link span changed')
  found=re.findall(r'https://[^\s<>]+',quote)
  if not found:raise PipelineError('Description span contains no HTTPS link')
  for url in found:
   https_url(url)
   if url not in urls:urls.append(url)
   try:official_url(url)
   except PipelineError:continue
   if url not in official:official.append(url)
 # Only link-presence statements are mechanically admitted. No payout, eligibility,
 # application completeness, liveness or future platform placement is established.
 m=re.fullmatch(r'(?:(?P<single>(?:The )?(?:official )?link) is|(?P<plural>(?:The )?links) are) in the description(?P<below> below)?[.!]?',narration.strip(),re.I)
 if not m:raise PipelineError('CTA exceeds the narrow verified description-link presence statement')
 if m.group('plural') and len(urls)<2:raise PipelineError('Plural CTA needs at least two distinct actual description links')
 if re.search(r'\bofficial\b',narration,re.I) and not official:raise PipelineError('Official-link CTA has no well-formed saved government URL')
 decision=(model_review or {}).get('decision')
 return {'rule':VERSION,'decision':'VERIFIED_PROGRAM_LINK_PRESENCE_ONLY','claim_keys':['cta'],'text_sha256':artifact['text_sha256'],'fact_version':artifact['fact_version'],'literal_link_excerpts':spans,'urls':urls,'official_saved_urls':official,'model_verdict_unverified':decision,'model_disagreement':decision is not None and decision!='supported','model_reason_unmodified':(model_review or {}).get('reason_ru'),'layout_review_required':bool(m.group('below')),'source_entailment_verified':False,'liveness_checked':False,'publication_authorized':False}
