"""Research probe for a free local picture maker (MediaEngine, later Merch Forge's designs and cartoon art).

FLUX.2 [klein] 4B (Black Forest Labs, Apache-2.0) through diffusers on the runner's processor: does it load, how much
memory and time does a picture take, how does it draw a merch illustration from a Forge brief, and how does it draw
exact words? Not part of the program; nothing paid. Memory: the text encoder and the image model are never in memory
together (prompts are encoded first, the encoder is dropped, then the pictures are drawn), so the 16 GB runner holds it.

Writes <out>/picture_probe.md, <out>/<name>.png and <out>/probe.json.
"""
import argparse
import gc
import inspect
import json
import os
import platform
import resource
import sys
import time
import traceback

# Three Forge briefs (MIGRATION/forge/2026-10-30/source_material/concepts/050_GENERATION_BRIEFS): the visual
# direction alone, drawn without words (the words are set later with a real font), and one with the exact words.
STYLE = ("flat vector t-shirt graphic, bold clean shapes, thick outlines, limited palette of 3 colors, centered "
         "composition, isolated on a plain pure white background, no text, no letters, no words")
CASES = [
    ("relay_meeting_art", "A tiny electrical toggle switch on a small panel casting a huge shadow shaped like a long "
     "conference table with many chairs. " + STYLE),
    ("dust_authority_art", "A single tiny speck of dust wearing a boss badge, floating above a worker in a white "
     "cleanroom bunny suit who looks up respectfully. " + STYLE),
    ("walk_fix_art", "A big clock showing 20:00 next to a small stopwatch showing 0:30, one small screwdriver "
     "between them. " + STYLE),
    ("relay_meeting_words", "Apparel graphic: a tiny toggle switch casting a huge conference-table shadow, with the "
     "text \"ONE CLICK AWAY FROM A VERY LARGE MEETING.\" in bold block letters, written exactly once. Flat vector, "
     "limited palette, plain pure white background."),
]


def rss_gb():
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6, 2)   # Linux: kilobytes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="the downloaded diffusers folder")
    ap.add_argument("--out", required=True)
    ap.add_argument("--size", type=int, default=512)
    ap.add_argument("--steps", type=int, default=4)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    import torch
    import diffusers
    import transformers
    torch.set_num_threads(os.cpu_count() or 4)
    rep = {"python": sys.version.split()[0], "torch": torch.__version__, "diffusers": diffusers.__version__,
           "transformers": transformers.__version__, "cpu": platform.processor() or platform.machine(),
           "threads": torch.get_num_threads(), "size": a.size, "steps": a.steps, "cases": []}
    lines = ["# picture probe: FLUX.2 [klein] 4B on the processor", ""]
    Pipe = getattr(diffusers, "Flux2KleinPipeline", None)
    rep["pipeline"] = Pipe.__name__ if Pipe else None
    if Pipe is None:
        rep["error"] = "diffusers has no Flux2KleinPipeline"
        json.dump(rep, open(os.path.join(a.out, "probe.json"), "w"), indent=1)
        print(rep["error"])
        return 1
    rep["call_args"] = list(inspect.signature(Pipe.__call__).parameters)
    rep["encode_args"] = list(inspect.signature(Pipe.encode_prompt).parameters) if hasattr(Pipe, "encode_prompt") else None
    dtype = torch.bfloat16
    embeds = {}
    try:
        t0 = time.time()
        enc = Pipe.from_pretrained(a.model, transformer=None, vae=None, torch_dtype=dtype)
        rep["encoder_load_s"] = round(time.time() - t0, 1)
        for name, prompt in CASES:
            t0 = time.time()
            with torch.inference_mode():
                out = enc.encode_prompt(prompt=prompt, device="cpu")
            embeds[name] = out
            print(name, "encoded in", round(time.time() - t0, 1), "s", flush=True)
        del enc
        gc.collect()
        rep["after_encoder_rss_gb"] = rss_gb()
        split = True
    except Exception:
        rep["split_error"] = traceback.format_exc()[-1500:]
        print(rep["split_error"], flush=True)
        split = False
    t0 = time.time()
    if split:
        pipe = Pipe.from_pretrained(a.model, text_encoder=None, tokenizer=None, torch_dtype=dtype)
    else:
        pipe = Pipe.from_pretrained(a.model, torch_dtype=dtype)
    rep["model_load_s"] = round(time.time() - t0, 1)
    for name, prompt in CASES:
        kw = dict(height=a.size, width=a.size, num_inference_steps=a.steps,
                  generator=torch.Generator("cpu").manual_seed(7))
        if split:
            e = embeds[name]
            if isinstance(e, tuple):
                kw["prompt_embeds"] = e[0]
                if len(e) > 1 and "text_ids" in rep["call_args"]:
                    kw["text_ids"] = e[1]
                rep.setdefault("embed_parts", len(e))
            else:
                kw["prompt_embeds"] = e
        else:
            kw["prompt"] = prompt
        t0 = time.time()
        try:
            with torch.inference_mode():
                img = pipe(**kw).images[0]
            sec = round(time.time() - t0, 1)
            img.save(os.path.join(a.out, name + ".png"))
            rep["cases"].append({"name": name, "seconds": sec, "ok": True})
            lines.append(f"- {name}: {sec} s")
            print(name, sec, "s", flush=True)
        except Exception:
            err = traceback.format_exc()[-1500:]
            rep["cases"].append({"name": name, "ok": False, "error": err})
            lines.append(f"- {name}: failed")
            print(err, flush=True)
    rep["peak_rss_gb"] = rss_gb()
    lines += ["", "```", json.dumps({k: v for k, v in rep.items() if k != "cases"}, indent=1)[:4000], "```"]
    open(os.path.join(a.out, "picture_probe.md"), "w").write("\n".join(lines) + "\n")
    json.dump(rep, open(os.path.join(a.out, "probe.json"), "w"), indent=1)
    return 0 if all(c["ok"] for c in rep["cases"]) else 1


if __name__ == "__main__":
    sys.exit(main())
