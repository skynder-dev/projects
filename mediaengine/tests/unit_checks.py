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
    # a folder of year folders: the subfolders with videos are offered
    yrs = work / "years"; (yrs / "2023").mkdir(parents=True, exist_ok=True); (yrs / "2024").mkdir(exist_ok=True); (yrs / "docs").mkdir(exist_ok=True)
    (yrs / "2023" / "a.mp4").write_bytes(b"0" * 2048); (yrs / "2024" / "b.MOV").write_bytes(b"0" * 2048); (yrs / "docs" / "c.txt").write_text("c")
    check("subfolders_with_videos", [(Path(x).name, n) for x, n in ae.subfolders_with_videos(yrs)] == [("2023", 1), ("2024", 1)],
          ae.subfolders_with_videos(yrs))
    # a nearly full data drive refuses a new build up front (not half-way)
    old_min = ae.MIN_FREE_BYTES
    ae.MIN_FREE_BYTES = 1 << 62
    check("full drive refuses a build", raises(ae.check_free_space))
    ae.MIN_FREE_BYTES = old_min
    check("normal drive allows a build", not raises(ae.check_free_space))
    # older versions next to this one can be listed and removed; never this one, never the data folder
    base = work / "builds"
    cur, old, other = base / "MediaEngine-3.13.0-b2", base / "MediaEngine-3.13.0-b1", base / "MediaEngine-notes"
    for d in (cur, old, other, base / "MediaEngine Data"):
        d.mkdir(parents=True, exist_ok=True)
    for d in (cur, old):
        for n in ae.BUILD_MARKERS:
            (d / n).write_text(f"MediaEngine {d.name}\n", encoding="utf-8")
    (other / "BUILD.txt").write_text("x", encoding="utf-8")
    lst = ae.other_builds(cur)
    check("other_builds lists only real other builds", [b["name"] for b in lst] == [old.name], lst)
    check("delete_build refuses this build and the data folder", raises(ae.delete_build, cur.name, cur) and raises(ae.delete_build, "MediaEngine Data", cur))
    check("delete_build removes an older build", ae.delete_build(old.name, cur) > 0 and not old.exists() and cur.exists()
          and (base / "MediaEngine Data").exists())
    # Windows must not sleep while a reel is built (no-op elsewhere)
    from archivist.platform_adapter import keep_awake
    with keep_awake() as k:
        check("keep_awake set on Windows", k.ok == (os.name == "nt"), k.ok)
    print({"passed": sum(checks), "total": len(checks)})
    return 0 if all(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
