"""Read-only content review flags from already verified stored Social evidence."""
import re,math
from pathlib import Path
from .common import read_json

def stored_quality(job):
    if job.get('preparation_integrity_pass') is True:return {'scope':'stored_preparation','checked':False,'state':'not_generated','detail':'Unvoiced draft; no measured narration/captions or subjective listening is implied'}
    if job.get('package_integrity_pass') is not True:return {'scope':'unverified_artifact','checked':False,'state':'unconfirmed','detail':'Verify the actual package before deriving content-quality flags'}
    try:
        root=Path(job['run_dir']);asr=read_json(root/'asr.json');score=asr['word_agreement']
        if type(score) not in (int,float) or not math.isfinite(score) or not 0<=score<=1:raise ValueError('Invalid stored ASR agreement')
        path=root/'subtitles.srt'
        if path.stat().st_size>256*1024:raise ValueError('Captions exceed bounded review input')
        text=path.read_text(encoding='utf-8');short=[];fast=[];count=0
        def seconds(value):
            h,m,s=value.replace(',','.').split(':');return int(h)*3600+int(m)*60+float(s)
        for block in text.strip().split('\n\n'):
            lines=block.splitlines()
            if len(lines)<3:raise ValueError('Malformed stored caption cue')
            a,b=lines[1].split(' --> ');duration=seconds(b)-seconds(a);caption=' '.join(lines[2:]);count+=1
            if count>1000 or not math.isfinite(duration) or duration<=0:raise ValueError('Invalid/bounded caption duration')
            item={'cue':count,'text':caption[:200],'duration_s':round(duration,3),'characters_per_second':round(len(caption)/duration,2)}
            if duration<.8:short.append(item)
            if len(caption)/duration>25:fast.append(item)
        flags=[]
        if asr.get('derived_audio_processing'):flags.append({'code':'derived_asr_timing_review','detail':'Word observations derive from verified source ASR through documented cuts/tempo mapping; no new Whisper inference or subjective listening implied'})
        if score<.95:flags.append({'code':'asr_below_review_target','detail':'Stored raw agreement below project review target0.95; technical gate result is separate'})
        if asr.get('differences'):flags.append({'code':'asr_lexical_differences','detail':'Stored recognition differs from scripted words; homophones/splitting do not establish spoken mistakes'})
        if asr.get('requires_editorial_review') or any(e.get('requires_editorial_review') or e.get('numeric_hypothesis') for e in asr.get('caption_exclusions',[])):flags.append({'code':'caption_display_exclusion_review','detail':'Stored caption exclusion requires editorial review; raw recognition is preserved'})
        if short:flags.append({'code':'short_caption_cue','detail':'Observed caption duration below project0.8s review target'})
        if fast:flags.append({'code':'higher_caption_reading_load','detail':'Cue exceeds project25characters/s review flag; not a subjective readability verdict'})
        from .asr_diagnostics import diagnose
        from .voice import speech_text, speech_for_script
        script=read_json(root/'script.json');expected=' '.join(speech_for_script(script,s['voiceover']) for s in script['segments']);diagnostics=diagnose(expected,asr['transcript'],score)
        package_id=read_json(root/'package_manifest.json')['package_id'];editorial=job.get('editorial_review') or {};approved=__import__('socialreel.workflow',fromlist=['editorial_state']).editorial_state(editorial,package_id)['approved']
        return {'scope':'Verified stored ASR/caption evidence, not source currency or subjective listening','checked':True,'state':'review_required' if flags or not approved else 'stored_editorial_record','artifact_id':package_id,'ASR_diagnostics':diagnostics,'ASR_gate_pass':asr.get('pass') is True,'ASR_agreement':score,'ASR_review_target':.95,'automatic_flags':flags,'caption_cues':count,'short_cues':short[:10],'higher_reading_load_cues':fast[:10],'subjective_listening_evidence':'not_recorded_by_this_automatic_check','editorial_approved_for_this_package':approved,'publication_authorized':False}
    except (OSError,ValueError,KeyError,TypeError,AttributeError,IndexError) as error:
        return {'scope':'stored_content_evidence','checked':False,'state':'unconfirmed','detail':type(error).__name__+': '+str(error)[:300],'publication_authorized':False}
