# LiteLLM reality test — frozen v1

Issue [#38](https://github.com/almajna/deviation-lab/issues/38). Follow-up to #37;
no previous experiment or evidence is changed. The executable configuration is
`experiments/litellm_reality_v1.json`. Commit this protocol before outcome runs.

Hypothesis: an enrolled provider can increase future allocation in LiteLLM's
nonstream latency strategy by changing only completion-token metadata, with
internally consistent total tokens. Falsifier: the actual parser/callback/selector
does not propagate this control, or the frozen primary comparisons show no gain.

Use unmodified source at `44b85d0c5c3093543b1f911c6808836f16dd3a58` and its frozen
dependency lock. Exercise the public `Router.acompletion` interface over real
loopback HTTP. Never replace the parser, routing code, cache, clock or callbacks
with a reimplementation. A controlled server provides realistic OpenAI-shaped JSON
and SSE fixtures; it is not a real LLM or a production traffic dataset. Both
providers return identical visible content, at configured 100/300 ms delays.
Actual client elapsed times and callback timestamps are measured, not invented.

Provider B may alter its own completion count by 8x and recompute total tokens.
It cannot change competitors, client clocks, router settings or history. The
defended condition is a trusted HTTP gateway that recomputes visible output tokens
with the declared tokenizer before the genuine client parser. It logs both raw and
forwarded usage. This assumes known tokenization and no hidden reasoning; it is
not a general hidden-token audit. Prompt usage is fixed and consistently declared.

One fresh process/cache per condition/mode/seed; pair Python RNG seeds. Preserve
the default ten-observation history, buffer, random sampling/choice and unused-arm
exploration. Do not manually seed latency samples. Four ordinary routed warmup
requests precede twenty measured requests. Wait for genuine callback completion.
Capture selected provider from actual endpoint requests and returned response IDs,
plus callback/cache observations for causal tracing.

Primary matrix: honest/inflated/defended x latency/default simple-shuffle/warm
streaming x three fixed seeds. Diagnostic matrix: all three conditions at seed 7
with B's TPM=1000, RPM=5, a 429 on B's second request, or streaming only after
nonstream warmup. High limits remain configured in primary cases. TPM includes
inflated total usage; quota windows use the actual clock. Cooldown filtering stays
enabled, configured for 30 seconds. No retries/fallbacks conceal errors. A 429
must travel through the real failure/cooldown path. Cold streaming is diagnostic:
without TTFT history it can fall back to normalized latency.

Freeze 39 cases/936 scheduled calls; at most 1100 provider requests and 720 seconds
per complete run, 45 seconds per case. One author run and one independent rerun.
At most three engineering attempts to repair demonstrable harness/setup defects;
retain every failure and never alter fixtures, thresholds or findings to obtain
PASS. Network namespace isolates execution; dependency installation occurs before
isolation. Standard public CPU runners only, no credentials or paid inference.

PASS for the controlled routing channel requires source fidelity, complete case
coverage, B's inflated-minus-honest measured allocation share >=0.50 in all three
primary latency seeds, and defended/default-shuffle/warm-stream differences <=0.10
in each paired seed. Require actual quota/cooldown evidence and preserved defaults;
missing or contradictory safeguards block PASS. FAIL applies to a valid completed
test that falsifies the claimed routing effect. Incomplete execution, uncontrolled
timing, missing controls or verification failure is INCONCLUSIVE. Report secondary
controls that fail separately rather than rewriting the hypothesis.

Report per-case provider counts, paired allocation differences, end-to-end latency,
TTFT, errors, quota usage and content equality. Client slowdown and inflated usage
are separate metrics. No invoices, provider costs or profits are observed; no
profit or deployment-exploit claim is permitted. Seeds describe these controlled
runs, not population-level uncertainty; use no significance claims from 20 related
requests. Independent reviewer replays receipts, recomputes allocation counts and
usage/quotas, verifies callback-to-history arithmetic and repeats actual routing.

The independent source review found the control path reachable before execution.
Stop if runtime inspection contradicts that path. No broad literature campaign,
new economic framework, frontend, holdout access, merge or live third-party attack.
