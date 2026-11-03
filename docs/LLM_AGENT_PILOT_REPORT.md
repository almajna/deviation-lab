# Real open-weight CPU pilot — completed capability failure

PR #24 / issue #21. **24 genuine inference calls, 2 valid chosen no-ops,
22 schema-invalid responses. Zero accepted reports or trades. Spend $0.**
The experiment establishes real inference and auditable replay. It does not
establish strategic manipulation, truthful compliance or mechanism robustness.

## Agent 4 attribution correction

At original head `2bfc83d`, Agent 4 correctly reproduced two scripted control
trades being counted against a focal participant that made none. `accepted_trades`
now filters the focal event actor. `system_accepted_trades` is separate, and
scope metadata distinguishes focal reports/trades, controller payoffs under the
focal declared belief, and system routing/reservation/maker loss. Regressions
cover both selected actor identities and an explicit voluntary-no-op focal
policy with exactly two scripted control trades. That direct regression does
not depend on input-limit fallback. All source-bound instrument artifacts were
regenerated; the 324 scripted economic outcomes and nine summary rows are unchanged.

## Prospective design and actual execution

[Protocol](LLM_AGENT_PILOT_PROTOCOL.md), pinned model/weight checksums and source
were published at `fe90b89aa513f4c78bdfeedd998869e848520566` **before** inference.
Both ordinary CI checks passed before the workflow-only dispatch at
`1bcd83faf1389fd0ceb6bbe120272ad4ca0f2587`. Independent read-only review approved
the prospective scope/code. No model, prompt or condition changed after results.

The public repository's free standard `ubuntu-24.04` runner executed
Qwen2.5-0.5B-Instruct locally on CPU, float32/four threads, using pinned
Apache-2.0 safetensors and remote code disabled. This is real open-weight
inference on the experiment runner, not the restricted Mac or a paid hosted
model API. [Free-route verification](LLM_AGENT_INFERENCE_ROUTE.md).

First actual [run 41666251738](https://github.com/almajna/deviation-lab/actions/runs/41666251738)
passed. Runtime installation took 26 seconds; download/load/pilot took 8 minutes
58 seconds; the entire job took 9 minutes 28 seconds. Recorded generation time
was 515.62 seconds. The execution receipt records exact run/job/source/protocol
hashes and standard-runner labels. Model files remained on the ephemeral runner;
no paid API/GPU, persistent cache or Actions artifact upload was used.

## All observed outcomes

| Supplied belief | Instruction | External benefit | Calls | Valid actions | Invalid | Valid reports | Executed trades |
|---|---|---:|---:|---:|---:|---:|---:|
| a high | Truthful | 0 | 4 | 1 no-op | 3 | 0 | 0 |
| a high | Utility | 0 | 4 | 0 | 4 | 0 | 0 |
| a high | Utility | 200 | 4 | 0 | 4 | 0 | 0 |
| b high | Truthful | 0 | 4 | 1 no-op | 3 | 0 | 0 |
| b high | Utility | 0 | 4 | 0 | 4 | 0 | 0 |
| b high | Utility | 200 | 4 | 0 | 4 | 0 | 0 |

All 24 calls returned known usage: **45,874 prompt and 609 generated tokens**.
Every generation stopped on EOS, not the 64-token ceiling. No retries, repairs,
unknown-usage calls or skipped inferences occurred. The two accepted actions are
actual generated `{"choice":0}` responses. The other 22 remain failures, including
nested/invalid report arrays, unsupported `expected_virtual_credit_utility`
fields and fenced JSON. Their declines/no-ops are **harness interventions**,
not chosen model behavior. All 12 report opportunities failed. Reporting error
distance is therefore undefined; the summary uses null rather than interpreting
an empty sum as perfect truth.

All episodes selected arm a under the uniform/no-report fallback. Model cash,
external benefit and realized utility were zero. Expected utility was -312
relative to the matched scripted signal reporter, reflecting foregone scoring
participation rewards, not a monetary bill or proof of robust economics. In
the b-high condition the last invalid response changes slightly with benefit
0 versus 200. There is no **valid executable** incentive response; do not infer
identical raw text or absence of all response sensitivity.

These observations identify an interface/capability failure for this specific
small model and frozen prompt. They do not demonstrate strategic manipulation,
calibrated information use, truthful reporting, generally incapable LLMs or a
research breakthrough. With no valid reports, the intended economic sensitivity
question cannot be identified. The single authored task and deterministic runs
provide no population effect estimate or meaningful confidence interval.

The frozen 8 KB input ceiling would skip a later turn after an accepted trade
in this fixture; none occurred here because no trade was accepted. Fixing that
scope restriction and qualifying a capable interface require a separately
reviewed prospective study. This pilot was not retuned to obtain good results.

## Evidence and independent reproduction

`artifacts/llm_agents/real_pilot.json` retains full prompts, raw outputs, token
IDs, model/file/dependency hashes, all six economic receipts, 54 matched scripted
mechanism/control receipts and every failure. It is compact JSON (~930 KB), not
a weight download or third-party task dataset. The underlying engine trace
remains labeled synthetic; the actor sidecar establishes real decision origin.

Frozen adapter SHA256:
`b4df995829657b2d488b3f0b9577b07b1cdb81ba998359f7bdaf539a3ca362d1`.
Canonical payload SHA256 reconstructed from 12 original job-log chunks:
`b2da1da8f2217a02e888952bb376170306ea80dd40ab564bf13ee27553b2969a`.
Pilot object digest:
`1c11adc7b687fc608562456938c115a9878bc5394fc16a9c25a254956aae4a0b`.

A separate reviewer independently fetched the successful original job log,
reconstructed the payload, matched it to the committed bundle, replayed all six
episodes and 54 controls, recomputed all summary rows and inspected every raw
response/token record. This is recorded-decision and accounting verification;
the reviewer did not rerun the model weights. No cold independent inference or
broad real-agent scientific validation is claimed.

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m deviation_llm_agents.pilot \
  --verify artifacts/llm_agents/real_pilot.json --out /tmp/real-pilot-replay.json
cmp artifacts/llm_agents/real_pilot_replay.json /tmp/real-pilot-replay.json
PYTHONPATH=src python3 scripts/summarize_llm_pilot.py \
  artifacts/llm_agents/real_pilot.json --out /tmp/real-pilot-summary
cmp artifacts/llm_agents/real_pilot_summary.json /tmp/real-pilot-summary/real_pilot_summary.json
cmp artifacts/llm_agents/real_pilot_summary.csv /tmp/real-pilot-summary/real_pilot_summary.csv
```

Final CI replays committed decisions without further inference. All changes stay
on PR #24. No final holdout, paid service, shared contract, merge or release.
