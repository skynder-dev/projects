"""Finite preparation diagnostics, not semantic/creative approval or text repair."""
import re,unicodedata

def guarantee_mentions(text):
    t=text.casefold().replace('\u2019',"'")
    rows=[]
    for m in re.finditer(r'\bguaranteed\b',t):
        prefix=t[:m.start()];clause=re.split(r'[.;!?:,\n\r\u2013\u2014-]|\b(?:and|or|nor|but|however)\b',prefix)[-1]
        direct=re.search(r"\b(?:not|never|no|non|isn't|aren't|wasn't)(?:\s+(?:a|an|any|longer|necessarily|yet|ever)){0,2}\s+$",clause)
        # Do not carry negation across a conjunction: a following predicate
        # can assert a guarantee. Ambiguous coordination remains review-only.
        double_negative=bool(re.search(r"\b(?:not|isn't|aren't|wasn't)\s+(?:not|never)\s+(?:a\s+)?$",clause))
        lexical=bool(re.search(r'\b(?:not|non)-$',prefix))
        lexical_double=bool(re.search(r"\b(?:not|never|isn't)\s+(?:not|non)-$",prefix))
        scope_prefix=re.split(r'[.;!?:,\n\r\u2013\u2014-]|\b(?:and|or|nor|but|however)\b',prefix[:-1] if lexical else prefix)[-1]
        negators=re.findall(r"\b(?:not|never|no|non|isn't|aren't|wasn't)\b",scope_prefix)
        # Multiple negators can invert the claim even with intervening adverbs
        # or a lexical non- prefix. Never infer safe negation from the final token.
        state='negated' if (direct or lexical) and len(negators)==1 and not (double_negative or lexical_double) else 'scope_review' if re.search(r'\b(?:if|unless|whether)\b',clause) else 'affirmative_or_unresolved'
        rows.append({'start':m.start(),'end':m.end(),'state':state,'scope':'Finite negation scope only; not proof a benefit is guaranteed/available'})
    return rows

def guarantee_risk(text):return any(r['state']!='negated' for r in guarantee_mentions(text))

def facet_binding(case,text,keys):
    """Presence of a known key is not support for every assertion in its quote."""
    if case.get('source_id')!='usa':
        return {'status':'requires_semantic_review','checked_facets':[],'missing':[],'semantic_entailment_verified':False}
    known={c['key'] for c in case['claims']};supplied=set(k for k in keys if isinstance(k,str)) if isinstance(keys,list) else set()
    t=' '.join(text.casefold().split()) if isinstance(text,str) else '';requirements=[]
    if re.search(r'\bstate\b',t) and (re.search(r'\bfirst\b|\bstart with\b',t)):
        requirements.append(('state_first_order',{'one_action'}))
    if re.search(r'\b(?:unpaid wages|back pay)\b',t):requirements.append(('wage_route',{'wages_scope','concrete_examples'}))
    if re.search(r'\b(?:unclaimed pension|pbgc)\b',t):requirements.append(('pension_route',{'pension_scope','concrete_examples'}))
    if 'usa.gov' in t:requirements.append(('official_guide_identity',{'guide','one_action','cta'}))
    rows=[{'facet':name,'accepted_existing_keys':sorted(options&known),'supplied_support':sorted(supplied&options&known)} for name,options in requirements]
    missing=[r for r in rows if not r['supplied_support']]
    return {'status':'insufficient_known_facet_binding' if missing else 'finite_facets_bound_not_semantic_approval' if rows else 'requires_semantic_review','checked_facets':rows,'missing':missing,'semantic_entailment_verified':False,'scope':'Missing facet binding is a provenance failure, not automatic factual falsehood'}

def screen_field(text,layout_note=None):
    if not isinstance(text,str):return {'preparation_valid':False,'errors':['Visible screen text must be a string'],'display_text_extracted':False}
    notes=[]
    if not has_spoken_content(text):notes.append('Visible screen wording requires a letter or number')
    # Detection view only: never expose normalized/stripped text as a caption.
    # Unicode quotes, Markdown wrappers and arbitrary field labels before a colon
    # must not hide an imperative. No catalogue of label names or pictured nouns.
    view=''.join(c for c in unicodedata.normalize('NFKC',text) if unicodedata.category(c)!='Cf')
    staged=bool(re.search(r"(?:^|[\n:;.!?\-\u2013\u2014]|[\"'\u2018\u2019\u201c\u201d\u00ab\u00bb\u2039\u203a\[({`>*])[^\w]*?(?:please\s+)?(?:show|display|highlight|render|animate|insert|place)\b",view,re.I))
    mixed=bool(re.search(r'\b(?:alongside the text|with the (?:headline|instruction))\b',text,re.I))
    if staged or mixed:notes.append('Visible-text field contains possible staging instructions; review literal wording separately, never extract or rewrite')
    if any(ord(c)<32 and c not in '\n\r\t' for c in text):notes.append('Visible text contains non-display control characters')
    if layout_note is not None and (not isinstance(layout_note,str) or not layout_note.strip() or len(layout_note)>400):notes.append('Optional layout_note must be nonempty bounded text')
    if isinstance(layout_note,str) and (guarantee_risk(layout_note) or re.search(r'[$\u00a3\u20ac]\s*\d',layout_note)):notes.append('Financial assertions in layout_note require separate review; staging cannot bypass visible-text grounding')
    return {'preparation_valid':not notes,'errors':notes,'display_text_extracted':False,'layout_note_separate':layout_note is not None,'semantic_correspondence_verified':False}

def narration_signals(text):
    words=len(text.split());opening=re.split(r'[.!?]',text,maxsplit=1)[0];signals=[]
    if re.match(r"\s*if you(?:'re| are) wondering\b",text,re.I):signals.append('Meta opening delays the practical viewer benefit; creative review required')
    if re.search(r'\bto take one concrete next action\b',text,re.I):signals.append('Task/meta phrasing in narration; creative review required')
    if words>60:signals.append('Long for planned short reel; review redundancy, not facts. No measured audio duration inferred')
    return {'spoken_words':words,'opening_words':len(opening.split()),'planning_word_range':[40,60],'range_is_soft':True,'signals':signals,'factual_error_from_length':False,'engagement_verified':False,'measured_audio_seconds':None}


def uncovered_narration_words(narration,evidence,known_keys):
    """Exact unique source bindings must cover each whole non-whitespace token.

    Coverage is mechanical provenance only, never entailment or approval.
    Screens cannot supply missing narration evidence. Invalid bindings count zero.
    """
    if not has_spoken_content(narration):raise ValueError("Narration requires spoken content")
    spans=[]
    for row in evidence:
        if not isinstance(row,dict):continue
        q=row.get('quote');keys=row.get('claim_keys')
        if not has_spoken_content(q) or narration.count(q)!=1:continue
        if not isinstance(keys,list) or not keys or any(not isinstance(k,str) or k not in known_keys for k in keys) or len(keys)!=len(set(keys)):continue
        start=narration.index(q);spans.append((start,start+len(q)))
    return [{'start':m.start(),'end':m.end(),'text':m.group()} for m in re.finditer(r'\S+',narration) if not any(a<=m.start() and m.end()<=b for a,b in spans)]


def has_spoken_content(text):
    """Require at least one Unicode letter or number; no minimum word count.

    Whitespace, format controls, punctuation, symbols and combining marks alone
    are not spoken evidence. This is presence only, not pronunciation or truth.
    """
    return isinstance(text,str) and any(c.isalnum() for c in text)
