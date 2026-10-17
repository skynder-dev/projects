# MediaEngine orders — how another program orders a video

Another program on the same PC can order a video from MediaEngine.
Everything goes through folders in the MediaEngine data folder. No network, no keys, no accounts.
MediaEngine never publishes anything and never sends anything anywhere.

```
MediaEngine Data\Orders\
  Inbox\      the program puts orders here
  Received\   orders MediaEngine has taken (their files stay here)
  Done\       answers: <order id>\video.mp4 + result.json + order.json
  Failed\     orders that could not be done: <order id>\result.json says why
```

The orders are handled by the running app (Auto Edit → **Orders**), one at a time. A new order starts at once, or
waits for the owner's **Run** if he chose *Wait for my OK*.

## Sending an order

1. Make a folder `Inbox\<order id>\`. The folder name is the order id: letters, digits, spaces, `. - _ ( )`,
   at most 80 characters, starting with a letter or digit. Every order needs a new id; an id that was already
   received is refused (`ORDER_ID_ALREADY_USED`).
2. Put the order's files into it (pictures, sound, videos).
3. Write `order.json` **last**. MediaEngine takes a folder only when `order.json` is there and nothing in the folder
   changed for 3 seconds. (Or make the folder elsewhere on the same drive and move it into `Inbox` in one step.)

An order that needs no files can also be a single file `Inbox\<order id>.json`.
Names starting with `.`, `~` or `_`, and names ending with `.tmp`, `.part`, `.partial`, `.crdownload` are ignored.

## Getting the answer

Wait for `Done\<order id>\` or `Failed\<order id>\`. Each answer folder appears complete at once (it is written
under a hidden name and then renamed), so when the folder exists, its `result.json` is final.

`result.json` (schema `mediaengine.result/1`):

```json
{
  "schema": "mediaengine.result/1",
  "order_id": "2026-10-17 morning news",
  "status": "done",
  "kind": "render_plan",
  "from": "social",
  "title": "Morning news",
  "order_sha256": "…SHA-256 of the order.json that was done…",
  "received_at": "2026-10-17T03:41:10", "started_at": "2026-10-17T03:41:10", "finished_at": "2026-10-17T03:41:22",
  "mediaengine": {"version": "3.13.0-rc1", "build": "b123"},
  "video": {"file": "video.mp4", "sha256": "…", "bytes": 1330299, "duration_s": 16.5, "width": 1080, "height": 1920},
  "checks": [
    {"check": "video", "pass": true, "detail": "h264"},
    {"check": "size", "pass": true, "detail": "1080x1920"},
    {"check": "length", "pass": true, "detail": "16.500 s (planned 16.500 s)"},
    {"check": "sound", "pass": true, "detail": "aac"},
    {"check": "plays_to_the_end", "pass": true, "detail": "decoded completely"}
  ]
}
```

A failed order has `"status": "failed"`, `"error": {"code": "…", "message": "…"}` and `"can_retry"`.
`video.mp4` is only ever written when every check passed.

## Kind 1: `render_plan` — a video exactly by plan

The program decides everything: pictures and/or pieces of videos, their times, and a sound track (a narration,
for example). MediaEngine renders it: H.264 + AAC MP4, frame-exact times.

```json
{
  "schema": "mediaengine.order/1",
  "kind": "render_plan",
  "from": "social",
  "title": "Morning news",
  "plan": {
    "width": 1080, "height": 1920, "fps": 30,
    "audio": "voice.wav",
    "clips": [
      {"still": "frames/01.png", "start_s": 0.0,   "end_s": 5.9},
      {"still": "frames/02.png", "start_s": 5.9,   "end_s": 12.0},
      {"video": "clips/sea.mp4", "from_s": 12.0, "start_s": 12.0,  "end_s": 16.5, "fit": "fill"}
    ]
  }
}
```

- `plan` can also be the name of a JSON file in the order folder with the same fields (`"plan": "timeline.json"`).
  Fields MediaEngine does not know are ignored.
- `width`, `height`: even, 160–4096 (default 1080×1920). `fps`: 1–60 (default 30).
- `clips`: 1–300 clips, one after another without gaps: the first starts at 0, each starts where the one before ends
  (±0.05 s). A clip is at least 0.1 s. The whole plan is at most 10 minutes.
- A clip has **either** `"still"` (a picture) **or** `"video"` (+ optional `"from_s"`: where in the video to start;
  a video shorter than its clip holds its last frame).
- `"fit"`: `"fit"` = whole picture on black (default for pictures), `"fill"` = cropped to fill the frame (default for videos).
- `audio` (optional): cut or filled with silence to the plan's length. Without it the video gets a silent sound track.
- Only files **inside the order folder** are used (relative paths, no `..`, no absolute or network paths).
- Plain media files only: pictures PNG, JPEG, WebP, BMP, TIFF (at most 50 megapixels); videos MP4/MOV, MKV/WebM, AVI,
  MPEG, MPEG-TS, WMV, FLV (at most 8192 pixels a side); sound WAV, MP3, M4A/AAC, FLAC, OGG, MKA, AIFF.
  Playlists (`.m3u8`, concat lists) are refused whatever their name: they could point to any file on the PC.

## Kind 2: `reel_from_videos` — MediaEngine chooses the moments

The usual Auto Edit reel. It also becomes a normal Auto Edit project (the owner can make variants, edit, export).

```json
{
  "schema": "mediaengine.order/1",
  "kind": "reel_from_videos",
  "from": "social",
  "title": "Sea trip",
  "videos": {"folder": "D:\\Videos\\Trip"},
  "length": 30,
  "format": "social_hd",
  "sound": "auto",
  "mode": "semantic",
  "text": {"title": "Summer 2026", "subtitle": "Black Sea"},
  "music": "D:\\Music\\track.mp3"
}
```

- `videos`: exactly one of
  - `{"folder": "…"}` — a folder of videos (at most 64),
  - `{"files": ["…", "…"]}` — chosen videos,
  - `{"library_theme": "sea"}` — the Library's videos of an AI+ theme (`sea`, `mountains`, `kids`, `family`, … `aerial`).
  Paths are absolute paths on this PC, or relative paths inside the order folder (videos sent with the order).
- `length`: 5, 15, 30, 60 or 120 s. `format`: `social_hd` (1080×1920), `horizontal_hd` (1920×1080), `vertical` (540×960).
- `sound`: `auto`, `source` or `mute`. `mode`: `semantic` (AI), `semantic_plus` (AI+; with `"theme"`), `technical`.
- `framing` (vertical from horizontal videos): `fill` or `fit_blur`. `text`, `music` (+ `music_mode`: `mix`/`music`,
  `beat_sync`: false) are optional.
- Videos marked **Private** or **Rejected** are never used.

The answer has the project (`"project": {"id": …, "url": …, "version": …}`), the settings, the names of the
videos used and the number of moments.

## Answer codes

| code | meaning |
|---|---|
| `ORDER_JSON_INVALID` | order.json is not one valid JSON object |
| `ORDER_SCHEMA_UNKNOWN` / `ORDER_KIND_UNKNOWN` | not `mediaengine.order/1` / unknown `kind` |
| `ORDER_FIELD_INVALID` | a field is wrong (the message names it) |
| `ORDER_FILE_MISSING` / `ORDER_PATH_OUTSIDE` / `ORDER_NETWORK_PATH` | a named file is missing / outside the order folder / on the network |
| `ORDER_ID_INVALID` / `ORDER_ID_ALREADY_USED` | bad or reused order id (the answer is in `Failed\<id> (2)` etc.) |
| `PLAN_TIMES_INVALID` / `PLAN_TOO_LONG` / `PLAN_TOO_MANY_CLIPS` | the plan's times do not fit / > 10 min / > 300 clips |
| `PLAN_IMAGE_UNREADABLE` / `PLAN_VIDEO_UNREADABLE` / `PLAN_AUDIO_UNREADABLE` | a file of the plan cannot be read (or is not a plain media file) |
| `PLAN_IMAGE_TOO_BIG` | a picture has more than 50 megapixels |
| `VIDEOS_NOT_USABLE` / `NO_VIDEOS` / `AIPLUS_NOT_READY` | the videos of a reel order cannot be used |
| `REEL_NOT_STARTED` / `REEL_FAILED` | the reel could not be started / built (the message says why) |
| `RENDER_FAILED` / `OUTPUT_CHECK_FAILED` / `OUTPUT_COPY_FAILED` | the video could not be made / failed its checks / copied |
| `REJECTED_BY_OWNER` / `STOPPED_BY_OWNER` | the owner rejected or stopped it on the Orders page |
| `INTERNAL_ERROR` | a MediaEngine bug: the message has the details |

## Notes

- The app must be running. Orders put in while it is closed are done when it starts. An order interrupted by a restart is done again;
  one started 3 times without finishing waits on the Orders page for **Try again** or **Delete**.
- Deleting an order on the Orders page removes only its folders in `Orders` (never the owner's videos or projects).
- A program on another computer (or in the cloud) cannot reach this folder; copying orders here is the owner's choice.
