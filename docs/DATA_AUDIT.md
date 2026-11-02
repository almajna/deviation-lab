# Phase 1 — dataset feasibility audit

**Verified 2026-11-02. Technical paired ingestion: PASS. Empirical/downstream gate: NO-GO.**

Issue: [#2](https://github.com/almajna/deviation-lab/issues/2). The integrator owns this report. `docs/CONTRACTS.md` remains unchanged and unapproved. Recorded outputs have been ingested; no empirical mechanism/benchmark claim is established, and the existing CLI demo remains synthetic.

## Reproduction and proof

Use Python >=3.11; no third-party Python packages, credentials, model calls, or paid services are required.

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
audit_cache="$(mktemp -d)"
audit_evidence="$(mktemp -d)"
PYTHONPATH=src python3 -m deviation.data \
  --manifest data/source_manifest.json \
  --cache "$audit_cache" \
  --out "$audit_evidence" --download
```

Use a Python >=3.11 interpreter. Reuse the populated cache and remove `--download` for offline reproduction. Size, range, checksum, schema, and pairing failures are explicit errors. Cache/output directory names are local runtime choices and are not part of the committed evidence.

Reproduction reads an 8,388,608-byte LLMRouterBench archive prefix, a 262,144-byte RouterBench prefix, and the 963,444-byte original ArenaHard question file: **9,614,196 payload bytes**. A separate bounded 32 MiB archive exploration reached only one complete Winogrande model, insufficient to validate its costed pair coverage. Neither full dataset was downloaded. No upstream program or benchmark-generated code was executed; pickle was inspected as bytes/opcodes, never deserialized.

Local verification after the review follow-up: all **26 tests** passed under Python 3.12.15, including failure-prefix regression and synthetic CLI integration. The existing `scripts/check.sh` verifies the full suite and synthetic starter trace. Independent review and reproduction evidence, its limitations, and the engineering-only APPROVE outcome are recorded in [DATA_REVIEW.md](DATA_REVIEW.md). A separate clean-cache download reproduced all committed evidence exactly. Hosted CI is linked in the PR; no remote result is inferred from local tests.

`artifacts/data_audit.json` holds aggregate evidence, `artifacts/data_manifest.json` pins source/member hashes, and `artifacts/splits.json` contains opaque task/group hashes only. Cache bytes remain outside Git. The offline fixture is explicitly `SYNTHETIC_FIXTURE`. **No raw questions, answers, outputs, or per-row real scores/costs are redistributed in this PR.** Whole-archive LFS digests in the manifest are upstream metadata, explicitly not locally verified; prefix and selected member digests were verified.

## Sources, costs, and licensing

| Source | Pinned revision | Finding |
|---|---|---|
| [LLMRouterBench code](https://github.com/ynulihao/LLMRouterBench/tree/811df08b1b37646064eeb8cb6acfd498bf99885a) | `811df08b1b37646064eeb8cb6acfd498bf99885a` | Collector/evaluator inspected only |
| [LLMRouterBench data](https://huggingface.co/datasets/NPULH/LLMRouterBench/tree/b95870f9e60c589e82f7972c91ffa8de9ca89f85) | `b95870f9e60c589e82f7972c91ffa8de9ca89f85` | Public, ungated JSON in a 1,283,503,080-byte tar.gz |
| [ArenaHard original prompts](https://huggingface.co/datasets/lmarena-ai/arena-hard-auto/tree/15f3746e21432264ce9b453999bde4f3c946d2e6) | `15f3746e21432264ce9b453999bde4f3c946d2e6` | Apache-2.0 declared in dataset card; all 253 sampled queries match exactly |
| [RouterBench data](https://huggingface.co/datasets/withmartian/routerbench/tree/784021482c3f320c6619ed4b3bb3b41a21424fcb) | `784021482c3f320c6619ed4b3bb3b41a21424fcb` | Public pickle files; no dataset LICENSE/license metadata at this revision |
| [RouterBench code](https://github.com/withmartian/routerbench/tree/cc67d1008bd8f3cf1e8040cc3ba4034d31b93c0c) | `cc67d1008bd8f3cf1e8040cc3ba4034d31b93c0c` | MIT code, not independent proof of HF dataset redistribution rights |

The [LLMRouterBench license](https://github.com/ynulihao/LLMRouterBench/blob/811df08b1b37646064eeb8cb6acfd498bf99885a/LICENSE) covers original code/benchmark contributions only to contributors' rights and preserves incorporated materials' licenses. The sampled prompts have an independently matched Apache-2.0 source; other task families require their own checks. Retain applicable notices if redistribution is later authorized. RouterBench raw redistribution permission is not established. Original ArenaHard question-file SHA-256: `6cfe75abb0e09cd39e7f9b0b18ea96d41be2d4d9ddf76dc1d07d78b6accb2039`.

## LLMRouterBench: measured coverage and schema

Selection: the first four fully readable cost-bearing model families in the 8 MiB prefix, including every row of each selected file. This is a complete **single-subset** feasibility sample, not a random or benchmark-wide representative sample. Do not extrapolate publication-wide counts.

All files identify `arenahard_coding`, source split `test`, `demo=false`, and 253 records. Task identity namespaces index by pinned source revision/dataset/source split, then requires matching query and ground-truth hashes across arms. Index alone is not durable identity. All 253 queries match the separately pinned 750-row original ArenaHard source.

| Model | Raw rows | Structurally accepted positive-cost rows | Zero-cost rejections |
|---|---:|---:|---:|
| claude-sonnet-4 | 253 | 253 | 0 |
| deepseek-v3.1-terminus | 253 | 253 | 0 |
| gemini-2.5-flash | 253 | 251 | 2 |
| qwen3-235b-a22b-2507 | 253 | 249 | 4 |
| Total | 1,012 | 1,006 | 6 |

Overlap after structural rejection:

| | Claude | DeepSeek | Gemini | Qwen |
|---|---:|---:|---:|---:|
| Claude | 253 | 253 | 251 | 249 |
| DeepSeek | 253 | 253 | 251 | 249 |
| Gemini | 251 | 251 | 251 | 247 |
| Qwen | 249 | 249 | 247 | 249 |

Four-arm complete intersection: **247 tasks / 988 outcomes**; six tasks are incomplete. Complete tasks also have aligned formatted prompts. Claude+DeepSeek provide a **253-task two-arm candidate** without these zero-cost exclusions. That is the recommended narrow candidate after Gate A; no policy/model-performance experiment was run. Counts demonstrate ingestion feasibility, not statistical power.

Observed columns: integer `index`, `prompt_tokens`, `completion_tokens`; string `origin_query`, `prompt`, `raw_output`; list-of-message-objects `prediction`; numeric `score`, `cost`; null `ground_truth` throughout. Envelopes also include aggregate performance/time/tokens/cost, `counts`, model/dataset/split/demo, `data_fingerprint`, and `records`.

An anonymized schema projection is `task_id=<opaque SHA-256>`, `model_id=<source model>`, `quality=<retained judged score>`, `cost=<reported amount>`, `cost_unit=reported_usd`, `cost_basis=api_usage_cost_or_token_pricing_unresolved`, `ground_truth_sha256=null`. No actual row is reproduced. This is an internal `data-audit-1` record, not an approved shared experiment schema or allocator input. Across the **1,006 accepted-record population**, retained scores are 287 zeros, 223 halves, and 496 ones; these are integrity diagnostics, not held-out performance results.

The [ArenaHard evaluator](https://github.com/ynulihao/LLMRouterBench/blob/811df08b1b37646064eeb8cb6acfd498bf99885a/evaluation/ArenaHard/arenahard.py) judges against a baseline: win/tie/loss = 1/0.5/0, with no objective ground truth. Missing baselines/invalid judgments can also become zero; retained rows omit individual judge status and historical judge configuration. Existing protocol permits judged quality, but **objective coding correctness and validity of every zero are unverified**.

The [generator](https://github.com/ynulihao/LLMRouterBench/blob/811df08b1b37646064eeb8cb6acfd498bf99885a/generators/generator.py) prefers API `usage.cost`, otherwise token counts times configured prices. Historical rows omit which path and code/config revision produced the cost. Call these **reported USD amounts of unresolved API-reported/token-priced provenance**, not verified invoices. Six other complete local-model files in the initial prefix had all-zero costs; they are outside the priced sample and cannot be assumed free compute. The complete-file count and model names were rechecked during the [review follow-up](DATA_REVIEW.md).

The [collector](https://github.com/ynulihao/LLMRouterBench/blob/811df08b1b37646064eeb8cb6acfd498bf99885a/data_collector/runner.py) can retain failures with null scores/zero costs. Our adapter rejects null scores rather than copying the upstream baseline loader's null-to-zero behavior. Unknown/missing/negative costs, nonfinite/out-of-range scores, failures, duplicates, demo files, mixed provenance/metrics/units, and mismatched questions/truths fail explicitly. Audit-mode exclusions remain visible.

## RouterBench: fallback NO-GO

Its [card](https://huggingface.co/datasets/withmartian/routerbench/blob/784021482c3f320c6619ed4b3bb3b41a21424fcb/README.md) explicitly describes estimated costs. The [conversion code](https://github.com/withmartian/routerbench/blob/cc67d1008bd8f3cf1e8040cc3ba4034d31b93c0c/convertors/common.py) and [paper Appendix A](https://arxiv.org/html/2403.12031v2#A1) use API/reference prices and actual responses; these are neither observed invoices nor decision-time-known costs.

Files: `routerbench_0shot.pkl` 99,567,659 bytes; `routerbench_5shot.pkl` 171,091,324; `routerbench_raw.pkl` 1,198,134,681. The 0-shot prefix contains pickle protocol 5 and pandas/NumPy reconstruction opcodes. Static inspection is not verified pair coverage. **Measured paired task count: unverified/null**, not a repeated publication count. The JSON-only loader rejects pickle before parsing. The old package link in the HF card returns 404; the current code repository is separately pinned.

Use no RouterBench raw data in this PR. A safe JSON/Parquet export with provenance, clarified dataset terms, and measured pair/cost/quality validation are prerequisites for adopting this fallback. A full-data path is optional: fetch pinned source files explicitly outside Git after terms/format review, check their complete LFS digests, and extend the audit with a documented source adapter; the bounded CLI deliberately does not fetch multi-GB files or run upstream code.

## Leakage boundary and exploratory splits

`decision_view` returns exactly `task_id`, original task `prompt`, and `model_options`. It excludes quality/scores, ground truth, responses, oracle selections, failure status, completion tokens, and realized cost. Add public model pricing only as separately sourced pre-decision metadata. A Python projection is a tested interface boundary, not a hostile-code sandbox.

Splits hash seed 7 plus NFKC/case/whitespace-normalized prompt hash. All arms and normalized-equivalent prompts across IDs share a split. Input order does not matter; new distinct groups do not move old groups. Validators check checksums, seed/algorithm, exact cohort coverage, and prompt-group contamination. Semantic near-duplicates and source-family holdouts still need scientific design before freezing.

The 247-task exploratory cohort gives **172 train / 31 validation / 44 test**. It is `EXPLORATORY_NOT_FROZEN`; no router is trained/evaluated. Source `test` is a provenance label, not our final holdout. Complete-case exclusions depend on realized cost validity and may bias research; do not treat this audit cohort as an untouched final test set.

## Scientific gate and next action

**Technical pairing PASS; empirical/downstream NO-GO.** Before scientific approval under existing Gate A:

1. Recover reliable judge status/configuration, or explicitly accept the retained score as an uncertain proxy with limited claims. Judged quality itself is already allowed by the protocol; indistinguishable failed judgments are the unresolved limitation.
2. Verify billing provenance if observed billed costs are required; otherwise explicitly adopt reported/estimated retrospective costs without observed-dollar-savings claims.
3. Define the pre-decision budget policy (training-only cost estimates or declared caps) before hard-budget deployability claims. Future realized costs remain hidden.

These are research assumptions, not permission requests for routine engineering choices. Existing scientific/contract approval remains pending. No downstream market, attack, simulator integration, or visual backend implementation has begun. **Incremental spend: $0.**
