"""Atomic concept-only JSON storage; no runtime or default output directory."""
import os,tempfile
from .common import stable_json,sha256_bytes
from pathlib import Path

def write_json(p: Path, obj) -> str:
    """Write deterministic JSON and return its sha256."""
    p.parent.mkdir(parents=True, exist_ok=True)
    data = stable_json(obj).encode("utf-8")
    atomic_bytes(p, data)
    return sha256_bytes(data)

def atomic_bytes(path, data):
    """Readers see the previous complete file or the next complete file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="." + path.name + ".", suffix=".partial", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        # Windows readers may briefly deny DELETE sharing on the old JSON file.
        # Retry only known sharing/access races, with a bounded1.26s wait; never bypass ACLs.
        import time
        for attempt,delay in enumerate((.02,.04,.08,.16,.32,.64,0)):
            try:os.replace(name,path);break
            except PermissionError as error:
                if os.name!='nt' or getattr(error,'winerror',None) not in (5,32,33) or delay==0:raise
                time.sleep(delay)
    finally:
        if os.path.exists(name):
            os.unlink(name)
