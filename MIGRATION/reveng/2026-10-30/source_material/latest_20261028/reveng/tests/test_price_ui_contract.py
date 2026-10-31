"""Python vector semantics and static native integration, NOT C# execution or GUI QA."""
from pathlib import Path
import argparse,json,sys,unittest

p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);a=p.parse_args()
SOURCE=a.source.resolve();sys.path.insert(0,str(SOURCE));sys.dont_write_bytecode=True
import price_experiments
VECTORS=json.loads(Path(__file__).with_name('price_ui_vectors.json').read_text(encoding='utf-8'))['cases']

class PriceUIContract(unittest.TestCase):
 def test_shared_vectors_match_actual_python_semantics(self):
  for case in VECTORS:
   with self.subTest(case=case['name']):
    candidate=case['candidate'];before=json.dumps(candidate,sort_keys=True)
    result=price_experiments.projection(candidate.get('price_experiment'))
    self.assertEqual('absent' if result is None else result['status'],case['expected_status'])
    if case['expected_status']=='proposed_unverified':
     self.assertIn(case['expected_display'].casefold(),result['label'].casefold())
     self.assertEqual('Zero means a proposed free test.' in result['label'],case['free_test'])
     self.assertFalse(result['execution_authorized']);self.assertIsNone(result['payment_evidence'])
    self.assertEqual(before,json.dumps(candidate,sort_keys=True))

 def test_real_main_card_calls_shared_native_formatter(self):
  text=(SOURCE/'RevEngLocalResearch.cs').read_text(encoding='utf-8')
  method=text.split('void RenderCard(Dictionary<string,object> c)',1)[1].split('static void AppendBuyer(',1)[0]
  self.assertEqual(method.count('PriceExperimentPresentation.Append(b,c);'),1)
  self.assertIn('detail.Text=b.ToString();',method)

 def test_real_compare_uses_original_verified_card_and_shared_formatter(self):
  text=(SOURCE/'EvidenceComparison.cs').read_text(encoding='utf-8')
  method=text.split('string Describe(Row row)',1)[1].split('void ShowPair()',1)[0]
  self.assertIn('var c=row.Original;',method)
  self.assertEqual(method.count('PriceExperimentPresentation.Append(b,c);'),1)
  self.assertIn('Original=original[key]',text)
  self.assertIn('ltext.Text=Describe(a);rtext.Text=Describe(b);',text)

if __name__=='__main__':unittest.main(argv=[sys.argv[0]],verbosity=2)
