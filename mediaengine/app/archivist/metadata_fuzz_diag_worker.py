from __future__ import annotations
import json,os,re,shutil,subprocess,tempfile
from pathlib import Path

def main():
    from PIL import Image
    import archivist.android as android
    import archivist.media as media
    import archivist.converter as converter
    import archivist.service as service

    result={}
    root=Path(os.environ["ARCHIVIST_HOME"]);root.mkdir(parents=True,exist_ok=True)

    original_query=android._content_query
    video_rows=[
      {"_id":"1","_display_name":"café_旅行_🚀.MP4","_size":"4096","date_modified":"1700000000",
       "datetaken":"1700000000123","duration":"1234","width":"1920","height":"1080","mime_type":"video/mp4","relative_path":"DCIM/旅行/"},
      {"_id":"2","_display_name":"seconds.mov","_size":"2048","date_modified":"1700000001",
       "datetaken":"1700000001","duration":"","width":"","height":"","mime_type":"video/quicktime","relative_path":"Movies/"},
      {"_id":"3","_display_name":"bad.mkv","_size":"x","date_modified":"not-a-number",
       "datetaken":"bad","duration":"-5","width":"-1920","height":"-1080","mime_type":"video/x-matroska","relative_path":"Movies/"}
    ]
    image_rows=[
      {"_id":"4","_display_name":"no-exif.jpg","_size":"1024","date_modified":"1700000002",
       "datetaken":"","width":"80","height":"40","mime_type":"image/jpeg","relative_path":"Pictures/"}
    ]
    def fake_query(adb,serial,uri,column_sets,timeout):
        if "/video/media" in uri:return video_rows,None
        if "/images/media" in uri:return image_rows,None
        return [],None
    android._content_query=fake_query
    try:items,errors=android.list_media("adb","SERIAL")
    finally:android._content_query=original_query
    by={x["media_id"]:x for x in items}
    result["android_ms_timestamp_normalized"]=abs(float(by["1"]["date_taken"])-1700000000.123)<0.001
    result["android_seconds_timestamp_preserved"]=float(by["2"]["date_taken"])==1700000001.0
    result["android_invalid_numeric_safe"]=by["3"]["size_bytes"] is None and by["3"]["mtime"] is None and by["3"]["date_taken"] is None
    result["android_unicode_path_preserved"]=by["1"]["path"]=="/storage/emulated/0/DCIM/旅行/café_旅行_🚀.MP4"
    result["android_missing_metadata_nullable"]=by["2"]["duration_ms"] is None and by["2"]["width"] is None and by["2"]["height"] is None
    result["android_negative_numeric_normalized"]=all((by["3"][k] is None or int(by["3"][k])>=0) for k in ("duration_ms","width","height"))
    result["android_clock_fields_independent"]=float(by["1"]["mtime"])==1700000000.0 and float(by["1"]["date_taken"])>float(by["1"]["mtime"])

    with tempfile.TemporaryDirectory(prefix="archivist_meta003_") as td:
        td=Path(td)
        oriented=td/"ориентация_旅行_🚀.jpg"
        im=Image.new("RGB",(80,40),(100,120,140));exif=Image.Exif();exif[274]=6
        im.save(oriented,"JPEG",exif=exif)
        thumb=td/"thumb_oriented.jpg";ok=media.make_thumbnail(oriented,"image",thumb)
        with Image.open(thumb) as out:result["exif_orientation_applied"]=ok and out.height>out.width

        plain=td/"без_exif_é.jpg";Image.new("RGB",(80,40),(80,90,100)).save(plain,"JPEG")
        plain_thumb=td/"thumb_plain.jpg";ok2=media.make_thumbnail(plain,"image",plain_thumb)
        with Image.open(plain_thumb) as out2:result["missing_exif_safe"]=ok2 and out2.width>out2.height
        result["unicode_local_path_safe"]=thumb.exists() and plain_thumb.exists()

        fixture=Path(media.__file__).resolve().parent/"assets"/"browser_fixture_h264.mp4"
        ffmpeg=media._ffmpeg_exe()
        if not fixture.exists() or not ffmpeg:raise RuntimeError("bundled ffmpeg fixture unavailable")
        current=converter._ffprobe_meta(fixture)
        coded_w=int(current.get("width") or 0);coded_h=int(current.get("height") or 0)
        result["video_rotation_fixture_observed"]=False
        result["video_rotation_normalized"]=None
        result["codec_container_extra_metadata_safe"]=int(current.get("duration_ms") or 0)>0 and coded_w>0 and coded_h>0

        fake_src=td/"source_é.mp4";fake_src.write_bytes(b"x");archive=td/"archive"
        row={"id":99,"filename":"名字_é.mp4","source_label":"Телефон 旅行","date_taken":4102444800.0,"mtime":1700000000.0}
        dest=service._archive_dest(archive,row,fake_src,"a"*64)
        result["unicode_archive_name_sanitized_deterministically"]=dest.suffix==".mp4" and not dest.exists()
        result["clock_conflict_current_policy_uses_date_taken"]="2100" in str(dest)

    hard=[
      "android_ms_timestamp_normalized","android_seconds_timestamp_preserved","android_invalid_numeric_safe",
      "android_unicode_path_preserved","android_missing_metadata_nullable","android_negative_numeric_normalized",
      "exif_orientation_applied","missing_exif_safe","unicode_local_path_safe",
      "codec_container_extra_metadata_safe"
    ]
    failed=[k for k in hard if not result.get(k)]
    print(json.dumps({"result":result,"hard":hard,"failed":failed,"pass":not failed},sort_keys=True))

if __name__=="__main__":main()
