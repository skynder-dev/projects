"""Bounded generated-schema vocabulary, strict JSON; no semantic approval."""
import json,re,math
KEYS={'type','properties','required','additionalProperties','items','prefixItems','minItems','maxItems','uniqueItems','minLength','maxLength','minimum','maximum','enum','const','pattern','oneOf','anyOf','allOf','$schema','title','description','$comment'}
def strict_loads(raw):
 def pairs(values):
  out={}
  for k,v in values:
   if k in out:raise ValueError('Duplicate JSON key: '+k)
   out[k]=v
  return out
 def invalid(value):raise ValueError('Non-JSON numeric constant: '+value)
 return json.loads(raw,object_pairs_hook=pairs,parse_constant=invalid)
def equal(a,b):
 if isinstance(a,bool) or isinstance(b,bool):return type(a)is type(b) and a==b
 if isinstance(a,(int,float)) and isinstance(b,(int,float)):return a==b
 if type(a)is not type(b):return False
 if isinstance(a,list):return len(a)==len(b) and all(equal(x,y) for x,y in zip(a,b))
 if isinstance(a,dict):return a.keys()==b.keys() and all(equal(a[k],b[k]) for k in a)
 return a==b
def check_schema(s):
 if not isinstance(s,dict) or set(s)-KEYS:raise ValueError('Unsupported generated schema keyword; refuse unchecked response')
 for key in ['properties']:
  for child in s.get(key,{}).values():check_schema(child)
 for key in ['items','additionalProperties']:
  if isinstance(s.get(key),dict):check_schema(s[key])
 for key in ['prefixItems','oneOf','anyOf','allOf']:
  for child in s.get(key,[]):check_schema(child)
 if 'pattern'in s:re.compile(s['pattern'])
def validate_node(s,v,path='$'):
 check_schema(s)
 def fail(reason):raise ValueError('JSON contract '+path+': '+reason)
 for key in ['oneOf','anyOf','allOf']:
  if key not in s:continue
  matches=0
  for branch in s[key]:
   try:validate_node(branch,v,path);matches+=1
   except ValueError:pass
  if key=='oneOf' and matches!=1 or key=='anyOf' and not matches or key=='allOf' and matches!=len(s[key]):fail(key+' alternatives mismatch')
 if 'const'in s and not equal(v,s['const']):fail('constant mismatch')
 if 'enum'in s and not any(equal(v,x) for x in s['enum']):fail('enum mismatch')
 def is_type(t):
  return {'object':lambda:isinstance(v,dict),'array':lambda:isinstance(v,list),'string':lambda:isinstance(v,str),'boolean':lambda:type(v)is bool,'null':lambda:v is None,'integer':lambda:type(v)is int or type(v)is float and math.isfinite(v) and v.is_integer(),'number':lambda:type(v)in (int,float) and (type(v)is int or math.isfinite(v))}[t]()
 if 'type'in s:
  types=s['type'] if isinstance(s['type'],list) else [s['type']]
  if not any(is_type(t) for t in types):fail('type mismatch')
 if isinstance(v,dict):
  properties=s.get('properties',{})
  if any(k not in v for k in s.get('required',[])):fail('missing required field')
  for k,x in v.items():
   if k in properties:validate_node(properties[k],x,path+'.'+k)
   elif s.get('additionalProperties')is False:fail('extra field '+k)
   elif isinstance(s.get('additionalProperties'),dict):validate_node(s['additionalProperties'],x,path+'.'+k)
 elif isinstance(v,list):
  if len(v)<s.get('minItems',0) or len(v)>s.get('maxItems',len(v)):fail('array length')
  if s.get('uniqueItems') and any(equal(x,y) for i,x in enumerate(v) for y in v[:i]):fail('duplicate array item')
  prefix=s.get('prefixItems',[])
  for i,x in enumerate(v):
   rule=prefix[i] if i<len(prefix) else s.get('items',{})
   if rule is False:fail('extra tuple item')
   if isinstance(rule,dict):validate_node(rule,x,path+'['+str(i)+']')
 elif isinstance(v,str):
  if not s.get('minLength',0)<=len(v)<=s.get('maxLength',len(v)):fail('string length')
  if 'pattern'in s and re.search(s['pattern'],v)is None:fail('string pattern/language')
  try:v.encode('utf-8',errors='strict')
  except UnicodeEncodeError:fail('invalid Unicode scalar')
 elif type(v)in (int,float):
  if type(v)is float and not math.isfinite(v) or v<s.get('minimum',v) or v>s.get('maximum',v):fail('numeric range')
