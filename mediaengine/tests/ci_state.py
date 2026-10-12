"""CI diagnostics: what a MediaEngine data folder says about running work (for a failed smoke step).

  python tests/ci_state.py <data root>
"""
import json, sqlite3, sys
from pathlib import Path

root = Path(sys.argv[1])
st = root / "data" / "update_status.json"
print("launcher status:", st.read_text(encoding="utf-8", errors="replace") if st.exists() else "(none)")
db = root / "data" / "archivist.db"
if db.exists():
    con = sqlite3.connect(str(db))
    for sql in ("SELECT id,status,stage,error,started_at,finished_at FROM ae_jobs ORDER BY id",
                "SELECT id,kind,status FROM jobs WHERE status IN ('running','queued') ORDER BY id"):
        try:
            print(sql.split(" FROM ")[1].split()[0] + ":", json.dumps(con.execute(sql).fetchall(), ensure_ascii=False))
        except Exception as exc:
            print("query failed:", exc)
