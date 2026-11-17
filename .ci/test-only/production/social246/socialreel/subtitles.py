"""Offline CPU ASR gate and source-script subtitles timed from real narration."""
from pathlib import Path
import difflib
import json
import re
from .common import PipelineError, write_json, write_text


def normalized_words(text, *, keep_and=False):
    from num2words import num2words
    text=text.replace("’","'")
    text=re.sub(r"\bcannot\b","can not",text,flags=re.I)
    text=re.sub(r"\b([A-Za-z]+)n't\b",lambda m:{'ca':'can','wo':'will','sha':'shall'}.get(m[1].lower(),m[1])+" not",text,flags=re.I)
    # A dot is a clock separator only with an explicit AM/PM and valid clock range.
    # Decimal amounts/rates and wrong minute values retain their original meaning.
    text = re.sub(r'(?<![\d.])(1[0-2]|[1-9])\.([0-5]\d)(?=\s*[ap]\.?m(?:\.|\b))', r'\1:\2', text, flags=re.I)
    text = re.sub(r'(\d)(?=[ap]\.?m(?:\.|\b))',r'\1 ',text,flags=re.I)
    text = re.sub(r'\b([ap])\.?m\.?(?=\s|$|[,;])',lambda m:m[1]+' m',text,flags=re.I)
    text = re.sub(r'([A-Za-z])(\d)', r'\1 \2', text)
    text = re.sub(r'\b[A-Z]{2,8}\b', lambda m: ' '.join(m[0]) if m[0] != 'NASA' else m[0], text)
    text = text.lower().replace(',', '')
    text = re.sub(r'([a-z])(\d)', r'\1 \2', text)
    text = re.sub(r'(?i)grants\.gov', 'grants dot gov', text)
    text = text.replace('non-profits', 'nonprofits')
    text = re.sub(r'\b501\s*c\s*3\b', 'five oh one c three', text)
    text = re.sub(r'\$(\d+(?:\.\d+)?)', r'\1 dollars', text)
    text = re.sub(r'(\d+(?:\.\d+)?) dollars (million|billion|thousand)', r'\1 \2 dollars', text)
    text = re.sub(r'\b(\d+)(st|nd|rd|th)\b', lambda m: num2words(int(m[1]), to='ordinal'), text)
    text = re.sub(r'\b\d+(?:\.\d+)?\b', lambda m: num2words(float(m[0]) if '.' in m[0] else int(m[0])), text)
    return [w for w in re.findall(r'[a-z]+', text) if keep_and or w != 'and']


def timestamp(seconds, sep):
    ms = round(seconds * 1000)
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f'{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}'


def inspect_narration(narration, speech, timing, cfg, package):
    from .asr_lineage import audio_inputs,verify_audio_inputs
    sealed=audio_inputs(narration,speech,timing,package,cfg)
    import os
    from .asr_cache import identity_for,load_observations,save_observations
    identity=identity_for(sealed);cached=load_observations(identity)
    model_dir=Path(cfg['model_dir'])
    if cached:
        full_narration,observed,cache_meta=cached
    else:
        if os.environ.get('SOCIAL_CACHE_ONLY')=='1':raise PipelineError('ASR cache-only miss; model not loaded')
        full_narration,observed=_decode_observations(narration,timing,cfg,package)
        cache_meta=None
    report=choose_observation(full_narration,observed,speech,timing,require_exact=True)
    report['input_lineage']=sealed
    verify_audio_inputs(report,narration,speech,timing,package,cfg)
    report['asr_cache_hit']=cached is not None
    report['asr_cache']=cache_meta or save_observations(identity,full_narration,observed)
    report['model_inference_started']=cached is None
    report.update(model_dir=str(model_dir),decoding={'temperature':0.0,'beam_size':5,'condition_on_previous_text':False})
    write_json(package/'asr.json',report)
    if report['pass']:write_captions(report,package)
    return report



def caption_text(text):
    # Formatting only: split merged fiscal-year/acronym tokens, retain all words.
    text = re.sub(r'\b([A-Z]{2,8})(FY)(\d{4})\b', r'\1 \2 \3', text)
    return re.sub(r'([A-Za-z])(\d)', r'\1 \2', text)


def timestamp_checks(observed, total):
    import math
    previous = 0.0
    for segment in observed:
        for word in segment.get('words', []):
            start, end = word['start'], word['end']
            if not (math.isfinite(start) and math.isfinite(end) and 0 <= start <= end <= total + .25):
                return False
            if start < previous - .05:
                return False
            previous = end
    return bool(observed) and any(segment.get('words') for segment in observed)


def segment_checks(observed, speech, timing):
    words = [word for segment in observed for word in segment.get('words', [])]
    # Assign once by greatest observed interval intersection, retaining all raw timestamps.
    assigned=[]
    for word in words:
        overlaps=[max(0.,min(word['end'],span['end_s'])-max(word['start'],span['start_s'])) for span in timing]
        maximum=max(overlaps,default=0.)
        candidates=[i for i,value in enumerate(overlaps) if maximum>0 and abs(value-maximum)<1e-9]
        if maximum==0 and word['start']==word['end']:
            candidates=[i for i,span in enumerate(timing) if span['start_s']<=word['start']<span['end_s']]
        assigned.append(candidates[0] if len(candidates)==1 else None)
    output = []
    for index,(text, span) in enumerate(zip(speech, timing)):
        actual = ''.join(w['word'] for w,owner in zip(words,assigned) if owner==index)
        expected, got = normalized_words(text), normalized_words(actual)
        checks = []
        cursor = 0
        for numeric_match in re.finditer(r'\d[\d,]*(?:\.\d+)?(?:st|nd|rd|th)?|\b(?:one|two|three|four|five|six|seven|eight|nine|ten)(?=\s+(?:Pilot|Implementation|applications?|proposals?|awards?|grants?|years?|months?|days?|persons?|applicants?|P I)\b)', text, re.I):
            token=numeric_match[0]
            tail=text[numeric_match.end():]
            unit_match=re.match(r'\s*((?:(?:million|billion|thousand)\s+)?(?:dollars?|cents?|years?|months?|days?|hours?|minutes?|seconds?|percent|applications?|proposals?|awards?|grants?|persons?|applicants?))\b',tail,re.I)
            clock_match=re.match(r'\s*([ap])\s*\.?\s*m\.?\b',tail,re.I)
            expected_unit=normalized_words(unit_match[1]) if unit_match else [clock_match[1].lower(),'m'] if clock_match else []
            phrases = [normalized_words(token), normalized_words(re.sub(r"(st|nd|rd|th)$", "", token))]
            positions = [(i, len(phrase)) for phrase in phrases for i in range(cursor, len(got))
                         if phrase and got[i:i+len(phrase)] == phrase]
            heard = bool(positions)
            observed_unit=[];unit_pass=not expected_unit
            if positions:
                position, length = min(positions)
                cursor = position + length
                observed_unit=got[cursor:cursor+len(expected_unit)]
                unit_pass=not expected_unit or observed_unit==expected_unit
            checks.append({'expected': token, 'heard': heard,'expected_unit':expected_unit,'heard_unit':observed_unit,'unit_pass':unit_pass})
        from collections import Counter
        critical = {'no', 'not', 'excluding', 'million', 'billion', 'thousand','per','annual','annually','only'}
        expected_terms, actual_terms = Counter(expected), Counter(got)
        critical_checks = {term: {'expected': expected_terms[term], 'heard': actual_terms[term]} for term in critical if expected_terms[term] or actual_terms[term]}
        critical_pass = all(v['expected'] == v['heard'] for v in critical_checks.values())
        output.append({'segment_id': span['id'], 'word_agreement': difflib.SequenceMatcher(None, expected, got, autojunk=False).ratio(),
                       'numeric_checks': checks, 'numbers_pass': all(c['heard'] and c['unit_pass'] for c in checks) and critical_pass, 'critical_terms': critical_checks})
    return output


def caption_words(observed, speech):
    from collections import Counter
    expected_counts=Counter(normalized_words(' '.join(speech)))
    observed_counts=Counter(normalized_words(' '.join(w['word'] for s in observed for w in s.get('words',[]))))
    allowed = set(expected_counts)
    protected=set('no not only per annual annually excluding zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety hundred thousand million billion first second third fourth fifth'.split())
    words, excluded = [], []
    for segment in observed:
        for word in segment.get('words', []):
            if word['end'] < word['start']:
                continue
            tokens=normalized_words(word['word']);normalized=set(tokens)
            previous=normalized_words(words[-1]['word']) if words else []
            duplicate=(len(tokens)==1 and tokens==previous and tokens[0] not in protected and not re.search(r'\d',word['word']) and word.get('probability',1)<.2 and 0<=word['end']-word['start']<=.12 and -.05<=word['start']-words[-1]['end']<=.1 and observed_counts[tokens[0]]>expected_counts[tokens[0]])
            if duplicate:
                excluded.append({**word,'numeric_hypothesis':False,'kind':'low_confidence_duplicate','requires_editorial_review':True,'reason':'Very brief low-confidence adjacent duplicate beyond approved word count; raw transcript/score retained, display exclusion needs editorial review'})
                observed_counts[tokens[0]]-=1;continue
            if (normalized and not normalized.intersection(allowed) and
                    word.get('probability', 1) < .2):
                excluded.append({**word, 'numeric_hypothesis':bool(re.search(r'\d',word['word'])), 'reason':'Low-confidence ASR token absent from approved narration; not used in captions'})
            else:
                words.append(word)
    return words, excluded


def readable_cues(words):
    """Fit real word-timed captions before render; never discard overflowing words."""
    from .render import font, wrap, W, MARGIN
    f=font('bold',54);width=W-2*MARGIN-24
    def fits(group):
        text=caption_text(''.join(w['word'] for w in group).strip())
        lines=wrap(text,f,width)
        return len(lines)<=2 and all(f.getlength(line)<=width for line in lines)
    # ASR may split "Grants" and ".gov"; keep the domain in one display unit.
    # Raw ASR remains in the report, and the joined interval is the observed union.
    units=[]
    for word in words:
        previous=units[-1]['word'] if units else ''
        fragment=word['word'].strip()
        domain=bool(re.match(r'^\.[A-Za-z]',word['word']))
        comma_number=bool(re.fullmatch(r'[,\.]\d+(?:[,\.]\d+)*',fragment) and re.search(r'\$?\d[\d,.]*$',previous))
        magnitude=bool(fragment.lower() in ('thousand','million','billion') and re.search(r'\$\d[\d,.]*$',previous))
        if units and (domain or comma_number or magnitude) and word['start']-units[-1]['end']<=.15:
            join=(' '+fragment) if magnitude else word['word'].lstrip() if comma_number else word['word']
            units[-1]={**units[-1],'word':previous+join,'end':max(units[-1]['end'],word['end'])}
        else:units.append(dict(word))
    cues,current=[],[]
    for word in units:
        if not fits([word]):raise PipelineError('ASR caption token cannot fit readable region: '+word['word'].strip()[:100])
        if current and (not fits(current+[word]) or word['end']-current[0]['start']>3.8):
            cues.append(current);current=[]
        current.append(word)
        if len(current)>=7 or re.search(r'[.!?]$',word['word'].strip()):
            cues.append(current);current=[]
    if current:cues.append(current)
    # Rebalance unreadably brief tail fragments using the same observed words/intervals.
    # Never pad duration, cross a pause or change the raw ASR observation.
    balanced=[]
    for group in cues:
        if balanced and len(group)<=4 and group[-1]['end']-group[0]['start']<.8:
            previous=balanced[-1]
            if group[0]['start']-previous[-1]['end']<=.8:
                combined=previous+group
                if fits(combined) and combined[-1]['end']-combined[0]['start']<=3.8:
                    balanced[-1]=combined;continue
                while len(previous)>1 and group[-1]['end']-group[0]['start']<.8:
                    moved=previous[-1]
                    if re.search(r'[.!?]$',moved['word'].strip()):break
                    candidate=[moved]+group;remaining=previous[:-1]
                    if not fits(candidate) or not fits(remaining) or candidate[-1]['end']-candidate[0]['start']>3.8 or remaining[-1]['end']-remaining[0]['start']<.8:break
                    previous=remaining;group=candidate;balanced[-1]=previous
        balanced.append(group)
    cues=balanced
    if any(group[-1]['end']<=group[0]['start'] for group in cues):
        raise PipelineError('ASR caption has no observed positive duration; timing needs review')
    return cues


def evaluate_observation(observed,speech,timing,mode):
    transcript=' '.join(s['text'].strip() for s in observed)
    exp,got=normalized_words(' '.join(speech)),normalized_words(transcript)
    matcher=difflib.SequenceMatcher(None,exp,got,autojunk=False)
    differences=[{'operation':op,'expected':exp[a:b],'heard':got[c:d]} for op,a,b,c,d in matcher.get_opcodes() if op!='equal']
    numeric=[]
    for token in sorted(set(re.findall(r'\d[\d,]*(?:\.\d+)?(?:st|nd|rd|th)?',' '.join(speech)))):
        phrases=[normalized_words(token),normalized_words(re.sub(r'(st|nd|rd|th)$','',token))]
        numeric.append({'expected':token,'heard':any(got[i:i+len(p)]==p for p in phrases for i in range(len(got)))})
    checks=segment_checks(observed,speech,timing)
    timestamps=timestamp_checks(observed,timing[-1]['end_s'])
    sane=bool(observed) and all(0<=s['start']<s['end']<=timing[-1]['end_s']+.25 for s in observed)
    numbers=all(c['heard'] for c in numeric) and all(c['numbers_pass'] for c in checks)
    words,exclusions=caption_words(observed,speech)
    caption_error=None
    try:readable_cues(words)
    except PipelineError as error:caption_error=str(error)
    passed=matcher.ratio()>=.85 and sane and timestamps and numbers and all(c['word_agreement']>=.75 for c in checks) and caption_error is None
    return {'check':'narration_asr_matches_script','pass':passed,'observation_mode':mode,'transcript':transcript,
            'word_agreement':matcher.ratio(),'differences':differences,'segments':observed,'numeric_checks':numeric,
            'numeric_checks_pass':numbers,'segment_checks':checks,'word_timestamps_pass':timestamps,
            'caption_exclusions':exclusions,'caption_error':caption_error,
            'requires_editorial_review':any(item.get('numeric_hypothesis') or item.get('requires_editorial_review') for item in exclusions),
            'detail':f'{mode}: ordered normalized word agreement {matcher.ratio():.3f}; numeric/critical terms={numbers}; captions={caption_error or "valid observed timings"}'}


def choose_observation(full,parts,speech,timing, *, require_exact=False):
    # Historical derived packages keep their recorded evaluation policy. Fresh
    # inspection/cache replay explicitly requires the same strict spoken words
    # that the next scene gate expects; prefer an already-observed exact pass.
    candidates=[evaluate_observation(full,speech,timing,'full_narration'),evaluate_observation(parts,speech,timing,'per_segment')]
    if require_exact:
        expected=normalized_words(' '.join(speech),keep_and=True)
        for candidate in candidates:
            exact=normalized_words(candidate['transcript'],keep_and=True)==expected
            per_scene=[]
            for text,span in zip(speech,timing):
                actual=' '.join(w['word'] for segment in candidate['segments'] for w in segment.get('words',[]) if span['start_s']<=(w['start']+w['end'])/2<span['end_s'])
                per_scene.append(normalized_words(actual,keep_and=True)==normalized_words(text,keep_and=True))
            candidate.update({'legacy_backend_pass':candidate['pass'],'strict_spoken_words_pass':exact,'strict_scene_words_pass':all(per_scene),'pass':bool(candidate['pass'] and exact and all(per_scene))})
    chosen=next((r for r in candidates if r['pass']),candidates[0])
    return {**chosen,'candidate_evaluations':[{k:v for k,v in r.items() if k not in ('segments','transcript')} for r in candidates],
            'full_narration_asr':full,'per_segment_asr':parts,
            'exact_policy_required':require_exact,
            'selection_rule':('Prefer a complete-narration observation only when every spoken word and scene matches; otherwise an already-observed exact per-segment pass; never synthesize or guess replacement words' if require_exact else 'Prefer complete-narration observation only if all existing numeric/critical-term/segment/timestamp/caption gates pass; otherwise independently passing per-segment observation; failed raw observations preserved')}



def write_captions(report,package):
    if report.get('pass') is not True:raise PipelineError('ASR observation failed strict validation; captions not generated')
    # Use the exclusions already evaluated against the approved speech, without
    # reclassifying every word against an empty whitelist on a saved replay.
    excluded={(w['start'],w['end'],w['word']) for w in report.get('caption_exclusions',[])}
    words=[w for s in report['segments'] for w in s.get('words',[]) if (w['start'],w['end'],w['word']) not in excluded]
    corrections=[]
    if report.get('input_lineage') and (Path(package)/'script.json').is_file() and (Path(package)/'timing.json').is_file():
        from .common import read_json
        from .voice import speech_text, speech_for_script
        from .asr_lineage import verify_audio_inputs
        from .caption_orthography import source_units
        script=read_json(Path(package)/'script.json');spans=read_json(Path(package)/'timing.json')['segments']
        verify_audio_inputs(report,Path(package)/'audio/narration.wav',[speech_for_script(script,s['voiceover']) for s in script['segments']],spans,package)
        words,corrections=source_units(words,spans,[s['voiceover'] for s in script['segments']])
        from .caption_clock import clock_units
        words,clock_changes=clock_units(words,spans,[s['voiceover'] for s in script['segments']]);corrections+=clock_changes
    report['caption_orthography_corrections']=corrections
    cues=readable_cues(words);srt=[];vtt=['WEBVTT','']
    for i,cue in enumerate(cues,1):
        start,end=cue[0]['start'],cue[-1]['end'];text=caption_text(''.join(w['word'] for w in cue).strip())
        srt += [str(i),f'{timestamp(start,",")} --> {timestamp(end,",")}',text,'']
        vtt += [f'{timestamp(start,".")} --> {timestamp(end,".")}',text,'']
    write_text(Path(package)/'subtitles.srt','\n'.join(srt)+'\n');write_text(Path(package)/'subtitles.vtt','\n'.join(vtt)+'\n')
    write_json(Path(package)/'asr.json',report)
    return len(cues)


def _decode_observations(narration,timing,cfg,package):
    from faster_whisper import WhisperModel
    model_dir = Path(cfg['model_dir'])
    if not (model_dir / 'model.bin').is_file():
        raise PipelineError(f'Social Whisper model missing: {model_dir}')
    model = WhisperModel(str(model_dir), device='cpu', compute_type='int8',
                         cpu_threads=int(cfg.get('cpu_threads', 4)), local_files_only=True)
    segments, info = model.transcribe(str(narration), language='en', beam_size=5,
                                      word_timestamps=True, condition_on_previous_text=False, temperature=0.0)
    observed = []
    for segment in segments:
        observed.append({'start': segment.start, 'end': segment.end, 'text': segment.text,
                         'words': [{'start': w.start, 'end': w.end, 'word': w.word, 'probability': w.probability}
                                   for w in (segment.words or [])]})
    full_narration = observed
    observed = []
    for span in timing:
        segment_file = package / span['audio']
        offset = span.get('speech_start_s', span['start_s'] + .18)
        parts, _ = model.transcribe(str(segment_file), language='en', beam_size=5,
                                    word_timestamps=True, condition_on_previous_text=False, vad_filter=True, temperature=0.0)
        for part in parts:
            observed.append({'start': part.start + offset, 'end': part.end + offset, 'text': part.text,
                             'source_audio': span['audio'],
                             'words': [{'start': w.start+offset, 'end': w.end+offset, 'word': w.word, 'probability': w.probability}
                                       for w in (part.words or [])]})
    return full_narration,observed
