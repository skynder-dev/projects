"""Synthetic orchestration controls only. These are NOT Forge behavior tests."""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from process_supervisor import run_owned
from supervise_performance import cases, checked, read_receipt, validate_receipt, SENTINEL

class SupervisorContract(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='performance-supervisor-selftest-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.run_root, self.copy_root = self.root/'run', self.root/'copy'
        self.run_root.mkdir(); self.copy_root.mkdir()
        self.pins = dict(sources={'Synthetic.ps1': 'a'*64}, expected_cases=cases(),
                         tests={'Test-ForgePerformanceMetrics.ps1':'b'*64, 'PerformanceFixtures.json':'c'*64, 'dependencies.json':'d'*64},
                         dependencies={'functions': {'Synthetic.ps1':['Synthetic-NeverApplication']}})
        self.receipt = dict(schema='forge.performance.native_receipt.v1', status='PASS', error=None,
                            run_id='1'*32, run_root=str(self.run_root), package_copy_root=str(self.copy_root),
                            pins_sha256='e'*64, test_sha256='b'*64, fixtures_sha256='c'*64, dependencies_sha256='d'*64,
                            source_hashes_before={'Synthetic.ps1':'a'*64},source_hashes_after={'Synthetic.ps1':'a'*64},
                            case_count=len(cases()), failed_case_count=0,
                            cases=[dict(name=name, status='PASS', error=None) for name in cases()],
                            loaded_actual_functions=[dict(source='Synthetic.ps1', name='Synthetic-NeverApplication')],
                            fixed_now_utc='2026-10-24T12:00:00.0000000Z', powershell_version='7.5.0',
                            ps_edition='Core', date_kind_string_available=True, minimum_powershell_core='7.5', synthetic_fixture_sha256=hashlib.sha256(SENTINEL).hexdigest(),
                            real_data_loaded=False, app_launched=False, model_calls=0, network_calls=0, remote_writes=0)
    def validate(self, receipt=None):
        validate_receipt(receipt or self.receipt, self.pins, '1'*32, self.run_root, self.copy_root, 'e'*64)
    def command(self, text, timeout=5):
        return run_owned([sys.executable,'-I','-B','-c',text],cwd=self.root,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),timeout=timeout,log=self.root/'execution.log')
    def test_control_complete_metadata_accepts(self):
        self.validate()
    def test_unsupported_runtime_metadata_fails(self):
        for field,value in [('powershell_version','7.4.9'),('powershell_version','7.5.0-preview.1'),('ps_edition','Desktop'),('date_kind_string_available',False)]:
            wrong=copy.deepcopy(self.receipt);wrong[field]=value
            with self.subTest(field=field,value=value):
                with self.assertRaises(RuntimeError):self.validate(wrong)
    def test_nonzero_exit_fails_even_with_printed_pass(self):
        with self.assertRaises(RuntimeError):
            self.command("print('PASS'); raise SystemExit(7)")
    def test_zero_exit_missing_receipt_fails(self):
        self.command("print('No receipt written')")
        with self.assertRaises(FileNotFoundError):
            read_receipt(self.run_root/'receipt.json', self.run_root)
    def test_empty_receipt_fails(self):
        (self.run_root/'receipt.json').write_bytes(b'')
        with self.assertRaises(RuntimeError):
            read_receipt(self.run_root/'receipt.json', self.run_root)
    def test_foreign_invocation_fails(self):
        wrong=copy.deepcopy(self.receipt);wrong['run_id']='2'*32
        with self.assertRaises(RuntimeError):self.validate(wrong)
    def test_source_change_fails(self):
        wrong=copy.deepcopy(self.receipt);wrong['source_hashes_after']['Synthetic.ps1']='f'*64
        with self.assertRaises(RuntimeError):self.validate(wrong)
    def test_incomplete_cases_fail(self):
        wrong=copy.deepcopy(self.receipt);wrong['cases'].pop()
        with self.assertRaises(RuntimeError):self.validate(wrong)
    def test_wrong_case_identity_fails(self):
        wrong=copy.deepcopy(self.receipt);wrong['cases'][0]['name']='invented'
        with self.assertRaises(RuntimeError):self.validate(wrong)
    def test_native_fail_receipt_rejected(self):
        wrong=copy.deepcopy(self.receipt);wrong['status']='FAIL'
        with self.assertRaises(RuntimeError):self.validate(wrong)
    def test_unclaimed_function_substitution_fails(self):
        wrong=copy.deepcopy(self.receipt);wrong['loaded_actual_functions']=[]
        with self.assertRaises(RuntimeError):self.validate(wrong)
    def test_redirected_receipt_fails(self):
        original=self.root/'original.json';original.write_text('{}')
        (self.run_root/'receipt.json').symlink_to(original)
        with self.assertRaises(RuntimeError):read_receipt(self.run_root/'receipt.json',self.run_root)
    def test_success_terminates_residual_owned_descendant(self):
        marker=self.root/'forbidden-success-late-write';started=self.root/'success-descendant-started'
        child=f"import time,pathlib;pathlib.Path({str(started)!r}).write_text('started');time.sleep(1.5);pathlib.Path({str(marker)!r}).write_text('late')"
        parent=f"import sys,subprocess,time;subprocess.Popen([sys.executable,'-I','-B','-c',{child!r}],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(0.3)"
        self.command(parent)
        time.sleep(1.7)
        self.assertTrue(started.exists(),'Ordinary-exit negative control must start its descendant')
        self.assertFalse(marker.exists(),'Residual descendant survived ordinary exit')
    def test_timeout_terminates_owned_descendant(self):
        marker=self.root/'forbidden-late-write';started=self.root/'descendant-started'
        child=f"import time,pathlib;pathlib.Path({str(started)!r}).write_text('started');time.sleep(2.0);pathlib.Path({str(marker)!r}).write_text('late')"
        parent=f"import sys,subprocess,time;subprocess.Popen([sys.executable,'-I','-B','-c',{child!r}]);time.sleep(5)"
        with self.assertRaises(TimeoutError):self.command(parent,timeout=0.5)
        time.sleep(2.2)
        self.assertTrue(started.exists(),'Timeout negative control must start its descendant')
        self.assertFalse(marker.exists(),'Timed-out descendant survived')
        self.assertIn('SUPERVISOR TIMEOUT: FAIL',(self.root/'execution.log').read_text())

if __name__=='__main__':unittest.main(verbosity=2)
