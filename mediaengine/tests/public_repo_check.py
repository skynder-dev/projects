"""The repository is public: nothing private may be in MediaEngine's files (acceptance row I23).

  python mediaengine/tests/public_repo_check.py            (from the repository root; exit 1 when something is found)

Checks every file git tracks under mediaengine/ (and MediaEngine's workflows):
  - no media, model or other binary files except the program's own (listed below with their SHA-256): no owner
    video, photo, recording or model weights in git;
  - no file bigger than 5 MB;
  - no secrets: GitHub / Hugging Face / OpenAI / AWS / Slack tokens, private keys, JWTs (Supabase keys are JWTs),
    password or token assignments with a value;
  - no e-mail addresses except the example ones (example.com / .org / .net), GitHub's noreply addresses and the
    commit-trailer address.
"""
from __future__ import annotations

import hashlib, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAX_BYTES = 5 * 1024 * 1024
# the program's own files that are not text (made by its tests, designed, or free fonts - no person, no owner
# footage), each pinned by its SHA-256: the same name with other content is found too
ALLOWED_BINARY = {
    "mediaengine/app/archivist/assets/browser_fixture_h264.mp4": "ec28d0ce0eac16dd6a4461e9f29cacfed9b1e58b2ff0b9ef1bb5a5c7b8712727",
    "mediaengine/app/archivist/assets/hevc_fixture.mp4": "d4a98ef2f4d5f3eba0c1f9bd017e2c9b4c6fcc7fa7e02842200fdb2a37aac27d",
    "mediaengine/app/archivist/assets/voice/host_9_2.flac": "903393c1db8026703450208bf6d084e0c2d9ee83d07afac16c473116b1abecc7",
    "mediaengine/app/archivist/assets/fonts/Montserrat-Black.ttf": "ea67b37f8776eebea135cd1fe9adeaf6f9427683e8dc11ab8398b6be5f102c60",
    "mediaengine/app/archivist/assets/fonts/Montserrat-ExtraBold.ttf": "d3ac6a843d3ba6d5cafd44cf39e437055c8aed7e261010f595f57d3c7b3e2c1b",
    "mediaengine/app/archivist/assets/fonts/Montserrat-SemiBold.ttf": "b4e1563393d73fdff491a869441245aef31add2ec03d9c97a6dae4de07c52fd0",
}
MEDIA_EXT = {".mp4", ".m4v", ".mov", ".mts", ".m2ts", ".mpg", ".mpeg", ".avi", ".wmv", ".mkv", ".webm", ".3gp", ".insv",
             ".lrv", ".thm", ".jpg", ".jpeg", ".png", ".heic", ".gif", ".webp", ".bmp", ".tif", ".tiff", ".dng", ".raw",
             ".cr2", ".cr3", ".nef", ".arw", ".wav", ".flac", ".mp3", ".m4a", ".aac", ".ogg", ".opus", ".onnx", ".bin",
             ".safetensors", ".pt", ".pth", ".ckpt", ".gguf", ".npy", ".npz", ".pkl", ".h5", ".tflite", ".zip", ".7z",
             ".rar", ".exe", ".dll", ".db", ".sqlite", ".sqlite3", ".db-wal", ".db-shm", ".ttf", ".otf", ".woff", ".woff2"}
SECRETS = [
    ("GitHub token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}\b|\bgithub_pat_[A-Za-z0-9_]{40,}")),
    ("Hugging Face token", re.compile(r"\bhf_[A-Za-z0-9]{30,}\b")),
    ("OpenAI / Anthropic key", re.compile(r"\bsk-(?:ant-|proj-)?[A-Za-z0-9_-]{32,}")),
    ("AWS key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("private key", re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----")),
    ("JWT (e.g. a Supabase key)", re.compile(r"\beyJ[A-Za-z0-9_-]{15,}\.eyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{10,}")),
    ("password / token with a value",
     re.compile(r"""(?i)\b(?:password|passwd|api_key|apikey|secret_key|access_token|auth_token)\b\s*[:=]\s*["'][^"'\s]{8,}["']""")),
]
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b")
EMAIL_OK = re.compile(r"(?i)@(?:[a-z0-9-]+\.)*example\.(?:com|org|net)$|^noreply@anthropic\.com$|@(?:users\.)?noreply\.github\.com$")


def tracked() -> list[str]:
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z", "mediaengine", ".github/workflows"],
                         capture_output=True, check=True).stdout.decode("utf-8", "replace")
    return [p for p in out.split("\0") if p and (p.startswith("mediaengine/") or "/mediaengine-" in p)]


def scan(files: list[str], root: Path = ROOT) -> list[str]:
    found = []
    for rel in files:
        path = root / rel
        if not path.is_file():
            continue
        size = path.stat().st_size
        if size > MAX_BYTES:
            found.append(f"{rel}: {size} bytes (over {MAX_BYTES})")
        data = path.read_bytes()
        binary = b"\0" in data[:8192] or path.suffix.lower() in MEDIA_EXT
        if binary:
            if rel not in ALLOWED_BINARY:
                found.append(f"{rel}: a media / model / binary file that is not one of the program's own files")
            elif hashlib.sha256(data).hexdigest() != ALLOWED_BINARY[rel]:
                found.append(f"{rel}: not the program's own file (its content changed - SHA-256 differs)")
            continue
        text = data.decode("utf-8", "replace")
        for name, rx in SECRETS:
            m = rx.search(text)
            if m:
                line = text.count("\n", 0, m.start()) + 1
                found.append(f"{rel}:{line}: looks like a {name}")
        for m in EMAIL.finditer(text):
            if not EMAIL_OK.search(m.group(0)):
                line = text.count("\n", 0, m.start()) + 1
                found.append(f"{rel}:{line}: an e-mail address ({m.group(0)})")
    return found


def self_test() -> list[str]:
    """The check finds what it must (planted in a temporary folder, never in git)."""
    import tempfile
    bad = {"a.py": 'token = "ghp_' + "A" * 36 + '"\n', "b.md": "write to " + "someone" + "@" + "gmail.com\n",
           "c.json": '{"key": "' + ".".join(["eyJ" + "h" * 20, "eyJ" + "r" * 20, "s" * 16]) + '"}',
           "own.MP4": "x", "blob.dat": "a\0b", "ok.py": 'mail = "alice.private@example.com"\npassword = ""\n'}
    with tempfile.TemporaryDirectory() as d:
        for name, text in bad.items():
            (Path(d) / name).write_text(text, "utf-8")
        got = scan(list(bad), Path(d))
    want = {"a.py", "b.md", "c.json", "own.MP4", "blob.dat"}
    hit = {g.split(":")[0] for g in got}
    return [] if hit == want else [f"self-test: found {sorted(hit)}, expected {sorted(want)}"]


def main() -> int:
    files = tracked()
    problems = self_test() + scan(files)
    for p in problems:
        print("FOUND " + p)
    print(json.dumps({"files": len(files), "found": len(problems)}))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
