from __future__ import annotations
import hashlib, json
from pathlib import Path

COMMIT = "9463a9c508a344c837ffefe9d724f3827bf2dc79"
MODEL_NAME = "model_int8.onnx"
MODEL_SIZE = 24281512
MODEL_SHA256 = "844d1a46ab18acf50c989e541b12fe3b6dc7f8d6004725b4e992d142788e0600"
SUPPORT_DIR = "support_" + COMMIT
SUPPORT = {
    "config.json": (850, "0ca46b868f12305e959a1cfa2b8085e7bffd521f68769ec3bf2999986b55bec3"),
    "merges.txt": (524619, "9fd691f7c8039210e0fced15865466c65820d09b63988b0174bfe25de299051a"),
    "preprocessor_config.json": (468, "5df7e578c37e907a431daf47fd592fc49fa50d23ed4c41285a0a34a58a9d2e06"),
    "special_tokens_map.json": (133, "92e1e31d71a7f63cd75b4dfa1469377bd2cd6b8292cf70b3ff5b7082b0edc1c9"),
    "tokenizer.json": (3642073, "6d9109cc838977f3ca94a379eec36aecc7c807e1785cd729660ca2fc0171fb35"),
    "tokenizer_config.json": (726, "f97b07bf147d9e4dbdb5f98941d35fc0b9412263a183483f73893adf756ede3e"),
    "vocab.json": (862328, "5047b556ce86ccaf6aa22b3ffccfc52d391ea4accdab9c2f2407da5b742d4363"),
}
RUNTIME = {"onnxruntime": "1.30.0", "numpy": "2.4.6", "Pillow": "11.3.0"}


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _exact(path: Path, size: int, sha: str) -> None:
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"P11_MODEL_CONTRACT_MISSING:{path.name}")
    if path.stat().st_size != size:
        raise RuntimeError(f"P11_MODEL_CONTRACT_SIZE:{path.name}")
    if _sha(path) != sha:
        raise RuntimeError(f"P11_MODEL_CONTRACT_SHA:{path.name}")


def validate(profile: str, profile_dir: Path):
    if profile != "FAST_LOCAL":
        raise RuntimeError("P11_MODEL_CONTRACT_PROFILE")
    profile_dir = Path(profile_dir)
    _exact(profile_dir / MODEL_NAME, MODEL_SIZE, MODEL_SHA256)
    support = profile_dir / SUPPORT_DIR
    for name, (size, sha) in SUPPORT.items():
        _exact(support / name, size, sha)

    cfg = json.loads((support / "config.json").read_text(encoding="utf-8"))
    if cfg.get("model_type") != "clip" or int(cfg.get("projection_dim", -1)) != 512:
        raise RuntimeError("P11_MODEL_CONTRACT_CONFIG")
    tcfg = cfg.get("text_config") or {}
    vcfg = cfg.get("vision_config") or {}
    if (int(tcfg.get("hidden_size", -1)), int(tcfg.get("num_hidden_layers", -1))) != (256, 3):
        raise RuntimeError("P11_MODEL_CONTRACT_TEXT_CONFIG")
    if (int(vcfg.get("hidden_size", -1)), int(vcfg.get("num_hidden_layers", -1)), int(vcfg.get("patch_size", -1))) != (256, 10, 16):
        raise RuntimeError("P11_MODEL_CONTRACT_VISION_CONFIG")

    pre = json.loads((support / "preprocessor_config.json").read_text(encoding="utf-8"))
    if pre.get("crop_size") != {"height": 224, "width": 224}:
        raise RuntimeError("P11_MODEL_CONTRACT_CROP")
    if pre.get("size") != {"shortest_edge": 224}:
        raise RuntimeError("P11_MODEL_CONTRACT_RESIZE")
    if [float(x) for x in pre.get("image_mean", [])] != [0.48145466, 0.4578275, 0.40821073]:
        raise RuntimeError("P11_MODEL_CONTRACT_MEAN")
    if [float(x) for x in pre.get("image_std", [])] != [0.26862954, 0.26130258, 0.27577711]:
        raise RuntimeError("P11_MODEL_CONTRACT_STD")

    special = json.loads((support / "special_tokens_map.json").read_text(encoding="utf-8"))
    if special != {
        "bos_token": "<|startoftext|>",
        "eos_token": "<|endoftext|>",
        "pad_token": "<|endoftext|>",
        "unk_token": "<|endoftext|>",
    }:
        raise RuntimeError("P11_MODEL_CONTRACT_SPECIAL_TOKENS")
    vocab = json.loads((support / "vocab.json").read_text(encoding="utf-8"))
    if vocab.get("<|startoftext|>") != 49406 or vocab.get("<|endoftext|>") != 49407:
        raise RuntimeError("P11_MODEL_CONTRACT_SPECIAL_IDS")

    return {
        "profile": profile,
        "repo": "onnx-community/TinyCLIP-ViT-8M-16-Text-3M-YFCC15M-ONNX",
        "revision": COMMIT,
        "model_sha256": MODEL_SHA256,
        "model_size_bytes": MODEL_SIZE,
        "support_dir": SUPPORT_DIR,
        "support_files": {k: {"bytes": v[0], "sha256": v[1]} for k, v in SUPPORT.items()},
        "runtime_pin": dict(RUNTIME),
        "network_during_analysis": False,
        "external_media_upload": False,
    }
