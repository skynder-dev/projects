import unittest,copy,time
from datetime import datetime,timezone,timedelta
import commercial_review as c
def row(url='https://example.org/1',title='Email activation spam delivery',author='a'):
 return {'url':url,'title':title,'excerpt':'Email activation spam delivery issue','source':'hackernews','kind':'public_ask_post','evidence_id':'E1','observed_at':datetime.now(timezone.utc).isoformat(),'author_id':author}
def card(rows):return {'title':'Fixture','buyer':'Hypothetical owner','validation_step':'Validate the workflow with permission','observed_basis':rows,'market_category':'email_delivery'}
class Tests(unittest.TestCase):
 def test_boilerplate_is_not_problem_repetition(self):
  a=row(title='Broken checkout screen');b=row('https://example.org/2','Changed menu layout');a.update(kind='public_topic_title',excerpt='Observed support-topic title; underlying post not fetched');b.update(kind='public_topic_title',excerpt=a['excerpt']);r=c.assess(card([a,b]),[]);self.assertEqual(r['corroboration']['lexical_repetition'],[])
 def test_package_listing_is_not_customer_problem(self):
  a=row();a['kind']='package_listing_not_demand';r=c.assess(card([a]),[]);self.assertEqual(r['evidence_status'],'no_observed_problem_report');self.assertEqual(r['demand_indicators'],[])
 def test_url_tracking_dedupe(self):
  a=row();b=dict(a,url='https://example.org/1?utm_source=test#frag');u,d=c.deduplicate([a,b]);self.assertEqual(len(u),1);self.assertEqual(len(d),1)
 def test_syndicated_copy_not_independent(self):
  a=row();b=dict(a,url='https://another.example/1');u,d=c.deduplicate([a,b]);self.assertEqual(len(u),2);self.assertTrue(any('possible_duplicate_of'in x for x in d));self.assertEqual(c.assess(card([a,b]),[])['corroboration']['independence'],'not_established')
 def test_single_question_no_buyer_no_income(self):
  r=c.assess(card([row()]),[]);self.assertEqual(r['evidence_status'],'single_report_research_note');self.assertIsNone(r['buyer']['payment_evidence']);self.assertIsNone(r['income_score'])
 def test_repetition_is_not_market_proof(self):
  a=row();b=row('https://example.org/2','Activation email spam report','b');r=c.assess(card([a,b]),[]);self.assertTrue(r['corroboration']['lexical_repetition']);self.assertEqual(len(r['corroboration']['publishers']),1);self.assertTrue(r['commercial_confidence'].startswith('low'))
 def test_no_independence_from_missing_authors(self):
  a=row(author=None);b=row('https://example.org/2','Activation email spam issue',None);r=c.assess(card([a,b]),[]);self.assertEqual(r['corroboration']['independence'],'not_established')
 def test_stale_record_downgrades(self):
  a=row();a['observed_at']=(datetime.now(timezone.utc)-timedelta(days=2)).isoformat();r=c.assess(card([a]),[]);self.assertEqual(r['observation_freshness'][0]['status'],'stale_or_future')
 def test_price_currency_not_invented(self):
  s={'provider':'Fixture','category':'email_delivery','url':'https://example.org/pricing'};p=c.parse_prices('Pro $19 USD/month Billed monthly. Other $5 /month billed yearly',s,'now','sha');self.assertEqual(p[0]['currency'],'USD');self.assertEqual(p[1]['currency'],'unknown');self.assertIn('billed yearly',p[1]['billing_qualifiers_observed'])
 def test_expired_price_not_current(self):
  p={'category':'email_delivery','cache_expires':time.time()-1,'provider':'old'};self.assertEqual(c.assess(card([row()]),[p])['existing_solutions'],[])
 def test_wrong_model_scope_not_wrong_competitor(self):
  a=row();a['source']='wordpress';value=card([a]);value['market_category']='home_projects';c.resolve_scope(value);self.assertEqual(value['market_category'],'website_maintenance');self.assertEqual(value['model_market_category'],'home_projects')
 def test_stable_ids_and_revision_history(self):
  value=card([row()]);first=c.merge_ledger([], [value]);second=c.merge_ledger(first,[copy.deepcopy(value)]);self.assertEqual(len(second),1);self.assertEqual(len(second[0]['history']),0);v=copy.deepcopy(value);v['title']='Changed hypothesis';third=c.merge_ledger(second,[v]);self.assertEqual(len(third),1);self.assertEqual(len(third[0]['history']),1);self.assertNotEqual(third[0]['review_revision_hash'],first[0]['review_revision_hash'])
if __name__=='__main__':unittest.main(verbosity=2)
