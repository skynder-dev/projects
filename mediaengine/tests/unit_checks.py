"""Small, fast checks of helper rules (no video work).

  python tests/unit_checks.py <work_dir>
"""
from __future__ import annotations

import os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    work = Path(sys.argv[1]).resolve()
    work.mkdir(parents=True, exist_ok=True)
    os.environ["ARCHIVIST_HOME"] = str(work / "home")
    sys.path.insert(0, str(ROOT / "app"))
    from archivist import auto_edit as ae
    import importlib.util
    spec = importlib.util.spec_from_file_location("launcher_v2", ROOT / "app" / "archivist" / "launcher_v2.py")
    L = importlib.util.module_from_spec(spec); spec.loader.exec_module(L)
    checks = []

    def check(name, ok, detail=None):
        checks.append(bool(ok))
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"))

    def raises(fn, *a):
        try:
            fn(*a)
            return False
        except ValueError:
            return True

    # times typed in the editor
    for raw, want in (("12.5", 12.5), ("12,5", 12.5), ("0:12.5", 12.5), ("1:05", 65.0), ("1:02:03", 3723.0), (" 7 ", 7.0), (3, 3.0)):
        check(f"parse_seconds {raw!r}", abs(ae.parse_seconds(raw) - want) < 1e-9, ae.parse_seconds(raw))
    for raw in ("", "abc", "-1", "nan", "inf", "1:70", "1::2", "1:2:3:4"):
        check(f"parse_seconds rejects {raw!r}", raises(ae.parse_seconds, raw))
    # Windows-safe export names
    for raw in ("CON", "con.mp4", "Trip: day/1?", "a" * 300, "name. . .", "  ", "COM1 - Social HD", "end." + "x" * 116 + "..."):
        n = ae.safe_filename(raw)
        bad = (not n or any(ch in n for ch in '<>:"/\\|?*') or n.endswith((".", " ")) or len(n) > 120
               or n.split(".")[0].strip().upper() in ae._WIN_RESERVED)
        check(f"safe_filename {raw[:20]!r}", not bad, n)
    # adaptive length never asks for more than the footage
    for total, want in ((9.3, 5), (28, 5), (30, 15), (89, 15), (90, 30), (600, 30)):
        check(f"recommend_length {total}", ae.recommend_length(total) == want, ae.recommend_length(total))
    # release ordering incl. pre-releases
    vs = ["3.12.42", "3.13.0-rc1", "3.13.0-rc2", "3.13.0", "3.13.1"]
    check("version_key orders pre-releases", sorted(vs, key=L.version_key) == vs)
    # friendly reasons for skipped files
    for code in ("PRIVATE", "NO_MOMENTS", "STATIC_VIDEO", "TOO_SHORT_FOR_ANALYSIS", "ANALYSIS_TIMEOUT", "ANALYSIS_FAILED:X", "DUPLICATE_OF:a.mp4"):
        check(f"friendly_skip {code}", ae.friendly_skip(code) and "_" not in ae.friendly_skip(code).split(" of ")[0], ae.friendly_skip(code))
    # chosen files: missing, unsupported and same-name files are refused
    d = work / "files"; (d / "x").mkdir(parents=True, exist_ok=True)
    (d / "a.mp4").write_bytes(b"0" * 2048); (d / "x" / "a.mp4").write_bytes(b"1" * 2048); (d / "t.txt").write_text("t")
    check("check_files refuses same names", raises(ae.check_files, [str(d / "a.mp4"), str(d / "x" / "a.mp4")]))
    check("check_files refuses non-video", raises(ae.check_files, [str(d / "t.txt")]))
    check("check_files refuses missing", raises(ae.check_files, [str(d / "nope.mp4")]))
    check("check_files refuses relative", raises(ae.check_files, ["a.mp4"]))
    check("check_files accepts one", [p.name for p in ae.check_files([str(d / "a.mp4")])] == ["a.mp4"])
    print({"passed": sum(checks), "total": len(checks)})
    return 0 if all(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
