"""Exercise canonical Forge ZIP functions, not the side-effecting release entrypoint.

Run: python -I -B -m unittest discover -s forge/tests -p test_release_packaging.py -v

The existing build script mutates release metadata at module top level. Extract
only its real sha/build_zip definitions and literal FIXED_TIME, without importing
or copying their implementation. All payloads are synthetic and temporary.
This does not test PowerShell, application storage, models, WPF or a full release.
"""
from __future__ import annotations

import ast
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
import zipfile


SOURCE = Path(__file__).resolve().parents[1] / "tools" / "build_release.py"


def load_canonical_functions(source: Path):
    raw = source.read_bytes()
    tree = ast.parse(raw.decode("utf-8-sig"), filename=str(source))
    wanted = ("sha", "build_zip")
    definitions = []
    for name in wanted:
        matches = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name]
        if len(matches) != 1:
            raise RuntimeError("Expected one canonical top-level function: " + name)
        function = matches[0]
        arguments = [*function.args.posonlyargs, *function.args.args, *function.args.kwonlyargs]
        if function.args.vararg:
            arguments.append(function.args.vararg)
        if function.args.kwarg:
            arguments.append(function.args.kwarg)
        if function.decorator_list or function.args.defaults or any(function.args.kw_defaults) or function.returns or any(arg.annotation for arg in arguments):
            raise RuntimeError("Review new definition-time behavior before extracting " + name)
        if any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in ast.walk(function)):
            raise RuntimeError("Review new function-local imports before executing " + name)
        definitions.append(function)
    fixed = [node.value for node in tree.body if isinstance(node, ast.Assign)
             and any(isinstance(target, ast.Name) and target.id == "FIXED_TIME" for target in node.targets)]
    if len(fixed) != 1:
        raise RuntimeError("Expected one literal canonical FIXED_TIME")
    fixed_time = ast.literal_eval(fixed[0])
    module = ast.Module(body=definitions, type_ignores=[])
    namespace = {"__builtins__": {"open": open}, "os": os, "zipfile": zipfile,
                 "hashlib": hashlib, "FIXED_TIME": fixed_time}
    exec(compile(module, str(source), "exec"), namespace)
    return namespace, raw


def snapshot(root: Path):
    return {path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*") if path.is_file()}


class CanonicalReleasePackagingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="forge-packaging-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.app = self.root / "renamed synthetic app"
        self.app.mkdir()
        self.source_before = SOURCE.read_bytes()
        self.source_copy = self.root / "canonical-source-copy" / "build_release.py"
        self.source_copy.parent.mkdir()
        self.source_copy.write_bytes(self.source_before)
        self.functions, copied_bytes = load_canonical_functions(self.source_copy)
        self.assertEqual(copied_bytes, self.source_before)
        self.assertEqual(self.functions["build_zip"].__code__.co_filename, str(self.source_copy))
        self.functions.update(APP=str(self.app), NAME="SYNTHETIC_FORGE_TEST_ONLY")
        self.payloads = {
            "z-last.txt": b"synthetic payload\n",
            "A-first.cmd": b"@echo off\r\nrem synthetic fixture only\r\n",
            "nested/Пример.bin": bytes(range(256)),
            "nested/empty.bin": b"",
            ".keep": b"\xef\xbb\xbfUTF-8 BOM preserved exactly\n",
        }
        self.populate(self.app, self.payloads.items(), 946684800)
        (self.app / "empty-directory").mkdir()
        self.before = snapshot(self.app)

    def tearDown(self):
        self.assertEqual(SOURCE.read_bytes(), self.source_before, "Canonical source changed")
        self.assertEqual(self.source_copy.read_bytes(), self.source_before, "Copied canonical source changed")

    @staticmethod
    def populate(root, items, timestamp):
        for name, data in items:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            os.utime(path, (timestamp, timestamp))

    def build(self, name):
        output = self.root / name
        digest = self.functions["build_zip"](str(output))
        self.assertEqual(digest, hashlib.sha256(output.read_bytes()).hexdigest())
        return output

    def test_exact_payloads_names_and_input_nonmutation(self):
        output = self.build("payload.zip")
        with zipfile.ZipFile(output) as archive:
            expected = {"SYNTHETIC_FORGE_TEST_ONLY/" + name: data for name, data in self.payloads.items()}
            self.assertEqual(set(archive.namelist()), set(expected))
            self.assertEqual({name: archive.read(name) for name in archive.namelist()}, expected)
            self.assertTrue(all("\\" not in name and not name.startswith("/") for name in archive.namelist()))
        self.assertEqual(snapshot(self.app), self.before)

    def test_same_inputs_rebuild_byte_identically(self):
        first = self.build("first.zip")
        second = self.build("second.zip")
        self.assertEqual(first.read_bytes(), second.read_bytes())
        self.assertEqual(snapshot(self.app), self.before)

    def test_creation_order_mtime_and_source_directory_do_not_change_zip(self):
        first = self.build("original.zip")
        relocated = self.root / "second differently named app"
        relocated.mkdir()
        self.populate(relocated, reversed(list(self.payloads.items())), 1704067200)
        self.functions["APP"] = str(relocated)
        second = self.build("relocated.zip")
        self.assertEqual(first.read_bytes(), second.read_bytes())
        self.assertEqual(snapshot(relocated), self.before)
        self.assertEqual(snapshot(self.app), self.before)

    def test_archive_metadata_matches_the_existing_release_contract(self):
        output = self.build("metadata.zip")
        with zipfile.ZipFile(output) as archive:
            entries = archive.infolist()
            self.assertEqual([entry.filename for entry in entries], [
                "SYNTHETIC_FORGE_TEST_ONLY/.keep",
                "SYNTHETIC_FORGE_TEST_ONLY/A-first.cmd",
                "SYNTHETIC_FORGE_TEST_ONLY/nested/empty.bin",
                "SYNTHETIC_FORGE_TEST_ONLY/nested/Пример.bin",
                "SYNTHETIC_FORGE_TEST_ONLY/z-last.txt",
            ])
            for entry in entries:
                self.assertEqual(entry.date_time, (2026, 1, 1, 0, 0, 0))
                self.assertEqual(entry.compress_type, zipfile.ZIP_DEFLATED)
                self.assertEqual(entry.create_system, 0)
                self.assertEqual(entry.external_attr, 0o644 << 16)
                self.assertFalse(entry.is_dir())
        self.assertEqual(snapshot(self.app), self.before)

    def test_payload_change_changes_digest_without_rewriting_other_inputs(self):
        first = self.build("before.zip")
        changed = self.app / "z-last.txt"
        changed.write_bytes(b"different synthetic bytes\n")
        second = self.build("after.zip")
        self.assertNotEqual(first.read_bytes(), second.read_bytes())
        self.assertNotEqual(self.functions["sha"](str(first)), self.functions["sha"](str(second)))
        expected = dict(self.before)
        expected["z-last.txt"] = b"different synthetic bytes\n"
        self.assertEqual(snapshot(self.app), expected)

    def test_output_creation_failure_preserves_input_payloads(self):
        with self.assertRaises(FileNotFoundError):
            self.functions["build_zip"](str(self.root / "absent output parent" / "failed.zip"))
        self.assertEqual(snapshot(self.app), self.before)


if __name__ == "__main__":
    unittest.main()
