# PR #3 — independent engineering review and follow-up

Date: 2026-11-02. PR: [#3](https://github.com/almajna/deviation-lab/pull/3). Issue: [#2](https://github.com/almajna/deviation-lab/issues/2). Reviewed baseline: `960f240ca5f2136b2086963139e58df68bf71ccd`.

## Review outcome and provenance

The repository owner reported that the independent audit returned **APPROVE for the Phase 1 engineering scope**, with the three follow-up findings below. This record preserves that supplied outcome; the external review's full transcript and reviewer identity were not supplied here, so it does not claim a separately submitted GitHub approval. The earlier read-only project reviewer also reproduced the paired-data audit and all three artifacts independently, and identified validator/schema findings that were fixed before this follow-up.

Engineering approval is **not empirical GO**, research-architecture approval, dataset redistribution permission, a frozen-test qualification, final release approval, or merge authorization. The retained judged-quality/cost uncertainties in [DATA_AUDIT.md](DATA_AUDIT.md) remain unresolved. RouterBench paired coverage remains unverified; no pickle was deserialized. No downstream implementation has begun.

## Findings and disposition

| Finding | Change | Verification |
|---|---|---|
| Missing upstream `Generation failed:` detector | Reject that prefix alongside `Processing failed:` and `Unexpected error:` | Regression uses otherwise valid score, cost, and token fields; strict loading rejects it and explicit audit mode records one rejection |
| Count of additional complete zero-cost files was five | Corrected to **six** | Rechecked every complete JSON member in the pinned 8 MiB prefix; incomplete trailing member is not counted |
| No synthetic end-to-end audit test | Added `tests/test_data_integration.py` | CLI parsing, local checksum cache, compressed archive/member validation, source prompt matching, record rejection, overlap/cohort construction, grouped splits, and all three written JSON artifacts run together |

The six complete all-zero-cost files each contain 253 rows: `DeepHermes-3-Llama-3-8B-Preview`, `DeepSeek-R1-Distill-Qwen-7B`, `Qwen2.5-Coder-7B-Instruct`, `Llama-3.1-8B-Instruct`, `MiniCPM4.1-8B`, and `MiMo-7B-RL-0530`. They are outside the priced research sample. This correction changes a documentation count, not the selected four-arm cohort or the zero-cost exclusion policy.

The integration fixture is explicitly `SYNTHETIC_FIXTURE`; the audit honors that manifest label and uses synthetic quality/cost metadata in its temporary output. The existing real manifest defaults to its previous behavior. The test creates two four-row mock model files, inserts one `Generation failed:` row, and verifies **8 source rows, 7 accepted rows, 3 complete tasks, and 6 cohort outcomes**. It checks rejection/missing-pair/overlap counts, input/member receipt hashes, split digest/group isolation, the NO-GO gate, and exact byte equality of two CLI runs. Network sockets are forbidden; only synthetic local bytes are consumed. Generated paths and fixture outputs are temporary and never committed.

## Reproduction evidence

Use Python >=3.11 from the repository root:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
bash scripts/check.sh
```

Local result: **26 tests passed** under Python 3.12.15; the starter synthetic trace check passed. GitHub's existing Python 3.11 workflow discovers the integration test automatically; the follow-up result is linked from the [feature branch's CI runs](https://github.com/almajna/deviation-lab/actions?query=branch%3Afeat%2Fdata-audit).

A separate read-only project reviewer inspected this follow-up and returned **APPROVE for the requested engineering follow-up**, independently ran all 26 tests, recounted the six complete zero-cost files, and reproduced all three real-data artifacts byte-for-byte. That reviewer authored no changes. This additional review has the same engineering-only limits; it does not approve the scientific gates.

Reproduce the real sample using the bounded-download command in [DATA_AUDIT.md](DATA_AUDIT.md), or reuse its populated cache without `--download`. Compare the generated files with the same names under `artifacts/`; no runtime directory path belongs in source control. After the detector fix, all three artifacts reproduce **byte-for-byte unchanged**:

| File | SHA-256 of file bytes |
|---|---|
| `artifacts/data_audit.json` | `2ef3bfeb70d821c9c63588c7b7d824b94fb496b44059b422365e80c5217c2a95` |
| `artifacts/data_manifest.json` | `111a07dfe4fe7abed39af5cdca230a9efcbf11a5aab4e93b676f3dc0d3d71ac3` |
| `artifacts/splits.json` | `4a3b1d1f5627cb87a392ab377089e9cd6948c1ec5a60feee138e4f20f693c88f` |

Preserved result: **247 complete tasks / 988 outcomes**, from 1,006 accepted of 1,012 retained records; six explicit zero-cost rejections. The exploratory split remains **172 train / 31 validation / 44 test** and `EXPLORATORY_NOT_FROZEN`. Technical pairing remains **PASS**; the empirical gate remains **NO_GO**. The file hash of `splits.json` above is distinct from its embedded canonical-manifest digest.

## Limits and materiality

The synthetic integration test proves engineering wiring and rejection/artifact behavior; it cannot establish real-model accuracy, historical judge validity, observed invoices, licensing for unreviewed sources, statistical power, or deployable budget guarantees. Cached real-sample reproduction verifies only the pinned selected sample, not the whole archive or all benchmark domains. The engineering APPROVE outcome does not remove these limitations.

Behavior changes only for failure-marked inputs that previously slipped through and for explicitly labeled synthetic audit manifests. No selected real input, committed evidence artifact, shared contract, scientific gate, or downstream mechanism changed. Incremental spend: **$0**. These review fixes remain unmerged pending the owner's decision.

## Delivery state

During preparation of these fixes, GitHub reported that PR #3 was merged outside this work at **2026-11-02 23:20:47 UTC**, merge commit [`c9b4761c3416ee28cc80aa74f0301846b6d5b3af`](https://github.com/almajna/deviation-lab/commit/c9b4761c3416ee28cc80aa74f0301846b6d5b3af). That merge includes the reviewed baseline, not this follow-up. The fixes stay on the existing `feat/data-audit` branch and require a separate follow-up PR because a merged PR cannot review new commits. No merge was performed by the agent; no further merge is authorized.
