#!/usr/bin/env python3
import copy
import hashlib
import json
from pathlib import Path
import unittest

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

    def test_rebuild_matches_when_receipts_available(self):
        paths = [Path(f'/tmp/deviation-{job}-results.json') for job in fixture.JOBS]
        if not all(p.is_file() for p in paths):
            self.skipTest('recovered raw job receipts not present locally')
        rebuilt = json.dumps(fixture.build(paths), indent=2, ensure_ascii=False, allow_nan=False) + '\n'
        self.assertEqual(rebuilt.encode(), fixture.OUTPUT.read_bytes())


if __name__ == '__main__':
    unittest.main()
