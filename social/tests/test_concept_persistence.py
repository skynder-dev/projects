"""Actual owner persistence failure recovery; synthetic owned temporary storage only."""
import concurrent.futures
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from socialreel import concept_owner_context as owner
from socialreel.common import PipelineError, read_json, stable_json
from socialreel.concept_store import ConceptStore
from socialreel.concept_storage import write_json


class OwnerPersistence(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=ConceptStore(Path(self.tmp.name)/'owned');self.job='a'*32
        with self.store.connect() as conn:
            conn.execute('INSERT INTO jobs(id,request_json,state,created,updated) VALUES(?,?,?,?,?)',(self.job,'{}','synthetic_test_only',0,0))
        self.first=owner.save(self.store,self.job,'absent',{'audience':'Original'})
        self.home=self.store.folder(self.job)/'concept_owner_context';self.head=self.home/'head.json'
        self.expected=self.first['revision'];self.context={'audience':'Edited'}

    def fail_head(self):
        replace=os.replace
        def fail(source,target):
            if Path(target)==self.head:raise OSError('Injected head replacement failure')
            return replace(source,target)
        before=self.head.read_bytes()
        with patch('socialreel.concept_storage.os.replace',side_effect=fail):
            with self.assertRaisesRegex(OSError,'Injected'):owner.save(self.store,self.job,self.expected,self.context)
        self.assertEqual(self.head.read_bytes(),before)
        self.assertEqual(owner.read(self.store,self.job),self.first)
        paths=list((self.home/'revisions').glob('*.json'));self.assertEqual(len(paths),2)
        return next(p for p in paths if p.stem!=self.expected)

    def test_failed_head_keeps_prior_and_exact_retry_recovers(self):
        orphan=self.fail_head();original=orphan.read_bytes()
        saved=owner.save(self.store,self.job,self.expected,self.context)
        self.assertEqual(saved['revision'],orphan.stem);self.assertEqual(orphan.read_bytes(),original)
        self.assertEqual(owner.read(self.store,self.job),saved)
        self.assertEqual(len(list((self.home/'revisions').glob('*.json'))),2)

    def test_failed_revision_fsync_must_succeed_before_reused_promotion(self):
        before=self.head.read_bytes()
        with patch('socialreel.concept_owner_context.os.fsync',side_effect=OSError('Injected sync failure')):
            with self.assertRaisesRegex(OSError,'sync failure'):
                owner.save(self.store,self.job,self.expected,self.context)
        self.assertEqual(self.head.read_bytes(),before)
        with patch('socialreel.concept_owner_context.os.fsync',side_effect=OSError('Retry sync failure')):
            with self.assertRaisesRegex(OSError,'Retry sync failure'):
                owner.save(self.store,self.job,self.expected,self.context)
        self.assertEqual(self.head.read_bytes(),before)
        saved=owner.save(self.store,self.job,self.expected,self.context)
        self.assertEqual(owner.read(self.store,self.job),saved)

    def test_divergent_orphan_is_not_overwritten_or_promoted(self):
        orphan=self.fail_head();orphan.write_bytes(b'{"different":true}\n');before=self.head.read_bytes()
        with self.assertRaisesRegex(PipelineError,'orphan revision differs'):
            owner.save(self.store,self.job,self.expected,self.context)
        self.assertEqual(orphan.read_bytes(),b'{"different":true}\n');self.assertEqual(self.head.read_bytes(),before)

    def test_semantically_equal_nonidentical_orphan_is_rejected(self):
        orphan=self.fail_head();value=read_json(orphan);orphan.write_text(__import__('json').dumps(value));before=self.head.read_bytes()
        with self.assertRaisesRegex(PipelineError,'orphan revision differs'):
            owner.save(self.store,self.job,self.expected,self.context)
        self.assertEqual(self.head.read_bytes(),before)

    def test_concurrent_advancement_blocks_orphan_retry(self):
        orphan=self.fail_head();original=orphan.read_bytes()
        advanced=owner.save(self.store,self.job,self.expected,{'audience':'Other valid edit'})
        before=self.head.read_bytes()
        with self.assertRaisesRegex(PipelineError,'revision conflict'):
            owner.save(self.store,self.job,self.expected,self.context)
        self.assertEqual(owner.read(self.store,self.job),advanced)
        self.assertEqual(self.head.read_bytes(),before);self.assertEqual(orphan.read_bytes(),original)

    def test_two_actual_writers_same_parent_only_one_advances(self):
        start=threading.Barrier(2)
        def save(audience):
            start.wait()
            try:return owner.save(self.store,self.job,self.expected,{'audience':audience})
            except PipelineError as error:return error
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(save,value) for value in ['Writer A','Writer B']]
            results=[f.result(timeout=10) for f in futures]
        successes=[r for r in results if isinstance(r,dict)];errors=[r for r in results if isinstance(r,PipelineError)]
        self.assertEqual(len(successes),1);self.assertEqual(len(errors),1)
        self.assertIn('revision conflict',str(errors[0]));self.assertEqual(owner.read(self.store,self.job),successes[0])

    def test_corrupt_head_revision_cannot_advance(self):
        write_json(self.head,{'revision':'../not-a-revision'});before=self.head.read_bytes()
        revision_bytes={p.name:p.read_bytes() for p in (self.home/'revisions').iterdir()}
        with self.assertRaisesRegex(PipelineError,'revision invalid'):
            owner.save(self.store,self.job,self.expected,self.context)
        self.assertEqual(self.head.read_bytes(),before)
        self.assertEqual(revision_bytes,{p.name:p.read_bytes() for p in (self.home/'revisions').iterdir()})

    def test_expected_head_is_rechecked_before_promotion(self):
        # Simulate an out-of-contract external head mutation during revision fsync.
        # It is detected, not used as authority to overwrite the newer head.
        value={**self.first,'context':{'audience':'External'},'parent_revision':self.expected}
        value.pop('revision');revision=owner.digest(value)
        (self.home/'revisions'/(revision+'.json')).write_text(stable_json(value))
        fsync=os.fsync;changed=False
        def inject(fd):
            nonlocal changed
            fsync(fd)
            if not changed:
                changed=True
                self.head.write_text(stable_json({'revision':revision}))
        with patch('socialreel.concept_owner_context.os.fsync',side_effect=inject):
            with self.assertRaisesRegex(PipelineError,'conflict before promotion'):
                owner.save(self.store,self.job,self.expected,self.context)
        self.assertEqual(read_json(self.head)['revision'],revision)
        self.assertEqual(owner.read(self.store,self.job)['context'],{'audience':'External'})


if __name__=='__main__':unittest.main(verbosity=2)
