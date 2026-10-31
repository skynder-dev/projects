"""WordPress public-page identity/error checks; stdlib only, no transport/model."""
from html.parser import HTMLParser
from urllib.parse import urlsplit
CONTRACT=4
def validate(url,raw,original=False):
 text=raw.decode('utf-8')if isinstance(raw,bytes)else raw
 if not isinstance(text,str):raise ValueError('UTF-8 WordPress HTML required')
 expected=urlsplit(url)
 if expected.scheme!='https'or expected.hostname!='wordpress.org'or expected.username is not None or expected.password is not None or expected.port not in [None,443]:raise ValueError('Expected original WordPress URL required')
 if original and not expected.path.startswith('/support/topic/'):raise ValueError('Original WordPress topic URL required')
 from html_document_identity import Metadata,denied
 m=Metadata();m.feed(text)
 if denied(m):raise ValueError('WordPress access-denied/challenge document is not an original question')
 if not m.urls:raise ValueError('WordPress canonical source identity missing')
 for value in m.urls:
  actual=urlsplit(value or'')
  if actual.scheme!='https'or actual.hostname!=expected.hostname or actual.username is not None or actual.password is not None or actual.port not in [None,443]or actual.path.rstrip('/')!=expected.path.rstrip('/'):raise ValueError('WordPress canonical source identity mismatched')
 if original and m.originals!=1:raise ValueError('Exactly one original WordPress topic body required; replies are not the question')
 return text
