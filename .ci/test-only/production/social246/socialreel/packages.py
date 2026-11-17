"""Verify actual package bytes before reuse, recovery or delivery."""
import wave
from pathlib import Path
from .common import PACKAGE_SCHEMA, CONTRACT, read_json, sha256_file, sha256_bytes


def verify_package(directory):
    root = Path(directory).resolve()
    errors = []
    try:
        manifest = read_json(root / 'package_manifest.json')
        media = read_json(root / 'media_manifest.json')
        result = read_json(root / 'result.json')
        errors.extend(acceptance_errors(result))
        if manifest.get('schema') != PACKAGE_SCHEMA or manifest.get('contract') != CONTRACT:
            errors.append('Unknown package schema or contract')
        entries = manifest.get('files', [])
        if not entries or not media.get('files'):
            errors.append('Empty package manifest')
        checked = set()
        for entry in entries + media.get('files', []):
            relative = str(entry['path']).replace('\\', '/')
            path = (root / relative).resolve()
            if Path(relative).is_absolute() or not path.is_relative_to(root):
                errors.append('Invalid manifest path: ' + relative)
                continue
            if (relative, entry['sha256']) in checked:
                continue
            checked.add((relative, entry['sha256']))
            if not path.is_file() or path.stat().st_size != entry['bytes'] or sha256_file(path) != entry['sha256']:
                errors.append('Missing or modified file: ' + relative)
        from .package_contract import semantic_errors
        errors.extend(semantic_errors(root, entries + media.get('files', [])))
        package_id = sha256_bytes('\n'.join(f"{e['path']} {e['sha256']}" for e in entries).encode())
        if package_id != manifest.get('package_id') or package_id != result.get('package_id'):
            errors.append('Package identity mismatch')
        video = root / 'final/reel.mp4'
        if not video.is_file() or sha256_file(video) != result.get('video', {}).get('sha256'):
            errors.append('Final video hash mismatch')
        for name, filename in [('claims_sha256', 'claims.json'), ('script_sha256', 'script.json'),
                               ('timing_sha256', 'timing.json'), ('narration_sha256', 'audio/narration.wav')]:
            path = root / filename
            if not path.is_file() or sha256_file(path) != manifest.get('lineage', {}).get(name):
                errors.append('Lineage mismatch: ' + filename)
        ledger = read_json(root / 'claims.json')
        for claim in ledger.get('claims', []):
            source = claim.get('source', {})
            sources = source.get('field_sources') or [source]
            for source_item in sources:
                name = source_item.get('snapshot_file', '')
                if name.startswith('fixture:'):
                    continue  # fixtures are never accepted as live packages
                path = (root / name).resolve()
                if not path.is_relative_to(root) or not path.is_file() or sha256_file(path) != source_item.get('snapshot_sha256'):
                    errors.append('Claim source missing or modified: ' + claim.get('key', '?'))
        if manifest.get('lineage', {}).get('video_sha256') != result.get('video', {}).get('sha256'):
            errors.append('Video lineage mismatch')
    except (OSError, ValueError, KeyError, TypeError, AttributeError, IndexError, EOFError, OverflowError, wave.Error) as e:
        errors.append('Unreadable package: ' + type(e).__name__ + ': ' + str(e)[:300])
    return {'pass': not errors, 'errors': errors, 'directory': str(root)}


def acceptance_errors(result):
    errors = []
    if not isinstance(result.get('accepted'), bool):
        return ['Acceptance flag must be a boolean']
    if result.get('accepted') is True:
        verification = result.get('verification', {})
        checks = verification.get('checks', [])
        if result.get('mode') != 'live': errors.append('Fixture result cannot be accepted as live')
        if verification.get('pass') is not True or not checks or any(c.get('pass') is not True for c in checks):
            errors.append('Accepted result contains missing/failed/non-boolean checks')
        required = {'full_decode_no_errors','audio_not_silent','narration_asr_matches_script','duration_matches_timeline'}
        if not required.issubset({c.get('check') for c in checks}): errors.append('Required actual-media checks missing')
        if result.get('voice', {}).get('test_only') is not False: errors.append('Test voice cannot be accepted')
    return errors


def source_freshness(directory, now=None, max_age_hours=24):
    import datetime as dt
    from .common import utc_now, parse_date
    now = now or utc_now()
    reasons=[]
    try:
        sources=read_json(Path(directory)/'sources.json')
        stored=read_json(Path(directory)/'topic.json')['selected']
        if stored.get('public_money_source'):
            from .editorial import production_gate
            gate=production_gate(stored,sources.get('selected_snapshot') or {},now,max_age_hours=max_age_hours)
            reasons.extend(gate['errors'])
            if sources.get('mode')!='live':reasons.append('Not an accepted live information-page observation')
            return {'fresh':not reasons,'reasons':reasons,'max_age_hours':max_age_hours,'scope':'Public information; no invented grant closing date'}
        fetched=dt.datetime.fromisoformat(sources['selected_snapshot']['fetched_at'])
        if fetched.tzinfo is None: reasons.append('Source timestamp lacks timezone')
        else:
            age=(now-fetched).total_seconds()
            if age < -300 or age > max_age_hours*3600: reasons.append('Source age outside live reuse window')
        topic=read_json(Path(directory)/'topic.json')
        record=topic['selected']
        if record.get('status') is not None and record['status'].lower() != 'posted':reasons.append('Stored listing is not posted')
        if (record.get('doc_type') or '').lower()=='forecast':reasons.append('Stored listing is a forecast')
        for label,step in (record.get('submission_steps') or {}).items():
            day=parse_date(step.get('date'))
            if day is None or day<=now.date():reasons.append('Submission stage expired or needs same-day clock review: '+label)
        closing=parse_date(record.get('close_date'))
        if not closing or closing <= now.date(): reasons.append('Listing date expired or unknown')
        if sources.get('mode') != 'live': reasons.append('Not a live source')
    except (OSError,ValueError,KeyError,TypeError,AttributeError): reasons.append('Source freshness cannot be established')
    return {'fresh':not reasons,'reasons':reasons,'max_age_hours':max_age_hours}
