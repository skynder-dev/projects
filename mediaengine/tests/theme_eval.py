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
With --coco N: image <-> text retrieval on N photos of the public COCO 2014 5k test set (5 human captions each:
people, children, food, animals, sport, streets...): for each caption, is its own photo the best match (R@1) or among
the best 5 (R@5) of the N photos; for each photo, is the best caption one of its own. That is the general "does the
model understand what is in the picture" measure, AI+ vs the accepted AI model; with --reference also the original
PyTorch PE-Core model (open_clip, full precision) to see what the int8 ONNX files lose.
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
LABELS = ("buildings", "forest", "glacier", "mountain", "sea", "street")
MAIN = {"buildings": "city", "forest": "nature", "glacier": "snow", "mountain": "mountains", "sea": "sea", "street": "city"}


def load_photos(per_class: int, seed: int = 13):
    import pyarrow.parquet as pq
    from huggingface_hub import hf_hub_download
    from PIL import Image
    p = hf_hub_download(DATA_REPO, DATA_FILE, repo_type="dataset", revision=DATA_REV)
    t = pq.read_table(p, columns=["image", "label"])
    names = [LABELS[int(x)] for x in t.column("label").to_pylist()]      # the dataset card's label order
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


COCO_REPO = "nlphuji/mscoco_2014_5k_test_image_text_retrieval"
COCO_REV = "551c4f7667f06fa82b4ef0a07617bfc4cf324ac3"


def _ascii(t: str) -> str:
    import unicodedata
    t = unicodedata.normalize("NFKD", str(t)).encode("ascii", "ignore").decode("ascii")
    return " ".join(t.split())


def load_coco(n: int):
    """The first n photos of the COCO 2014 5k test set (sorted by file name) and their captions."""
    import csv, zipfile
    from huggingface_hub import hf_hub_download
    from PIL import Image
    csvp = hf_hub_download(COCO_REPO, "test_5k_mscoco_2014.csv", repo_type="dataset", revision=COCO_REV)
    zp = hf_hub_download(COCO_REPO, "images_mscoco_2014_5k_test.zip", repo_type="dataset", revision=COCO_REV)
    with open(csvp, encoding="utf-8", newline="") as fh:
        rows = sorted(csv.DictReader(fh), key=lambda r: r["filename"])[:n]
    images, caps, owner = [], [], []
    with zipfile.ZipFile(zp) as z:
        where = {Path(x).name: x for x in z.namelist() if not x.endswith("/")}
        for k, r in enumerate(rows):
            with z.open(where[r["filename"]]) as fh:
                images.append(Image.open(io.BytesIO(fh.read())).convert("RGB"))
            for c in json.loads(r["raw"]):
                c = _ascii(c)
                if c:
                    caps.append(c); owner.append(k)
    return images, caps, owner


def retrieval(logits: np.ndarray, owner) -> dict:
    """logits: photos x captions."""
    owner = np.asarray(owner)
    order = np.argsort(-logits, axis=0)                     # photos ranked for every caption
    rank = np.array([int(np.where(order[:, j] == owner[j])[0][0]) for j in range(logits.shape[1])])
    best_cap = np.argmax(logits, axis=1)
    return {"text_to_photo_R1": round(float(np.mean(rank == 0)), 3), "text_to_photo_R5": round(float(np.mean(rank < 5)), 3),
            "photo_to_text_R1": round(float(np.mean(owner[best_cap] == np.arange(logits.shape[0]))), 3)}


class Reference:
    """The original PE-Core L/14 (open_clip, PyTorch, full precision) - Linux lab only."""

    def __init__(self):
        import open_clip, torch
        self.torch = torch
        self.model, _, self.pre = open_clip.create_model_and_transforms("hf-hub:timm/PE-Core-L-14-336")
        self.tok = open_clip.get_tokenizer("hf-hub:timm/PE-Core-L-14-336")
        self.model.eval()

    def encode_images(self, images):
        out = []
        with self.torch.no_grad():
            for i in range(0, len(images), 8):
                out.append(self.model.encode_image(self.torch.stack([self.pre(x) for x in images[i:i + 8]])).float().numpy())
        a = np.concatenate(out); return a / np.linalg.norm(a, axis=1, keepdims=True)

    def encode_text(self, texts):
        out = []
        with self.torch.no_grad():
            for i in range(0, len(texts), 64):
                out.append(self.model.encode_text(self.tok(list(texts[i:i + 64]))).float().numpy())
        a = np.concatenate(out); return a / np.linalg.norm(a, axis=1, keepdims=True)


def fast_logits(fa, processor, sess, images, texts):
    rows = []
    for i in range(0, len(images), 16):
        rows.append(np.concatenate([fa.semantic_logits(processor, sess, images[i:i + 16], texts[j:j + 256])
                                    for j in range(0, len(texts), 256)], axis=1))
    return np.concatenate(rows, axis=0)


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
    fa = processor = sess = None
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
    if "--coco" in sys.argv:
        n = int(sys.argv[sys.argv.index("--coco") + 1])
        t0 = time.time()
        cimgs, caps, cown = load_coco(n)
        report["coco"] = {"repo": COCO_REPO, "revision": COCO_REV, "photos": len(cimgs), "captions": len(caps), "load_s": round(time.time() - t0, 1)}
        t0 = time.time()
        sc = pa.PECoreScorer(pe_dir, full_check=False)
        report["coco"]["aiplus"] = retrieval(100.0 * sc.encode_images(cimgs) @ sc.encode_text(caps).T, cown)
        report["coco"]["aiplus"]["seconds"] = round(time.time() - t0, 1)
        del sc
        (out_dir / "theme_eval.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        if sess is not None:
            try:
                t0 = time.time()
                report["coco"]["ai_fast_local"] = retrieval(fast_logits(fa, processor, sess, cimgs, caps), cown)
                report["coco"]["ai_fast_local"]["seconds"] = round(time.time() - t0, 1)
            except Exception as exc:
                report["coco"]["ai_fast_local_error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
        (out_dir / "theme_eval.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        if "--reference" in sys.argv:
            try:
                t0 = time.time()
                ref = Reference()
                report["coco"]["aiplus_reference_fp32"] = retrieval(100.0 * ref.encode_images(cimgs) @ ref.encode_text(caps).T, cown)
                report["coco"]["aiplus_reference_fp32"]["seconds"] = round(time.time() - t0, 1)
                t0 = time.time()
                lr = 100.0 * ref.encode_images(images) @ ref.encode_text(prompts).T
                report["aiplus_reference_fp32"] = evaluate(lr, classes, hook.THEMES, owner, neg_idx)
                report["aiplus_reference_fp32"]["seconds"] = round(time.time() - t0, 1)
            except Exception as exc:
                report["reference_error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
        (out_dir / "theme_eval.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
