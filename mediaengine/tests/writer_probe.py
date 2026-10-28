"""Which free local model writes Cartoon Studio's stories well enough? (a research probe, not part of the program)

  python tests/writer_probe.py --server http://127.0.0.1:8090 --out <dir> [--label 4b] [--only en_topic,...]

The program's own requests (cartoon/writer.py: prompt, clean, judge) sent to a llama.cpp server already running a
model: a topic in English and in Russian, a pasted text, the example story retold for Romania and for Russia. Per task:
the time and tokens, the story as the model wrote it, what the program reads from it (scenes, lines, words, pictures,
gestures and feelings understood, the judge's verdict) and a picture of every scene drawn by the program.
Writes writer_probe.json, writer_probe.md, <task>.txt, sheet_<task>.png.
"""
from __future__ import annotations

import argparse, json, re, sys, time, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "app"))

SOURCE = """In 2024 the education department of a mid-sized region bought 2,000 laptops for its schools. The tender was
open for only six days and asked for a laptop with a rare combination of features that only one model on the market had.
Only one company applied: a firm registered eight months earlier, whose co-owner is the brother-in-law of the
department's deputy head. It won at 1,450 dollars per laptop, 2.9 million dollars in total, while the same model sold in
ordinary shops for about 600 dollars. Auditors later found that a third of the laptops were never delivered: they exist
only in the acceptance papers signed by the department. Teachers say the delivered ones were slow and broke within a year."""

TASKS = [
    {"id": "en_topic", "mode": "topic", "lang": "en", "format": "vertical", "secs": 75,
     "topic": "Why a city hospital pays three times more for the same medicine"},
    {"id": "ru_topic", "mode": "topic", "lang": "ru", "format": "vertical", "secs": 75,
     "topic": "Как управляющая компания зарабатывает на ремонте подъезда, который так и не сделали"},
    {"id": "en_text", "mode": "text", "lang": "en", "format": "horizontal", "secs": 80, "source": SOURCE},
    {"id": "ro_adapt", "mode": "adapt", "lang": "ro", "country": "Moldova", "format": "vertical"},
    # the rhythm of a studied reference (Reference Lab): quick cuts and lively speech, then a calm one
    {"id": "en_quick", "mode": "topic", "lang": "en", "format": "vertical", "secs": 60,
     "topic": "How a school pays twice for the same meals",
     "style": {"shot_avg": 3.0, "wps": 2.9, "first_at": 0.4, "opens": "question"}},
    {"id": "ru_calm", "mode": "topic", "lang": "ru", "format": "horizontal", "secs": 90,
     "topic": "Как район платит за уборку снега, которой не было",
     "style": {"shot_avg": 11.0, "wps": 1.9, "first_at": 2.5, "opens": "statement"}},
    {"id": "ru_adapt", "mode": "adapt", "lang": "ru", "country": "Russia", "format": "vertical"},
]


def ask(server: str, messages: list, max_tokens: int = 2600) -> dict:
    body = {"messages": messages, "temperature": 0.7, "top_p": 0.8, "top_k": 20, "min_p": 0.0, "repeat_penalty": 1.05,
            "max_tokens": max_tokens, "stream": False, "seed": 7, "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(server.rstrip("/") + "/v1/chat/completions", json.dumps(body).encode("utf-8"),
                                 {"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=7200) as r:
        res = json.load(r)
    return {"text": res["choices"][0]["message"]["content"], "s": round(time.time() - t0, 1), "usage": res.get("usage") or {},
            "timings": res.get("timings") or {}, "finish": res["choices"][0].get("finish_reason")}


def sheet(sc: dict, out: Path) -> None:
    import cv2, numpy as np
    from archivist.cartoon import film as F
    from archivist.cartoon.draw import Canvas
    film = F.check_script(sc)
    tl = F.timeline(film)
    W, H = F.FORMATS[film["format"]]
    w, h = W // 3, H // 3
    tiles = []
    for s in tl["scenes"]:
        cv = Canvas(w, h, 1920 if W >= H else 1080)
        t = (s["lines"][-1]["s"] + s["lines"][-1]["e"]) / 2 if s["lines"] else s["e"] - 0.5
        F.draw_frame(cv, film, s, max(s["s"] + 0.3, t), {})
        tiles.append(cv.img.copy())
    cols = 4 if W < H else 3
    rows = (len(tiles) + cols - 1) // cols
    grid = np.full((rows * h, cols * w, 3), 255, np.uint8)
    for i, im in enumerate(tiles):
        r, c = divmod(i, cols)
        grid[r * h:(r + 1) * h, c * w:(c + 1) * w] = im
    cv2.imwrite(str(out), grid)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--label", default=""); ap.add_argument("--only", default="")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    from archivist.cartoon import film as F, textscript as T, writer as W
    report = {"label": a.label, "tasks": []}
    md = [f"# Cartoon Studio stories: {a.label}\n"]
    for task in TASKS:
        if a.only and task["id"] not in a.only.split(","):
            continue
        job = dict(task)
        if task["mode"] == "adapt":
            job["source"] = T.ROAD_TEXT
        secs = int(task.get("secs") or 75)
        if task["mode"] == "adapt":
            src = T.parse(T.ROAD_TEXT)
            secs = max(30, int(sum(len(ln["text"].split()) for s in src["scenes"] for ln in s["lines"]) / 2.2))
        messages = [{"role": "system", "content": W.SYSTEM}, {"role": "user", "content": W.prompt(job)}]
        print(f"== {task['id']}: asking", flush=True)
        tries = []
        text, problem = "", "not asked"
        for attempt in range(2):
            try:
                ans = ask(a.server, messages)
            except Exception as exc:
                tries.append({"error": repr(exc)})
                break
            text = W.clean(ans["text"], task["format"])
            info, problem = W.judge(text, secs, task.get("style"))
            tries.append({"s": ans["s"], "usage": ans["usage"], "finish": ans["finish"], "problem": problem,
                          "speed": {k: ans["timings"].get(k) for k in ("prompt_per_second", "predicted_per_second")}})
            if not problem:
                break
            messages += [{"role": "assistant", "content": ans["text"]},
                         {"role": "user", "content": f"This script cannot be used: {problem}. Write the whole script again, "
                                                     "exactly in THE FORMAT, with all its scenes."}]
        (out / f"{task['id']}.txt").write_text(text, "utf-8")
        sc = T.parse(text) if text else {"scenes": [], "cast": {}}
        lines = [ln for s in sc["scenes"] for ln in s["lines"]]
        row = {"id": task["id"], "task": {k: v for k, v in task.items() if k != "source"}, "tries": tries, "problem": problem,
               "scenes": len(sc["scenes"]), "lines": len(lines), "words": sum(len(ln["text"].split()) for ln in lines),
               "visuals": [(s.get("visual") or {}).get("kind", "-") for s in sc["scenes"]], "bgs": [s["bg"] for s in sc["scenes"]],
               "poses": sum(1 for ln in lines if ln.get("pose")), "feelings": sum(1 for ln in lines if ln.get("emotion")),
               "cast": {c.get("name"): [c.get("role"), c.get("female")] for c in sc["cast"].values()},
               "language": sc.get("language")}
        if task.get("style"):                              # (what the rhythm asked: scenes from-to, words)
            from archivist.cartoon import reference as R
            lo, hi, w_ = R.targets(task["style"], secs)
            row["asked"] = {"scenes": [lo, hi], "words": w_, "followed": lo <= len(sc["scenes"]) <= hi}
        if sc["scenes"]:
            try:
                row["seconds_estimated"] = F.timeline(F.check_script(sc))["seconds"]
                sheet(sc, out / f"sheet_{task['id']}.png")
            except Exception as exc:
                row["sheet_error"] = repr(exc)
        report["tasks"].append(row)
        print(f"   {json.dumps({k: row[k] for k in ('scenes', 'lines', 'words', 'poses', 'feelings', 'problem')}, ensure_ascii=False)} "
              f"~{row.get('seconds_estimated')} s, tries {tries}", flush=True)
        md += [f"## {task['id']}", "", f"- tries: {json.dumps(tries, ensure_ascii=False)}",
               f"- read: scenes {row['scenes']}, lines {row['lines']}, words {row['words']}, ~{row.get('seconds_estimated')} s, "
               f"gestures {row['poses']}/{row['lines']}, feelings {row['feelings']}/{row['lines']}, visuals {row['visuals']}",
               f"- cast: {json.dumps(row['cast'], ensure_ascii=False)}", f"- problem: {problem or '-'}", "", "```", text.strip(), "```", ""]
    (out / "writer_probe.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), "utf-8")
    (out / "writer_probe.md").write_text("\n".join(md), "utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
