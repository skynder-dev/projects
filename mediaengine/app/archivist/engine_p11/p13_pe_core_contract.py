"""Exact identity of the stronger local model for "AI+" (PE-Core L/14, Meta, Apache-2.0).

The ONNX files come from the public Hugging Face repo onnx-community/PE-Core-L14-336-ONNX at a pinned revision; the
CLIP tokenizer files (vocab.json, merges.txt) are the very files of the accepted FAST_LOCAL support folder. Every file
is checked by size and SHA-256 before use; nothing is ever downloaded while video is analysed.
"""
from __future__ import annotations

import hashlib, json
from pathlib import Path

PROFILE = "PE_CORE_L14"
MODEL_REPO = "onnx-community/PE-Core-L14-336-ONNX"
MODEL_REVISION = "40c36ae81cea6449c590afcafe4a7378f1f26644"   # pinned commit (checked by tests/pe_core_probe.py)
TOKENIZER_REPO = "onnx-community/TinyCLIP-ViT-8M-16-Text-3M-YFCC15M-ONNX"
TOKENIZER_REVISION = "9463a9c508a344c837ffefe9d724f3827bf2dc79"

# local name: (path in the repo, bytes, sha256)
MODEL_FILES = {
    "vision_model_int8.onnx": ("onnx/vision_model_int8.onnx", 321065966, "7e28961190da8378b2b1faf562287da4d66128b5a013c3eb43558f210d273769"),
    "text_model_int8.onnx": ("onnx/text_model_int8.onnx", 355596172, "1f3a1123723d5c8abf0cf9f22b9fa8e4c836ca1105ce2ab86083cb74696526aa"),
}
TOKENIZER_FILES = {
    "vocab.json": ("vocab.json", 862328, "5047b556ce86ccaf6aa22b3ffccfc52d391ea4accdab9c2f2407da5b742d4363"),
    "merges.txt": ("merges.txt", 524619, "9fd691f7c8039210e0fced15865466c65820d09b63988b0174bfe25de299051a"),
}
ALL_FILES = {**MODEL_FILES, **TOKENIZER_FILES}
TOTAL_BYTES = sum(v[1] for v in ALL_FILES.values())

IMAGE_SIZE = 336                  # open_clip preprocess_cfg of timm/PE-Core-L-14-336: squash resize, bilinear,
IMAGE_MEAN = (0.5, 0.5, 0.5)      # mean / std 0.5
IMAGE_STD = (0.5, 0.5, 0.5)
CONTEXT_LENGTH = 32               # text_cfg.context_length


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download_url(name: str) -> str:
    """Public, pinned download address of one file (used only by the explicit "Download" button and by CI)."""
    if name in MODEL_FILES:
        return f"https://huggingface.co/{MODEL_REPO}/resolve/{MODEL_REVISION}/{MODEL_FILES[name][0]}"
    return f"https://huggingface.co/{TOKENIZER_REPO}/resolve/{TOKENIZER_REVISION}/{TOKENIZER_FILES[name][0]}"


def check_file(path: Path, name: str, full: bool = True) -> None:
    _, size, sha = ALL_FILES[name]
    p = Path(path)
    if not p.is_file() or p.is_symlink():
        raise RuntimeError(f"P13_MODEL_FILE_MISSING:{name}")
    if p.stat().st_size != size:
        raise RuntimeError(f"P13_MODEL_FILE_SIZE:{name}")
    if full and sha256_file(p) != sha:
        raise RuntimeError(f"P13_MODEL_FILE_SHA:{name}")


def validate(model_dir: Path, full: bool = True) -> dict:
    """Every file present with its exact size (and SHA-256 when full=True). Returns the identity for reports."""
    model_dir = Path(model_dir)
    for name in ALL_FILES:
        check_file(model_dir / name, name, full)
    vocab = json.loads((model_dir / "vocab.json").read_text(encoding="utf-8"))
    if vocab.get("<|startoftext|>") != 49406 or vocab.get("<|endoftext|>") != 49407:
        raise RuntimeError("P13_TOKENIZER_SPECIAL_IDS")
    return {
        "profile": PROFILE,
        "repo": MODEL_REPO,
        "revision": MODEL_REVISION,
        "files": {k: {"bytes": v[1], "sha256": v[2]} for k, v in ALL_FILES.items()},
        "image_size": IMAGE_SIZE,
        "context_length": CONTEXT_LENGTH,
        "network_during_analysis": False,
    }
