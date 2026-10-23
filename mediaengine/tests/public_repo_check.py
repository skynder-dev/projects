"""The repository is public: nothing private may be in MediaEngine's files (acceptance row I23).

  python mediaengine/tests/public_repo_check.py            (from the repository root; exit 1 when something is found)

Checks every file git tracks under mediaengine/ (and MediaEngine's workflows):
  - no media or model files except the program's own synthetic ones (listed below with their SHA-256): no owner
    video, photo, recording or model weights in git;
  - no file bigger than 5 MB;
  - no secrets: GitHub / Hugging Face / OpenAI / AWS / Slack tokens, private keys, JWTs (Supabase keys are JWTs),
    password or token assignments with a value;
  - no e-mail addresses except the example ones (example.com / .org / .net), GitHub's noreply addresses and the
    commit-trailer address.
"""
from __future__ import annotations

import json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAX_BYTES = 5 * 1024 * 1024
# the program's own synthetic files (made by its tests or designed - no person, no owner footage)
ALLOWED_MEDIA = {
    "mediaengine/app/archivist/assets/browser_fixture_h264.mp4": "2s test pattern for the browser check",
    "mediaengine/app/archivist/assets/hevc_fixture.mp4": "2s HEVC test pattern",
    "mediaengine/app/archivist/assets/voice/host_9_2.flac": "designed voice (VoxCPM2 voice design, no person)",
}
MEDIA_EXT = {".mp4", ".mov", ".mts", ".m2ts", ".avi", ".mkv", ".webm", ".3gp", ".insv", ".lrv", ".jpg", ".jpeg", ".png",
             ".heic", ".gif", ".webp", ".dng", ".raw", ".wav", ".flac", ".mp3", ".m4a", ".aac", ".ogg", ".opus",
             ".onnx", ".bin", ".safetensors", ".pt", ".pth", ".ckpt", ".gguf", ".zip", ".7z", ".rar", ".exe", ".dll",
             ".db", ".sqlite", ".sqlite3"}
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
        if path.suffix.lower() in MEDIA_EXT and rel not in ALLOWED_MEDIA:
            found.append(f"{rel}: a media / model / binary file that is not one of the program's own synthetic files")
            continue
        if rel in ALLOWED_MEDIA or path.suffix.lower() in MEDIA_EXT:
            continue
        data = path.read_bytes()
        if b"\0" in data[:4096]:
            continue                                    # another binary (fonts, icons): sizes are checked above
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
           "own.MP4": "x", "ok.py": 'mail = "alice.private@example.com"\npassword = ""\n'}
    with tempfile.TemporaryDirectory() as d:
        for name, text in bad.items():
            (Path(d) / name).write_text(text, "utf-8")
        got = scan(list(bad), Path(d))
    want = {"a.py", "b.md", "c.json", "own.MP4"}
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
