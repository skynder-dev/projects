"""Geometric mask QA with source overlays; never infers anatomical correctness."""
from pathlib import Path
from fractions import Fraction
import shutil,numpy as np
from PIL import Image,ImageDraw,ImageFont
from .common import PipelineError,ASSETS,write_json
from .replacement import command

def mask_geometry(directory,frames,size):
    directory=Path(directory)
    names={f'{i:06d}.png' for i in range(frames)}
    if {p.name for p in directory.glob('*.png')}!=names:raise PipelineError('Mask frame sequence missing, extra or non-contiguous')
    rows=[]
    for index in range(frames):
        try:
            with Image.open(directory/f'{index:06d}.png') as image:
                image.load()
                if image.size!=tuple(size):raise PipelineError('Mask frame dimensions mismatch at '+str(index))
                pixels=np.asarray(image.convert('L'));values=set(np.unique(pixels).tolist())
                if not values.issubset({0,255}):raise PipelineError('Prepared mask not binary at '+str(index))
                area=float((pixels>0).mean())
                if not .001<area<.9:raise PipelineError('Mask empty/full or covers background at frame '+str(index))
                bbox=image.convert('L').getbbox()
        except (OSError,ValueError) as error:raise PipelineError('Mask frame damaged at '+str(index)) from error
        rows.append({'frame':index,'coverage':area,'bbox':list(bbox)})
    return rows

def overview(video,masks,media,scope,directory,source_indices=None,source_offset=0):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    rows=mask_geometry(masks,media['frames'],(media['width'],media['height']))
    for row in rows:row['source_frame']=row['frame']+source_offset;row['source_time_s']=float(Fraction(row['source_frame'],1)/Fraction(media['fps']))
    indices=source_indices or [0,media['frames']//2,media['frames']-1]
    select='+'.join(f'eq(n\\,{i})' for i in indices)
    raw=command([shutil.which('ffmpeg'),'-v','error','-i',str(video),'-vf','select='+select,'-fps_mode','passthrough','-f','rawvideo','-pix_fmt','rgb24','pipe:1'],'overview frames')
    try:images=np.frombuffer(raw,np.uint8).reshape(len(indices),media['height'],media['width'],3)
    except ValueError:raise PipelineError('Overview source frames missing')
    tile_w=512;tile_h=round(media['height']*tile_w/media['width']);header=120
    sheet=Image.new('RGB',(tile_w*len(indices),tile_h+header),(18,25,35));draw=ImageDraw.Draw(sheet)
    font=ImageFont.truetype(str(ASSETS/'fonts/Inter-SemiBold.otf'),18)
    draw.text((12,8),'EDIT REGION = RED; GEOMETRY ONLY, NOT ANATOMY VERIFICATION',font=font,fill='white')
    draw.text((12,34),'Scope: '+scope,font=font,fill=(255,190,100))
    for column,index in enumerate(indices):
        with Image.open(Path(masks)/f'{index:06d}.png') as image:mask=np.asarray(image.convert('L'))>0
        base=images[column].copy();base[mask]=np.rint(base[mask]*.6+np.array([255,40,40])*.4).astype(np.uint8)
        overlay=Image.fromarray(base);od=ImageDraw.Draw(overlay);od.rectangle(rows[index]['bbox'],outline=(255,235,0),width=3)
        overlay=overlay.resize((tile_w,tile_h),Image.Resampling.BILINEAR);sheet.paste(overlay,(column*tile_w,header))
        draw.text((column*tile_w+12,72),f'Source frame {index+source_offset}; {float(Fraction(index+source_offset,1)/Fraction(media["fps"])):.3f}s; area {rows[index]["coverage"]:.1%}',font=font,fill='white')
    sheet.save(directory/'mask_overview.png')
    report={'geometry_valid':True,'semantic_accuracy_verified':False,'full_body_replacement_approved':False,'mask_scope':scope,'source_media':media,'sampled_frames':indices,'source_sampled_frames':[index+source_offset for index in indices],'source_offset':source_offset,'frames':rows}
    write_json(directory/'mask_metrics.json',report);return report
