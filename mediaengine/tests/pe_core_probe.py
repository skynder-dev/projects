"""PE-Core L/14 for "AI+": does our ONNX adapter see what the original model sees? (CI only, needs internet)

  python tests/pe_core_probe.py <out_dir> [--reference] [--model-dir DIR]

Downloads the pinned ONNX files + tokenizer files (Hugging Face, public, free) unless --model-dir has them, checks
size + SHA-256, prints the ONNX inputs / outputs, measures speed and memory of the int8 model on this CPU.
With --reference (Linux CI): also loads the original open_clip PyTorch model (timm/PE-Core-L-14-336) and compares
tokens, preprocessing, image and text embeddings and zero-shot choices with our adapter.
"""
from __future__ import annotations

import json, os, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app" / "archivist" / "engine_p11"))
import p13_pe_core_contract as contract  # noqa: E402

TEXTS = ["a photo of a cat", "a photo of two cats lying on a couch", "a photo of a dog", "a car dashboard",
         "a black empty frame", "a beautiful sunset over the sea", "children playing in a park",
         "a happy moment with people smiling or laughing", "a blurry or shaky low quality frame"]


def download(model_dir: Path, report: dict) -> None:
    from huggingface_hub import HfApi, hf_hub_download
    info = HfApi().model_info(contract.MODEL_REPO)
    report["model_repo_head_sha"] = info.sha
    model_dir.mkdir(parents=True, exist_ok=True)
    for name, (path, size, sha) in contract.ALL_FILES.items():
        dst = model_dir / name
        if dst.is_file() and dst.stat().st_size == size:
            continue
        repo, rev = ((contract.MODEL_REPO, contract.MODEL_REVISION if contract.MODEL_REVISION != "main" else info.sha)
                     if name in contract.MODEL_FILES else (contract.TOKENIZER_REPO, contract.TOKENIZER_REVISION))
        got = Path(hf_hub_download(repo, path, revision=rev, local_dir=str(model_dir / "_dl")))
        os.replace(got, dst)


def sample_images():
    from PIL import Image
    import numpy as np
    out = {}
    try:
        from huggingface_hub import hf_hub_download
        for fn in ("coco_sample.png", "pipeline-cat-chonk.jpeg"):
            try:
                p = hf_hub_download("huggingface/documentation-images", fn, repo_type="dataset")
                out[fn] = Image.open(p).convert("RGB")
            except Exception as exc:
                print("sample image not available:", fn, exc)
    except Exception:
        pass
    out["black"] = Image.new("RGB", (640, 360), (0, 0, 0))
    g = np.zeros((360, 640, 3), np.uint8)
    g[..., 0] = np.linspace(255, 40, 360)[:, None]; g[..., 1] = np.linspace(120, 20, 360)[:, None]; g[..., 2] = 60
    out["orange_gradient"] = Image.fromarray(g)
    rng = np.random.default_rng(7)
    out["noise"] = Image.fromarray(rng.integers(0, 255, (360, 640, 3), dtype=np.uint8))
    return out


def main():
    out_dir = Path(sys.argv[1]); out_dir.mkdir(parents=True, exist_ok=True)
    model_dir = Path(sys.argv[sys.argv.index("--model-dir") + 1]) if "--model-dir" in sys.argv else out_dir / "PE_CORE_L14"
    report: dict = {"platform": sys.platform, "cpu_count": os.cpu_count()}
    t0 = time.time()
    download(model_dir, report)
    report["download_s"] = round(time.time() - t0, 1)
    t0 = time.time()
    report["identity"] = contract.validate(model_dir, True)
    report["validate_s"] = round(time.time() - t0, 1)
    import numpy as np
    import onnxruntime as ort
    report["onnxruntime"] = ort.__version__
    for name in contract.MODEL_FILES:
        s = ort.InferenceSession(str(model_dir / name), providers=["CPUExecutionProvider"])
        report["io_" + name] = {"inputs": [[x.name, x.type, x.shape] for x in s.get_inputs()],
                                "outputs": [[x.name, x.type, x.shape] for x in s.get_outputs()]}
        del s
    import psutil
    proc = psutil.Process()
    rss0 = proc.memory_info().rss
    import p13_pe_core_adapter as A
    t0 = time.time()
    sc = A.PECoreScorer(model_dir, full_check=False)
    report["load_s"] = round(time.time() - t0, 1)
    imgs = sample_images()
    names = list(imgs)
    t0 = time.time()
    te = sc.encode_text(TEXTS)
    report["text_encode_s"] = round(time.time() - t0, 2)
    frames = [imgs[n] for n in names] * 4                   # 8+ frames: a realistic batch
    t0 = time.time()
    ie = sc.encode_images(frames)
    dt = time.time() - t0
    report["image_encode_s_per_frame"] = round(dt / len(frames), 3)
    report["rss_mb_after_load_and_run"] = round((proc.memory_info().rss - rss0) / 1e6)
    ie = ie[: len(names)]
    probs = {}
    for n, row in zip(names, 100.0 * ie @ te.T):
        e = np.exp(row - row.max()); e /= e.sum()
        probs[n] = {TEXTS[i]: round(float(e[i]), 3) for i in np.argsort(-e)[:3]}
    report["adapter_top3"] = probs
    if "--reference" in sys.argv:
        reference(report, sc, imgs, names, te, ie)
    (out_dir / "pe_core_probe.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


def reference(report, sc, imgs, names, te, ie):
    import numpy as np, torch, open_clip
    import p13_pe_core_adapter as A
    model, _, preprocess = open_clip.create_model_and_transforms("hf-hub:timm/PE-Core-L-14-336")
    tok = open_clip.get_tokenizer("hf-hub:timm/PE-Core-L-14-336")
    model.eval()
    ref_ids = tok(TEXTS).numpy()
    our_ids = sc.tokenizer.batch(TEXTS)
    report["tokens_equal"] = bool(ref_ids.shape == our_ids.shape and (ref_ids == our_ids).all())
    if not report["tokens_equal"]:
        report["tokens_ref"] = ref_ids[:3].tolist(); report["tokens_ours"] = our_ids[:3].tolist()
    diffs = [float(np.abs(preprocess(imgs[n]).numpy() - A.preprocess(imgs[n])).max()) for n in names]
    report["preprocess_max_abs_diff"] = round(max(diffs), 4)
    report["logit_scale"] = float(model.logit_scale.exp())
    with torch.no_grad():
        rt = model.encode_text(torch.from_numpy(ref_ids)).float().numpy()
        ri = model.encode_image(torch.stack([preprocess(imgs[n]) for n in names])).float().numpy()
    rt /= np.linalg.norm(rt, axis=1, keepdims=True); ri /= np.linalg.norm(ri, axis=1, keepdims=True)
    report["cos_text_int8_vs_ref"] = [round(float(x), 4) for x in (rt * te).sum(1)]
    report["cos_image_int8_vs_ref"] = [round(float(x), 4) for x in (ri * ie).sum(1)]
    ref_top, our_top = {}, {}
    for n, rrow, orow in zip(names, ri @ rt.T, ie @ te.T):
        ref_top[n] = TEXTS[int(np.argmax(rrow))]; our_top[n] = TEXTS[int(np.argmax(orow))]
    report["zero_shot_ref"] = ref_top
    report["zero_shot_same"] = ref_top == our_top
    # the fp32 export too: is the ONNX conversion itself right (int8 adds only rounding)?
    try:
        import onnxruntime as ort
        from huggingface_hub import hf_hub_download
        rev = report.get("model_repo_head_sha")
        vp = hf_hub_download(contract.MODEL_REPO, "onnx/vision_model.onnx", revision=rev)
        vs = ort.InferenceSession(vp, providers=["CPUExecutionProvider"])
        px = np.stack([A.preprocess(imgs[n]) for n in names])
        outs = [o.name for o in vs.get_outputs()]
        v = vs.run(None, {vs.get_inputs()[0].name: px})
        for o, arr in zip(outs, v):
            if np.asarray(arr).ndim == 2:
                a = np.asarray(arr, np.float32); a /= np.linalg.norm(a, axis=1, keepdims=True)
                report["cos_image_fp32_vs_ref_" + o] = [round(float(x), 4) for x in (ri * a).sum(1)]
    except Exception as exc:
        report["fp32_check_error"] = str(exc)[:300]


if __name__ == "__main__":
    main()
