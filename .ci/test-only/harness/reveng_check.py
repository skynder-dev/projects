from pathlib import Path
import sys,json,copy
root=Path(sys.argv[1]);sys.path.insert(0,str(root/'ResearchLocal'))
import commercial_review as c,wordpress_identity as w,source_context
card={'title':'Synthetic','buyer':'Test role','problem_hypothesis':'Question','solution_hypothesis':'Synthetic proposal','observed_basis':[],'risks':[],'functional_comparisons':[{'plan_evidence_source_profile':{'observed_at':'2026-01-01T00:00:00Z','response_sha256':'a'*64,'price_scope':{'trial':{'status':'unknown','value':None}}}}],'direct_alternatives':{'classification':'source_unavailable','error':'No offline cache','observed_at':'2026-01-01T00:00:00Z','expires':1}}
a=c.revision(card);b=copy.deepcopy(card);b['direct_alternatives'].update(observed_at='2026-01-02T00:00:00Z',expires=2);assert c.revision(b)==a
b['functional_comparisons'][0]['plan_evidence_source_profile']['price_scope']['trial']['value']=False;assert c.revision(b)!=a
url='https://wordpress.org/support/topic/synthetic/'
def page(body,title='Fixture | WordPress.org'):return ('<html><title>'+title+'</title><link rel="canonical" href="'+url+'"><div class="bbp-topic-content">'+body+'</div><div class="bbp-reply-content">Synthetic reply</div></html>').encode()
assert source_context.wordpress(page('Synthetic question'),url)['context_text']=='Synthetic question'
try:source_context.wordpress(page('Access denied. Why have I been blocked? Your request was blocked by our security service.','Access Denied | WordPress.org'),url)
except ValueError:pass
else:raise AssertionError('Denial admitted')
print('PASS RevEng028 functional revision / technical-clock stability / unknown-vs-false / real bs4 question-not-reply / denial')
