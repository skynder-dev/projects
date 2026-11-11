"""Observe model-library imports in the owned worker; never load a model."""
import sys
from pathlib import Path
from .common import write_json,utc_now
def install(path):
 path=Path(path);events=[];roots={"torch","kokoro","faster_whisper","ctranslate2","transformers","onnxruntime","llama_cpp","vllm"}
 write_json(path,{"scope":"Owned worker library-import observations, not GPU usage sampling","imports":events})
 def observe(event,args):
  if event=="import" and str(args[0]) in roots and not any(e["module"]==str(args[0]) for e in events):
   events.append({"module":str(args[0]),"at":utc_now().isoformat()});write_json(path,{"scope":"Owned worker library-import observations, not GPU usage sampling","imports":events})
 sys.addaudithook(observe)
