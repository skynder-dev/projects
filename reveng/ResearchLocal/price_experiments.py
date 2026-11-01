"""Optional proposed test-offer values, never observed prices or payment evidence."""
import copy,json
import json_contract

def schema():
 return {'description':'Optional proposed test offer, never an observed price, payment, revenue or demand claim. Omit or use null when amount/currency is unknown. Zero means a proposed free test, not payment evidence. Currency is a three-letter label, not verified ISO support.',
  'oneOf':[{'type':'null'},{'type':'object','properties':{'status':{'const':'proposed_unverified'},'amount':{'type':'number','minimum':0},'currency':{'type':'string','minLength':3,'maxLength':3,'pattern':'^[A-Z]{3}$'}},'required':['status','amount','currency'],'additionalProperties':False}]}

def projection(value):
 if value is None:return None
 try:
  json_contract.validate_node(schema(),value)
  amount=json.dumps(value['amount'],allow_nan=False)
  if len(amount)>64:raise ValueError('Amount display exceeds bounded length')
 except (ValueError,TypeError,OverflowError):
  return {'status':'malformed_untrusted_offer','label':'Proposed offer data is malformed or too large; amount/currency withheld pending review.','payment_evidence':None,'execution_authorized':False}
 return {'status':'proposed_unverified','amount':value['amount'],'currency_label':value['currency'],'currency_validation':'THREE_LETTER_SYNTAX_ONLY_NOT_VERIFIED_ISO','label':'Proposed UNVERIFIED test offer: '+amount+' '+value['currency']+' (unverified currency label). '+('Zero means a proposed free test. ' if value['amount']==0 else '')+'Not observed price, payment, revenue or demand; no action authorized.','payment_evidence':None,'execution_authorized':False}

def comparison_fields(card):
 value=projection(card.get('price_experiment'))
 return {'proposed_price_experiment':value} if value is not None else {}

def preview_fields(row):
 saved=row.get('proposed_price_experiment')
 if saved is None:return {}
 # Reconstruct rather than trusting a caller-supplied label/status/amount pair.
 value=projection({'status':saved.get('status'),'amount':saved.get('amount'),'currency':saved.get('currency_label')}) if isinstance(saved,dict) else projection(saved)
 return {'proposed_price_experiment':value}

def csv_uncertainties(card):
 existing=card.get('missing_evidence',[]);value=projection(card.get('price_experiment'))
 if value is None:return existing
 return copy.deepcopy(existing)+[value['label']] if isinstance(existing,list) else [existing,value['label']]
