"""Exercise the read-only validator through its public CLI."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'check_workflow.py'
VALID = '''version: 1
name: sample
steps:
  - id: inspect
    skills:
      - name: code-review
        instruction: 检查改动。
      - name: project-docs
        instruction: 检查受影响文档。
  - id: finish
    when:
      all:
        - {step: inspect, field: changed, equals: true}
        - any:
            - {step: inspect, field: status, equals: completed}
            - {step: inspect, field: has_unresolved, equals: false}
    skills:
      - name: project-docs
        instruction: 同步文档。
'''


class ValidatorTests(unittest.TestCase):
    def run_cli(self, source, expected=1):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / 'workflow.yml'
            path.write_text(source, encoding='utf-8')
            before = {p.relative_to(root): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            proc = subprocess.run([sys.executable, '-B', str(SCRIPT), str(path), '--json'],
                                  capture_output=True, encoding='utf-8')
            self.assertEqual(proc.returncode, expected, proc.stdout + proc.stderr)
            result = json.loads(proc.stdout)
            self.assertEqual(result['valid'], expected == 0)
            after = {p.relative_to(root): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            self.assertEqual(before, after)
            return result

    def test_valid_multiple_skills_nested_conditions(self):
        result = self.run_cli(VALID, 0)
        self.assertEqual(result['steps'], ['inspect', 'finish'])
        self.assertEqual(result['skills'], ['code-review', 'project-docs'])

    def test_schema_rejections(self):
        variants = {
            'unknown_root': VALID + 'run: destructive command\n',
            'wrong_version': VALID.replace('version: 1', 'version: 2'),
            'bool_version': VALID.replace('version: 1', 'version: true'),
            'empty_steps': 'version: 1\nname: sample\nsteps: []\n',
            'mapping_steps': 'version: 1\nname: sample\nsteps: {}\n',
            'duplicate_id': VALID.replace('id: finish', 'id: inspect'),
            'unknown_step': VALID.replace('  - id: finish', '  - run: echo hello\n    id: finish'),
            'self_reference': VALID.replace('step: inspect', 'step: finish'),
            'forward_reference': VALID.replace('step: inspect', 'step: future'),
            'unknown_result': VALID.replace('field: changed', 'field: good'),
            'string_boolean': VALID.replace('equals: true', 'equals: "true"'),
            'yaml11_boolean': VALID.replace('equals: true', 'equals: yes'),
            'null_comparison': VALID.replace('equals: true', 'equals: null'),
            'unknown_status': VALID.replace('equals: completed', 'equals: passed'),
            'empty_skills': 'version: 1\nname: sample\nsteps:\n  - id: a\n    skills: []\n',
            'unknown_skill_field': VALID.replace('      - name: code-review', '      - path: /tmp/a\n        name: code-review'),
            'blank_instruction': VALID.replace('instruction: 检查改动。', 'instruction: "  "'),
            'path_skill': VALID.replace('name: code-review', 'name: ../code-review'),
            'missing_instruction': VALID.replace('        instruction: 检查改动。\n', ''),
            'empty_group': VALID.replace('    when:\n      all:', '    when:\n      any: []\n      all:'),
            'scalar_condition': VALID.replace('    when:\n      all:', '    when: true\n    other:'),
            'mixed_condition': VALID.replace('      all:', '      step: inspect\n      all:'),
            'duplicate_yaml_key': VALID.replace('version: 1', 'version: 1\nversion: 1'),
            'alias': VALID.replace('name: sample', 'name: &label sample'),
            'custom_tag': VALID.replace('name: sample', 'name: !!str sample'),
            'multiple_documents': VALID + '\n---\nname: second\n',
            'malformed': 'version: [\n',
        }
        for label, source in variants.items():
            with self.subTest(label=label):
                result = self.run_cli(source)
                self.assertTrue(result['errors'])

    def test_empty_all_is_rejected(self):
        source = VALID[:VALID.index('  - id: finish')] + '''  - id: finish
    when: {all: []}
    skills:
      - name: project-docs
        instruction: 检查。
'''
        self.run_cli(source)

    def test_namespaced_skill(self):
        self.run_cli(VALID.replace('name: code-review', 'name: superpowers:systematic-debugging'), 0)

    def test_utf8_bom(self):
        self.run_cli('\ufeff' + VALID, 0)

    def test_io_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            proc = subprocess.run([sys.executable, '-B', str(SCRIPT), str(Path(folder) / 'missing.yml'), '--json'],
                                  capture_output=True, encoding='utf-8')
            self.assertEqual(proc.returncode, 2)
            self.assertFalse(json.loads(proc.stdout)['valid'])

    def test_invalid_implicit_date_is_reported_as_config_error(self):
        self.run_cli(VALID.replace('name: sample', 'name: 2026-99-99'))

    def test_oversized_integer_is_reported_as_config_error(self):
        self.run_cli(VALID.replace('version: 1', 'version: ' + '1' * 5000))

    def test_deep_yaml_is_config_error(self):
        self.run_cli('version: 1\nname: sample\nsteps: ' + '[' * 1500 + '1' + ']' * 1500)

    def test_missing_dependency_is_environment_error(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'workflow.yml'
            path.write_text(VALID, encoding='utf-8')
            proc = subprocess.run([sys.executable, '-I', '-S', str(SCRIPT), str(path), '--json'],
                                  capture_output=True, encoding='utf-8')
            self.assertEqual(proc.returncode, 2, proc.stderr)
            self.assertIn('PyYAML', json.loads(proc.stdout)['errors'][0])


if __name__ == '__main__':
    unittest.main()
