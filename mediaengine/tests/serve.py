"""Run the app's real Flask server for screenshots/smoke checks: python tests/serve.py [port]"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from archivist.web import create_app  # noqa: E402

create_app().run(host="127.0.0.1", port=int(sys.argv[1]) if len(sys.argv) > 1 else 8765, threaded=True, use_reloader=False)
