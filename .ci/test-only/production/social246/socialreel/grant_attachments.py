"""Bounded official Grants.gov HTML attachment discovery and transport.

Transport validation is deliberately separate from full NOFO review/readiness.
"""
import email.message
import json
import ssl
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit
from .common import PipelineError, atomic_bytes, sha256_bytes, utc_now, check_cancel, write_json

LIMIT = 2 * 1024 * 1024


def _id(value):
    return str(value) if isinstance(value, (int, str)) and not isinstance(value, bool) and str(value).isascii() and str(value).isdigit() and int(value) > 0 else None


def discover(detail, opportunity_id, mime="text/html"):
    """Only full-announcement HTML descriptors with matching parent associations."""
    oid = _id(opportunity_id)
    if not oid or _id(detail.get('id')) != oid:
        return []
    result = []
    folders = detail.get('synopsisAttachmentFolders') or []
    if not isinstance(folders, list):
        return []
    for folder in folders:
        if not isinstance(folder, dict) or _id(folder.get('opportunityId')) != oid:
            continue
        fid = _id(folder.get('id'))
        if not fid or str(folder.get('folderType', '')).strip().casefold() != 'full announcement':
            continue
        attachments = folder.get('synopsisAttachments') or []
        if not isinstance(attachments, list):
            continue
        for att in attachments:
            if not isinstance(att, dict):
                continue
            aid = _id(att.get('id'))
            name = att.get('fileName')
            size = att.get('fileLobSize')
            if not (aid and _id(att.get('opportunityId')) == oid and _id(att.get('synopsisAttFolderId')) == fid):
                continue
            if str(att.get('mimeType', '')).split(';')[0].strip().lower() not in ({'application/pdf','application/octet-stream'} if mime=='application/pdf' else {mime}):
                continue
            if not isinstance(name, str) or not name.lower().endswith(('.html', '.htm') if mime=='text/html' else ('.pdf',)) or '/' in name or '\\' in name:
                continue
            if not isinstance(size, int) or isinstance(size, bool) or not 0 < size <= LIMIT:
                continue
            result.append({'opportunity_id': oid, 'folder_id': fid, 'attachment_id': aid,
                           'file_name': name, 'bytes': size, 'mime_type': att['mimeType']})
    return result


def official_url(value):
    try:
        p = urlsplit(value)
        host = (p.hostname or '').lower()
        return p.scheme == 'https' and not p.username and not p.password and p.port in (None, 443) and (host == 'grants.gov' or host.endswith('.grants.gov'))
    except ValueError:
        return False


def _fetch(descriptor, snapshot, directory, mime="text/html"):
    """Rebind descriptor to saved API bytes before issuing one bounded GET."""
    directory = Path(directory)
    oid = _id(descriptor.get('opportunity_id'))
    aid = _id(descriptor.get('attachment_id'))
    expected_file = 'source/opportunity_' + str(oid) + '.json'
    if not oid or not aid or snapshot.get('file') != expected_file:
        raise PipelineError('Attachment metadata snapshot identity is invalid')
    saved = (directory / ('opportunity_' + oid + '.json')).read_bytes()
    if sha256_bytes(saved) != snapshot.get('sha256'):
        raise PipelineError('Attachment metadata snapshot hash differs')
    detail = json.loads(saved).get('data') or {}
    if descriptor not in discover(detail, oid, mime):
        raise PipelineError('Attachment is not associated with this official detail snapshot')
    # Ambiguous documents require content-aware review; never select the first silently.
    if len(discover(detail, oid, mime)) != 1:
        raise PipelineError('Full announcement HTML attachment is ambiguous')
    url = 'https://apply07.grants.gov/grantsws/rest/opportunity/att/download/' + aid

    class Redirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, request, fp, code, msg, headers, newurl):
            if not official_url(newurl):
                raise PipelineError('Attachment redirect outside official HTTPS Grants.gov scope')
            return super().redirect_request(request, fp, code, msg, headers, newurl)

    try:
        import truststore
        context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except ImportError:
        context = ssl.create_default_context()
    opener = urllib.request.build_opener(Redirect(), urllib.request.HTTPSHandler(context=context))
    check_cancel()
    with opener.open(urllib.request.Request(url, headers={'User-Agent': 'SocialReels/1.0 official-source-review'}), timeout=15) as response:
        raw = response.read(LIMIT + 1)
        final = response.url
        status = response.status
        content_type = response.headers.get('Content-Type', '')
        disposition = response.headers.get('Content-Disposition', '')
    check_cancel()
    if status != 200 or not official_url(final):
        raise PipelineError('Attachment did not return an official successful response')
    if len(raw) != descriptor['bytes'] or len(raw) > LIMIT:
        raise PipelineError('Attachment size differs from official metadata')
    if content_type.split(';')[0].strip().lower() not in ({'application/pdf','application/octet-stream'} if mime=='application/pdf' else {mime}):
        raise PipelineError('Attachment response MIME type differs from descriptor')
    message = email.message.Message()
    message['Content-Disposition'] = disposition
    if message.get_filename() != descriptor['file_name']:
        raise PipelineError('Attachment response filename differs from official metadata')
    if mime=='text/html':
        try:raw.decode('utf-8')
        except UnicodeDecodeError as error:raise PipelineError('Attachment HTML is not valid UTF-8') from error
    elif not raw.startswith(b'%PDF-'):raise PipelineError('Attachment PDF signature missing')
    filename = 'attachment_' + aid + ('.html' if mime=='text/html' else '.pdf')
    atomic_bytes(directory / filename, raw)
    meta = {'kind': 'grants_gov_html_attachment' if mime=='text/html' else 'grants_gov_pdf_attachment', 'url': url, 'final_url': final,
                 'http_status': status, 'content_type': content_type, 'descriptor': descriptor,
                 'listing_snapshot': dict(snapshot), 'file': 'source/' + filename,
                 'sha256': sha256_bytes(raw), 'bytes': len(raw), 'fetched_at': utc_now().isoformat(),
                 'full_conditions_confirmed': False, 'scope': 'Official association and transport only'}
    write_json(directory/('attachment_'+aid+'_transport.json'),meta)
    return raw,meta


def fetch_html(descriptor,snapshot,directory):
    return _fetch(descriptor,snapshot,directory)

def discover_pdf(detail,opportunity_id):
    return discover(detail,opportunity_id,"application/pdf")

def fetch_pdf(descriptor,snapshot,directory):
    return _fetch(descriptor,snapshot,directory,"application/pdf")
