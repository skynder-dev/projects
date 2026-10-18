"""The in-app update of one package (app/archivist/updater.py reads it): latest.json + the program as one ZIP.

  python mediaengine/tools/make_update_bundle.py <package_folder> <out_dir> [--name MediaEngine-<ver>-b<N>] [--run-url URL]

The ZIP holds every file of the package folder except the runtime (.venv), paths relative to the folder. latest.json
says which build it is, its size and SHA-256, the runtime it needs (runtime.txt) and what is new (WHATS_NEW_ITEMS of
the package's auto_edit.py with their Russian text from auto_edit_ru.py, read as text - nothing of the package runs).
--name: publish the package under another build name (the CI check of the update makes a "next build" this way).
"""
from __future__ import annotations

import argparse, ast, hashlib, json, os, re, sys, zipfile
from datetime import datetime, timezone
from pathlib import Path

FORMAT = "mediaengine.update/1"


def _literal_assign(path: Path, name: str):
    """The value of `name = <literal>` in a Python file, without running it (dict: the pairs that are literals)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            v = node.value
            if isinstance(v, ast.Dict):
                out = {}
                for k, val in zip(v.keys, v.values):
                    try:
                        out[ast.literal_eval(k)] = ast.literal_eval(val)
                    except Exception:
                        continue
                return out
            return ast.literal_eval(v)
    return None


def notes(pkg: Path) -> list[dict]:
    arch = pkg / "app" / "archivist"
    try:
        items = _literal_assign(arch / "auto_edit.py", "WHATS_NEW_ITEMS") or []
        ru = _literal_assign(arch / "auto_edit_ru.py", "PHRASES") or {}
    except Exception:
        return []
    return [{"since": str(d), "en": str(t), "ru": str(ru.get(t, ""))} for d, t in items]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("package"); ap.add_argument("out")
    ap.add_argument("--name", default=""); ap.add_argument("--run-url", default="")
    a = ap.parse_args()
    pkg = Path(a.package).resolve(); out = Path(a.out).resolve(); out.mkdir(parents=True, exist_ok=True)
    name = a.name or pkg.name
    if not re.fullmatch(r"MediaEngine-([0-9][0-9A-Za-z.\-]*)-b(\d+)", name):
        raise SystemExit(f"not a build name: {name}")
    for need in ("runtime.txt", "port.txt", "BUILD.txt", "launcher.py", "app/main.py", "Start MediaEngine.vbs", "version.txt"):
        if not (pkg / need).is_file():
            raise SystemExit(f"package without {need}: {pkg}")
    zname = f"{name}-update.zip"
    zpath = out / zname
    files = []
    for root, dirs, fs in os.walk(pkg):
        rel_root = Path(root).relative_to(pkg)
        if rel_root.parts[:1] == (".venv",):
            dirs[:] = []
            continue
        dirs[:] = sorted(d for d in dirs if not (rel_root == Path(".") and d == ".venv"))
        for f in sorted(fs):
            files.append((Path(root) / f, (rel_root / f).as_posix()))
    with zipfile.ZipFile(zpath, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for src, arc in files:
            zf.write(src, arc)
    data = zpath.read_bytes()
    commit = ""
    for ln in (pkg / "BUILD.txt").read_text(encoding="utf-8", errors="replace").splitlines():
        if ln.startswith("commit "):
            commit = ln.split(None, 1)[1].strip()
    manifest = {
        "format": FORMAT, "pkg": name, "version": (pkg / "version.txt").read_text(encoding="utf-8").strip(),
        "file": zname, "size": len(data), "sha256": hashlib.sha256(data).hexdigest(),
        "runtime": (pkg / "runtime.txt").read_text(encoding="utf-8").strip(), "commit": commit,
        "run_url": a.run_url, "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "files": len(files), "notes": notes(pkg),
    }
    (out / "latest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ("pkg", "file", "size", "sha256", "runtime", "files")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
