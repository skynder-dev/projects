"""Runs tests/dress_check.py and, if it is still running after 20 minutes, prints where every thread is (then stops),
so a hang on a Windows runner can be seen (workflow mediaengine-probe).

  python tests/hang_probe.py <fixtures_dir> <work_dir> <out_json>
"""
import faulthandler, runpy, sys
from pathlib import Path

fx, work = sys.argv[1], sys.argv[2]
faulthandler.dump_traceback_later(1200, exit=True)
script = str(Path(__file__).with_name("dress_check.py"))
sys.argv = [script, fx, work]
runpy.run_path(script, run_name="__main__")
