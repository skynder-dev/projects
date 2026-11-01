"""Storage primitives only. Explicit owned root, no enqueue/worker/model methods.

This does not establish research provenance or register imported source jobs.
"""
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from .common import PipelineError

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
