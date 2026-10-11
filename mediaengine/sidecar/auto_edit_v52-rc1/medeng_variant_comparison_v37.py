#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,json,os,shutil,subprocess,time
from pathlib import Path
from medeng_media_probe_v41 import duration as media_duration
from PIL import Image,ImageDraw,ImageFont,ImageOps

CANDIDATE='MEDENG_VARIANT_COMPARISON_V37_RC1'
SCHEMA_VERSION=1
DEFAULT_FFMPEG=os.environ.get('MEDENG_FFMPEG','ffmpeg')
DEFAULT_FFPROBE=os.environ.get('MEDENG_FFPROBE','ffprobe')
FRACTIONS=(0.25,0.50,0.75)
class CompareError(RuntimeError): pass

def sha256_file(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()

def read_json(p:Path)->dict:
    try:o=json.loads(p.read_text(encoding='utf-8'))
    except Exception as e:raise CompareError(f'JSON_READ_FAILED:{p}:{type(e).__name__}:{e}') from e
    if not isinstance(o,dict):raise CompareError(f'JSON_OBJECT_REQUIRED:{p}')
    return o

def atomic_json(p:Path,o):
    p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name(p.name+'.part');t.write_text(json.dumps(o,indent=2,sort_keys=True),encoding='utf-8');os.replace(t,p)

def run(cmd,timeout=45):
    cp=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout,check=False)
    if cp.returncode:raise CompareError('COMMAND_FAILED:'+((cp.stderr or b'')[-1200:].decode('utf-8','replace')))
    return cp

def duration(ffprobe:str,p:Path,ffmpeg:str=DEFAULT_FFMPEG)->float:
    return media_duration(p, ffmpeg, 20)

def extract(ffmpeg:str,p:Path,frac:float,out:Path,dur:float):
    ss=max(0.0,min(dur*frac,max(0.0,dur-0.05))); tmp=out.with_name(out.stem+'.part.jpg');tmp.unlink(missing_ok=True);out.parent.mkdir(parents=True,exist_ok=True)
    run([ffmpeg,'-hide_banner','-loglevel','error','-y','-ss',f'{ss:.3f}','-i',str(p),'-frames:v','1','-vf','scale=640:-2:force_original_aspect_ratio=decrease','-q:v','2',str(tmp)],45)
    with Image.open(tmp) as im: im.verify()
    os.replace(tmp,out)

def validate_source(p:Path,sha:str,size:int):
    if not p.is_file():raise CompareError('SOURCE_MISSING:'+str(p))
    if p.stat().st_size!=int(size):raise CompareError('SOURCE_SIZE_MISMATCH:'+p.name)
    if sha256_file(p)!=sha:raise CompareError('SOURCE_SHA_MISMATCH:'+p.name)

def collect_variants(outdir:Path)->list[dict]:
    jr=read_json(outdir/'JOB_RESULT.json')
    rows=[]
    auto_out={o['profile']:o for o in jr.get('outputs') or []}
    if set(auto_out)!={'16x9','9x16'}:raise CompareError('AUTO_PAIR_INCOMPLETE')
    for profile,o in auto_out.items():validate_source(outdir/o['filename'],o['sha256'],o['bytes'])
    auto_identity_payload={
        'fingerprint':str(jr.get('fingerprint') or ''),
        'outputs':sorted([{'profile':p,'bytes':int(o['bytes']),'sha256':str(o['sha256'])} for p,o in auto_out.items()],key=lambda x:x['profile']),
    }
    auto_identity_sha=hashlib.sha256(json.dumps(auto_identity_payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    rows.append({'key':'AUTO','name':'Automatic Cut','selected_event_ids':[], 'outputs':{p:{**o,'path':str((outdir/o['filename']).resolve())} for p,o in auto_out.items()},'source_manifest':str((outdir/'JOB_RESULT.json').resolve()),'source_manifest_sha256':auto_identity_sha,'source_identity_kind':'CANONICAL_AUTO_OUTPUT_PAIR'})
    ap=outdir/'Alternatives'/'ALTERNATIVES_MANIFEST.json'
    if not ap.is_file():raise CompareError('ALTERNATIVES_MANIFEST_MISSING')
    a=read_json(ap)
    if a.get('candidate')!='MEDENG_AUTO_VARIANTS_V36_RC1' or a.get('status')!='PASS':raise CompareError('ALTERNATIVES_MANIFEST_INVALID')
    for r in a.get('variants') or []:
        key=str(r.get('strategy_key') or '');vid=str(r.get('variant_id') or '');mp=outdir/'Alternatives'/'variants'/vid/'VARIANT_MANIFEST.json'
        if key not in ('ALT_A','ALT_B') or not mp.is_file():raise CompareError('VARIANT_MANIFEST_MISSING')
        m=read_json(mp); outs={o['profile']:o for o in m.get('outputs') or []}
        if set(outs)!={'16x9','9x16'}:raise CompareError('VARIANT_PAIR_INCOMPLETE')
        for profile,o in outs.items():validate_source(mp.parent/o['filename'],o['sha256'],o['bytes'])
        rows.append({'key':key,'name':str(r.get('strategy_name') or m.get('strategy_name') or key),'selected_event_ids':[x['event_id'] for x in m.get('selected_events') or []],'outputs':{p:{**o,'path':str((mp.parent/o['filename']).resolve())} for p,o in outs.items()},'source_manifest':str(mp.resolve()),'source_manifest_sha256':sha256_file(mp)})
    return rows

def build_board(rows:list[dict],profile:str,frames:dict[tuple[str,str,float],Path],out:Path):
    cols=len(FRACTIONS); row_h=250; label_w=170; cell_w=360; canvas=Image.new('RGB',(label_w+cell_w*cols,row_h*len(rows)),'#101010');draw=ImageDraw.Draw(canvas);font=ImageFont.load_default()
    for ri,r in enumerate(rows):
        y=ri*row_h;draw.text((12,y+18),r['key'],fill='white',font=font);draw.text((12,y+40),r['name'][:24],fill='#bbbbbb',font=font)
        ids=r['selected_event_ids'];draw.text((12,y+70),f'scenes={len(ids) if ids else "auto"}',fill='#888888',font=font)
        for ci,frac in enumerate(FRACTIONS):
            p=frames[(r['key'],profile,frac)]
            with Image.open(p).convert('RGB') as im:
                fit=ImageOps.contain(im,(cell_w-10,row_h-35));x=label_w+ci*cell_w+(cell_w-fit.width)//2;py=y+25+(row_h-35-fit.height)//2;canvas.paste(fit,(x,py))
            draw.text((label_w+ci*cell_w+8,y+6),f'{int(frac*100)}%',fill='#dddddd',font=font)
    tmp=out.with_name(out.stem+'.part.jpg');out.parent.mkdir(parents=True,exist_ok=True);canvas.save(tmp,'JPEG',quality=90,optimize=True);os.replace(tmp,out)

def canonical_hash(variants,assets):
    data={'variants':[{k:r[k] for k in ('key','name','source_manifest_sha256')} for r in variants],'assets':sorted(assets,key=lambda x:x['path'])}
    return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def validate(outdir:Path)->dict|None:
    root=outdir/'Review'/'VariantComparison';mp=root/'COMPARISON_MANIFEST.json'
    if not mp.is_file():return None
    try:
        m=read_json(mp)
        if m.get('candidate')!=CANDIDATE or m.get('status')!='PASS':return None
        for a in m.get('assets') or []:
            p=root/a['path']
            if not p.is_file() or p.stat().st_size!=int(a['bytes']) or sha256_file(p)!=a['sha256']:return None
        rows=collect_variants(outdir)
        expected_sources={r['key']:r['source_manifest_sha256'] for r in rows}
        if expected_sources!=m.get('source_manifest_sha256_by_variant'):return None
        if canonical_hash(rows,m.get('assets') or [])!=m.get('comparison_content_sha256'):return None
        return m
    except Exception:return None

def build(outdir:Path,ffmpeg=DEFAULT_FFMPEG,ffprobe=DEFAULT_FFPROBE):
    outdir=Path(outdir).resolve();existing=validate(outdir)
    if existing:
        x=dict(existing);x['resume_status']='SKIPPED_EXACT_COMPLETED';return x
    rows=collect_variants(outdir);review=outdir/'Review';root=review/'VariantComparison'
    if root.exists():
        q=outdir/'_VariantComparisonCorrupt';q.mkdir(exist_ok=True);os.replace(root,q/f'VariantComparison.{int(time.time())}.{os.getpid()}')
    tmp=review/f'.VariantComparison.part.{os.getpid()}.{int(time.time()*1000)}';shutil.rmtree(tmp,ignore_errors=True);tmp.mkdir(parents=True);(tmp/'Frames').mkdir()
    frames={}
    for r in rows:
        for profile,o in r['outputs'].items():
            p=Path(o['path']);dur=duration(ffprobe,p,ffmpeg)
            for frac in FRACTIONS:
                f=tmp/'Frames'/f"{r['key']}_{profile}_{int(frac*100):02d}.jpg";extract(ffmpeg,p,frac,f,dur);frames[(r['key'],profile,frac)]=f
    for profile in ('16x9','9x16'):build_board(rows,profile,frames,tmp/f'COMPARE_{profile}.jpg')
    with (tmp/'VARIANT_COMPARISON.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['variant','name','selected_event_ids','manifest_sha256','reel_16x9_sha256','reel_9x16_sha256'])
        for r in rows:w.writerow([r['key'],r['name'],' '.join(r['selected_event_ids']),r['source_manifest_sha256'],r['outputs']['16x9']['sha256'],r['outputs']['9x16']['sha256']])
    (tmp/'README.txt').write_text('MediaEngine Variant Comparison\nAUTO / ALT-A / ALT-B sampled at identical 25% / 50% / 75% positions.\nThis is review-only; it does not change selection or approved delivery.\n',encoding='utf-8')
    assets=[]
    for p in sorted(tmp.rglob('*')):
        if p.is_file() and p.name!='COMPARISON_MANIFEST.json':assets.append({'path':p.relative_to(tmp).as_posix(),'bytes':p.stat().st_size,'sha256':sha256_file(p)})
    m={'candidate':CANDIDATE,'schema_version':1,'status':'PASS','variant_count':len(rows),'semantic_selection_claim':False,'source_manifest_sha256_by_variant':{r['key']:r['source_manifest_sha256'] for r in rows},'assets':assets,'created_at_unix':time.time()};m['comparison_content_sha256']=canonical_hash(rows,assets);atomic_json(tmp/'COMPARISON_MANIFEST.json',m)
    if not (tmp/'COMPARE_16x9.jpg').is_file() or not (tmp/'COMPARE_9x16.jpg').is_file():raise CompareError('COMPARISON_BOARD_MISSING')
    os.replace(tmp,root);checked=validate(outdir)
    if not checked:raise CompareError('COMPARISON_POSTWRITE_VERIFY_FAILED')
    return checked

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--outdir',required=True);ap.add_argument('--ffmpeg',default=DEFAULT_FFMPEG);ap.add_argument('--ffprobe',default=DEFAULT_FFPROBE);a=ap.parse_args();r=build(Path(a.outdir),a.ffmpeg,a.ffprobe);print(json.dumps({'candidate':r['candidate'],'status':r['status'],'variant_count':r['variant_count'],'comparison_content_sha256':r['comparison_content_sha256'],'resume_status':r.get('resume_status')},indent=2))
if __name__=='__main__':main()
