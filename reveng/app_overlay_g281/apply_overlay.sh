#!/bin/bash
# Apply the G281 overlay onto an extracted, frozen G280 package (RevEng_Working_REVA2_G280_WINDOWS_CLOSED).
# Usage: apply_overlay.sh /path/to/RevEng_Working_REVA2_G280_WINDOWS_CLOSED /path/to/new/G281_dir
set -euo pipefail
BASE="$1"; OUT="$2"; HERE="$(cd "$(dirname "$0")" && pwd)"
[ -f "$BASE/docs/REVA2_POST_G280_WINDOWS_CLOSURE_MANIFEST.json" ] || { echo "not a G280 closure package: $BASE" >&2; exit 2; }
[ ! -e "$OUT" ] || { echo "output exists: $OUT" >&2; exit 2; }
cp -a "$BASE" "$OUT"
python3 -I - "$OUT" "$HERE/files/docs/REVA2_G281_OVERLAY_MANIFEST.json" <<'PY'
import json, hashlib, sys
from pathlib import Path
out, ov = Path(sys.argv[1]), json.loads(Path(sys.argv[2]).read_text())
for m in ov['modified']:
    h = hashlib.sha256((out / m['path']).read_bytes()).hexdigest()
    if h != m['baselineSha256']: sys.exit(f"baseline file differs from frozen G280: {m['path']}")
print('baseline hashes of modified files verified')
PY
cp -a "$HERE/files/." "$OUT/"
python3 -I "$OUT/diagnostics/tests/verify_reva2_g281_overlay.py"
