"""Conservative extraction of explicit OJP two-stage deadlines from official NOFO PDFs."""
import io
import re
import ssl
import urllib.request
from urllib.parse import urlparse
from .common import PipelineError, parse_date, sha256_bytes, utc_now, write_json, atomic_bytes


def parse_steps(text):
    text = ' '.join(text.split())
    output = {}
    date = r'([A-Za-z]+\s+\d{1,2},\s+\d{4})'
    clock = r'(\d{1,2}:\d{2}\s*[ap]\.m\.)\s*ET'
    for label in ('Grants.gov', 'JustGrants'):
        pattern = re.escape(label) + r'\s*:\s*' + date + r',?\s*(?:by\s+)?' + clock
        matches = re.findall(pattern, text, re.I)
        valid = {(parse_date(d), t.lower().replace(' ', '')) for d, t in matches if parse_date(d)}
        if len(valid) != 1:
            return None
        d, t = next(iter(valid))
        output[label] = {'date': d.isoformat(), 'time': t, 'timezone': 'ET'}
    if output['Grants.gov']['date'] > output['JustGrants']['date']:
        return None
    return output


def fetch_document(record, directory):
    url = record.get('full_announcement_url') or ''
    host = (urlparse(url).hostname or '').lower()
    if not host.endswith('.ojp.gov') and host != 'ojp.gov':
        return {'checked': False, 'reason': 'No supported official OJP PDF linked'}
    if urlparse(url).scheme != 'https' or not urlparse(url).path.lower().endswith('.pdf'):
        return {'checked': False, 'reason': 'Announcement link is not a supported HTTPS PDF'}
    class SameHostRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, request, fp, code, msg, headers, newurl):
            if urlparse(newurl).scheme != 'https' or urlparse(newurl).hostname != host:
                raise PipelineError('Official NOFO redirected outside its source host')
            return super().redirect_request(request, fp, code, msg, headers, newurl)
    try:
        import truststore
        context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except ImportError:
        context = ssl.create_default_context()
    opener = urllib.request.build_opener(SameHostRedirect(), urllib.request.HTTPSHandler(context=context))
    request = urllib.request.Request(url, headers={'User-Agent':'SocialReels/1.0 official-NOFO-check'})
    with opener.open(request, timeout=30) as response:
        data = response.read(8*1024*1024+1)
    if len(data) > 8*1024*1024 or not data.startswith(b'%PDF-'):
        raise PipelineError('Official NOFO is not a valid bounded PDF')
    filename = 'nofo_'+record['opportunity_id']+'.pdf'
    atomic_bytes(directory/filename, data)
    meta = {'url':url,'file':'source/'+filename,'sha256':sha256_bytes(data),'bytes':len(data),'fetched_at':utc_now().isoformat()}
    return data,meta


def check_nofo(record, directory):
    fetched=fetch_document(record,directory)
    if isinstance(fetched,dict):return fetched
    data,meta=fetched
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data))
    text = reader.pages[0].extract_text() or ''
    steps = parse_steps(text)
    report = {'checked':True,'source':meta,'page':1,'steps':steps,
              'reason':None if steps else 'Explicit two-stage dates not unambiguously extracted'}
    write_json(directory/'nofo_check.json', report)
    if steps:
        expected = parse_date(record.get('close_date'))
        if expected and expected.isoformat() != steps['Grants.gov']['date']:
            raise PipelineError('Grants.gov listing and official NOFO first-step deadlines disagree')
        record['submission_steps'] = steps
        record['submission_steps_source'] = meta
    elif 'JustGrants' in text:
        raise PipelineError('Multi-stage application detected but deadlines need review; no generic closing claim')
    return report
