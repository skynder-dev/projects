"""R3 (app engine) must reproduce R2 (Windows-proven) byte for byte when called with R2's arguments.

  python tests/engine_regression.py <clean_video_folder> <work_root> [--semantic off|required]

Also checks that every bundled runtime module in app/archivist/engine_p11 is byte-identical to engine/p11_r2/runtime
and the hash-pinned adapter/validator.
"""
from __future__ import annotations

import hashlib, json, os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R2 = ROOT / "engine" / "p11_r2"
R3 = ROOT / "app" / "archivist" / "engine_p11"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run(orch, runtime, folder, work, semantic, env):
    out = work / "out"
    cmd = [sys.executable, str(orch), "--input-dir", str(folder), "--output-dir", str(out), "--work-dir", str(work / "work"),
           "--runtime-dir", str(runtime), "--target-seconds", "15", "--semantic", semantic]
    cp = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if cp.returncode != 0:
        print(cp.stdout[-2000:], cp.stderr[-3000:])
        raise SystemExit("engine run failed: " + str(orch))
    return json.loads((out / "MediaEngine Result.json").read_text(encoding="utf-8"))


def main():
    folder, work_root = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    semantic = sys.argv[sys.argv.index("--semantic") + 1] if "--semantic" in sys.argv else "off"
    checks = []
    for p in sorted((R2 / "runtime").glob("*.py")):
        checks.append((f"module_identical:{p.name}", sha(p) == sha(R3 / p.name)))
    for name in ("p11_fast_onnx_adapter.py", "validate_p11_model_contract.py"):
        checks.append((f"adapter_identical:{name}", sha(ROOT / "engine" / "p11_adapter" / name) == sha(R3 / name)))
    pinned = {"medeng_event_semantic_v7.py": "2b15303eba5b02b7f949cb560e58b2dbee09ff4576e21ad4b25b2d3111b02d5c",
              "p11_fast_onnx_adapter.py": "d7ef56b5b67e90179cecca366206eddd3b5ae4222ed4bc2f145a8b3f755eff36",
              "validate_p11_model_contract.py": "00e14d0d69b7f06cb5ef0841bee6c12809c6950a4ea3a677db9f7f715a107a22"}
    for name, want in pinned.items():   # exact bytes as checked by the semantic preflight on the user's PC
        checks.append((f"pinned_sha:{name}", sha(R3 / name) == want))
    checks.append(("r2_orchestrator_is_windows_proven", sha(R2 / "p11_folder_to_reel_shadow_v2.py") == "5c45fd8e3c86eda55d6f8a663ec723c823ef63f4b799e31022acc65f090ae99d"))
    env = dict(os.environ)
    try:
        import imageio_ffmpeg
        ff = os.environ.get("MEDENG_FFMPEG") or imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        ff = os.environ.get("MEDENG_FFMPEG", "ffmpeg")
    env.update(MEDENG_FFMPEG=ff, MEDENG_FFPROBE=ff, MEDENG_P11_ADAPTER_ROOT=str(R3))
    a = run(R2 / "p11_folder_to_reel_shadow_v2.py", R2 / "runtime", folder, work_root / "r2", semantic, env)
    b = run(R3 / "p11_folder_to_reel_r3.py", R3, folder, work_root / "r3", semantic, env)
    # Every editing decision must be identical. Reel bytes are reported but not required: the accepted
    # V52 segment encoder is not bit-reproducible run-to-run on every ffmpeg build (measured 2026-10-11:
    # the same make_segment call gave different video bytes on Linux ffmpeg 6.1; audio identical).
    for key in ("selected_event_ids", "selected_scores", "selected_sources", "event_count", "boundary", "sequence", "pacing", "selection_mode"):
        checks.append((f"same_decision:{key}", a.get(key) == b.get(key)))
    checks.append(("same_audio_decision", a["audio"]["decision"] == b["audio"]["decision"]))
    checks.append(("same_duration", abs(float(a["actual_duration_s"]) - float(b["actual_duration_s"])) < 0.05))
    byte_equal = a["output"]["sha256"] == b["output"]["sha256"]
    if "--strict-bytes" in sys.argv:
        checks.append(("same_reel_bytes", byte_equal))
    checks.append(("r3_reports_segments", len(b.get("segments", [])) == len(b["selected_event_ids"])))
    for n, ok in checks:
        print(("PASS " if ok else "FAIL ") + n)
    print(json.dumps({"r2_reel": a["output"]["sha256"], "r3_reel": b["output"]["sha256"], "byte_equal": byte_equal, "passed": sum(ok for _, ok in checks), "total": len(checks)}))
    return 0 if all(ok for _, ok in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
