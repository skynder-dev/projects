"""Pin/copy/supervise native PowerShell; never implements Forge business behavior.

The bundled runner intentionally supports POSIX private roots only. Windows may
run the native .ps1 under an independently reviewed Windows ACL/job supervisor.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import uuid
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
INPUTS = ('Test-ForgePerformanceMetrics.ps1', 'PerformanceFixtures.json',
          'dependencies.json', 'supervise_performance.py', 'process_supervisor.py',
          'test_supervisor_contract.py', 'README.md')
SENTINEL = b'SYNTHETIC PRESERVATION SENTINEL - no existing fixture or original may be modified.'

def utc():
    return datetime.now(timezone.utc).isoformat()

def checked(path: Path, directory=False):
    path = Path(os.path.abspath(path))
    for part in (path, *path.parents):
        info = part.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise RuntimeError(f'Symlink/reparse input rejected: {part}')
    info = path.stat()
    if not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)):
        raise RuntimeError(f'Unexpected path kind: {path}')
    return path

def sha(path):
    return hashlib.sha256(checked(Path(path)).read_bytes()).hexdigest()

def dump_fresh(path, obj):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(obj, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())

def cases():
    names = ['mixed_currency_not_summed', 'ranking_uses_units_not_raw_money',
             'ranking_ties_are_stable_not_money', 'unverified_999_and_99_excluded_unknown',
             'unverified_receipt_excluded_and_unknown_product',
             'utc_day_29_in_30_out_89_in_90_out', 'utc_day_6_in_7_out',
             'future_and_undated_rows_excluded', 'refund_and_zero_are_observed_transactions',
             'aggregate_and_each_product_agree_all_windows']
    names += [f'{field}_{variant}_is_unknown'
              for field in ('units', 'royalty')
              for variant in ('missing', 'null', 'blank', 'NaN', 'positive_infinity',
                              'negative_infinity', 'too_large', 'unreadable', 'array',
                              'object', 'boolean', 'missing_flag', 'false_flag', 'string_true_flag')]
    names += ['singleton_currency_array_is_unknown', 'singleton_date_array_is_undated',
              'legacy_v1_with_true_numeric_flags_remains_valid',
              'legacy_source_identity_without_numeric_flags_stays_unknown_unchanged',
              'es_ES_culture_does_not_change_numeric_totals']
    names += [f'render_{locale}_currency_and_fractional_labels' for locale in ('en', 'ru', 'es')]
    if len(names) != 46:
        raise RuntimeError('Exactly 46 native case names are required')
    return names

def make_pins(base: Path, candidate: Path, output: Path):
    base, candidate = checked(base, True), checked(candidate, True)
    deps = json.loads((HERE/'dependencies.json').read_text())
    sources, provenance = {}, {}
    for relative in deps['functions']:
        preferred = candidate/relative
        original = checked(preferred if preferred.exists() else base/relative)
        sources[relative] = sha(original)
        provenance[relative] = str(original)
    tests = {name: sha(HERE/name) for name in INPUTS}
    pins = dict(schema='forge.performance.pins.v1', created_at_utc=utc(),
                source_policy='Two changed candidate modules, unchanged bootstrap/localization from frozen v2 base; no original modified.',
                sources=sources, provenance=provenance, tests=tests,
                expected_cases=cases(), dependencies=deps)
    # Ensure capture did not straddle an edit.
    for relative, original in provenance.items():
        if sha(original) != sources[relative]:
            raise RuntimeError(f'Source changed while pinning: {relative}')
    for name, expected in tests.items():
        if sha(HERE/name) != expected:
            raise RuntimeError(f'Test changed while pinning: {name}')
    dump_fresh(output, pins)
    return pins

def read_receipt(path: Path, root: Path):
    checked(root, True)
    path = checked(path)
    if path.parent != root:
        raise RuntimeError('Receipt outside owned invocation root')
    if path.stat().st_size == 0 or path.stat().st_size > 4*1024*1024:
        raise RuntimeError('Empty or oversized receipt')
    return json.loads(path.read_text(encoding='utf-8-sig'))

def validate_receipt(receipt, pins, run_id, run_root, copy_root, pins_sha):
    def require(ok, reason):
        if not ok:
            raise RuntimeError(reason)
    require(receipt.get('schema') == 'forge.performance.native_receipt.v1', 'Wrong native receipt schema')
    require(receipt.get('status') == 'PASS' and receipt.get('error') is None, 'Native suite did not pass')
    require(receipt.get('run_id') == run_id, 'Wrong invocation nonce')
    require(receipt.get('run_root') == str(run_root) and receipt.get('package_copy_root') == str(copy_root), 'Wrong owned run/copy root')
    require(receipt.get('pins_sha256') == pins_sha, 'Wrong pin manifest hash')
    for receipt_key, name in [('test_sha256', 'Test-ForgePerformanceMetrics.ps1'),
                              ('fixtures_sha256', 'PerformanceFixtures.json'),
                              ('dependencies_sha256', 'dependencies.json')]:
        require(receipt.get(receipt_key) == pins['tests'][name], f'Wrong input hash: {name}')
    require(receipt.get('source_hashes_before') == pins['sources'] == receipt.get('source_hashes_after'), 'Native source before/after hashes mismatch')
    actual = receipt.get('cases', [])
    require(receipt.get('case_count') == len(pins['expected_cases']) == len(actual), 'Wrong native case count')
    require(receipt.get('failed_case_count') == 0, 'Nonzero failed native case count')
    require([row.get('name') for row in actual] == pins['expected_cases'], 'Missing, reordered or duplicate native case names')
    require(all(row.get('status') == 'PASS' and row.get('error') is None for row in actual), 'Not every native case passed')
    expected_functions = [(source, name) for source, names in pins['dependencies']['functions'].items() for name in names]
    loaded = [(row.get('source'), row.get('name')) for row in receipt.get('loaded_actual_functions', [])]
    require(loaded == expected_functions, 'Wrong actual function extraction list')
    require(receipt.get('fixed_now_utc') == '2026-10-24T12:00:00.0000000Z', 'Fixed clock not established')
    runtime_version = receipt.get('powershell_version', '')
    require(isinstance(runtime_version, str) and re.fullmatch(r'\d+\.\d+(?:\.\d+){0,2}', runtime_version) is not None, 'Missing/unsupported stable native runtime version')
    require(tuple(int(part) for part in runtime_version.split('.')[:2]) >= (7, 5), 'PowerShell 7.5+ required')
    require(receipt.get('ps_edition') == 'Core', 'PowerShell Core edition required')
    require(receipt.get('date_kind_string_available') is True and receipt.get('minimum_powershell_core') == '7.5', 'Explicit DateKind String support required')
    require(receipt.get('synthetic_fixture_sha256') == hashlib.sha256(SENTINEL).hexdigest(), 'Wrong preservation sentinel')
    for field in ('real_data_loaded', 'app_launched'):
        require(receipt.get(field) is False, f'Unexpected side effect: {field}')
    for field in ('model_calls', 'network_calls', 'remote_writes'):
        require(receipt.get(field) == 0, f'Unexpected side effect: {field}')

def run(pins_path: Path, output_parent: Path, executable: str, timeout: int):
    if os.name != 'posix':
        raise RuntimeError('This runner provisions POSIX owner-private roots only; Windows needs an approved ACL supervisor.')
    if not 5 <= timeout <= 300:
        raise RuntimeError('Timeout must be within 5..300 seconds')
    pins_path = checked(pins_path)
    pins_sha = sha(pins_path)
    pins = json.loads(pins_path.read_text())
    if pins.get('schema') != 'forge.performance.pins.v1':
        raise RuntimeError('Wrong pins schema')
    output_parent = checked(output_parent, True)
    owned = Path(tempfile.mkdtemp(prefix='forge-performance-', dir=output_parent))
    os.chmod(owned, 0o700)
    if owned.stat().st_uid != os.getuid() or stat.S_IMODE(owned.stat().st_mode) != 0o700:
        raise RuntimeError('Supervisor private-root ownership/mode verification failed')
    run_id = uuid.uuid4().hex
    invocation = dict(schema='forge.performance.supervisor_invocation.v1', run_id=run_id,
                      started_at_utc=utc(), status='FAIL', native_executed=False,
                      owned_root=str(owned), pins_sha256=pins_sha, timeout_seconds=timeout,
                      source_hashes_before={}, source_hashes_after={},
                      copied_hashes_before={}, copied_hashes_after={}, input_hashes_after={},
                      original_files_modified_by_supervisor=False)
    copy_root, suite_root, run_root = owned/'source-copy', owned/'suite-copy', owned/'native-run'
    for directory in (copy_root, suite_root, run_root, owned/'home', owned/'temp'):
        directory.mkdir(mode=0o700)
    error = None
    try:
        if pins['expected_cases'] != cases():
            raise RuntimeError('Pin case contract mismatch')
        if set(pins['tests']) != set(INPUTS):
            raise RuntimeError('Pin test/input file set mismatch')
        if pins['dependencies'] != json.loads((HERE/'dependencies.json').read_text()):
            raise RuntimeError('Pin dependency contract mismatch')
        if set(pins['sources']) != set(pins['dependencies']['functions']) or set(pins['provenance']) != set(pins['sources']):
            raise RuntimeError('Pin source/provenance set mismatch')
        for relative, expected in pins['sources'].items():
            if Path(relative).is_absolute() or '..' in Path(relative).parts:
                raise RuntimeError('Invalid relative source path')
            source = checked(Path(pins['provenance'][relative]))
            invocation['source_hashes_before'][relative] = sha(source)
            if sha(source) != expected:
                raise RuntimeError(f'Pinned original source mismatch: {source}')
            target = copy_root/relative
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with target.open('xb') as stream:
                stream.write(source.read_bytes())
            os.chmod(target, 0o400)
            invocation['copied_hashes_before'][relative] = sha(target)
            if sha(target) != expected:
                raise RuntimeError(f'Copied source mismatch: {relative}')
        for name, expected in pins['tests'].items():
            if name not in INPUTS or sha(HERE/name) != expected:
                raise RuntimeError(f'Pinned suite input mismatch: {name}')
            target = suite_root/name
            with target.open('xb') as stream:
                stream.write((HERE/name).read_bytes())
            os.chmod(target, 0o400)
            if sha(target) != expected:
                raise RuntimeError(f'Copied suite input mismatch: {name}')
        copied_pins = suite_root/'PerformancePins.json'
        with copied_pins.open('xb') as stream:
            stream.write(pins_path.read_bytes())
        os.chmod(copied_pins, 0o400)
        if sha(copied_pins) != pins_sha:
            raise RuntimeError('Copied pin manifest mismatch')
        exe = shutil.which(executable)
        if not exe:
            invocation['status'] = 'BLOCKED_NATIVE_RUNTIME_UNAVAILABLE'
            raise FileNotFoundError(f'Native PowerShell executable not found: {executable}. No install attempted.')
        from process_supervisor import run_owned
        command = [str(Path(exe).resolve()), '-NoLogo', '-NoProfile', '-NonInteractive',
                   '-File', str(suite_root/'Test-ForgePerformanceMetrics.ps1'),
                   '-PackageRoot', str(copy_root), '-PinsPath', str(copied_pins),
                   '-RunId', run_id, '-RunRoot', str(run_root)]
        invocation['command'] = command
        environment = {k: v for k, v in os.environ.items() if k in ('PATH', 'LANG', 'LC_ALL', 'SystemRoot', 'WINDIR')}
        environment.update(HOME=str(owned/'home'), TMPDIR=str(owned/'temp'), TEMP=str(owned/'temp'),
                           TMP=str(owned/'temp'), POWERSHELL_TELEMETRY_OPTOUT='1',
                           POWERSHELL_UPDATECHECK='Off', PYTHONDONTWRITEBYTECODE='1')
        invocation['native_executed'] = True
        run_owned(command, cwd=copy_root, env=environment, timeout=timeout, log=owned/'native.log')
        invocation['native_exit_code'] = 0
        native = read_receipt(run_root/'receipt.json', run_root)
        validate_receipt(native, pins, run_id, run_root, copy_root, pins_sha)
        invocation['native_receipt_sha256'] = sha(run_root/'receipt.json')
        if sha(run_root/'existing-synthetic-fixture.txt') != hashlib.sha256(SENTINEL).hexdigest():
            raise RuntimeError('Synthetic preservation fixture changed')
        if set(p.name for p in run_root.iterdir()) != {'.forge-performance.claim', 'receipt.json', 'existing-synthetic-fixture.txt'}:
            raise RuntimeError('Unexpected native fixture write')
        invocation['status'] = 'PASS_FOCUSED_NATIVE_ONLY'
    except Exception as exc:
        error = f'{type(exc).__name__}: {exc}'
    finally:
        # Always rehash originals AND copies after completion, timeout or failure.
        try:
            for relative, expected in pins['sources'].items():
                invocation['source_hashes_after'][relative] = sha(Path(pins['provenance'][relative]))
                invocation['copied_hashes_after'][relative] = sha(copy_root/relative)
            for name, expected in pins['tests'].items():
                invocation['input_hashes_after'][name] = dict(original=sha(HERE/name), copy=sha(suite_root/name))
            unchanged = all(invocation[key] == pins['sources'] for key in ('source_hashes_before', 'source_hashes_after', 'copied_hashes_before', 'copied_hashes_after'))
            unchanged = unchanged and all(row == {'original': pins['tests'][name], 'copy': pins['tests'][name]} for name, row in invocation['input_hashes_after'].items())
            unchanged = unchanged and sha(pins_path) == pins_sha and sha(suite_root/'PerformancePins.json') == pins_sha
            invocation['all_sources_copies_inputs_unchanged'] = unchanged
            if not unchanged:
                invocation['status'] = 'FAIL'
                error = (error+'; ' if error else '')+'Final source/copy/input rehash mismatch'
        except Exception as exc:
            invocation['status'] = 'FAIL'
            error = (error+'; ' if error else '')+f'Final integrity validation failed: {exc}'
        invocation['error'] = error
        invocation['finished_at_utc'] = utc()
        if error and invocation['status'] == 'PASS_FOCUSED_NATIVE_ONLY':
            invocation['status'] = 'FAIL'
        dump_fresh(owned/'invocation.json', invocation)
    print(json.dumps({'status': invocation['status'], 'invocation_receipt': str(owned/'invocation.json'), 'error': error}))
    return 0 if invocation['status'] == 'PASS_FOCUSED_NATIVE_ONLY' else 1

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    pin = commands.add_parser('pin')
    pin.add_argument('--base', type=Path, required=True, help='Frozen v2 app package root')
    pin.add_argument('--candidate', type=Path, required=True, help='New candidate app package root')
    pin.add_argument('--output', type=Path, required=True, help='New manifest only; never overwritten')
    launch = commands.add_parser('run')
    launch.add_argument('--pins', type=Path, required=True)
    launch.add_argument('--output-parent', type=Path, required=True)
    launch.add_argument('--pwsh', default='pwsh')
    launch.add_argument('--timeout', type=int, default=90)
    args = parser.parse_args()
    if args.action == 'pin':
        make_pins(args.base, args.candidate, args.output)
        print(json.dumps({'status': 'PINNED_NOT_EXECUTED', 'pins': str(args.output)}))
        return 0
    return run(args.pins, args.output_parent, args.pwsh, args.timeout)

if __name__ == '__main__':
    raise SystemExit(main())
