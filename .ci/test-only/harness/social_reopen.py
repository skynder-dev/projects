from pathlib import Path
import sys,os
from unittest.mock import patch
root=Path(sys.argv[1]);sys.path[:0]=[str(root),str(root/'app')];os.environ['SOCIAL_AI_HOME']=str(root/'fake-ai');os.environ['SOCIAL_RUNTIME_PATHS']=str(root/'missing-runtime-ci.json')
from socialreel.jobs import JobStore
from local_bridge import LocalBridge
with patch('socialreel.packages.verify_package',return_value={'pass':True,'errors':[]}),patch('socialreel.packages.source_freshness',return_value={'fresh':True,'reasons':[]}):
 value=LocalBridge(JobStore(root/'data/jobs')).get('/local/selection');assert value['selection']['job_id']=='1'*32 and value['owner_view']['language']=='ru'
print('PASS relocated backend reopened in a fresh interpreter with RU LocalBridge selection; media integrity stubbed')
