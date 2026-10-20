"""Repeat-use identity checks for full official NSF HTML solicitations."""
import datetime as dt
import difflib
import re
from pathlib import Path
from .common import PipelineError,read_json,sha256_bytes,sha256_file,utc_now
from .announcements import nsf_page
from .nsf_document import parse_solicitation,deadline_agreement

def document_check_nsf(root,current,evidence,fetch=None):
    root=Path(root).resolve();evidence=Path(evidence)
    result={'kind':'nsf_html_solicitation','current_content_confirmed':False,'changed':False,'differences':[],
            'scope':'Full solicitation article/markup, document version, publisher alerts and recognized full-proposal date; not all linked policies or applicant qualification'}
    try:
        saved=read_json(root/'topic.json')['selected'];previous=saved['announcement_source']
        old=(root/previous['file']).resolve()
        if not old.is_relative_to(root) or not old.is_file() or sha256_file(old)!=previous['sha256']:
            raise ValueError('Saved full HTML source missing or hash mismatch')
        olddoc=parse_solicitation(old.read_bytes(),previous.get('final_url') or previous['url'])
        if not olddoc['complete'] or olddoc['content_sha256']!=previous['content_sha256']:
            raise ValueError('Saved full HTML document identity invalid')
        raw,meta=(fetch or nsf_page)(current,evidence)
        if len(raw)>2*1024*1024 or sha256_bytes(raw)!=meta['sha256']:raise ValueError('Current HTML response bytes invalid')
        stamp=dt.datetime.fromisoformat(meta['fetched_at'])
        if stamp.tzinfo is None or not -300<=(utc_now()-stamp).total_seconds()<=300:raise ValueError('Current HTML observation not fresh')
        document=parse_solicitation(raw,meta.get('final_url') or meta['url'])
        result.update(saved_document=previous,current_document={**meta,'content_sha256':document['content_sha256'],'document_version':document['document_version']},
                      raw_html_changed=previous['sha256']!=meta['sha256'],document_complete=document['complete'],
                      explicitly_closed=document['explicitly_closed'],publisher_status_quote=document['publisher_status_quote'])
        if not document['complete']:raise ValueError('Current response is not a complete supported solicitation; content unconfirmed')
        agreement=deadline_agreement(document,current.get('close_date'));result['deadline_agreement']=agreement
        for field in ('document_version','content_sha256'):
            if olddoc[field]!=document[field]:result['differences'].append({'kind':field,'before':olddoc[field],'after':document[field]})
        if previous.get('final_url')!=meta.get('final_url'):
            result['differences'].append({'kind':'document_final_url','before':previous.get('final_url'),'after':meta.get('final_url')})
        if olddoc['explicitly_closed']!=document['explicitly_closed']:
            result['differences'].append({'kind':'publisher_closed_status','before':olddoc['explicitly_closed'],'after':document['explicitly_closed']})
        if not agreement['pass']:result['differences'].append({'kind':'deadline_source_conflict','detail':agreement})
        result['changed']=bool(result['differences'])
        result['current_content_confirmed']=not result['changed'] and not document['explicitly_closed']
        if document['explicitly_closed']:result['reason']='Official publisher is not currently accepting proposals'
        if olddoc['text']!=document['text']:
            delta=list(difflib.unified_diff(olddoc['text'].splitlines(),document['text'].splitlines(),fromfile='saved_full_solicitation',tofile='current_full_solicitation',lineterm=''))
            evidence.mkdir(parents=True,exist_ok=True);path=evidence/'nsf_document_text_diff.txt';path.write_text('\n'.join(delta),encoding='utf-8')
            result['text_diff_file']=str(path.resolve())
            important=re.compile(r'\$|eligib|applicant|deadline|award|funding|million|thousand|proposals',re.I)
            result['important_condition_excerpts']={kind:[line[1:] for line in delta if line.startswith(sign) and not line.startswith(sign*3) and important.search(line)][:40]
                                                   for kind,sign in [('removed','-'),('added','+')]}
    except (PipelineError,OSError,ValueError,KeyError,TypeError,AttributeError) as error:
        result['error']=type(error).__name__+': '+str(error)[:300]
    return result
