"""Declarative capability evidence. Labels depend on matched rules, not candidate IDs."""
TASKS={
 'safari_embed_debug':{'required':['branded_safari','local_container','youtube_reproduction'],'role':'Web developer','remaining':['Actual branded Safari in the proposed local container','YouTube/media reproduction on matching OS/codecs']},
 'transactional_delivery_testing':{'required':['multi_domain_delivery','automated_testing','optimization'],'role':'Transactional email operator','remaining':['Real delivery across recipient domains, not a single test mailbox','Automation/API plan and activation-link workflow','Proven benefit of suggested text/link changes']},
 'elementor_block_conversion':{'required':['elementor_conversion','style_preservation'],'role':'WordPress site maintainer migrating from Elementor','remaining':['Elementor layout to native blocks conversion','Preservation of responsive styles/widgets and reversible migration']},
 'wordpress_support_templates':{'required':['editor_diagnosis','log_analysis'],'role':'WordPress site administrator','remaining':['Diagnosis of the actual editor failure','Automated log interpretation and reusable error-specific response']},
}
SOURCES={
 'playwright_browsers':{'provider':'Playwright official browser documentation','task':'safari_embed_debug','url':'https://playwright.dev/docs/browsers','rules':{'webkit_testing':r'Playwright can run tests on Chromium, WebKit and Firefox','not_branded_safari':r"Playwright doesn.t work with the branded version of Safari",'platform_codecs':r'available media codecs vary substantially between Linux, macOS and Windows'},'limits':['WebKit is not branded Safari; video codecs depend on OS','No local Safari container or YouTube reproduction tested; no software installed']},
 'mail_tester':{'provider':'mail-tester official public test page','task':'transactional_delivery_testing','url':'https://mail-tester.com/','rules':{'single_mailbox_test':r'Test the Spammyness of your Emails','manual_send':r'First, send your email to'},'limits':['A test mailbox is not evidence of multi-domain inbox placement','No email sent, account created or result retrieved; API plan, quotas and price unknown']},
 'wp_classic':{'provider':'WordPress Classic block documentation','task':'elementor_block_conversion','url':'https://wordpress.org/documentation/article/classic-block/','rules':{'classic_content_conversion':r'Selecting this option will convert the content to blocks','classic_scope':r'The Classic block looks just like the classic editor'},'limits':['Classic block conversion does not document Elementor layouts or style preservation','No migration or plugin installation performed']},
 'wp_troubleshooting':{'provider':'WordPress troubleshooting documentation','task':'wordpress_support_templates','url':'https://wordpress.org/documentation/article/faq-troubleshooting/','rules':{'manual_plugin_diagnosis':r'two methods available to deactivate all plugins','admin_access':r'can.t access the Administration Screens'},'limits':['Public general troubleshooting, not a verified fix for the source editor failure','No changes made to any WordPress site; support/hosting costs unknown']},
 'wp_debug':{'provider':'WordPress official debugging documentation','task':'wordpress_support_templates','url':'https://developer.wordpress.org/advanced-administration/debug/debug-wordpress/','rules':{'debug_logging':r'WP_DEBUG_LOG','developer_scope':r'PHP code|developers|debugging'},'limits':['Logging errors is not automated interpretation or proof of their cause','No debug settings enabled; logs may need operator review; no support tariff established']},
}
SOURCES.update({
 'mail_tester_api':{'provider':'mail-tester official JSON API documentation','task':'transactional_delivery_testing','url':'https://mail-tester.com/manager/api-documentation.html','rules':{'automated_testing':r'return a JSON object','optimization':r'the code, the score and our suggestions','link_checks':r'broken links we found'},'limits':['API describes spam/authentication/content/link checks of a received message','Does not establish placement at different destination providers; no endpoint invoked']},
 'mail_tester_price':{'provider':'mail-tester official account pricing','task':'transactional_delivery_testing','url':'https://mail-tester.com/manager/','rules':{'account_api_integration':r'Integrate mail-tester results in your own application either by using an iframe or our JSON API','monthly_quota_price':r'50 Tests / Month\s+\$10','tax_exclusion':r'Price \(excl\. VAT\)'},'limits':['50 monthly tests at the literal displayed $10, excluding VAT; currency code not established','Account features include JSON API integration, not multi-domain inbox placement','No account, subscription, test purchase or email sent']},
})
import research_tasks
TASKS.update(research_tasks.TASKS)
SOURCES.update(research_tasks.SOURCES)
import api_capability
TASKS.update(api_capability.TASKS)
SOURCES.update(api_capability.SOURCES)
def source_tasks(card):
 import re
 found=set()
 for row in card.get('observed_basis',[]):
  # Titles are observations of the reported issue, never evidence of its cause.
  text=(row.get('title','')+' '+(row.get('excerpt','')if row.get('kind')not in ['public_topic_title','public_question_title']else'')).lower()
  if 'woocommerce'in text and re.search(r'\b(?:cod|cash on delivery)\b',text):found.add('woocommerce_cod_checkout')
  if 'second checked bag'in text:found.add('baggage_allowance_rules')
  if 'safari'in text and 'youtube'in text:found.add('safari_embed_debug')
  if 'elementor'in text and 'block editor'in text:found.add('elementor_block_conversion')
  if 'deliverability'in text or 'email'in text and 'spam'in text:found.add('transactional_delivery_testing')
  if row.get('source')=='wordpress'and('critical error'in text or 'blank screen'in text):found.add('wordpress_support_templates')
 return found

def task_for(card):
 observed=source_tasks(card)
 if observed:return next(iter(observed))if len(observed)==1 else None
 specific=research_tasks.task(card)
 if specific:return specific
 text=(card.get('title','')+' '+card.get('solution_hypothesis','')).lower();category=card.get('market_category','')
 if 'elementor' in text:return 'elementor_block_conversion'
 if 'woocommerce' in text:return None
 if 'safari' in text or category=='browser_compatibility':return 'safari_embed_debug'
 if category=='email_delivery':return 'transactional_delivery_testing'
 if category=='travel_operations':return 'baggage_allowance_rules'
 if 'wordpress' in text:return 'wordpress_support_templates'
 return None

def question_task_binding(card,task,documents):
 import hashlib,json
 pin=lambda value:hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
 observed=source_tasks(card);refs=[]
 bindings=[]
 def require(requirement,pattern,scope):
  import re
  values=[(r,field,r.get(field,''))for r in card.get('observed_basis',[])for field in ['title','context_text','excerpt']if field!='excerpt'or r.get('kind')not in ['public_topic_title','public_question_title']]if scope=='question'else[(card,'solution_hypothesis',card.get('solution_hypothesis',''))]
  for row,field,text in values:
   match=re.search(pattern,text,re.I)
   if match:
    bindings.append({'requirement':requirement,'scope':scope,'field':field,'url':row.get('url'),'evidence_id':row.get('evidence_id'),'text_sha256':hashlib.sha256(text.encode()).hexdigest(),'start':match.start(),'end':match.end(),'quote':match.group(0),'meaning':'Exact input fragment; question report or unverified proposal, not a proven cause'});return True
  return False
 # Derive particulars only from the current input; category membership is not evidence.
 needed=[]
 button=require('Checkout type, gateways/extensions and reproduction of this reported payment-button text',r'Pay\s+Credit\s*/\s*Debit\s+Card','question')
 if button:needed.append('Evidence connecting this reported button text to a specific COD setting; no proof it is not a bug or that guides are absent')
 require('COD behavior and settings for the actual reported symptom; no button defect assumed',r'\b(?:COD|cash on delivery)\b','question')
 require('Exact ticket/operating-carrier and through-check/interline conditions for the stated second-bag question; once-versus-twice payment remains unverified',r'second checked bag','question')
 require('Actual Safari/OS versions and reproduction of the reported video failure',r'Safari','question')
 require('Documented branded Safari in the proposed local container; implementation and codecs remain unverified',r'container|контейнер','proposal')
 require('Measured inbox placement and actual activation-message context, beyond spam score',r'deliverability|activation emails|spam','question')
 require('Elementor-to-native-block layout/widget/style requirements and explicit conversion evidence',r'Elementor','question')
 require('Bodies and logs for each distinct reported failure; no shared cause, frequency or novice segment inferred',r'critical error|blank screen','question')
 needed+=list(dict.fromkeys(b['requirement']for b in bindings))
 if not needed:needed=['Exact reported task context and explicit documentary function match; specific settings and solution requirements are unknown']
 for row in card.get('observed_basis',[]):
  refs.append({'evidence_id':row.get('evidence_id'),'url':row.get('url'),'observed_at':row.get('observed_at'),'source_row_sha256':pin(row),'title':row.get('title'),'scope':'title_only'if row.get('kind')in ['public_topic_title','public_question_title']else row.get('content_scope','saved_excerpt_not_full_post'),'context_available':bool(row.get('body_available')),'context_text':row.get('context_text'),'context_text_sha256':row.get('context_text_sha256'),'saved_context_origin':row.get('saved_context_origin'),'field_reference':'Exact saved observation object; not a raw HTTP span'})
 docs=[{'source_url':d.get('source_url'),'response_sha256':d.get('response_sha256'),'record_sha256':pin(d),'facts':d.get('facts',[]),'documented_scope':d.get('function_scope'),'error':d.get('error'),'provenance_scope':'Saved parsed document record; no invented source offsets'}for d in documents]
 rejected=[]
 kinds={f.get('kind')for d in documents if not d.get('error')for f in d.get('facts',[])}
 if task=='woocommerce_cod_checkout'and'checkout_control'in kinds and button:rejected.append('Checkout payment-method Title setting is not proof of the cause or repair of the reported payment-button label.')
 profiles=[r.get('source_profile',{})for r in card.get('functional_comparisons',[])if r.get('source_profile')]
 functional_refs=[{'vendor':p.get('vendor'),'source_url':p.get('source_url'),'observed_at':p.get('observed_at'),'record_sha256':pin(p),'facts':p.get('facts',[]),'provenance_scope':'Saved function profile; not a complete document or raw response'}for p in profiles]
 if task=='baggage_allowance_rules'and any(p.get('vendor')=='TripIt Pro'and any(f.get('quote')=='Baggage Claim Info'for f in p.get('facts',[]))for p in profiles):rejected.append('TripIt Baggage Claim Info is not evidence of second checked-bag allowance/purchase or mixed-carrier payment coverage.')
 if 'not_branded_safari'in kinds:rejected.append('Playwright WebKit is explicitly not branded Safari.')
 if 'classic_content_conversion'in kinds:rejected.append('WordPress Classic content conversion is not Elementor layout/style conversion.')
 if 'single_mailbox_test'in kinds or 'automated_testing'in kinds:rejected.append('Single-mailbox spam checks/API responses are not multi-provider inbox placement.')
 if 'debug_logging'in kinds:rejected.append('WP_DEBUG_LOG records errors; it does not prove automatic cause analysis or one fix for distinct failures.')
 return {'status':'review_required','routed_task':task,'observed_source_tasks':sorted(observed),'source_task_scope':'Reported issue from exact saved input fields; diagnosis, generalized demand and proposed solution not entailed','question_references':refs,'document_references':docs,'functional_profile_references':functional_refs,'rejected_equivalences':rejected,'requirement_bindings':bindings,'needed_evidence':needed,'payment_evidence':None,'active_candidate_admission':False}
def parse(key,text,stamp,response_sha,schema):
 import re,time
 if key in api_capability.SOURCES:return api_capability.parse(key,text,stamp,response_sha,schema)
 spec=SOURCES[key];task=TASKS[spec['task']];text=' '.join(text.split());facts=[];remaining=25
 for capability,pattern in spec['rules'].items():
  found=re.search(pattern,text,re.I)
  if found and remaining:
   quote=' '.join(found.group(0).split()[:min(remaining,10)]);remaining-=len(quote.split());facts.append({'id':'D'+str(len(facts)+1),'kind':capability,'quote':quote})
 observed={f['kind'] for f in facts};required=set(task['required']);covered=sorted(required&observed)
 status='exact_task_alternative' if required<=observed else 'partial_alternative' if observed else 'not_found_in_checked_source'
 plan={'status':'unknown','name':'Public documentation/tool entry point','price_literal':None,'limits':spec['limits']+['No applicable paid/free tier, API quota or total cost inferred from page access']}
 if {'account_api_integration','monthly_quota_price','tax_exclusion'}<=observed:
  plan={'status':'observed','name':'Account: 50 Tests / Month','price_literal':'$10','currency':'unknown','billing':'monthly; excludes VAT','function_binding':'Account API integration explicitly listed on this pricing page','evidence_ids':[f['id'] for f in facts],'limits':spec['limits']}
 return {'schema':schema,'provider':spec['provider'],'task':spec['task'],'source_url':spec['url'],'observed_at':stamp,'response_sha256':response_sha,'expires':time.time()+86400,'facts':facts,'classification':status,'function_scope':'Observed capabilities: '+(', '.join(sorted(observed)) or 'none established'),'buyer_match':{'status':'scope_inference_not_verified_buyer' if facts else 'unknown','role':task['role'],'evidence_ids':[f['id'] for f in facts],'limitation':'Role inferred from documented workflow; actual operator, budget authority and buyer remain unverified'},'plan':plan,'covered':covered,'related_capabilities':sorted(observed-required),'unproven':[x for x in task['required'] if x not in observed]+task['remaining'],'payment_evidence':None,'paying_customer_status':'unknown','market_demand':'not established','interpretation':'Evidence-backed capability comparison. Related capability is not full target coverage; absent text is not proof that a product lacks the feature.'}
