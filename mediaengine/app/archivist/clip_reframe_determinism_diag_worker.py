from __future__ import annotations
import json,math,tempfile
from pathlib import Path

def main():
    from archivist import media_brain as mb
    from archivist import composer
    from archivist import clip_export as ce

    result={}

    # 1) Crop-keyframe validation/interpolation must be deterministic and bounded.
    keys=[
      {"time_ms":0,"x":0.10,"y":0.20,"w":0.70,"h":0.60,"confidence":0.20,"locked":0},
      {"time_ms":500,"x":0.20,"y":0.10,"w":0.60,"h":0.70,"confidence":0.80,"locked":0},
      {"time_ms":1000,"x":0.30,"y":0.15,"w":0.50,"h":0.60,"confidence":1.20,"locked":1},
    ]
    a=mb.validate_crop_keyframes(keys,1000)
    b=mb.validate_crop_keyframes(keys,1000)
    result["keyframe_validation_repeatable"]=(a==b and a[-1]["confidence"]==1.0)
    samples=[-100,0,1,125,250,499,500,501,750,999,1000,1200]
    run1=[mb.interpolate_crop_keyframes(keys,t) for t in samples]
    run2=[mb.interpolate_crop_keyframes(keys,t) for t in samples]
    result["interpolation_repeatable"]=(run1==run2)
    result["interpolation_clamps_endpoints"]=(run1[0]["time_ms"]==0 and run1[-1]["time_ms"]==1000)
    result["interpolation_stays_in_bounds"]=all(
      0<=r["x"]<=1 and 0<=r["y"]<=1 and r["w"]>0 and r["h"]>0
      and r["x"]+r["w"]<=1.000001 and r["y"]+r["h"]<=1.000001
      and 0<=r["confidence"]<=1
      for r in run1
    )
    invalid=[
      [{"time_ms":0,"x":0,"y":0,"w":1,"h":1},{"time_ms":0,"x":0,"y":0,"w":1,"h":1}],
      [{"time_ms":5,"x":0,"y":0,"w":1,"h":1},{"time_ms":4,"x":0,"y":0,"w":1,"h":1}],
      [{"time_ms":1001,"x":0,"y":0,"w":1,"h":1}],
      [{"time_ms":0,"x":float("nan"),"y":0,"w":1,"h":1}],
      [{"time_ms":0,"x":0.9,"y":0,"w":0.2,"h":1}],
    ]
    blocked=0
    for case in invalid:
      try: mb.validate_crop_keyframes(case,1000)
      except (ValueError,TypeError): blocked+=1
    result["invalid_keyframes_fail_closed"]=(blocked==len(invalid))

    # 2) Pan limiter: displacement may never exceed rate*dt and output is repeatable.
    pan_cases=[
      ((0.2,0.2),(0.9,0.9),0.1,0.5),
      ((0.5,0.5),(0.51,0.51),1.0,0.5),
      ((0.1,0.9),(0.9,0.1),2.0,0.2),
      (None,(0.3,0.4),1.0,0.3),
    ]
    pan_ok=True
    for prev,want,dt,rate in pan_cases:
      p1=mb._bounded_center(prev,want,dt,rate);p2=mb._bounded_center(prev,want,dt,rate)
      if p1!=p2:pan_ok=False
      if prev is not None:
        dist=math.hypot(p1[0]-prev[0],p1[1]-prev[1])
        if dist>max(.001,rate*max(.001,dt))+1e-9:pan_ok=False
    result["pan_rate_bound_repeatable"]=pan_ok

    # 3) Locked keyframes override generated values at the same timestamp, sorted deterministically.
    generated=[
      {"time_ms":0,"x":0.1,"y":0.1,"w":0.5,"h":0.5,"confidence":0.5,"locked":0},
      {"time_ms":500,"x":0.2,"y":0.2,"w":0.5,"h":0.5,"confidence":0.5,"locked":0},
    ]
    existing={"keyframes":[{"time_ms":500,"x":0.4,"y":0.3,"w":0.4,"h":0.4,"confidence":1.0,"locked":1}]}
    m1=mb._merge_locked_keyframes(existing,generated);m2=mb._merge_locked_keyframes(existing,generated)
    result["locked_merge_repeatable"]=(m1==m2 and [x["time_ms"] for x in m1]==[0,500] and m1[1]["x"]==0.4 and m1[1]["locked"]==1)

    # 4) Scene/window segmentation must be repeatable and stay within source duration.
    seg_ok=True
    for duration,cuts in [(0,[]),(2.0,[]),(12.0,[3,7]),(25.0,[2,5,9,15,22]),(60.0,[4,8,12,30,45,58])]:
      s1=mb._segments(duration,cuts);s2=mb._segments(duration,cuts)
      if s1!=s2:seg_ok=False
      for s,e,_kind in s1:
        if not (0<=s<e<=duration+1e-9):seg_ok=False
    result["segment_boundaries_repeatable"]=seg_ok

    # 5) Center-crop transform must remain inside normalized source and preserve target aspect.
    center_ok=True
    for sw,sh in [(1920,1080),(1080,1920),(1000,1000),(4000,3000),(1,10000),(10000,1)]:
      for aspect,(tw,th) in composer.ASPECTS.items():
        p1=composer._center_plan(sw,sh,aspect);p2=composer._center_plan(sw,sh,aspect)
        if p1!=p2:center_ok=False
        if not (0<=p1["x"]<=1 and 0<=p1["y"]<=1 and p1["w"]>0 and p1["h"]>0 and p1["x"]+p1["w"]<=1.000001 and p1["y"]+p1["h"]<=1.000001):center_ok=False
        crop_ratio=(float(sw)*p1["w"])/(float(sh)*p1["h"])
        if abs(crop_ratio-(tw/th))>1e-6:center_ok=False
    result["center_plan_geometry_repeatable"]=center_ok

    # 6) Clip-export command math: negative/reversed times clamp to 0/.05 deterministically.
    captured=[]
    old_exe=ce._ffmpeg_exe;old_run=ce.subprocess.run
    def fake_exe():return "ffmpeg-fake"
    class R:
      returncode=0;stderr="";stdout=""
    def fake_run(cmd,*a,**kw):
      captured.append(list(cmd));Path(cmd[-1]).write_bytes(b"x"*2048);return R()
    ce._ffmpeg_exe=fake_exe;ce.subprocess.run=fake_run
    try:
      with tempfile.TemporaryDirectory(prefix="medbuf004_") as td:
        td=Path(td)
        source=td/"source.mp4";source.write_bytes(b"synthetic")
        r1=ce._render_source(source,-2,-4,td/"a.mp4",None,"original")
        cmd1=captured[-1]
        valid={"x":0.1,"y":0.1,"w":0.5,"h":0.5}
        r2=ce._render_source(source,2,3,td/"b.mp4",valid,"9:16")
        cmd2=captured[-1]
        extreme={"x":1.0,"y":1.0,"w":1.0,"h":1.0}
        r3=ce._render_source(source,0,1,td/"c.mp4",extreme,"9:16")
        cmd3=captured[-1]
        result["clip_time_clamp_repeatable"]=(r1["duration_s"]==0.05 and cmd1[cmd1.index("-ss")+1]=="0.000" and cmd1[cmd1.index("-t")+1]=="0.050")
        result["valid_reframe_command_deterministic"]=("crop=iw*0.50000000:ih*0.50000000:iw*0.10000000:ih*0.10000000" in cmd2[cmd2.index("-vf")+1])
        vf3=cmd3[cmd3.index("-vf")+1]
        import re
        mm=re.search(r"crop=iw\*([0-9.]+):ih\*([0-9.]+):iw\*([0-9.]+):ih\*([0-9.]+)",vf3)
        if not mm:raise RuntimeError("extreme reframe crop filter not parseable: "+vf3)
        cw,ch,cx,cy=[float(x) for x in mm.groups()]
        result["extreme_reframe_clamp_inside_bounds"]=(cx>=0 and cy>=0 and cw>0 and ch>0 and cx+cw<=1.000001 and cy+ch<=1.000001)
        result["extreme_reframe_filter"]=vf3
        result["extreme_reframe_geometry"]={"x":cx,"y":cy,"w":cw,"h":ch,"x2":cx+cw,"y2":cy+ch}
    finally:
      ce._ffmpeg_exe=old_exe;ce.subprocess.run=old_run

    hard=[
      "keyframe_validation_repeatable","interpolation_repeatable","interpolation_clamps_endpoints",
      "interpolation_stays_in_bounds","invalid_keyframes_fail_closed","pan_rate_bound_repeatable",
      "locked_merge_repeatable","segment_boundaries_repeatable","center_plan_geometry_repeatable",
      "clip_time_clamp_repeatable","valid_reframe_command_deterministic","extreme_reframe_clamp_inside_bounds"
    ]
    failed=[k for k in hard if not result.get(k)]
    print(json.dumps({"result":result,"hard":hard,"failed":failed,"pass":not failed},sort_keys=True))

if __name__=="__main__":main()
