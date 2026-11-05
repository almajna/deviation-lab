#!/usr/bin/env python3
import copy
import hashlib
import json
from pathlib import Path
import unittest
import tempfile
import zipfile
from unittest.mock import patch

import verify_routing_archives as archives

import build_routing_fixture as fixture


class RoutingFixtureTest(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(fixture.OUTPUT.read_text(encoding='utf-8'))

    def test_fixture_matrix_and_rows(self):
        self.assertEqual(self.data['schema_version'], 'routing-replay-v1')
        self.assertEqual([r['job_id'] for r in self.data['runs']], list(fixture.JOBS))
        for run in self.data['runs']:
            self.assertEqual(len(run['cases']), 39)
            self.assertEqual(run['raw_sha256'], fixture.JOBS[run['job_id']])
            self.assertEqual(run['source_commit'], fixture.COMMIT)
            for case in run['cases']:
                fixture.transform_case(case)

    def test_bad_measurement_and_binding_are_rejected(self):
        case = copy.deepcopy(self.data['runs'][0]['cases'][0])
        case['summary']['B_share'] = -1
        with self.assertRaisesRegex(ValueError, 'B share'):
            fixture.transform_case(case)
        case = copy.deepcopy(self.data['runs'][0]['cases'][0])
        case['rows'][0]['endpoint']['provider'] = 'wrong'
        with self.assertRaisesRegex(ValueError, 'provider binding'):
            fixture.transform_case(case)
        case = copy.deepcopy(self.data['runs'][0]['cases'][0])
        case['rows'][4]['phase'] = 'warmup'
        with self.assertRaisesRegex(ValueError, 'phase mismatch'):
            fixture.transform_case(case)

    def test_receipt_sha_is_enforced(self):
        with self.assertRaisesRegex(ValueError, 'SHA256'):
            fixture.transform(b'{}', next(iter(fixture.JOBS)))

    def test_original_archive_required_and_hash_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'archive.zip'
            with self.assertRaises(FileNotFoundError):
                archives.read_archive(path, '0' * 64)
            with zipfile.ZipFile(path, 'w') as z:
                z.writestr('results.json', b'authentic-test-bytes')
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(archives.read_archive(path, digest), b'authentic-test-bytes')
            path.write_bytes(path.read_bytes() + b'tamper')
            with self.assertRaisesRegex(ValueError, 'archive SHA256 mismatch'):
                archives.read_archive(path, digest)

    def test_verifier_rejects_missing_archives_and_fixture_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            with self.assertRaises(FileNotFoundError):
                archives.verify(directory)
            wrong_fixture = directory / 'routing.json'
            wrong_fixture.write_text('{}')
            with patch.object(archives, 'read_archive', return_value=b'receipt'), \
                 patch.object(fixture, 'transform', return_value={}), \
                 patch.object(fixture, 'OUTPUT', wrong_fixture):
                with self.assertRaisesRegex(ValueError, 'fixture differs'):
                    archives.verify(directory)

    def test_rebuild_matches_when_receipts_available(self):
        paths = [Path(f'/tmp/deviation-{job}-results.json') for job in fixture.JOBS]
        if not all(p.is_file() for p in paths):
            self.skipTest('recovered raw job receipts not present locally')
        rebuilt = json.dumps(fixture.build(paths), indent=2, ensure_ascii=False, allow_nan=False) + '\n'
        self.assertEqual(rebuilt.encode(), fixture.OUTPUT.read_bytes())


if __name__ == '__main__':
    unittest.main()
