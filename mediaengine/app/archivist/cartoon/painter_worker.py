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


def standin(job):
    from PIL import Image, ImageDraw
    for n, p in enumerate(job["pictures"], 1):
        img = Image.new("RGB", (p["w"], p["h"]), (250, 250, 250))
        d = ImageDraw.Draw(img)
        if p.get("ref") is not None or "Full body" in p["prompt"]:
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
        _save(img, p["out"])
        print(f"PIC {n} {p.get('what') or ''}", flush=True)


def flux(job):
    """Pictures without a reference first (the model moved to the card part by part: fast), then those drawn from a
    reference with the model moved layer by layer (sequential offload): a reference needs more of the card than a 12 GB
    card shared with other programs has, and without it a picture took half an hour (measured on the owner's RTX 3060:
    43 s instead)."""
    import torch
    from diffusers import Flux2KleinPipeline
    from PIL import Image
    pics = list(enumerate(job["pictures"], 1))
    plain = [x for x in pics if not x[1].get("ref")]
    by_ref = [x for x in pics if x[1].get("ref")]
    done = 0
    for group, seq in ((plain, False), (by_ref, True)):
        if not group:
            continue
        pipe = Flux2KleinPipeline.from_pretrained(job["model"], torch_dtype=torch.bfloat16)
        pipe.enable_sequential_cpu_offload() if seq else pipe.enable_model_cpu_offload()
        for _n, p in group:
            kw = dict(prompt=p["prompt"], height=p["h"], width=p["w"], num_inference_steps=4,
                      generator=torch.Generator("cuda").manual_seed(int(p.get("seed") or 7)))
            if p.get("ref") and os.path.isfile(p["ref"]):
                ref = Image.open(p["ref"]).convert("RGB")
                ref.thumbnail((448, 784))
                kw["image"] = [ref]
            _save(pipe(**kw).images[0], p["out"])
            done += 1
            print(f"PIC {done} {p.get('what') or ''}", flush=True)
        del pipe
        torch.cuda.empty_cache()


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
