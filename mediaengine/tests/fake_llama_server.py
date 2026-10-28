"""A stand-in for llama.cpp's server in the checks of Cartoon Studio's story writer (writer_check.py): the same
command line, /health and a streamed /v1/chat/completions that answers with fixed stories - no model.

  python fake_llama_server.py -m <model> --port <p> --api-key <k> [-ngl 99] [--device none] ...

FAKE_LLAMA_GPU_FAIL=1: exits at once when asked for the graphics card (the writer then starts it on the processor).
FAKE_LLAMA_RECORD=<dir>: every request is written there (request_<time>.json).
"""
from __future__ import annotations

import argparse, json, os, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

STORY_EN = """Title: Why the Hospital Pays Three Times More
Format: vertical
Narrator: Anna (woman, narrator)
Doctor Paul (man, doctor)
Victor Price (man, supplier boss)
Clerk Sam (man, official)

== City street | title: Why the Hospital Pays More / for the same medicine
Anna (wave, happy): Every hospital buys medicine. So why does ours pay three times more for the same box?

== Office | tender: TENDER; brand X only; delivery in 2 days; 3 days to apply
Anna (explain, sly): Clerk Sam writes a tender that only one supplier can win.
Clerk Sam (present, sly): Just normal requirements!

== Night | bag: thank you
Victor Price (rubs hands, sly) [bubble]: Win it for me, and I will thank you.
Anna: Only Victor's company fits the rules. What a surprise.

== Office | contract: CONTRACT; price $90 a box; stamp APPROVED
Anna: The hospital signs. Ninety dollars a box, when a pharmacy sells it for thirty.
Doctor Paul (facepalm, sad): The same pills. Three times the price.

== Board | flow: Hospital -> Price Pharma $900K; Price Pharma -> Officials kickback
Anna: The hospital pays nine hundred thousand dollars.
Anna: And part of it quietly goes back to the officials who signed.

== Board | bars: pharmacy 30, hospital 90 $
Anna: Thirty dollars in a pharmacy, ninety in the hospital.
Doctor Paul (angry, fist): That money could pay for two more nurses.

== City hall | list: Red flags; One bidder; A brand name in the tender; A price far above the shops
Anna (point up, happy): Look for one bidder, a brand name in the rules, and a price far above the shops.
Anna (wave, happy): Follow the money. Ask who wrote the tender.
"""

STORY_RU = """Title: Как город теряет миллионы на ремонте дороги
Format: vertical
Narrator: Катя (woman, narrator)
Мэр Громов (man, мэр)
Чиновник Эдуард (man, чиновник)
Рустам Каменев (man, подрядчик)
Борис (man, дорожный рабочий)
Лена (woman, журналистка)

== City street | title: Как город теряет миллионы / на простом ремонте дороги
Катя (wave, happy): Дорога вся в ямах. Отремонтировать её просто, правда?
Катя (explain, sly): Посмотрим, как это обходится городу в миллионы.

== Road | road
Лена (shrug, angry) [bubble]: Это не дорога, а катастрофа!
Катя: Город объявляет тендер на ремонт двух километров дороги.
Катя: Честная цена — около ста двадцати миллионов рублей.

== Office | tender: TENDER; опыт 10 лет; особый асфальт; 5 дней на заявку
Катя: Но Эдуард пишет условия тендера под одну фирму.
Чиновник Эдуард (present, sly): Совершенно обычные требования!

== Night
Рустам Каменев (rubs hands, sly) [bubble]: Мы выиграем, а вас отблагодарят.
Чиновник Эдуард (sneaky, happy): Люблю, когда благодарят.

== Office | contract: CONTRACT; price 480 млн ₽; stamp APPROVED
Катя: Фирма Каменева побеждает с ценой в четыре раза выше рынка.
Мэр Громов (point up, happy): Утверждаю! Наш город достоин лучшего!

== Board | flow: Бюджет -> ДорСтрой 480 млн; ДорСтрой -> Бригада 100 млн; ДорСтрой -> Чиновники откат
Катя: Город платит четыреста восемьдесят миллионов рублей.
Катя: Дешёвая бригада получает сто миллионов, а часть разницы тихо уходит чиновникам.

== Road | road: repair
Борис (shrug, worried) [bubble]: Асфальта вполовину меньше, сказал начальник.
Катя: Ямы закрывают тонким слоем. Выглядит хорошо. Пока.

== Road | road: holes back
Катя: Одна зима, и ямы вернулись. Все до одной.
Лена (facepalm, sad): Опять те же ямы.

== Board | bars: честная цена 120, заплатили 960 млн
Катя: Одна дорога. Заплатили в восемь раз больше честной цены.

== City hall | list: Признаки; Одна заявка; Сжатые сроки; Цена выше рынка
Лена (point up, angry): Одна заявка, сжатые сроки и цена выше рынка.
Катя (wave, happy): Следите за деньгами и спрашивайте, кто писал тендер.
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-m"); ap.add_argument("-c"); ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, required=True); ap.add_argument("--api-key", default="")
    ap.add_argument("-np"); ap.add_argument("--jinja", action="store_true"); ap.add_argument("-ngl", default="99")
    ap.add_argument("--device", default="")
    a, _rest = ap.parse_known_args()
    gpu = a.ngl != "0" and a.device != "none"
    print(f"main: model {a.m}", flush=True)
    if gpu and os.environ.get("FAKE_LLAMA_GPU_FAIL") == "1":
        print("ggml_vulkan: device lost (a stand-in failure)", flush=True)
        return 1
    if gpu:
        print("ggml_vulkan: Found 1 Vulkan devices:\nggml_vulkan: 0 = Fake GPU 3000 (Test) | uma: 0 | fp16: 1", flush=True)
        print("load_tensors: offloaded 37/37 layers to GPU", flush=True)
    else:
        print("load_tensors: offloaded 0/37 layers to GPU", flush=True)
    record = os.environ.get("FAKE_LLAMA_RECORD")
    seen = [0]

    class H(BaseHTTPRequestHandler):
        def _send(self, code: int, obj) -> None:
            b = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            if self.path == "/health":
                return self._send(200, {"status": "ok"})
            self._send(404, {})

        def do_POST(self):
            if a.api_key and self.headers.get("Authorization") != f"Bearer {a.api_key}":
                return self._send(401, {"error": "Invalid API Key"})
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
            if record:
                seen[0] += 1                   # (named by the time: every server started writes beside the others)
                Path(record).mkdir(parents=True, exist_ok=True)
                Path(record, f"request_{time.time_ns()}.json").write_text(json.dumps(body, ensure_ascii=False, indent=1), "utf-8")
            msgs = body.get("messages") or []
            user = str(msgs[-1].get("content") or "") if msgs else ""
            everything = " ".join(str(m.get("content") or "") for m in msgs)
            slow = "TOPIC: slow" in everything
            if "Answer with one word" in user:
                text = "Ready"
            elif "Retell this cartoon script" in everything:
                text = STORY_RU
            elif "TOPIC: broken" in everything and "This script cannot be used" not in everything:
                text = "Sorry, I can only write a short note about it."
            else:
                text = "```\n" + STORY_EN + "```\n"
            if body.get("stream") is False:            # (the writer probe asks for the whole answer at once)
                return self._send(200, {"choices": [{"index": 0, "message": {"role": "assistant", "content": text},
                                                     "finish_reason": "stop"}], "usage": {"completion_tokens": len(text) // 4},
                                        "timings": {"predicted_per_second": 42.0}})
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            pieces = [text[i:i + 12] for i in range(0, len(text), 12)]
            try:
                for p in pieces:
                    chunk = {"choices": [{"index": 0, "delta": {"content": p}, "finish_reason": None}]}
                    self.wfile.write(b"data: " + json.dumps(chunk, ensure_ascii=False).encode("utf-8") + b"\n\n")
                    self.wfile.flush()
                    if slow:
                        time.sleep(0.25)
                end = {"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                       "usage": {"prompt_tokens": len(everything) // 4, "completion_tokens": len(pieces)},
                       "timings": {"predicted_per_second": 42.0}}
                self.wfile.write(b"data: " + json.dumps(end).encode() + b"\n\ndata: [DONE]\n\n")
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, *args):
            pass

    srv = ThreadingHTTPServer((a.host, a.port), H)
    print(f"main: server is listening on http://{a.host}:{a.port}", flush=True)
    srv.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
