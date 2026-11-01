"""Explicit saved-row comparison/preparation proposal. No queue write or token claim."""
from pathlib import Path
from urllib.parse import urlsplit
import copy
import hashlib
import json
import math
import os
import re
import stat
import time
import json_contract
import model_packet
import quote_contract
import source_context

MAX_INPUT_FILES = 4
MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_SELECTED_ROWS = 12
MAX_PACKET_BYTES = 64 * 1024
POLICY = 'explicit-saved-context-proposal-v1'
PUBLIC_HOSTS = {
    'wordpress': 'wordpress.org', 'hackernews': 'news.ycombinator.com',
    'npm': 'www.npmjs.com', 'superuser': 'superuser.com',
    'webapps': 'webapps.stackexchange.com', 'webmasters': 'webmasters.stackexchange.com',
    'softwarerecs': 'softwarerecs.stackexchange.com', 'opensource': 'opensource.stackexchange.com',
    'diy': 'diy.stackexchange.com', 'travel': 'travel.stackexchange.com',
    'design': 'graphicdesign.stackexchange.com',
}
PUBLIC_KINDS = {'public_question_title', 'public_question_context', 'public_topic_title',
                'public_topic_context', 'public_ask_post', 'package_listing_not_demand'}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def row_sha256(row):
    return hashlib.sha256(canonical(row)).hexdigest()


def _sha(value):
    return hashlib.sha256(value).hexdigest()


def _exact(value, keys, label):
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError('Exact ' + label + ' fields required')


def _hash(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
        raise ValueError('Explicit lowercase SHA256 required')
    return value


def _plain_path(path):
    for component in [path, *path.parents]:
        info = component.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('Saved context reparse/symlink paths are not supported')


def _root(root):
    text = os.fspath(root)
    if text.startswith(('\\\\', '//')):
        raise ValueError('Network roots are forbidden')
    root = Path(root).absolute()
    _plain_path(root)
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError('Existing local research root required')
    return root


def _read_input(m, root, locator):
    _exact(locator, ['input_sha256', 'input_file_sha256'], 'saved input locator')
    identifier = _hash(locator['input_sha256'])
    expected_file_hash = _hash(locator['input_file_sha256'])
    path = root / 'analysis-inputs' / (identifier + '.json')
    _plain_path(path)
    if path.resolve(strict=True) != path or not path.is_relative_to(root):
        raise ValueError('Saved context path is outside its canonical root')
    flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
    with os.fdopen(os.open(path, flags), 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or not before.st_ino:
            raise ValueError('Regular saved input with verifiable file identity required')
        if before.st_size > MAX_INPUT_BYTES:
            raise ValueError('Saved context input exceeds bounded size')
        raw = stream.read(MAX_INPUT_BYTES + 1)
        after = os.fstat(stream.fileno())
        _plain_path(path)
        current = path.lstat()
        if (path.resolve(strict=True) != path or
                (current.st_dev, current.st_ino) != (after.st_dev, after.st_ino) or
                (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) !=
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)):
            raise ValueError('Saved context file changed while reading')
    if len(raw) > MAX_INPUT_BYTES or _sha(raw) != expected_file_hash:
        raise ValueError('Saved input file hash/size mismatch')
    data = json_contract.strict_loads(raw.decode('utf-8-sig'))
    if type(data) is not dict or data.get('schema') != 'reveng-prepared-analysis':
        raise ValueError('Existing sealed preparation required')
    payload = {key: value for key, value in data.items() if key not in ['input_sha256', 'payload_sha256', 'prepared_at']}
    identity = {key: value for key, value in payload.items() if key != 'source_expires'}
    digest = lambda value: m.sha(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode())
    if digest(identity) != identifier or data.get('input_sha256') != identifier or digest(payload) != data.get('payload_sha256'):
        raise ValueError('Saved prepared-input integrity mismatch')
    quote_contract.index_observations(data.get('observations'))
    expiry = data.get('source_expires')
    if type(expiry) not in (int, float) or not math.isfinite(expiry):
        raise ValueError('Finite source expiry from sealed input required')
    return data


def _public_packet(row):
    try:
        url = urlsplit(row['url'])
        if (row.get('kind') not in PUBLIC_KINDS or PUBLIC_HOSTS.get(row.get('source')) != url.hostname or
                url.scheme != 'https' or url.username is not None or url.password is not None or url.port not in (None, 443)):
            raise ValueError('Only explicitly selected supported public-source rows are eligible')
        return model_packet.project([row])[0]
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError('Saved public source row is incomplete') from error


def _origin(locator, row, role, expiry):
    return {'input_sha256': locator['input_sha256'], 'input_file_sha256': locator['input_file_sha256'],
            'original_evidence_id': row['evidence_id'], 'original_row_sha256': row_sha256(row),
            'selection_role': role, 'source_expires': expiry,
            'saved_dates': {key: row.get(key) for key in ['observed_at', 'published_at', 'context_observed_at', 'answer_observed_at']},
            'source_kind': row.get('kind'), 'original_novelty': row.get('novelty')}


def _load_selection(m, root, selection):
    _exact(selection, ['current_input', 'selected_inputs'], 'context selection')
    chosen = selection['selected_inputs']
    if type(chosen) is not list or not 1 <= len(chosen) <= MAX_INPUT_FILES - 1:
        raise ValueError('Select one to three explicit saved inputs')
    root = _root(root)
    current_locator = selection['current_input']
    current = _read_input(m, root, current_locator)
    if not 1 <= len(current['observations']) <= MAX_SELECTED_ROWS:
        raise ValueError('Current input row count exceeds bounded context scope')
    entries = [(row, _origin(current_locator, row, 'current_prepared_input', current['source_expires'])) for row in current['observations']]
    expiry_values = [current['source_expires']]
    expected_count = len(entries)
    ordered = []
    for item in chosen:
        _exact(item, ['input_sha256', 'input_file_sha256', 'rows'], 'selected saved input')
        if type(item['rows']) is not list or not item['rows']:
            raise ValueError('Explicit selected E-IDs/row hashes required')
        expected_count += len(item['rows'])
        if expected_count > MAX_SELECTED_ROWS:
            raise ValueError('Selected row count exceeds bound; no silent truncation')
        for row in item['rows']:
            _exact(row, ['evidence_id', 'row_sha256'], 'selected row')
            if not isinstance(row['evidence_id'], str) or not row['evidence_id']:
                raise ValueError('Explicit selected E-ID required')
            _hash(row['row_sha256'])
        ordered.append(item)
    for item in sorted(ordered, key=canonical):
        locator = {key: item[key] for key in ['input_sha256', 'input_file_sha256']}
        data = _read_input(m, root, locator)
        expiry_values.append(data['source_expires'])
        rows = quote_contract.index_observations(data['observations'])
        for reference in sorted(item['rows'], key=canonical):
            row = rows.get(reference['evidence_id'])
            if row is None or row_sha256(row) != reference['row_sha256']:
                raise ValueError('Selected E-ID is missing or its exact saved row changed')
            entries.append((row, _origin(locator, row, 'saved_context_not_new_capture', data['source_expires'])))
    return root, current, entries, min(expiry_values)


def proposal(m, root, selection):
    """Read-only comparison/request proposal; never a ready or admitted input."""
    _, current, entries, expiry = _load_selection(m, root, selection)
    rows = []
    bindings = []
    by_content = {}
    seen_origins = set()
    used_ids = {row['evidence_id'] for row in current['observations']}
    next_alias = 1
    for original, origin in entries:
        _public_packet(original)  # Explicit public-source scope, not semantic approval.
        origin_key = (origin['input_sha256'], origin['original_evidence_id'], origin['original_row_sha256'])
        if origin_key in seen_origins:
            continue
        seen_origins.add(origin_key)
        comparable = {key: value for key, value in original.items() if key not in ['evidence_id', 'same_author_evidence_ids', 'shared_context_evidence_ids']}
        fingerprint = row_sha256(comparable)
        if fingerprint in by_content:
            bindings[by_content[fingerprint]]['origins'].append(origin)
            continue
        row = copy.deepcopy(original)
        if origin['selection_role'] == 'saved_context_not_new_capture':
            while 'H' + str(next_alias) in used_ids:
                next_alias += 1
            row['evidence_id'] = 'H' + str(next_alias)
            used_ids.add(row['evidence_id'])
            next_alias += 1
        by_content[fingerprint] = len(rows)
        rows.append(row)
        bindings.append({'packet_evidence_id': row['evidence_id'], 'origins': [origin]})
    source_context.annotate_relations(rows)
    quote_contract.index_observations(rows)
    packets = model_packet.project(rows)
    for packet, row, binding in zip(packets, rows, bindings):
        roles = sorted({origin['selection_role'] for origin in binding['origins']})
        packet['analysis_context'] = {'selection_roles': roles,
            'meaning': 'Explicit comparison selection only; saved context is not a new capture, task fit or independent buyer.',
            'same_exact_url_packet_ids': [other['evidence_id'] for other in rows if other is not row and other['url'] == row['url']],
            'independence': 'NOT_ESTABLISHED', 'source_dates_renewed': False}
    result = {'schema': POLICY, 'status': 'TOKEN_ADMISSION_REQUIRED',
              'selection_manifest': bindings, 'source_packets': packets, 'effective_source_expires': expiry,
              'source_dates_renewed': False, 'collection_novelty_changed': False,
              'independence': 'NOT_ESTABLISHED', 'execution_authorized': False,
              'queue_written': False, 'model_calls': 0, 'network_calls': 0,
              'token_admission': {'status': 'NOT_PERFORMED', 'token_count': None, 'reason': 'No qualified exact tokenizer/admission implementation in canonical source; no estimate or fallback.'}}
    if expiry <= time.time():
        result['status'] = 'EXPIRED_SELECTION_READ_ONLY'
    else:
        # Do not drop an existing API attachment or replace an unfamiliar request.
        if current['request'] != m.build_model_request(current['observations']):
            raise ValueError('Non-default current request cannot be silently rewritten')
        request = m.build_model_request(rows)
        marker = 'SOURCE OBSERVATIONS:\n'
        prefix, _ = request['messages'][1]['content'].split(marker, 1)
        request['messages'][1]['content'] = (prefix +
            'EXPLICIT SAVED CONTEXT: packet aliases map to immutable input/E-ID/row hashes in the selection manifest. Historical context remains historical even when its saved TTL has not expired. Selection is not semantic relatedness, an independent author, payment or new demand. Dates and source roles are not renewed.\n' +
            marker + json.dumps(packets, ensure_ascii=False, separators=(',', ':')))
        result['request_proposal'] = request
    # Construction time never renews TTL. Recheck before exposing a request.
    if expiry <= time.time():
        result['status'] = 'EXPIRED_SELECTION_READ_ONLY'
        result.pop('request_proposal', None)
    if len(canonical(result)) > MAX_PACKET_BYTES:
        raise ValueError('Combined context proposal exceeds byte cap; no clipping or partial fallback')
    return result


class TokenAdmissionRequired(ValueError):
    def __init__(self, preview):
        super().__init__('TOKEN_ADMISSION_REQUIRED: exact combined request is a proposal only; no prepared-input or queue write')
        self.proposal = preview


def preparation_boundary(m, root, observations, prices, errors, expiry, request, selection):
    """Opt-in stage of the existing prepare API. Deliberately stops before writes."""
    root, current, _, _ = _load_selection(m, root, selection)
    if (observations != current['observations'] or prices != current['public_price_records'] or
            errors != current['source_errors'] or request != current['request'] or expiry != current['source_expires']):
        raise ValueError('Current preparation arguments differ from the exact sealed input; no caller expiry override')
    preview = proposal(m, root, selection)
    if preview['status'] != 'TOKEN_ADMISSION_REQUIRED':
        raise ValueError('Expired saved context is read-only; no prepared request or TTL renewal')
    raise TokenAdmissionRequired(preview)
