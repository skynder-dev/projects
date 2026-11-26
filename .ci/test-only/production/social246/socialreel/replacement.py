"""Prepare bounded native VACE replacement jobs, preserving input geometry and provenance.

This is a backend adapter, not a new editor or an identity approval. Preparation
never starts a worker, downloads weights or submits a sampler.
"""
import copy
import json
import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw
from .common import AI_HOME, HIDDEN_PROCESS, PipelineError, read_json, write_json, sha256_file

VACE_HOME = AI_HOME.parent / 'VACE'


def choose_canvas(width, height, budget=114688):
    if min(width, height) <= 0:
        raise PipelineError('Invalid video dimensions')
    ratio = width / height
    candidates = [(w, h) for w in range(64, 769, 16) for h in range(64, 769, 16)
                  if w*h <= budget]
    return min(candidates, key=lambda size: abs(math.log((size[0]/size[1])/ratio)) +
               .05*math.log(budget/(size[0]*size[1])))


def fit_size(width, height, canvas):
    scale = min(canvas[0]/width, canvas[1]/height)
    # Even dimensions avoid chroma alignment failures for input YUV video.
    return max(2, round(width*scale)//2*2), max(2, round(height*scale)//2*2)


def template_files(template):
    root = VACE_HOME.resolve()
    files = {}
    kind=template.get('control_type')
    if kind not in (None,'pose','depth') or ((kind is None)!=('control_video' not in template)):raise PipelineError('Structural control requires pose/depth type and hashed video; no implicit gray fallback')
    for key in ('video', 'mask', 'reference') + (('control_video',) if kind else ()):
        item = template.get(key, {})
        if not isinstance(item,dict):raise PipelineError('Replacement '+key+' must contain path and sha256')
        path = Path(item.get('path', '')).resolve()
        if 'fullbody02' in str(path).lower():raise PipelineError('Reference outside authorized input scope; file not opened')
        if not path.is_relative_to(root) or not path.is_file():
            raise PipelineError('Replacement template file missing or outside VACE: ' + key)
        if not item.get('sha256') or sha256_file(path) != item['sha256']:
            raise PipelineError('Replacement template file hash mismatch: ' + key)
        files[key] = path
    if not template.get('source_url') or not template.get('license') or template.get('test_allowed') is not True:
        raise PipelineError('Replacement template needs explicit source/license/test approval')
    if template.get('identity_approved') is not False:
        raise PipelineError('This bounded experimental adapter does not confer presenter identity approval')
    return files


def probe(path):
    from .verify import probe as inspect
    data = inspect(path)
    video = next((s for s in data['streams'] if s.get('codec_type') == 'video'), None)
    if video is None:
        raise PipelineError('Template input has no video stream')
    return video


def build_workflow(video_name, mask_name, original_name, reference_name, canvas, prompt, prefix):
    graph = {}
    def node(i, kind, **inputs): graph[str(i)] = {'class_type': kind, 'inputs': inputs}
    def link(i, slot=0): return [str(i), slot]
    node(1, 'UNETLoader', unet_name='wan2.1_vace_1.3B_fp16.safetensors', weight_dtype='default')
    node(2, 'ModelSamplingSD3', model=link(1), shift=8)
    node(3, 'CLIPLoader', clip_name='umt5_xxl_fp8_e4m3fn_scaled.safetensors', type='wan', device='cpu')
    node(4, 'VAELoader', vae_name='wan_2.1_vae.safetensors')
    node(5, 'CLIPTextEncode', clip=link(3), text=prompt)
    node(6, 'CLIPTextEncode', clip=link(3), text='distorted face, extra limbs, broken anatomy, flicker, text, watermark')
    for i, name in [(7, video_name), (9, mask_name), (11, original_name)]:
        node(i, 'LoadVideo', file=name)
        node(i+1, 'GetVideoComponents', video=link(i))
    node(13, 'ImageToMask', image=link(10), channel='red')
    node(14, 'LoadImage', image=reference_name)
    node(15, 'WanVaceToVideo', positive=link(5), negative=link(6), vae=link(4),
         width=canvas[0], height=canvas[1], length=17, batch_size=1, strength=1,
         control_video=link(8), control_masks=link(13), reference_image=link(14))
    node(16, 'KSampler', model=link(2), seed=20261014, steps=20, cfg=6,
         sampler_name='uni_pc', scheduler='simple', positive=link(15), negative=link(15, 1),
         latent_image=link(15, 2), denoise=1)
    node(17, 'TrimVideoLatent', samples=link(16), trim_amount=link(15, 3))
    node(18, 'VAEDecode', samples=link(17), vae=link(4))
    node(19, 'ImageCompositeMasked', destination=link(12), source=link(18), x=0, y=0,
         resize_source=False, mask=link(13))
    node(20, 'SaveImage', images=link(19), filename_prefix=prefix+'/native_composite/VACE')
    node(21, 'SaveImage', images=link(18), filename_prefix=prefix+'/raw/VACE')
    return graph


def prepare(template_path, directory, canvas=None, base_directory=None, start_frame=0):
    template = read_json(template_path)
    files = template_files(template)
    media = media_pair(files['video'],files['mask'],template.get('media'))
    if template.get('control_type'):media_pair(files['video'],files['control_video'],media)
    reference_info(files['reference'])
    window=valid_window(media,start_frame)
    source = {'width':media['width'],'height':media['height'],'r_frame_rate':media['fps']}
    canvas = tuple(canvas or choose_canvas(source['width'], source['height']))
    if len(canvas)!=2 or any(type(n) is not int for n in canvas):
        raise PipelineError("Replacement canvas must contain two integer dimensions")
    if min(canvas) < 64 or any(n % 16 for n in canvas) or canvas[0]*canvas[1] > 114688:
        raise PipelineError('Replacement canvas exceeds the tested small-job budget or grid')
    directory = Path(directory).resolve()
    if not directory.is_relative_to((VACE_HOME/'input').resolve()):
        raise PipelineError('Replacement preparation must stay inside VACE')
    directory.mkdir(parents=True, exist_ok=True)
    import shutil
    ff = shutil.which('ffmpeg')
    if not ff:
        raise PipelineError('FFmpeg missing')
    content = fit_size(source['width'], source['height'], canvas)
    x, y = (((canvas[0]-content[0])//2)//2*2, ((canvas[1]-content[1])//2)//2*2)
    filter_text = f'trim=start_frame={start_frame}:end_frame={start_frame+17},setpts=PTS-STARTPTS,format=rgb24,scale={content[0]}:{content[1]},pad={canvas[0]}:{canvas[1]}:{x}:{y}:color=black'
    # Identical fit/pad geometry, but a categorical mask needs nearest sampling.
    if base_directory is not None:
        base_directory=Path(base_directory).resolve()
        if not base_directory.is_relative_to((VACE_HOME/'input/motion_bases').resolve()):
            raise PipelineError('Base cache outside motion preparation root')
        plan=read_json(base_directory/'base.json')
        if plan.get('signature')!=base_signature(template,canvas,start_frame):raise PipelineError('Base cache input signature mismatch')
        for entry in plan['files']:
            path=(base_directory/entry['path']).resolve()
            if not path.is_relative_to(base_directory) or not path.is_file() or sha256_file(path)!=entry['sha256']:
                raise PipelineError('Base preparation cache damaged')
        for name in ['original.mkv','mask.mkv','control.mkv']+(['structure.mkv'] if template.get('control_type') else []):shutil.copy2(base_directory/name,directory/name)
    else:
        for name,source_path in [('original',files['video']),('mask',files['mask'])]+([('structure',files['control_video'])] if template.get('control_type') else []):
            vf=filter_text if name!='mask' else filter_text.replace(f'scale={content[0]}:{content[1]}',f'scale={content[0]}:{content[1]}:flags=neighbor')+',lutrgb=r=if(gte(val\\,128)\\,255\\,0):g=if(gte(val\\,128)\\,255\\,0):b=if(gte(val\\,128)\\,255\\,0)'
            command([ff,'-v','error','-y','-i',str(source_path),'-vf',vf,'-frames:v','17','-an','-c:v','ffv1','-pix_fmt','bgr0',str(directory/(name+'.mkv'))],'video/mask fit')
    # Masked control: gray unknown area, source outside. This replaces separate
    # prepared-video dependencies and keeps mask alignment in one decoder.
    import numpy as np
    def frames(name):
        raw = command([ff,'-v','error','-i',str(directory/(name+'.mkv')),'-f','rawvideo','-pix_fmt','rgb24','pipe:1'],'prepared frames')
        array = np.frombuffer(raw, np.uint8).reshape(-1, canvas[1], canvas[0], 3)
        if len(array) != 17:
            raise PipelineError('Replacement input must contain at least 17 frames')
        return array
    originals, masks = frames('original'), frames('mask')
    weight = masks[:, :, :, :1].astype(np.float32)/255
    for index,mask_frame in enumerate(weight):
        if not .001 < float((mask_frame>.5).mean()) < .9:
            raise PipelineError('Replacement mask empty/missing or covers background at frame '+str(index))
    mask_dir=directory/'mask_frames';mask_dir.mkdir(exist_ok=True)
    for index,mask_frame in enumerate(masks):Image.fromarray(mask_frame[:,:,0]).save(mask_dir/(f'{index:06d}.png'))
    controls = np.rint(originals*(1-weight)+127*weight).astype(np.uint8)
    if template.get('control_type'):
        structure=frames('structure')
        if any(np.ptp(frame,axis=(0,1)).max()<8 for frame in structure):raise PipelineError('Structural control has empty/constant frame; no motion claim')
        controls=np.where(masks>0,structure,originals).astype(np.uint8)
    if base_directory is None:
        command([ff,'-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{canvas[0]}x{canvas[1]}','-r',source['r_frame_rate'],'-i','pipe:0','-an','-c:v','ffv1','-pix_fmt','bgr0',str(directory/'control.mkv')],'control encoding',controls.tobytes())
    with Image.open(files['reference']) as raw_reference:
        raw_reference.load()
        reference=Image.new('RGB',raw_reference.size,'white')
        rgba=raw_reference.convert('RGBA');reference.paste(rgba,(0,0),rgba.getchannel('A'))
    scale = min(canvas[0]/reference.width, canvas[1]/reference.height)
    reference_source=reference.size
    size = (round(reference.width*scale), round(reference.height*scale))
    if min(size)<16:
        raise PipelineError('Reference aspect/resolution incompatible: fitted subject canvas too small; no stretch or crop used')
    reference = reference.resize(size, Image.Resampling.BILINEAR)
    ref = Image.new('RGB', canvas, 'white')
    ref.paste(reference, ((canvas[0]-size[0])//2, (canvas[1]-size[1])//2))
    ref.save(directory/'reference.png')
    contact = Image.new('RGB', (canvas[0]*2, (canvas[1]+24)*2), (25,25,25));draw=ImageDraw.Draw(contact)
    for cx, cy, title, im in [(0,0,'original',Image.fromarray(originals[0])),
                              (1,0,'white = generated',Image.fromarray(masks[0])),
                              (0,1,'masked control',Image.fromarray(controls[0])), (1,1,'complete reference',ref)]:
        draw.text((cx*canvas[0]+5,cy*(canvas[1]+24)+5),title,fill='white')
        contact.paste(im,(cx*canvas[0],cy*(canvas[1]+24)+24))
    contact.save(directory/'inputs.png')
    relative = directory.relative_to(VACE_HOME/'input').as_posix() if directory.is_relative_to(VACE_HOME/'input') else None
    if relative is None:
        raise PipelineError('Prepared files must be under VACE/input for the isolated worker')
    prefix = 'social_replacement/'+directory.name
    graph = build_workflow(relative+'/control.mkv', relative+'/mask.mkv', relative+'/original.mkv',
                           relative+'/reference.png', canvas, template['prompt'], prefix)
    write_json(directory/'workflow_api.json', graph)
    result = {'template_id': template['id'], 'canvas': list(canvas), 'content': list(content),
              'frames':17,'window':window,'semantic_mask_accuracy_verified':False,'source_media':media,'steps':20,'sampling_limit_seconds':300,'reference_content':list(size),'reference_transform':{'mode':'whole image contain on white; no crop','uniform_scale':scale,'offset':[(canvas[0]-size[0])//2,(canvas[1]-size[1])//2],'source':list(reference_source),'content':list(size)},
              'source_url':template['source_url'],'license':template['license'],'reference_source_size':list(reference_info(files['reference'])),'mask_sampling':'nearest then binary threshold 128',
              'identity_approved':False,'production_approved':False,'prefix':prefix,'input_relative':relative,'motion_prompt':template['prompt'],
              'files':[{'path':p.name,'sha256':sha256_file(p)} for p in directory.iterdir() if p.is_file()]}
    if template.get('control_type'):
        result['control_type']=template['control_type'];result['control_source_sha256']=template['control_video']['sha256']
        result['control_composition']='original RGB outside edit mask; structural signal inside edit mask (official repaint+control composition)'
    write_json(directory/'prepared.json',result)
    return result


def composite_output(directory, history, output):
    import numpy as np
    import shutil
    from fractions import Fraction
    directory, output = Path(directory), Path(output)
    validate_prepared(directory)
    plan = read_json(directory / 'prepared.json')
    width, height = plan['canvas']
    ff = shutil.which('ffmpeg')
    def read_video(name):
        data = subprocess.check_output([ff,'-v','error','-i',str(directory/name),'-f','rawvideo','-pix_fmt','rgb24','pipe:1'],timeout=30,**HIDDEN_PROCESS)
        return np.frombuffer(data,np.uint8).reshape(17,height,width,3)
    original, mask = read_video('original.mkv'), read_video('mask.mkv')[:,:,:,0]
    images = history.get('outputs',{}).get('21',{}).get('images',[])
    if len(images) != 17:
        raise PipelineError('VACE did not produce the required 17 real frames')
    expected_raw=(VACE_HOME/'output'/plan['prefix']/'raw').resolve()
    seen=set()
    for entry in images:
        if not isinstance(entry,dict) or entry.get('type','output')!='output':raise PipelineError('VACE output metadata malformed')
        path=(VACE_HOME/'output'/entry.get('subfolder','')/entry.get('filename','')).resolve()
        if path.parent!=expected_raw or path in seen or not path.is_file():raise PipelineError('VACE output belongs to another job, is duplicated or missing')
        seen.add(path)
    frames = []
    frame_dir = output/'frames'
    frame_dir.mkdir(parents=True,exist_ok=True)
    for i, entry in enumerate(images):
        path = (VACE_HOME/'output'/entry['subfolder']/entry['filename']).resolve()
        if not path.is_relative_to((VACE_HOME/'output').resolve()):
            raise PipelineError('Unexpected VACE output path')
        generated = np.asarray(Image.open(path).convert('RGB'))
        if generated.shape != original[i].shape:
            raise PipelineError('Generated frame dimensions differ from prepared input')
        weight = mask[i,:,:,None].astype(np.float32)/255
        final = np.rint(generated*weight+original[i]*(1-weight)).clip(0,255).astype(np.uint8)
        final[mask[i]==0]=original[i][mask[i]==0]
        if not np.array_equal(final[mask[i]==0],original[i][mask[i]==0]):
            raise PipelineError('Background preservation failed')
        Image.fromarray(final).save(frame_dir/(str(i).zfill(3)+'.png'))
        frames.append(final)
    fps = float(Fraction(probe(directory/'original.mkv')['r_frame_rate']))
    video = output/'replacement.mp4'
    process = subprocess.Popen([ff,'-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{width}x{height}',
                                '-r',str(fps),'-i','pipe:0','-an','-c:v','libx264','-threads','4','-crf','18',
                                '-pix_fmt','yuv420p',str(video)],stdin=subprocess.PIPE,**HIDDEN_PROCESS)
    try:
        for frame in frames: process.stdin.write(frame.tobytes())
        process.stdin.close()
        if process.wait(timeout=30): raise PipelineError('Replacement video encoding failed')
    finally:
        if process.poll() is None: process.kill();process.wait(timeout=10)
    decoded = subprocess.run([ff,'-v','error','-i',str(video),'-f','null','-'],capture_output=True,timeout=30,**HIDDEN_PROCESS)
    if decoded.returncode or decoded.stderr.strip(): raise PipelineError('Replacement video decode failed')
    check=media_pair(video,video)
    if check['frames']!=17 or [check['width'],check['height']]!=plan['canvas']:raise PipelineError('Replacement result video count/canvas mismatch')
    return {'file':str(video),'sha256':sha256_file(video),'frames':17,'canvas':[width,height],
            'fps':fps,'background_max_rgb_error_pre_encode':0,'full_decode_passed':True,
            'identity_approved':False,'production_approved':False}


def run_prepared(directory, cancel_file=None):
    """Explicit caller starts one bounded job; never called by default Reel production."""
    from .common import ROOT
    from .watchdog import run_command
    interpreter = AI_HOME.parent/'ComfyUI/v0.39.0/ComfyUI_windows_portable/python_embeded/python.exe'
    if not interpreter.is_file():
        raise PipelineError('Existing ComfyUI interpreter missing; no auto-install')
    directory = Path(directory).resolve()
    if not directory.is_relative_to((VACE_HOME/'input').resolve()):
        raise PipelineError('Prepared input outside VACE')
    validate_prepared(directory)
    bootstrap = 'import sys,runpy; sys.path.insert(0,' + repr(str(ROOT)) + '); runpy.run_module("socialreel.replacement_worker",run_name="__main__")'
    command = [str(interpreter),'-s','-c',bootstrap,str(directory)]
    if cancel_file: command.append(str(cancel_file))
    log = VACE_HOME/'logs'/('adapter_'+directory.name+'.log')
    code = run_command(command,log,timeout=780,cancel_file=cancel_file,cwd=ROOT)
    return {'return_code':code,'log':str(log),'production_approved':False}


def command(args,label,input_data=None):
    from .watchdog import WindowsJob
    proc=None;job=None
    try:
        proc=subprocess.Popen(args,stdin=subprocess.PIPE if input_data is not None else subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,**HIDDEN_PROCESS)
        if __import__('os').name=='nt':job=WindowsJob(proc)
        stdout,stderr=proc.communicate(input=input_data,timeout=30)
        if proc.returncode or stderr.strip():raise PipelineError('Motion '+label+' failed: '+stderr.decode(errors='replace')[-500:])
        return stdout
    except (OSError,subprocess.TimeoutExpired) as error:raise PipelineError('Motion '+label+' unavailable or timed out; own codec isolated') from error
    finally:
        if job:job.close()
        if proc and proc.poll() is None:proc.kill();proc.wait(timeout=10)
        if proc:
            for stream in (proc.stdin,proc.stdout,proc.stderr):
                if stream and not stream.closed:stream.close()


def media_pair(video,mask,declared=None):
    import shutil
    from fractions import Fraction
    fp=shutil.which('ffprobe')
    if not fp:raise PipelineError('FFprobe missing')
    def metadata(path):
        raw=command([fp,'-v','error','-select_streams','v:0','-count_frames','-show_entries','stream=width,height,r_frame_rate,avg_frame_rate,nb_read_frames','-of','json',str(path)],'metadata/decode')
        try:
            item=json.loads(raw)['streams'][0];fps=Fraction(item['r_frame_rate']);average=Fraction(item['avg_frame_rate']);frames=int(item['nb_read_frames'])
            if fps<=0 or fps>120 or fps!=average or not 17<=frames<=4096:raise ValueError()
            return {'width':int(item['width']),'height':int(item['height']),'fps':str(fps),'frames':frames}
        except (ValueError,KeyError,IndexError,TypeError,ZeroDivisionError):raise PipelineError('Motion input FPS/count invalid, variable, or outside bounded contract')
    source,masked=metadata(video),metadata(mask)
    if source!=masked:raise PipelineError('Motion video/mask dimensions, FPS or frame count differ')
    if declared is not None:
        try:
            expected={'width':int(declared['width']),'height':int(declared['height']),'fps':str(Fraction(str(declared['fps']))),'frames':int(declared['frames'])}
        except (ValueError,KeyError,TypeError,ZeroDivisionError):raise PipelineError('Declared motion metadata invalid')
        if source!=expected:raise PipelineError('Motion FPS/dimensions/frame count disagree with registered metadata')
    return source


def reference_info(path):
    try:
        with Image.open(path) as image:
            size=image.size
            if min(size)<32 or max(size)>8192 or size[0]*size[1]>16_777_216:raise PipelineError('Reference resolution incompatible with bounded preparation')
            image.verify()
        return size
    except (OSError,ValueError,Image.DecompressionBombError) as error:raise PipelineError('Reference missing, damaged or incompatible') from error


def base_signature(template,canvas,start_frame=0):
    value={'video':template['video']['sha256'],'mask':template['mask']['sha256'],'canvas':list(canvas),'selected_frames':17,'start_frame':start_frame,'method':'aspect-fit-rgb-even-pad-nearest-binary-mask-window-qa-v6-rounding-verified'}
    if template.get('control_type'):value.update(control_type=template['control_type'],control_sha256=template['control_video']['sha256'],composition='repaint-plus-structure-v1')
    return value


def extract_source_masks(path,directory,media):
    import numpy as np,shutil
    if media['width']*media['height']*media['frames']>134_217_728:raise PipelineError('Full mask catalogue exceeds bounded CPU memory budget')
    raw=command([shutil.which('ffmpeg'),'-v','error','-i',str(path),'-f','rawvideo','-pix_fmt','gray','pipe:1'],'source masks decode')
    try:frames=np.frombuffer(raw,np.uint8).reshape(media['frames'],media['height'],media['width'])
    except ValueError:raise PipelineError('Source mask frames missing or malformed')
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    for index,frame in enumerate(frames):
        binary=(frame>=128).astype(np.uint8)*255
        if not .001<(binary>0).mean()<.9:raise PipelineError('Source mask empty/missing or covers background at frame '+str(index))
        Image.fromarray(binary).save(directory/(f'{index:06d}.png'))


def valid_window(media,start_frame):
    from fractions import Fraction
    if type(start_frame) is not int or not 0<=start_frame<=media['frames']-17:raise PipelineError('Motion start frame outside valid 17-frame range 0..'+str(media['frames']-17))
    fps=Fraction(media['fps'])
    return {'start_frame':start_frame,'end_frame_exclusive':start_frame+17,'frame_count':17,'source_fps':media['fps'],'source_start_s':float(Fraction(start_frame,1)/fps),'source_end_s':float(Fraction(start_frame+17,1)/fps)}


def validate_prepared(directory):
    from .motion_review import mask_geometry
    directory=Path(directory).resolve();plan=read_json(directory/'prepared.json')
    if not isinstance(plan,dict):raise PipelineError('Prepared motion metadata must be an object')
    if plan.get('identity_approved') is not False or plan.get('production_approved') is not False or plan.get('frames')!=17:raise PipelineError('Prepared motion exceeds experimental contract')
    if plan.get('full_body_replacement_approved',False) is not False or plan.get('semantic_mask_accuracy_verified',False) is not False:raise PipelineError('Geometric motion validation cannot confer semantic or full-body approval')
    entries=plan.get('files')
    if not isinstance(entries,list) or not entries or any(not isinstance(e,dict) or not isinstance(e.get('path'),str) or not isinstance(e.get('sha256'),str) for e in entries):raise PipelineError('Prepared motion manifest malformed')
    names=[e['path'] for e in entries]
    kind=plan.get('control_type')
    if kind not in (None,'pose','depth'):raise PipelineError('Prepared structural control type unknown')
    required={'original.mkv','mask.mkv','control.mkv','reference.png','workflow_api.json'}
    if kind:required.add('structure.mkv')
    if not required.issubset(names) or len(names)!=len(set(names)):raise PipelineError('Prepared motion required files missing or duplicated')
    for entry in entries:
        path=(directory/entry['path']).resolve()
        if not path.is_relative_to(directory) or not path.is_file() or sha256_file(path)!=entry['sha256']:raise PipelineError('Prepared motion file missing, changed or outside input')
    root=(VACE_HOME/'input').resolve()
    if not directory.is_relative_to(root):raise PipelineError('Prepared motion outside owned input')
    relative=plan.get('input_relative',directory.relative_to(root).as_posix())
    if not isinstance(relative,str) or Path(relative).is_absolute() or '..' in Path(relative).parts:raise PipelineError('Prepared input path must be relative to this job')
    bound=(root/relative).resolve()
    staging=(root/'motion_staging').resolve()
    if not bound.is_relative_to(root) or (not directory.is_relative_to(staging) and bound!=directory):raise PipelineError('Prepared motion input bound to another job')
    if plan.get('prefix')!='social_replacement/'+bound.name:raise PipelineError('Prepared motion output prefix belongs to another job')
    graph=read_json(directory/'workflow_api.json')
    try:prompt=graph['5']['inputs']['text']
    except (KeyError,TypeError):raise PipelineError('Prepared workflow text missing')
    if not isinstance(prompt,str) or not prompt.strip() or prompt!=plan.get('motion_prompt',prompt):raise PipelineError('Prepared workflow user text changed')
    expected_graph=build_workflow(relative+'/control.mkv',relative+'/mask.mkv',relative+'/original.mkv',relative+'/reference.png',tuple(plan['canvas']),prompt,plan['prefix'])
    if graph!=expected_graph:raise PipelineError('Prepared workflow inputs, outputs or sampler contract differ from this job')
    reference_info(directory/'reference.png')
    control=media_pair(directory/'original.mkv',directory/'control.mkv')
    pair=media_pair(directory/'original.mkv',directory/'mask.mkv')
    if control!=pair:raise PipelineError('Prepared control video mismatches source/mask')
    if pair['frames']!=17 or [pair['width'],pair['height']]!=plan['canvas']:raise PipelineError('Prepared video/mask canvas/count mismatch')
    mask_geometry(directory/'mask_frames',17,plan['canvas'])
    validate_prepared_pixels(directory,plan)
    if 'window' in plan:
        expected=valid_window(plan['source_media'],plan['window']['start_frame'])
        if expected!=plan['window']:raise PipelineError('Prepared window metadata inconsistent')
    if plan.get('source_review'):
        review=Path(plan['source_review']).resolve()
        if not review.is_relative_to((VACE_HOME/'cache/motion_reviews').resolve()):raise PipelineError('Source mask review outside owned cache')
        index=read_json(review/'review.json')
        for entry in index['files']:
            path=(review/entry['path']).resolve()
            if not path.is_relative_to(review) or not path.is_file() or sha256_file(path)!=entry['sha256']:raise PipelineError('Source mask review frame missing or changed')
        media=plan['source_media'];mask_geometry(review/'source_mask_frames',media['frames'],(media['width'],media['height']))
    return {'valid':True,'frames':17,'window':plan.get('window'),'semantic_accuracy_verified':False,'gpu_started':False}


def validate_prepared_pixels(directory,plan):
    """Check review PNGs and actual sampler videos describe exactly the same job."""
    import numpy as np,shutil
    width,height=plan['canvas'];ff=shutil.which('ffmpeg')
    def decode(name):
        raw=command([ff,'-v','error','-i',str(directory/name),'-f','rawvideo','-pix_fmt','rgb24','pipe:1'],'prepared pixel consistency')
        try:return np.frombuffer(raw,np.uint8).reshape(17,height,width,3)
        except ValueError:raise PipelineError('Prepared pixel count/canvas inconsistent')
    mask=decode('mask.mkv')
    for index in range(17):
        with Image.open(directory/'mask_frames'/f'{index:06d}.png') as image:png=np.asarray(image.convert('L'))
        if not np.array_equal(mask[index],np.repeat(png[:,:,None],3,axis=2)):raise PipelineError('Prepared mask video differs from reviewed PNG at frame '+str(index))
    original=decode('original.mkv');control=decode('control.mkv')
    expected=np.where(mask>0,127,original).astype(np.uint8)
    if plan.get('control_type'):
        structure=decode('structure.mkv')
        if any(np.ptp(frame,axis=(0,1)).max()<8 for frame in structure):raise PipelineError('Structural control has empty/constant frame')
        expected=np.where(mask>0,structure,original).astype(np.uint8)
    if not np.array_equal(control,expected):raise PipelineError('Prepared control pixels differ from source outside mask or declared gray/structural region inside mask')
