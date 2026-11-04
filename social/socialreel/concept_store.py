"""Storage primitives only. Explicit owned root, no enqueue/worker/model methods.

Imported trial results are editorial archives, not runnable research jobs.
"""
import json
import sqlite3
import time
from pathlib import Path
from contextlib import contextmanager
from .common import PipelineError, read_json, sha256_bytes, stable_json
from .concept_locks import motion_lock
from .concept_storage import immutable_bytes, write_json

RESULT_STATE = 'concept_trial_import'
RESULT_SCHEMA = 'SOCIAL_CONCEPT_SAVED_REVISION_V1'


def _hash(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)

class ConceptStore:
    def __init__(self, root):
        self.root = Path(root).resolve()
        if any((p/'MIGRATION_REVIEW_ONLY.json').is_file() for p in (self.root,*self.root.parents)):raise PipelineError('Review-only discovery migration copy cannot run jobs')
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = self.root / 'queue.sqlite3'
        with self.connect() as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS jobs (
                  id TEXT PRIMARY KEY, request_key TEXT UNIQUE, request_json TEXT NOT NULL,
                  state TEXT NOT NULL, created REAL NOT NULL, updated REAL NOT NULL,
                  owner_pid INTEGER, owner_token TEXT, return_code INTEGER,
                  run_dir TEXT, detail TEXT);
                CREATE INDEX IF NOT EXISTS pending ON jobs(state, created);
            ''')
    @contextmanager
    def connect(self):
        conn = None
        try:
            conn = sqlite3.connect(self.db, timeout=10)
            conn.row_factory = sqlite3.Row
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('PRAGMA synchronous=FULL')
            with conn:
                yield conn
        except sqlite3.DatabaseError as error:
            raise PipelineError('Queue database unavailable or corrupt; original files preserved: ' + type(error).__name__) from error
        finally:
            if conn is not None:
                conn.close()
    def folder(self, job_id):
        if not isinstance(job_id,str) or len(job_id) != 32 or any(c not in '0123456789abcdef' for c in job_id):
            raise PipelineError('Invalid Social job identifier')
        return self.root / job_id
    def local_directory(self,value):
        path=Path(value)
        return (path if path.is_absolute() else self.root/path).resolve()
    def stored_directory(self,value):
        path=Path(value).resolve()
        return path.relative_to(self.root).as_posix() if path.is_relative_to(self.root) else str(path)

    def result_jobs(self):
        with self.connect() as conn:
            return [dict(row) for row in conn.execute('SELECT * FROM jobs WHERE state=? ORDER BY created,id', (RESULT_STATE,))]

    def _result_metadata(self, job_id):
        self.folder(job_id)
        with self.connect() as conn:
            row = conn.execute('SELECT * FROM jobs WHERE id=? AND state=?', (job_id, RESULT_STATE)).fetchone()
        if row is None:
            raise PipelineError('Saved concept job not found')
        metadata = json.loads(row['request_json'])
        if (not isinstance(metadata, dict) or not _hash(metadata.get('trial_sha256')) or
                metadata['trial_sha256'][:32] != job_id or row['request_key'] != 'trial:' + metadata['trial_sha256']):
            raise PipelineError('Imported trial metadata integrity mismatch')
        return metadata

    def _result_history(self, job_id):
        home = self.folder(job_id) / 'concept_results'
        header = read_json(home / 'head.json') if (home / 'head.json').exists() else {'revision': 'absent'}
        if not isinstance(header, dict):
            raise PipelineError('Saved concept head invalid')
        head = header.get('revision')
        cursor, history, seen = head, [], set()
        while cursor != 'absent':
            if not _hash(cursor) or cursor in seen or len(history) >= 1000:
                raise PipelineError('Saved concept revision chain invalid or exceeds bound')
            path = home / 'revisions' / (cursor + '.json')
            if path.is_symlink() or not path.is_file():
                raise PipelineError('Saved concept revision missing; original files preserved')
            raw = path.read_bytes()
            value = json.loads(raw)
            if (sha256_bytes(raw) != cursor or raw != stable_json(value).encode('utf-8') or
                    value.get('job_id') != job_id or value.get('schema') != RESULT_SCHEMA):
                raise PipelineError('Saved concept revision integrity mismatch')
            seen.add(cursor)
            history.append({'revision': cursor, **value})
            cursor = value.get('parent_revision')
        # Only the head's committed chain is authoritative. Failed writes remain
        # visible as orphans; reading never promotes, deletes or executes them.
        pending = [p.name for p in sorted((home / 'revisions').glob('*.json')) if p.stem not in seen]
        return {'revision': head, 'history': history, 'uncommitted_revisions': pending}

    def result_snapshot(self, job_id):
        self.folder(job_id)
        with motion_lock(self.root, 'concept_results_' + job_id, wait=5):
            metadata = self._result_metadata(job_id)
            snapshot = self._result_history(job_id)
            path = self.folder(job_id) / 'concept_results' / 'trial.json'
            raw = path.read_bytes() if path.exists() else None
            if raw is not None and sha256_bytes(raw) != metadata['trial_sha256']:
                raise PipelineError('Saved raw trial SHA-256 mismatch')
            return {**snapshot, 'import': metadata, 'raw_trial': raw}

    def _append_result(self, job_id, expected_revision, value):
        current = self._result_history(job_id)['revision']
        if current != expected_revision:
            raise PipelineError('Concept revision conflict; read current revision before saving')
        if value.get('schema') != RESULT_SCHEMA or value.get('job_id') != job_id or value.get('parent_revision') != current:
            raise PipelineError('Saved concept revision envelope mismatch')
        home = self.folder(job_id) / 'concept_results'
        data = stable_json(value).encode('utf-8')
        revision = sha256_bytes(data)
        immutable_bytes(home / 'revisions' / (revision + '.json'), data)
        if self._result_history(job_id)['revision'] != expected_revision:
            raise PipelineError('Concept revision conflict before promotion; original revisions preserved')
        write_json(home / 'head.json', {'revision': revision})
        return revision

    def append_result(self, job_id, expected_revision, value):
        self.folder(job_id)
        with motion_lock(self.root, 'concept_results_' + job_id, wait=5):
            self._result_metadata(job_id)
            return self._append_result(job_id, expected_revision, value)

    def export_result(self, job_id, expected_revision, path, data):
        """Create an artifact only while its exact reviewed revision is current."""
        self.folder(job_id)
        with motion_lock(self.root, 'concept_results_' + job_id, wait=5):
            self._result_metadata(job_id)
            if self._result_history(job_id)['revision'] != expected_revision:
                raise PipelineError('Concept revision conflict before export; read current revision')
            return immutable_bytes(path, data)

    def import_result(self, raw, value):
        digest = sha256_bytes(raw)
        job_id = digest[:32]
        self.folder(job_id)
        with motion_lock(self.root, 'concept_results_' + job_id, wait=5):
            metadata = {'kind': RESULT_STATE, 'trial_sha256': digest, 'source': value['source']}
            with self.connect() as conn:
                found = conn.execute('SELECT request_key,state FROM jobs WHERE id=?', (job_id,)).fetchone()
                if found and (found['request_key'] != 'trial:' + digest or found['state'] != RESULT_STATE):
                    raise PipelineError('Imported trial job identity collision; existing job preserved')
                if not found:
                    conn.execute('INSERT INTO jobs(id,request_key,request_json,state,created,updated) VALUES(?,?,?,?,?,?)',
                                 (job_id, 'trial:' + digest, stable_json(metadata), RESULT_STATE, time.time(), time.time()))
            immutable_bytes(self.folder(job_id) / 'concept_results' / 'trial.json', raw)
            current = self._result_history(job_id)['revision']
            if current != 'absent':
                return job_id, current, False
            if value.get('trial_sha256') != digest:
                raise PipelineError('Imported trial identity mismatch')
            revision = self._append_result(job_id, 'absent', value)
            return job_id, revision, True
