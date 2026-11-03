# Independent probe reproduction

Use a clean full-history checkout of PR #27 at `680c8d7c8a5e9103c34ecb332282935d181fc625`, with historical commit `b67bf93b7a23c5c5d62e9d7f04ddfb614cfb0d81` available. The probe uses only Python/Git and trusted numerical verification; actual sandbox experiment execution is supported separately by CI.

Keep the unchanged probe at its fixed ROOT, `/tmp/harness-rebase-independent/probe.py`. Copy the committed `artifacts/research/rebase/manifest.json` to `ROOT/expected-manifest.json` and `comparison.json` to `ROOT/comparison.json`.

Obtain the decoded log of actual research CI job `126242579307`, run `41729424265`. Strip each ISO timestamp prefix (`^\d{4}-\d{2}-\d{2}T\S+ `). Use lines exactly equal to the marker names, not echoed Python print statements. The JSON between `RESEARCH_REBASE_MANIFEST_BEGIN/END` must equal the committed expected manifest under canonical JSON encoding; likewise `RESEARCH_REBASE_COMPARISON_BEGIN/END` must equal committed comparison.json. This was checked independently in the review.

Concatenate/base64-decode the lines between exact `RESEARCH_ARCHIVE_BEGIN/END`, then open as gzip tar. Safely extract only regular `.json`/`.jsonl` files under `research-rebase/historical/` or `research-rebase/current/`, preserving those full relative names beneath `ROOT/evidence/`. Resolve ROOT first on macOS (/tmp is a symlink), reject absolute/parent-traversal paths and require every resolved target to remain under ROOT. This recovers 44 JSON artifacts; do not run or import archived files.

Layout:

```
/tmp/harness-rebase-independent/
  probe.py
  expected-manifest.json
  comparison.json
  evidence/research-rebase/historical/...
  evidence/research-rebase/current/...
```

From the exact clean checkout, verify SHA-256 of each `src/deviation_research_replay/*.py` against `expected-manifest.json`'s `replay_adapter_source`, then run:

```sh
PYTHONOPTIMIZE=0 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src" python3.12 /tmp/harness-rebase-independent/probe.py
```

PYTHONOPTIMIZE=0 keeps this test probe's intentional assert statements active; the production source-binding guard uses explicit failures. The independent run must report all four old/current reviews PASS with producer functions disabled, valid source/resource bindings, an independently recomputed digest map, seven forgery rejections, 54 event relations and the unchanged original findings. It runs no experiment adapter and incurs no new inference.
