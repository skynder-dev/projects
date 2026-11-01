"""Offline candidate: source-attributed monetary utterances, never buyer verification."""
import re,hashlib
AMOUNT=r'(?:US\$\s*\d+(?:[.,]\d+)*|(?:USD|EUR|GBP|RUB|BZD)\s*\d+(?:[.,]\d+)*|[$€£]\s*\d+(?:[.,]\d+)*|\d+(?:[.,]\d+)*\s*(?:USD|EUR|GBP|RUB|BZD|dollars?|euros?|pounds?|rubles?)\b)'
QUAL=r'(?:(?:like|about|around|roughly|approximately)\s+)*(?:(?:less\s+than|up\s+to|at\s+most|under)\s+|[<≤]\s*)?'
ACTUAL=re.compile(r'\b(?:I|we)\s+(?:currently\s+|already\s+)?(?:pay|paid|spend|spent)\s+'+QUAL+AMOUNT,re.I)
INTENT=re.compile(r"\b(?:I|we)(?:['’]d\s+like\s+to\s+|\s+would\s+like\s+to\s+|\s+(?:would|will|can|am\s+willing\s+to|are\s+willing\s+to)\s+|\s+(?:want|plan|intend)\s+to\s+)(?:pay|spend|budget)\s+"+QUAL+AMOUNT,re.I)
MONEY_WORD=re.compile(r'\b(?:pay|paid|payment|fee|fees|charge|price|purchase|buy|budget|cost)\b',re.I)
def segment(text,start,end):
 # Sentence boundaries only at punctuation followed by whitespace/end; decimal points stay intact.
 left=0;right=len(text)
 for match in re.finditer(r'[.!?](?=\s|$)',text):
  if match.end()<=start:left=match.end()
  elif match.end()>=end:right=match.end();break
 return left,right,text[left:right]
def extract(text,source,eid,field,url,observed_at):
 if not isinstance(text,str):raise TypeError('Exact saved normalized text required')
 digest=hashlib.sha256(text.encode()).hexdigest();events=[];occupied=[]
 def add(kind,start,end,reason,qualifier=None):
  literal=text[start:end];amounts=[m.group() for m in re.finditer(AMOUNT,literal,re.I)]
  ctx_start,ctx_end,ctx=segment(text,start,end)
  event={'category':kind,'source':source,'evidence_id':eid,'source_field':field,'start':start,'end':end,'literal':literal,'context_start':ctx_start,'context_end':ctx_end,'context_literal':ctx,'source_field_sha256':digest,'source_url':url,'observed_at':observed_at,'amount_expressions_as_written':amounts,'amount_normalized':None,'currency_inferred':False,'qualifier':qualifier,'basis':reason,'epistemic_status':'attributed_utterance_not_independently_verified','actual_transaction_verified':False,'buyer_verified':False,'budget_authority_verified':False,'payment_for_our_solution':None,'demand_verified':False};events.append(event);occupied.append((start,end))
 for kind,pattern in [('budget_intent',INTENT),('actual_spent',ACTUAL)]:
  for match in pattern.finditer(text):
   if any(a<=match.start()<b for a,b in occupied):continue
   left,right,clause=segment(text,match.start(),match.end());prefix=text[left:match.start()].lower();ending=text[match.end():right]
   amount=''.join(re.findall(r'\d+',match.group()))
   if not any(ch in '123456789' for ch in amount):continue
   if re.search(r"\b(?:not|never|don't|won't|wouldn't|didn't)\b",prefix):continue
   if re.search(r'\b(?:said|says|wrote|writes|quoted|quote|claims|reported|for example|for instance|imagine|suppose)\b',prefix):
    add('third_party',match.start(),match.end(),'Quoted/example context prevents attribution as the source author actual spending.');continue
   if kind=='actual_spent' and (clause.rstrip().endswith('?') or re.search(r'\bif\b',clause,re.I) or re.search(r'\b(?:whether|did|will|would|can|should|must)\b',prefix)):
    add('question',match.start(),match.end(),'Question/conditional context, not an assertion of actual payment.');continue
   bound='upper_bound_not_actual_amount' if re.search(r'less\s+than|up\s+to|at\s+most|under|[<≤]',match.group(),re.I) else 'as_written_no_normalization'
   add(kind,match.start(),match.end(),'First-person '+('prospective willingness/desired spending, not purchase.' if kind=='budget_intent' else 'claimed current/past spending, not a verified transaction.'),bound)
 # Distinct non-first-person/question mentions retain their own complete clause context.
 for match in MONEY_WORD.finditer(text):
  if re.match(r'pay\s+(?:attention|respect|tribute)\b',text[match.start():],re.I):continue
  if match.group().lower()=='buy' and text[max(0,match.start()-5):match.start()].lower().endswith('best '):continue
  if any(a<=match.start()<b for a,b in occupied):continue
  left,right,clause=segment(text,match.start(),match.end())
  if any(a==left and b==right for a,b in occupied):continue
  if clause.rstrip().endswith('?') or re.search(r'\bassume\b',clause,re.I):add('question',left,right,'Financial question/hypothetical, not actual expense or stated author budget.')
  elif re.search(r'\b(?:people|they|them|company|someone|others|blogs|passenger|customers)\b',clause,re.I):add('third_party',left,right,'Other people/provider-policy/hoped-for revenue mention, not author actual spending.')
  # Unclassified mentions remain unclassified; no forced monetary signal.
 for event in events:
  assert text[event['start']:event['end']]==event['literal']
 return {'schema':'reveng-spending-utterance-candidate-v1','events':sorted(events,key=lambda e:(e['start'],e['end'],e['category'])),'classification_scope':'Local linguistic hints only; even actual_spent means author claim, not independently verified transaction. Context/manual attribution required.','model_calls':0,'network_calls':0,'automatic_admission':False}
