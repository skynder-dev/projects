"""Clock display punctuation from exact source agreement and observed word unions."""
import re

def clock_units(words,spans,source_text):
    pattern=re.compile(r'\s*(\d{1,2})\s*[:,. ]\s*(\d{1,2})\s*([ap])\.?\s*m\.?([,;!?]?)\s*',re.I)
    source_pattern=re.compile(r'\b(1[0-2]|[1-9]):([0-5]\d)\s*([ap])\.?\s*m\.?',re.I)
    output=[];changes=[];i=0
    while i<len(words):
        changed=False
        for length in (4,3,2,1):
            group=words[i:i+length]
            if len(group)!=length:continue
            found=pattern.fullmatch(' '.join(w['word'].strip() for w in group))
            if not found:continue
            hour,minute,period=int(found[1]),int(found[2]),found[3].lower()
            if not 1<=hour<=12 or not 0<=minute<60:continue
            matches=[span for span,text in zip(spans,source_text) if span['start_s']-.12<=group[0]['start'] and group[-1]['end']<=span['end_s']+.12 and (hour,minute,period) in {(int(h),int(m),p.lower()) for h,m,p in source_pattern.findall(text)}]
            if len(matches)!=1 or any(b['start']-a['end']>.8 or b['start']<a['start'] for a,b in zip(group,group[1:])):continue
            if any(w['end']<w['start'] for w in group) or group[-1]['end']-group[0]['start']>3:continue
            display=f' {hour}:{minute:02d} {period}.m.'+found[4]
            if len(group)==1 and group[0]['word']==display:continue
            unit={**group[0],'word':display,'start':group[0]['start'],'end':max(w['end'] for w in group)};output.append(unit)
            changes.append({'raw_words':[dict(w) for w in group],'display_text':display,'start':unit['start'],'end':unit['end'],'source_segment':matches[0]['id'],'basis':'Exact source-agreeing clock punctuation; original observed word union, no new word/audio timing or recognition score'})
            i+=length;changed=True;break
        if not changed:output.append(dict(words[i]));i+=1
    return output,changes
