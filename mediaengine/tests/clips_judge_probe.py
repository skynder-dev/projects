"""Would a small local language model choose better clips than the word counting of clips.py? (a research probe)

  python tests/clips_judge_probe.py --found clips_found.json --words clips_words.json --out <dir> [--models a,b]

The clips found in a real public-domain NASA interview by the voice add-on check (Whisper's words, the program's own
scoring) are read by each model: per clip one look (no text written), the chances it gives to the answers 0..9 to
"how well does this work as a short clip on its own" -> its expected mark. Writes judge_probe.json (marks, time per
clip, the model's revision) and judge_probe.md (the clips in the program's order and in each model's order, with
their opening words) to compare by reading. Free models from Hugging Face (Apache-2.0); nothing paid, nothing sent
anywhere but the downloads. Not part of the program.
"""
from __future__ import annotations

import argparse, json, sys, time
from pathlib import Path

PROMPT = ("Below are the words of a part of a long talk (an interview, podcast or stream), {secs:.0f} seconds long. "
          "Someone wants to post it on its own as a short vertical video (TikTok, Reels, Shorts).\n\n"
          "\"\"\"{text}\"\"\"\n\n"
          "How well does this part work as a short video on its own? Think of a viewer scrolling past: does the first "
          "sentence make them stay, can they follow it without the rest of the talk, does it have a point, a story, "
          "a surprise, an emotion or a laugh? Radio or sound checks, greetings, thanks, introductions and goodbyes "
          "without anything else are bad. Answer with one digit from 0 (useless) to 9 (excellent).")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--found", required=True); ap.add_argument("--words", default=""); ap.add_argument("--out", required=True)
    ap.add_argument("--models", default="Qwen/Qwen3-1.7B,Qwen/Qwen3-4B-Instruct-2507")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    found = json.loads(Path(a.found).read_text("utf-8"))
    cands = found["candidates"]
    import torch
    from huggingface_hub import snapshot_download
    from transformers import AutoModelForCausalLM, AutoTokenizer
    torch.set_num_threads(max(1, torch.get_num_threads()))
    report = {"video": found.get("video"), "candidates": [{k: c[k] for k in ("id", "s", "e", "score", "why", "first")}
                                                          for c in cands], "models": {}}
    for repo in [m.strip() for m in a.models.split(",") if m.strip()]:
        t0 = time.time()
        try:
            path = snapshot_download(repo, allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model", "*.jinja"])
            tok = AutoTokenizer.from_pretrained(path)
            dtype = torch.float32 if "1.7B" in repo or "0.6B" in repo else torch.bfloat16
            model = AutoModelForCausalLM.from_pretrained(path, dtype=dtype)
            model.eval()
        except Exception as exc:
            report["models"][repo] = {"error": f"{type(exc).__name__}: {exc}"[:500]}
            continue
        load_s = round(time.time() - t0, 1)
        digits = [tok.convert_tokens_to_ids(str(d)) for d in range(10)]
        marks = []
        for c in cands:
            msgs = [{"role": "user", "content": PROMPT.format(secs=c["e"] - c["s"], text=c["text"])}]
            try:
                ids = tok.apply_chat_template(msgs, add_generation_prompt=True, enable_thinking=False, return_tensors="pt")
            except TypeError:
                ids = tok.apply_chat_template(msgs, add_generation_prompt=True, return_tensors="pt")
            if not torch.is_tensor(ids):
                ids = ids["input_ids"]
            t1 = time.time()
            with torch.no_grad():
                logits = model(ids).logits[0, -1].float()
            p = torch.softmax(logits[digits], dim=0)
            mark = float((p * torch.arange(10)).sum())
            marks.append({"id": c["id"], "mark": round(mark, 2), "top": int(p.argmax()), "sure": round(float(p.max()), 2),
                          "digit_share": round(float(torch.softmax(logits, 0)[digits].sum()), 3), "s": round(time.time() - t1, 2),
                          "tokens": int(ids.shape[1])})
            print(repo, c["id"], marks[-1], flush=True)
        rev = ""
        try:
            rev = Path(path).name
        except Exception:
            pass
        report["models"][repo] = {"revision": rev, "load_s": load_s, "marks": marks}
        del model
    (out / "judge_probe.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), "utf-8")
    md = ["# Clips of the NASA interview: the program's order and each model's", ""]
    md.append("## The program's order (word counting)")
    md += [f"{k + 1}. [{c['score']}] {c['s']:.0f}-{c['e']:.0f} s: {c['text'][:120]}" for k, c in enumerate(cands)]
    for repo, r in report["models"].items():
        md += ["", f"## {repo} ({r.get('error') or str(r.get('load_s')) + ' s to load'})"]
        by = {c["id"]: c for c in cands}
        for k, m in enumerate(sorted(r.get("marks", []), key=lambda x: -x["mark"])):
            c = by[m["id"]]
            md.append(f"{k + 1}. [{m['mark']:.1f}, program {c['score']}] {c['s']:.0f}-{c['e']:.0f} s: {c['text'][:120]}")
    (out / "judge_probe.md").write_text("\n".join(md) + "\n", "utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
