"""Offline synthetic routing regressions: hints never prove relevance or demand."""
from pathlib import Path
import argparse,ast,copy,hashlib,json,os,sys,unittest
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',required=True,type=Path);args=parser.parse_args()
SOURCE=args.source.resolve();sys.dont_write_bytecode=True;sys.path.insert(0,str(SOURCE))
def inventory():return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCE.iterdir() if p.suffix in {'.py','.cs'}}
BEFORE=inventory()
def audit(event,args):
 if event.startswith('socket.') or event in {'subprocess.Popen','os.system','os.exec','os.posix_spawn','urllib.Request'}:raise PermissionError('No network/processes in task-routing tests')
 if event=='import' and str(args[0]).split('.')[0] in {'torch','transformers','onnxruntime','faster_whisper'}:raise PermissionError('No model imports')
 if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
  path=Path(os.fsdecode(args[0])).resolve();flags=args[2] or 0
  if (path==SOURCE or SOURCE in path.parents) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):raise PermissionError('Source writes forbidden')
sys.addaudithook(audit)
import source_rules as rules,research_tasks,direct_alternatives as direct,research_candidate_review as research,reveng_local_research as m
# candidate_queue has a Windows-only publication import. Execute its actual pure
# signature functions only; this is not a substitute for Windows queue tests.
queue_tree=ast.parse((SOURCE/'candidate_queue.py').read_text(encoding='utf-8-sig'))
queue_functions=[node for node in queue_tree.body if isinstance(node,ast.FunctionDef) and node.name in {'digest','signature'}]
if len(queue_functions)!=2:raise RuntimeError('Actual queue signature functions missing')
queue_namespace={'m':m,'json':json,'direct':direct,'source_rules':rules}
exec(compile(ast.Module(body=queue_functions,type_ignores=[]),'candidate_queue.py:pure-signature','exec'),queue_namespace)

def card(title,category='other',solution='SYNTHETIC unverified proposal; not a tested solution.'):
 return {'title':title,'solution_hypothesis':solution,'market_category':category,'observed_basis':[],'candidate_id':'SYNTHETIC','research_id':'SYNTHETIC'}
def source(title,url='https://wordpress.org/support/topic/synthetic/',kind='public_topic_title',provider='wordpress'):
 return {'title':title,'url':url,'kind':kind,'source':provider,'evidence_id':'SYN1'}

class RoutingTests(unittest.TestCase):
 def test_category_only_never_dispatches_specific_documents(self):
  for title,category in [('SYNTHETIC visa appointment reminder','travel_operations'),('SYNTHETIC Firefox screen-reader accessibility','browser_compatibility'),('SYNTHETIC shared email inbox ownership','email_delivery')]:
   with self.subTest(title=title):
    c=card(title,category);self.assertIsNone(rules.task_for(c));route=rules.routing_review(c)
    self.assertEqual(route['status'],'unmapped_needs_discovery');self.assertEqual(route['category_hint'],category);self.assertFalse(route['category_selects_documents']);self.assertFalse(route['automatic_admission'])
 def test_generic_product_words_are_not_specific_task_identity(self):
  for title in ['SYNTHETIC Elementor licensing audit','SYNTHETIC WordPress invoice archive','SYNTHETIC Safari accessibility repair','SYNTHETIC Wikipedia bibliography list','SYNTHETIC Википедия список литературы','SYNTHETIC package deliverability report']:
   with self.subTest(title=title):self.assertIsNone(rules.task_for(card(title)))
 def test_specific_document_scopes_still_route_as_unverified_hints(self):
  cases={'SYNTHETIC second checked bag charges':'baggage_allowance_rules','SYNTHETIC Safari YouTube container debugging':'safari_embed_debug','SYNTHETIC email deliverability and spam checks':'transactional_delivery_testing','SYNTHETIC Elementor to native blocks':'elementor_block_conversion','SYNTHETIC WordPress critical error':'wordpress_support_templates','SYNTHETIC Wikipedia watchlist to reading list':'wikipedia_watchlist_migration','SYNTHETIC Safari YouTube repair tool':'safari_embed_repair'}
  for title,expected in cases.items():
   with self.subTest(title=title):
    c=card(title);self.assertEqual(rules.task_for(c),expected);self.assertEqual(rules.routing_review(c)['task_fit'],'NOT_VERIFIED')
 def test_exact_saved_cod_and_baggage_and_elementor_scopes_remain(self):
  for title,expected in [('SYNTHETIC WooCommerce COD configuration','woocommerce_cod_checkout'),('SYNTHETIC second checked bag fee','baggage_allowance_rules'),('SYNTHETIC Elementor to block editor','elementor_block_conversion')]:
   c=card('SYNTHETIC unrelated proposal','other');c['observed_basis']=[source(title)];self.assertEqual(rules.task_for(c),expected)
 def test_saved_source_hint_precedes_unverified_model_category(self):
  c=card('SYNTHETIC visa appointment','travel_operations');c['observed_basis']=[source('SYNTHETIC Safari YouTube playback issue')]
  self.assertEqual(rules.task_for(c),'safari_embed_debug');self.assertEqual(rules.routing_review(c)['origin'],'saved_source_words')
 def test_ambiguous_sources_do_not_fall_back_to_category_or_proposal(self):
  c=card('SYNTHETIC Safari YouTube repair','browser_compatibility');c['observed_basis']=[source('SYNTHETIC second checked bag issue'),source('SYNTHETIC Safari YouTube issue')]
  self.assertIsNone(rules.task_for(c));self.assertEqual(rules.routing_review(c)['status'],'ambiguous_needs_task_review')
 def test_ambiguous_proposal_scopes_are_not_first_match_wins(self):
  c=card('SYNTHETIC Wikipedia watchlist to reading list and Safari YouTube repair')
  self.assertIsNone(research_tasks.task(c));self.assertIsNone(rules.task_for(c));self.assertEqual(len(rules.routing_review(c)['hint_tasks']),2)
 def test_unmapped_projection_requests_discovery_not_absence(self):
  c=card('SYNTHETIC Firefox accessibility','browser_compatibility');out=direct.for_task(None,[],c)
  self.assertEqual(out['status'],'review_required');self.assertEqual(out['document_collection_status'],'not_evaluated_no_document_scope');self.assertEqual(out['routing_review']['status'],'unmapped_needs_discovery')
  self.assertFalse(out['active_candidate_admission']);self.assertTrue(out['question_task_binding']['needed_evidence']);self.assertIn('not evidence that alternatives are absent',out['routing_review']['next_step'])
 def test_research_hostname_only_no_longer_selects_wordpress_troubleshooting(self):
  c=card('SYNTHETIC');c['observed_basis']=[source('SYNTHETIC invoice template licensing')]
  out=research.source_hint_routes(c);self.assertEqual(out['tasks'],[]);self.assertEqual(out['discovery_status'],'unmapped_needs_discovery')
  c['observed_basis']=[source('SYNTHETIC critical error after update')];out=research.source_hint_routes(c);self.assertEqual(out['tasks'],['wordpress_support_templates']);self.assertEqual(out['mode'],'COLLECTION_HINT_ONLY')
 def test_research_wiki_and_safari_scopes_are_specific_not_any_list_or_iframe(self):
  for title in ['SYNTHETIC Wikipedia bibliography list','SYNTHETIC Safari iframe CSS layout']:
   c=card(title);c['observed_basis']=[source(title,'https://softwarerecs.stackexchange.com/questions/123/synthetic',provider='softwarerecs')];self.assertEqual(research.source_hint_routes(c)['tasks'],[])
  c['observed_basis']=[source('SYNTHETIC Wikipedia watchlist to reading list','https://softwarerecs.stackexchange.com/questions/123/synthetic',provider='softwarerecs')];self.assertEqual(research.source_hint_routes(c)['tasks'],['wikipedia_watchlist_migration'])
 def test_changed_routing_policy_invalidates_both_saved_review_paths(self):
  from unittest.mock import patch
  c=card('SYNTHETIC visa reminders','travel_operations');before=(queue_namespace['signature'](c),research.signature(c))
  with patch.object(direct,'REVIEW_POLICY','SYNTHETIC_OLD_POLICY'),patch.object(rules,'ROUTING_POLICY','SYNTHETIC_OLD_POLICY'):
   old=(queue_namespace['signature'](c),research.signature(c))
  self.assertNotEqual(before[0],old[0]);self.assertNotEqual(before[1],old[1])
  self.assertFalse(direct.review_cache_matches({'direct_schema':direct.SCHEMA}));self.assertFalse(direct.review_cache_matches({'direct_schema':direct.SCHEMA,'direct_review_policy':'old'}));self.assertTrue(direct.review_cache_matches({'direct_schema':direct.SCHEMA,'direct_review_policy':direct.REVIEW_POLICY}))
 def test_routing_does_not_mutate_inputs_or_approve_task_fit(self):
  c=card('SYNTHETIC visa appointments','travel_operations');before=copy.deepcopy(c);rules.routing_review(c);direct.for_task(None,[],c);research.source_hint_routes(c);self.assertEqual(c,before)

def tearDownModule():
 if inventory()!=BEFORE:raise AssertionError('Source bytes changed')
if __name__=='__main__':unittest.main(argv=[sys.argv[0]],verbosity=2)
