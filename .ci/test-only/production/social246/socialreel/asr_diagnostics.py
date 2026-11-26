"""Source-scoped ASR diagnostic formatting; never replaces raw score or acceptance gates."""
import re,difflib
from .subtitles import normalized_words

def formatting_words(text,source):
    rules=[]
    if re.search(r'\bon[- ]?screen\b',source,re.I):rules.append((r'\bon[- ]?screen\b','on screen'))
    for joined,separated in (('cybertraining','cyber training'),('cyberinfrastructure','cyber infrastructure')):
        if re.search(r'\b'+joined+r'\b',source,re.I):rules.append((r'\b'+separated.replace(' ',r'[- ]?')+r'\b',separated))
    for pattern,value in rules:text=re.sub(pattern,value,text,flags=re.I)
    return normalized_words(text)

def diagnose(expected,heard,raw_score):
    raw_expected=normalized_words(expected);raw_heard=normalized_words(heard)
    raw=difflib.SequenceMatcher(None,raw_expected,raw_heard,autojunk=False)
    a,b=formatting_words(expected,expected),formatting_words(heard,expected);canonical=difflib.SequenceMatcher(None,a,b,autojunk=False)
    differences=[]
    for op,i,j,k,l in raw.get_opcodes():
        if op=='equal':continue
        want,got=raw_expected[i:j],raw_heard[k:l];left=' '.join(want);right=' '.join(got)
        if formatting_words(left,expected)==formatting_words(right,expected):category='confirmed_writing_or_compound_tokenization'
        elif want==['proposer'] and got==['proposal']:category='unresolved_lexical_hypotheses_not_a_confirmed_synthesis_error'
        elif 'principal' in want and 'principle' in got:category='homophone_spelling_ambiguity'
        else:category='unresolved_lexical_or_boundary_difference'
        if 'across' in want and got[:2]==['a','cross']:category='boundary_and_homophone_ambiguity'
        differences.append({'operation':op,'expected':want,'heard':got,'category':category,'confirmed_synthesis_error':False})
    remaining=[{'operation':op,'expected':a[i:j],'heard':b[k:l]} for op,i,j,k,l in canonical.get_opcodes() if op!='equal']
    return {'scope':'Diagnostic writing/compound comparison only; not an alternative PASS or auditory judgment','original_stored_ASR_agreement':raw_score,'strict_agreement_recomputed':raw.ratio(),'formatting_diagnostic_agreement':canonical.ratio(),'difference_classification':differences,'remaining_after_formatting':remaining,'automatic_equivalences':['onscreen/on-screen/on screen when source contains this form','source-listed cybertraining/cyber training and cyberinfrastructure/cyber infrastructure compounds'],'homophones_or_proposer_proposal_not_normalized':True,'raw_score_or_threshold_changed':False,'subjective_listening':False,'synthesis_error_confirmed':False,'review_required':bool(remaining)}
