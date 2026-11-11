"""Narrow caption spelling repairs, source-scoped and anchored to observed unions."""
import re


def source_units(words,spans,source_text):
    rules=[(('cyber','infrastructure'),'cyberinfrastructure'),
           (('a','cross','principle','investigator'),'across principal investigator'),
           (('co','principle','investigator'),'co-principal investigator')]
    output=[];corrections=[];i=0
    def clean(value):return re.sub(r'[^a-z]','',value.lower())
    def phrase(value):return ' '.join(re.sub(r'[^a-z ]',' ',value.lower()).split())
    while i<len(words):
        changed=False
        for tokens,target in rules:
            group=words[i:i+len(tokens)]
            if len(group)!=len(tokens) or tuple(clean(w['word']) for w in group)!=tokens:continue
            matches=[(span,text) for span,text in zip(spans,source_text) if span['start_s']-.12<=group[0]['start'] and group[-1]['end']<=span['end_s']+.12]
            if len(matches)!=1 or phrase(target) not in phrase(matches[0][1]):continue
            if any(b['start']-a['end']>.15 or b['start']<a['start'] for a,b in zip(group,group[1:])):continue
            punctuation=re.search(r'[,.;:!?]+$',group[-1]['word']);suffix=punctuation[0] if punctuation else ''
            unit={**group[0],'word':' '+target+suffix,'start':group[0]['start'],'end':max(w['end'] for w in group)}
            output.append(unit);corrections.append({'raw_words':[dict(w) for w in group],'display_text':unit['word'],'start':unit['start'],'end':unit['end'],
                                                     'source_segment':matches[0][0]['id'],'basis':'Exact source-script orthography for a listed compound/homophone; observed union retained, no new word-level timing or audio claim'})
            i+=len(group);changed=True;break
        if not changed:output.append(dict(words[i]));i+=1
    return output,corrections
