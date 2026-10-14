"""The engine step of "Prepare AI+ for the whole Library" (app/archivist/engine_p11/p13_prepare_scout.py) with a
STAND-IN scorer instead of the AI+ model - for the app checks (library_flow_check, scale_library_check), which do
not have the model. Same arguments as the real step; everything but the model is the real code.
STANDIN_PREPARE_DELAY (seconds per call of the model) makes it slow enough to be paused by a reel build in a check.
"""
from __future__ import annotations

import argparse, json, os, sys, time
from pathlib import Path

import numpy as np


class StandInScorer:
    identity = {"profile": "STAND_IN_NOT_THE_MODEL"}
    vision = text = True

    def encode_images(self, images):
        delay = float(os.environ.get("STANDIN_PREPARE_DELAY") or 0)
        if delay:
            time.sleep(delay)
        a = np.asarray([[float(np.asarray(i.convert("RGB"), np.float32).std(axis=2).mean() / 255.0), 0.05] for i in images], np.float32)
        v = np.zeros((a.shape[0], 1024), np.float32); v[:, :2] = a
        return v / np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-9)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", required=True); ap.add_argument("--cache", required=True)
    ap.add_argument("--runtime-dir", required=True); ap.add_argument("--pe-dir", default="")
    ap.add_argument("--progress", default=""); ap.add_argument("--stop", default="")
    ap.add_argument("--skip-sha", default=""); ap.add_argument("--skipped", default="")
    a = ap.parse_args()
    runtime = Path(a.runtime_dir).resolve()
    sys.path.insert(0, str(runtime))
    import p13_prepare_scout as prep
    files = prep.parse_list(Path(a.list).read_text(encoding="utf-8-sig").splitlines())
    r = prep.prepare(files, Path(a.cache), runtime, StandInScorer, Path(a.progress) if a.progress else None,
                     Path(a.stop) if a.stop else None, os.environ.get("MEDENG_FFMPEG", "ffmpeg"), os.environ.get("MEDENG_FFPROBE", "ffprobe"),
                     Path(a.skip_sha) if a.skip_sha else None, Path(a.skipped) if a.skipped else None)
    print(json.dumps({k: v for k, v in r.items() if k != "skipped"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
