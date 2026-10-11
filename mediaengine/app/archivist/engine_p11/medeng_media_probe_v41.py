#!/usr/bin/env python3
from __future__ import annotations
import os, re, subprocess
from fractions import Fraction
from pathlib import Path

CANDIDATE = 'MEDENG_MEDIA_PROBE_V41_FFMPEG_ONLY'
DEFAULT_FFMPEG = os.environ.get('MEDENG_FFMPEG','ffmpeg')
_DURATION_RE = re.compile(r'Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)')
_STREAM_RE = re.compile(r'^\s*Stream #\d+:(\d+)(?:\[[^\]]+\])?(?:\([^)]*\))?:\s*(Video|Audio):\s*([^,\s]+)', re.I)
_SIZE_RE = re.compile(r'(?<!\d)(\d{2,5})x(\d{2,5})(?!\d)')
_FPS_RE = re.compile(r'(?<![\d.])(\d+(?:\.\d+)?)\s*fps\b', re.I)

class ProbeError(RuntimeError):
    pass

def _rate_string(value: float | None) -> str | None:
    if not value or value <= 0:
        return None
    return f'{Fraction(str(round(value, 6))).limit_denominator(100000).numerator}/{Fraction(str(round(value, 6))).limit_denominator(100000).denominator}'

def probe_json(path: str | Path, ffmpeg: str = DEFAULT_FFMPEG, timeout: int = 30) -> dict:
    p = Path(path)
    if not p.is_file():
        raise ProbeError('PROBE_INPUT_MISSING:' + str(p))
    cmd = [str(ffmpeg), '-hide_banner', '-nostdin', '-i', str(p),
           '-map', '0:v:0?', '-map', '0:a:0?', '-t', '0.001', '-f', 'null', '-']
    cp = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                        text=True, errors='replace', timeout=timeout, check=False)
    text = cp.stderr or ''
    # Restrict parsing to input description. Output streams may have converted codecs.
    marker = text.find('Stream mapping:')
    if marker >= 0:
        text = text[:marker]
    dm = _DURATION_RE.search(text)
    if not dm:
        raise ProbeError('FFMPEG_INPUT_DURATION_MISSING:' + text[-1200:])
    duration = int(dm.group(1))*3600 + int(dm.group(2))*60 + float(dm.group(3))
    if duration <= 0:
        raise ProbeError('FFMPEG_INPUT_DURATION_INVALID')
    streams = []
    seen = set()
    for raw in text.splitlines():
        sm = _STREAM_RE.match(raw)
        if not sm:
            continue
        idx = int(sm.group(1)); typ = sm.group(2).lower(); codec = sm.group(3).lower()
        key = (idx, typ)
        if key in seen:
            continue
        seen.add(key)
        row = {'index': idx, 'codec_type': typ, 'codec_name': codec}
        if typ == 'video':
            zm = _SIZE_RE.search(raw)
            if zm:
                row['width'] = int(zm.group(1)); row['height'] = int(zm.group(2))
            fm = _FPS_RE.search(raw)
            if fm:
                row['r_frame_rate'] = _rate_string(float(fm.group(1)))
        streams.append(row)
    if not any(x.get('codec_type') == 'video' for x in streams):
        raise ProbeError('FFMPEG_INPUT_VIDEO_STREAM_MISSING:' + text[-1200:])
    return {
        'candidate': CANDIDATE,
        'format': {'duration': f'{duration:.6f}'},
        'streams': streams,
        'probe_backend': 'FFMPEG_INPUT_METADATA_V41',
        'external_ffprobe_required': False,
    }

def duration(path: str | Path, ffmpeg: str = DEFAULT_FFMPEG, timeout: int = 30) -> float:
    return float(probe_json(path, ffmpeg, timeout)['format']['duration'])
