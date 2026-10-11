from __future__ import annotations
import json, math, subprocess
from pathlib import Path
import numpy as np
from medeng_media_probe_v41 import probe_json as media_probe_json

ALGO_VERSION = "P11_AUDIO_COHERENCE_SHADOW_V2"
AUDIBLE_THRESHOLD_DBFS = -50.0

def probe_audio_activity(path, ffmpeg="ffmpeg", ffprobe="ffprobe"):
    path=Path(path)
    # Use the same accepted V52 ffmpeg-only input probe. The ffprobe argument
    # is retained for API compatibility but no external ffprobe executable is required.
    meta=media_probe_json(path, ffmpeg=ffmpeg, timeout=30)
    has_audio=any(s.get("codec_type")=="audio" for s in meta.get("streams",[]))
    if not has_audio:
        return {"has_audio_stream":False,"rms_dbfs":-180.0,"audible":False}
    cp=subprocess.run(
        [ffmpeg,"-hide_banner","-loglevel","error","-i",str(path),
         "-vn","-ac","1","-ar","16000","-f","f32le","-"],
        capture_output=True,check=True
    )
    x=np.frombuffer(cp.stdout,dtype="<f4")
    if x.size==0:
        rms_db=-180.0
    else:
        rms=float(np.sqrt(np.mean(x.astype(np.float64)**2)+1e-18))
        rms_db=20.0*math.log10(max(rms,1e-9))
    return {
        "has_audio_stream":True,
        "rms_dbfs":round(float(rms_db),3),
        "audible":bool(rms_db > AUDIBLE_THRESHOLD_DBFS),
    }

def plan_audio(events,user_mode="auto"):
    """Choose only between the two existing V52 modes: source or mute.

    Auto uses actual audible activity (RMS), not merely presence of an audio stream.
    No audio is synthesized; explicit source/mute user intent is always respected.
    """
    mode=str(user_mode or "auto").strip().lower()
    if mode not in ("auto","source","mute"):
        return {"algorithm":ALGO_VERSION,"mode":"mute","reason":"invalid_mode_fail_closed","changed":True}

    flags=[bool(e.get("audible",False)) for e in (events or [])]
    hazards=sum(a!=b for a,b in zip(flags,flags[1:]))

    if mode=="source":
        return {"algorithm":ALGO_VERSION,"mode":"source","reason":"explicit_source",
                "audible_presence":flags,"hazard_edges":hazards,"changed":False}
    if mode=="mute":
        return {"algorithm":ALGO_VERSION,"mode":"mute","reason":"explicit_mute",
                "audible_presence":flags,"hazard_edges":hazards,"changed":False}

    if not flags or not any(flags):
        return {"algorithm":ALGO_VERSION,"mode":"mute","reason":"no_audible_source_audio",
                "audible_presence":flags,"hazard_edges":0,"changed":True}

    if hazards>0:
        return {
            "algorithm":ALGO_VERSION,"mode":"mute",
            "reason":"mixed_audible_activity_continuity_guard",
            "audible_presence":flags,"hazard_edges":hazards,
            "audible_clip_count":sum(flags),"silent_clip_count":len(flags)-sum(flags),
            "changed":True,
        }

    return {
        "algorithm":ALGO_VERSION,"mode":"source","reason":"continuous_audible_source_audio",
        "audible_presence":flags,"hazard_edges":0,
        "audible_clip_count":sum(flags),"silent_clip_count":len(flags)-sum(flags),
        "changed":False,
    }
