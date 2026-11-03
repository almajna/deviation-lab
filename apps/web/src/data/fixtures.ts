// Bundled traces. The only approved v0.2 trace today is the hand-specified synthetic conformance
// fixture. We bundle ONLY its public projection (apps/web/fixtures/gate-a.synthetic.json, pinned by
// fixtures/manifest.json). The source pack also contains an agent's private signal and must never be
// imported here. Budget and prompts come from a separately labelled annotation of public receipts.

import trace from '../../fixtures/gate-a.synthetic.json';
import annotation from '../../fixtures/gate-a.annotations.json';
import manifest from '../../fixtures/manifest.json';
import type { FixtureAnnotation, TraceBundle } from '../trace/types';
import { validateTrace } from '../trace/validate';

export const CONFORMANCE_FIXTURE: TraceBundle = {
  id: 'fixture:gate-a',
  label: 'Gate A conformance fixture',
  origin: 'SYNTHETIC_FIXTURE',
  trace: validateTrace(trace),
  annotation: annotation as FixtureAnnotation,
  file: { path: 'apps/web/fixtures/gate-a.synthetic.json', sha256: manifest.public_trace_sha256, source: manifest.source_projection },
};

export const BUNDLED: TraceBundle[] = [CONFORMANCE_FIXTURE];
