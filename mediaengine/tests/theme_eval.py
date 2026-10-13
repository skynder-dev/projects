"""How well the AI+ themes recognise real photos (CI model lab only; public data, no owner media).

  python tests/theme_eval.py <out_dir> --pe-dir DIR [--fast-dir DIR] [--per-class 40]

Public labelled scene photos: prithivMLmods/OpenScene-Classification (Apache-2.0, pinned commit) - the Intel scene
classification set: buildings, forest, glacier, mountain, sea, street (small 150 px photos). Every photo is scored for
the 13 AI+ themes the way a themed reel scores a frame (mean of the two best descriptions of a theme). Reported:
- top-1 theme: is the best of the 13 themes one that fits the photo (buildings: city; forest: nature; glacier:
  snow / mountains; mountain: mountains / snow; sea: sea; street: city / road);
- the theme filter of themed reels (theme score minus the best "bad frame" description > 0): share of photos of a
  class that pass its theme, and share of photos of unrelated classes that pass it (false matches);
- the same numbers with the accepted AI model (FAST_LOCAL, TinyCLIP) for comparison, when --fast-dir is given.
This says how well the descriptions and the model fit common scenes; it is not a proof of reel quality on the
owner's own videos.
"""
from __future__ import annotations

import io, json, sys, time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app" / "archivist" / "engine_p11"))

DATA_REPO = "prithivMLmods/OpenScene-Classification"
DATA_REV = "bbf9f337d6c56ce5c4d31fe1ab4f1852af2a8cfe"
DATA_FILE = "dataset/OpenScene-Classification.parquet"
ALLOWED = {"buildings": {"city"}, "forest": {"nature"}, "glacier": {"snow", "mountains"}, "mountain": {"mountains", "snow"},
           "sea": {"sea"}, "street": {"city", "road"}}
MAIN = {"buildings": "city", "forest": "nature", "glacier": "snow", "mountain": "mountains", "sea": "sea", "street": "city"}


def load_photos(per_class: int, seed: int = 13):
    import pyarrow.parquet as pq
    from huggingface_hub import hf_hub_download
    from PIL import Image
    p = hf_hub_download(DATA_REPO, DATA_FILE, repo_type="dataset", revision=DATA_REV)
    t = pq.read_table(p, columns=["image", "label_name"])
    names = t.column("label_name").to_pylist()
    rng = np.random.default_rng(seed)
    picked = []
    for cls in ALLOWED:
        idx = [i for i, n in enumerate(names) if n == cls]
        for i in sorted(rng.choice(idx, size=min(per_class, len(idx)), replace=False).tolist()):
            picked.append((cls, i))
    col = t.column("image")
    photos = []
    for cls, i in picked:
        cell = col[i].as_py()
        photos.append((cls, Image.open(io.BytesIO(cell["bytes"])).convert("RGB")))
    return photos


def evaluate(logits: np.ndarray, classes, themes, prompt_owner, neg_idx):
    """logits: photos x prompts (all theme descriptions, then the bad ones)."""
    theme_names = list(themes)
    score = np.zeros((logits.shape[0], len(theme_names)), np.float32)
    for k, t in enumerate(theme_names):
        cols = [j for j, o in enumerate(prompt_owner) if o == t]
        score[:, k] = np.sort(logits[:, cols], axis=1)[:, -2:].mean(axis=1)
    margin = score - logits[:, neg_idx].max(axis=1, keepdims=True)
    pred = [theme_names[int(i)] for i in np.argmax(score, axis=1)]
    out = {"top1_fits": {}, "top1_examples": {}, "filter": {}}
    for cls in ALLOWED:
        ix = [i for i, c in enumerate(classes) if c == cls]
        out["top1_fits"][cls] = round(float(np.mean([pred[i] in ALLOWED[cls] for i in ix])), 3)
        wrong = {}
        for i in ix:
            if pred[i] not in ALLOWED[cls]:
                wrong[pred[i]] = wrong.get(pred[i], 0) + 1
        out["top1_examples"][cls] = dict(sorted(wrong.items(), key=lambda x: -x[1])[:3])
    for t in sorted(set(MAIN.values())):
        k = theme_names.index(t)
        own = [i for i, c in enumerate(classes) if MAIN[c] == t]
        other = [i for i, c in enumerate(classes) if t not in ALLOWED[c]]
        out["filter"][t] = {"own_pass": round(float(np.mean(margin[own, k] > 0)), 3) if own else None,
                            "unrelated_pass": round(float(np.mean(margin[other, k] > 0)), 3) if other else None}
    out["top1_fits_all"] = round(float(np.mean([pred[i] in ALLOWED[c] for i, c in enumerate(classes)])), 3)
    return out


def main():
    out_dir = Path(sys.argv[1]); out_dir.mkdir(parents=True, exist_ok=True)
    pe_dir = Path(sys.argv[sys.argv.index("--pe-dir") + 1])
    fast_dir = Path(sys.argv[sys.argv.index("--fast-dir") + 1]) if "--fast-dir" in sys.argv else None
    if fast_dir is not None and not (fast_dir / "model_int8.onnx").is_file():
        # the accepted AI model from its public, pinned commit (the exact files the engine checks by SHA-256)
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from real_models_check import FAST_REPO, FAST_REV, FAST_SUPPORT, fetch
        fetch(f"https://huggingface.co/{FAST_REPO}/resolve/{FAST_REV}/onnx/model_int8.onnx", fast_dir / "model_int8.onnx")
        for n in FAST_SUPPORT:
            fetch(f"https://huggingface.co/{FAST_REPO}/resolve/{FAST_REV}/{n}", fast_dir / f"support_{FAST_REV}" / n)
    per_class = int(sys.argv[sys.argv.index("--per-class") + 1]) if "--per-class" in sys.argv else 40
    import p13_event_semantic_pe as hook
    report = {"data": {"repo": DATA_REPO, "revision": DATA_REV, "per_class": per_class}}
    t0 = time.time()
    photos = load_photos(per_class)
    report["data"]["photos"] = len(photos)
    report["data"]["load_s"] = round(time.time() - t0, 1)
    classes = [c for c, _ in photos]
    images = [im for _, im in photos]
    prompts, owner = [], []
    for t, (_name, ps) in hook.THEMES.items():
        prompts += list(ps); owner += [t] * len(ps)
    neg_idx = list(range(len(prompts), len(prompts) + len(hook.NEGATIVE_PROMPTS)))
    prompts += list(hook.NEGATIVE_PROMPTS); owner += ["_bad"] * len(hook.NEGATIVE_PROMPTS)

    import p13_pe_core_adapter as pa
    t0 = time.time()
    sc = pa.PECoreScorer(pe_dir, full_check=False)
    logits = 100.0 * sc.encode_images(images) @ sc.encode_text(prompts).T
    report["aiplus"] = evaluate(logits, classes, hook.THEMES, owner, neg_idx)
    report["aiplus"]["seconds"] = round(time.time() - t0, 1)
    del sc
    if fast_dir is not None:
        try:
            import p11_fast_onnx_adapter as fa
            t0 = time.time()
            processor, sess, _ident = fa.load_runtime(fast_dir)
            rows = [fa.semantic_logits(processor, sess, images[i:i + 16], prompts) for i in range(0, len(images), 16)]
            report["ai_fast_local"] = evaluate(np.concatenate(rows, axis=0), classes, hook.THEMES, owner, neg_idx)
            report["ai_fast_local"]["seconds"] = round(time.time() - t0, 1)
        except Exception as exc:
            report["ai_fast_local_error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
    (out_dir / "theme_eval.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
