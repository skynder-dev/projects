"""Bind a saved scenario to the actual current NOFO bytes, not just POSTED status."""
import difflib
import io
import re
from pathlib import Path
from .common import PipelineError,read_json,sha256_bytes,sha256_file,write_json,utc_now
from .nofo import fetch_document,parse_steps

def document_check(root, current, detail, evidence, fetch=None):
    root=Path(root);evidence=Path(evidence)
    result={'current_content_confirmed':False,'changed':False,'differences':[],
            'scope':'Exact current PDF bytes and announced synopsis version; changed documents require editorial review'}
    try:
        saved=read_json(root/'topic.json')['selected']
        if (saved.get('announcement_source') or {}).get('kind')=='structured_pdf_nofo':
            from .structured_nofo import document_check as structured_check
            return structured_check(root,current,detail,evidence,fetch=fetch)
        if (saved.get('announcement_source') or {}).get('kind')=='nih_html_attachment':
            from .nih_review import document_check_nih
            return document_check_nih(root,current,detail,evidence,fetch=fetch)
        if (saved.get('announcement_source') or {}).get('kind')=='nsf_html_solicitation':
            from .nsf_document_review import document_check_nsf
            return document_check_nsf(root,current,evidence,fetch=fetch)
        previous=saved.get('submission_steps_source') or read_json(root/'source/nofo_check.json')['source']
        old=(root/previous['file']).resolve()
        if not old.is_relative_to(root.resolve()) or not old.is_file() or sha256_file(old)!=previous['sha256']:
            raise ValueError('Saved NOFO missing or hash mismatch')
        result['saved_document']=previous
        fetched=(fetch or fetch_document)(current,evidence)
        if isinstance(fetched,dict):raise ValueError(fetched.get('reason','NOFO unavailable'))
        data,meta=fetched
        if not data.startswith(b'%PDF-') or len(data)>8*1024*1024 or sha256_bytes(data)!=meta['sha256']:
            raise ValueError('Current NOFO response bytes invalid')
        import datetime as dt
        stamp=dt.datetime.fromisoformat(meta['fetched_at'])
        if stamp.tzinfo is None or not -300<=(utc_now()-stamp).total_seconds()<=300:
            raise ValueError('Current NOFO observation missing a fresh timestamp')
        result['current_document']=meta
        result['evidence_file']=str((evidence/Path(meta['file']).name).resolve())
        snapshot=read_json(root/'sources.json')['selected_snapshot']['file']
        olddetail=read_json(root/snapshot).get('data',{})
        for key in ('version','revision','createTimeStamp'):
            before=(olddetail.get('synopsis') or {}).get(key)
            after=(detail.get('synopsis') or {}).get(key)
            if before!=after:result['differences'].append({'kind':'announced_version','field':key,'before':before,'after':after})
        if previous.get('url')!=meta.get('url'):
            result['differences'].append({'kind':'document_url','before':previous.get('url'),'after':meta.get('url')})
        if previous['sha256']!=meta['sha256']:
            result['differences'].append({'kind':'document_bytes','before_sha256':previous['sha256'],'after_sha256':meta['sha256'],
                                          'meaning':'Changed bytes require review even if extracted text appears unchanged'})
            result['changed']=True
            try:
                from pypdf import PdfReader
                def text(raw):
                    pdf=PdfReader(io.BytesIO(raw))
                    if len(pdf.pages)>100:raise ValueError('NOFO exceeds bounded 100-page text comparison')
                    lines=[]
                    for number,page in enumerate(pdf.pages,1):
                        lines.extend('[page '+str(number)+'] '+line.strip() for line in (page.extract_text() or '').splitlines() if line.strip())
                        if sum(map(len,lines))>2_000_000:raise ValueError('NOFO text comparison exceeds bound')
                    return lines
                before=text(old.read_bytes());after=text(data)
                delta=list(difflib.unified_diff(before,after,fromfile='saved_NOFO',tofile='current_NOFO',lineterm=''))
                evidence.mkdir(parents=True,exist_ok=True)
                diff=evidence/'nofo_text_diff.txt';diff.write_text('\n'.join(delta),encoding='utf-8')
                result['text_diff_file']=str(diff.resolve())
                result['text_changed']=bool(delta)
                terms=re.compile(r'\$|eligib|applicant|deadline|Grants\.gov|JustGrants|award|funding|million|thousand',re.I)
                result['important_condition_excerpts']={
                    'removed':[line[1:] for line in delta if line.startswith('-') and not line.startswith('---') and terms.search(line)][:40],
                    'added':[line[1:] for line in delta if line.startswith('+') and not line.startswith('+++') and terms.search(line)][:40]}
                result['submission_steps_before']=parse_steps(' '.join(before))
                result['submission_steps_after']=parse_steps(' '.join(after))
                result['text_diff_is_complete']=True
            except Exception as error:
                result['text_review_error']=type(error).__name__+': '+str(error)[:300]
                result['text_diff_is_complete']=False
        result['changed']=bool(result['differences'])
        result['current_content_confirmed']=not result['changed']
    except (PipelineError,OSError,ValueError,KeyError,TypeError,AttributeError) as error:
        result['error']=type(error).__name__+': '+str(error)[:300]
    return result

def revoke_editorial(folder, package_id, report):
    """Persist a confirmed source change in the owned job, preserving original approval."""
    changes=report.get('changed_synopsis_fields') or (report.get('nofo') or {}).get('differences')
    if not changes:return False
    folder=Path(folder);path=folder/'editorial_review.json'
    try:approval=read_json(path)
    except FileNotFoundError:approval=None
    if isinstance(approval,dict) and approval.get('approved') is True:
        archive=folder/('editorial_review_before_source_change_'+package_id[:16]+'.json')
        if not archive.exists():write_json(archive,approval)
    invalidation={'approved':False,'reason':'Confirmed official source/NOFO change requires scenario review',
                  'package_id':package_id,'revoked_at':utc_now().isoformat(),
                  'synopsis_changes':report.get('changed_synopsis_fields',[]),
                  'document_differences':(report.get('nofo') or {}).get('differences',[])}
    write_json(path,invalidation)
    return True


def _owned_registered_run(db,stored,root):
    # Queue stores new runs relative to its root; retain legacy absolute rows.
    candidate=Path(stored)
    if not candidate.is_absolute():candidate=db.parent/candidate
    candidate=candidate.resolve()
    return candidate.is_relative_to(db.parent.resolve()) and candidate==root


def revoke_owned_approval(root, report):
    """Only a matching durable Social job may have its saved approval changed."""
    import sqlite3
    from contextlib import closing
    root=Path(root).resolve();folder=root.parent.parent
    if root.parent.name!='runs' or len(folder.name)!=32 or any(c not in '0123456789abcdef' for c in folder.name):
        return False
    db=folder.parent/'queue.sqlite3'
    if not db.is_file():return False
    with closing(sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)) as connection:
        row=connection.execute('SELECT run_dir FROM jobs WHERE id=?',(folder.name,)).fetchone()
    if not row or not row[0] or not _owned_registered_run(db,row[0],root):return False
    return revoke_editorial(folder,report['package_id'],report)


def owned_approval(root,package_id):
    """Only an actual approval of this exact owned package can be called valid."""
    import sqlite3
    from contextlib import closing
    root=Path(root).resolve();folder=root.parent.parent
    if root.parent.name!='runs' or len(folder.name)!=32 or any(c not in '0123456789abcdef' for c in folder.name):return None
    db=folder.parent/'queue.sqlite3'
    if not db.is_file():return None
    with closing(sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)) as connection:
        row=connection.execute('SELECT run_dir FROM jobs WHERE id=?',(folder.name,)).fetchone()
    if not row or not row[0] or not _owned_registered_run(db,row[0],root):return None
    try:approval=read_json(folder/'editorial_review.json')
    except FileNotFoundError:return None
    from .workflow import editorial_state
    return editorial_state(approval,package_id)['approved']
