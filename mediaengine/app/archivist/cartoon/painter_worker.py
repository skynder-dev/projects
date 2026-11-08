"""The picture add-on's worker (run by painter.py in its own process, below normal priority): draws the pictures of a
request one after another with FLUX.2 [klein] 4B, each written whole (a .part file renamed), and prints "PIC <n> <what>"
after each. "standin": plain figures drawn with Pillow instead (checks without a graphics card or the model).
python painter_worker.py <request.json>"""
import json
import os
import sys


def _save(img, out):
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = out + ".part.png"
    img.save(tmp)
    os.replace(tmp, out)


def _refs(p):
    return [r for r in (p.get("refs") or ([p["ref"]] if p.get("ref") else [])) if r]


def standin(job):
    from PIL import Image, ImageDraw
    n = 0
    for p in job["pictures"]:
        if p.get("depth_of"):
            continue
        img = Image.new("RGB", (p["w"], p["h"]), (250, 250, 250))
        d = ImageDraw.Draw(img)
        if _refs(p) or "Full body" in p["prompt"] or "Character sheet" in p["prompt"]:
            w, h = p["w"], p["h"]
            d.rectangle((w * 0.37, h * 0.15, w * 0.63, h * 0.52), fill=(120, 60, 160))
            d.rectangle((w * 0.37, h * 0.52, w * 0.47, h * 0.93), fill=(80, 80, 90))
            d.rectangle((w * 0.53, h * 0.52, w * 0.63, h * 0.93), fill=(80, 80, 90))
            d.rectangle((w * 0.36, h * 0.93, w * 0.64, h * 0.96), fill=(20, 20, 20))
            d.ellipse((w * 0.42, h * 0.04, w * 0.58, h * 0.15), fill=(230, 190, 160))
            if "open" in os.path.basename(p["out"]):
                d.ellipse((w * 0.48, h * 0.11, w * 0.52, h * 0.13), fill=(120, 20, 30))
        else:
            d.rectangle((0, 0, p["w"], p["h"]), fill=(150, 200, 230))
            d.rectangle((0, p["h"] * 0.7, p["w"], p["h"]), fill=(170, 170, 160))
            d.ellipse((p["w"] * 0.4, p["h"] * 0.5, p["w"] * 0.6, p["h"] * 0.9), fill=(90, 140, 70))
        _save(img, p["out"])
        n += 1
        print(f"PIC {n} {p.get('what') or ''}", flush=True)
    for p in job["pictures"]:                              # (depth: lower is nearer, a plain slope)
        src = p.get("depth_of") or (p["out"] if p.get("depth") else None)
        if src and os.path.isfile(src):
            import numpy as np
            w, h = Image.open(src).size
            g = np.repeat(np.linspace(0, 65535, h, dtype=np.float64)[:, None], w, axis=1).astype(np.uint16)
            _save(Image.fromarray(g), p.get("depth") or p["out"])
            if p.get("depth_of"):
                n += 1
                print(f"PIC {n} {p.get('what') or ''}", flush=True)


def depth(job, items, done):
    """Depth maps (Depth Anything V2 Small, on the processor: the card stays free) as 16-bit pictures, light = near."""
    import numpy as np
    import torch
    from PIL import Image
    from transformers import AutoImageProcessor, AutoModelForDepthEstimation
    proc = AutoImageProcessor.from_pretrained(job["depth_model"])
    model = AutoModelForDepthEstimation.from_pretrained(job["depth_model"]).eval()
    torch.set_num_threads(max(1, (os.cpu_count() or 4) // 2))
    for src, out, what, counts in items:
        try:
            im = Image.open(src).convert("RGB")
            with torch.no_grad():
                pred = model(**proc(images=im, return_tensors="pt")).predicted_depth
            d = torch.nn.functional.interpolate(pred.unsqueeze(1), size=im.size[::-1], mode="bicubic", align_corners=False)[0, 0]
            d = d.cpu().numpy().astype(np.float32)
            d = (d - d.min()) / max(1e-6, float(d.max() - d.min()))
            _save(Image.fromarray((d * 65535).astype(np.uint16)), out)
        except Exception as exc:                           # (one picture without depth: it is shown still)
            print(f"DEPTH FAILED {what}: {exc!r}", flush=True)
        if counts:
            done += 1
            print(f"PIC {done} {what}", flush=True)
    return done


def flux(job):
    """Pictures without a reference first, then those drawn from references (a person drawn once, the same in every
    scene), all with the model moved to the card layer by layer (sequential offload): the faster way crashed on the
    owner's RTX 3060 shared with other programs (43 s a reference picture this way). Then the depth maps."""
    pics = list(enumerate(job["pictures"], 1))
    plain = [x for x in pics if not _refs(x[1]) and not x[1].get("depth_of")]
    by_ref = [x for x in pics if _refs(x[1]) and not x[1].get("depth_of")]
    done = 0
    if plain or by_ref:
        import torch
        from diffusers import Flux2KleinPipeline
        from PIL import Image
        for group in (plain, by_ref):
            if not group:
                continue
            better = job.get("quality") == "better" and os.path.isfile(os.path.join(job.get("base") or "", "transformer", "config.json"))
            if better:                                     # (the undistilled model: slower, more careful; guidance)
                from diffusers import Flux2Transformer2DModel
                tr = Flux2Transformer2DModel.from_pretrained(os.path.join(job["base"], "transformer"), torch_dtype=torch.bfloat16)
                pipe = Flux2KleinPipeline.from_pretrained(job["model"], transformer=tr, torch_dtype=torch.bfloat16, is_distilled=False)
            else:
                pipe = Flux2KleinPipeline.from_pretrained(job["model"], torch_dtype=torch.bfloat16)
            pipe.enable_sequential_cpu_offload()
            for _n, p in group:
                kw = dict(prompt=p["prompt"], height=p["h"], width=p["w"], num_inference_steps=20 if better else 4,
                          generator=torch.Generator("cuda").manual_seed(int(p.get("seed") or 7)))
                if better:
                    kw["guidance_scale"] = 4.0
                refs = []
                for r in _refs(p):
                    if os.path.isfile(r):
                        im = Image.open(r).convert("RGB")
                        im.thumbnail((448, 784))
                        refs.append(im)
                if refs:
                    kw["image"] = refs
                _save(pipe(**kw).images[0], p["out"])
                done += 1
                print(f"PIC {done} {p.get('what') or ''}", flush=True)
            del pipe
            torch.cuda.empty_cache()
    items = [(p["out"], p["depth"], p.get("what") or "", False) for _n, p in plain + by_ref if p.get("depth")]
    items += [(p["depth_of"], p["out"], p.get("what") or "", True) for _n, p in pics if p.get("depth_of")]
    items = [x for x in items if os.path.isfile(x[0])]
    if items and job.get("depth_model") and os.path.isfile(os.path.join(job["depth_model"], "model.safetensors")):
        depth(job, items, done)


_DLL: list = []


def main():
    import faulthandler
    faulthandler.enable()                  # (a crash in the graphics card's code: where it was, in the log)
    with open(sys.argv[1], encoding="utf-8") as f:
        job = json.load(f)
    if job.get("site") and not job.get("standin"):
        import site
        site.addsitedir(job["site"])
        if os.name == "nt":                                # (torch's CUDA libraries made known to Windows)
            lib = os.path.join(job["site"], "torch", "lib")
            if os.path.isdir(lib):
                _DLL.append(os.add_dll_directory(lib))
                os.environ["PATH"] = lib + os.pathsep + os.environ.get("PATH", "")
    (standin if job.get("standin") else flux)(job)


if __name__ == "__main__":
    main()
