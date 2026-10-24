"""Run only canonical offline Social concept-core tests in owned temporary space."""
from pathlib import Path
import importlib
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOCIAL = ROOT / 'social'
sys.dont_write_bytecode = True
sys.path.insert(0, str(SOCIAL))

def offline_only(event, args):
    if event in {'socket.connect', 'socket.connect_ex', 'socket.bind', 'subprocess.Popen', 'os.system', 'os.posix_spawn', 'os.exec', 'os.spawn'}:
        raise RuntimeError('Offline concept-core suite forbids external/native execution: ' + event)

sys.addaudithook(offline_only)
with tempfile.TemporaryDirectory(prefix='social-concept-core-') as owned:
    old = tempfile.tempdir
    tempfile.tempdir = owned
    try:
        module = importlib.import_module('tests.test_concept_offline')
        for name, imported in list(sys.modules.items()):
            if name == 'socialreel' or name.startswith('socialreel.'):
                if not Path(imported.__file__).resolve().is_relative_to(SOCIAL / 'socialreel'):
                    raise RuntimeError('Concept test imported non-canonical source: ' + name)
        suite = unittest.defaultTestLoader.loadTestsFromModule(module)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    finally:
        tempfile.tempdir = old
raise SystemExit(0 if result.wasSuccessful() else 1)
