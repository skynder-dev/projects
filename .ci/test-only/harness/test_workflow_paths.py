"""Offline path-filter regression checks; no GitHub/API or product execution."""
import ast
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS = tuple(
    f'.github/workflows/test-only-{project}.yml'
    for project in ('social246', 'forgeAlphaZero', 'reveng028')
)


def read_paths(name):
    text = (ROOT / name).read_text(encoding='utf-8')
    # Deliberately support only our quoted, inline YAML list. Fail closed if
    # the workflow format changes; do not silently inspect a different event.
    match = re.search(r'^on:\n  pull_request:\n    paths: (\[[^\n]+\])$',
                      text, re.MULTILINE)
    if match is None:
        raise AssertionError(f'{name}: expected inline pull_request paths')
    paths = ast.literal_eval(match.group(1))
    if not isinstance(paths, list) or not paths:
        raise AssertionError(f'{name}: empty or invalid paths')
    for pattern in paths:
        # Only literals, * and terminal /** are needed here. Reject unsupported
        # syntax rather than pretend to emulate all of GitHub's glob language.
        if not isinstance(pattern, str) or not re.fullmatch(r'[\w./*\-]+', pattern):
            raise AssertionError(f'{name}: unsupported path pattern {pattern!r}')
        if '**' in pattern and (not pattern.endswith('/**') or pattern.count('*') != 2):
            raise AssertionError(f'{name}: unsupported recursive pattern')
    return paths


def triggers(patterns, changed_paths):
    for pattern in patterns:
        expression = re.escape(pattern).replace(r'\*\*', '.*').replace(r'\*', '[^/]*')
        if any(re.fullmatch(expression, path) for path in changed_paths):
            return True
    return False


class WorkflowPathsTest(unittest.TestCase):
    def test_every_verified_dependency_triggers_every_workflow(self):
        manifest = json.loads((ROOT / 'FILE_MANIFEST.json').read_bytes())
        # The manifest is itself an input, but must never hash itself.
        self.assertNotIn('FILE_MANIFEST.json', manifest)
        for workflow in WORKFLOWS:
            patterns = read_paths(workflow)
            for changed in [*manifest, 'FILE_MANIFEST.json']:
                with self.subTest(workflow=workflow, changed=changed):
                    self.assertTrue(triggers(patterns, [changed]))

    def test_new_owned_paths_trigger_every_workflow(self):
        for workflow in WORKFLOWS:
            for changed in ('.ci/test-only/new-fixture.json',
                            '.ci/test-only/harness/nested/new_check.py',
                            '.github/workflows/test-only-new.yml'):
                with self.subTest(workflow=workflow, changed=changed):
                    self.assertTrue(triggers(read_paths(workflow), [changed]))

    def test_unrelated_and_near_miss_paths_do_not_trigger(self):
        unrelated = ('social/socialreel/pipeline.py', 'forge/README.md',
                     'reveng/src/pipeline.js', '.github/workflows/production.yml',
                     '.github/workflows/nested/test-only-new.yml',
                     '.ci/test-only-other/check.py', 'docs/README.txt',
                     'docs/FILE_MANIFEST.json', 'README.txt.bak', 'README.md')
        for workflow in WORKFLOWS:
            patterns = read_paths(workflow)
            self.assertFalse(triggers(patterns, []))
            self.assertFalse(triggers(patterns, unrelated))
            for changed in unrelated:
                with self.subTest(workflow=workflow, changed=changed):
                    self.assertFalse(triggers(patterns, [changed]))

    def test_mixed_change_set_triggers(self):
        for workflow in WORKFLOWS:
            self.assertTrue(triggers(read_paths(workflow),
                                     ['social/README.md', 'README.txt']))


if __name__ == '__main__':
    unittest.main(verbosity=2)
