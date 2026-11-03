# Independent Agent 3 engineering review

A separate read-only reviewer did not author this feature. It challenged the
locally committed protocol before the first campaign and inspected actual code,
ran tests, tried adversarial audit mutations, built a wheel and executed the
installed package. This is an independent agent engineering review, not human
scientific approval or verification of real model behavior.

Protocol findings addressed before evaluation: separate truthful-instruction
capability from utility maximization; matched setting IDs and expected net
utility/no-action comparisons; trusted-local-server versus loopback/cloud
distinction; attempted versus skipped calls and unknown usage; preserve the
synthetic engine contract separately from actor provenance.

Actual-code findings fixed with regressions:

- High: rehashed false provenance and budget totals passed replay. Replay now
  recomputes record origins, attempted/skipped decisions, byte counters, usage,
  valid decision counts, metrics and receipt linkage.
- Medium: malformed usage envelopes could escape without a record. They now
  remain failed attempts with raw response and unknown usage.
- Medium: NaN server usage could fail during hashing after inference. Strict
  finite JSON and canonical usage checks retain a failed attempt safely.
- Bounded-context limitation: requests could exceed server context. The default
  and maximum supported serialized prompt ceiling is now 8192 bytes; larger
  inputs are refused before dispatch.

Reviewer independently passed 19 focused / 159 total tests at code commit
`f72ece1` and source hash
`301add6d7f5b901203fd68123a6e05812716b45bff5b092456409d535f74c7fd`.
It built and installed an offline wheel using a local setuptools wheel, then
ran the isolated installed campaign. All 324 rows matched the original run
despite audit-hardening changes. Shared package/contract and historical files
were checked unchanged. Final evidence fixture reproduction tests are additional
checks added after that review and do not change the reviewed source hash.

Disposition: **engineering APPROVE subject to final artifact reproduction and
green hosted CI; scientific real-agent validation BLOCKED**. Zero actual local
model decisions or live-local server integration were verified. Hosted CI and
the final artifact comparison must be reported from observed runs, not assumed.

## PR #24 resumption and actual pilot review

Agent 4 independently found a missed attribution bug: the original trade count
included other scripted actors. The correction filters the focal actor and
adds a separately scoped system total/controller identity. Regressions cover
both actor identities and a valid voluntary-no-op focal policy with two control
trades. The reviewer independently reproduced 0 focal / 2 system trades.

Before inference, the reviewer challenged and approved the six-episode CPU
protocol, public/free runner guard, pinned model/runtime/weight/license, no
repair/retry rule, token evidence and strict call cap. Review additionally found
unrecorded RuntimeError paths and protocol validation after model construction;
both were fixed before dispatch, with regression coverage. Model identity and
token-count evidence checks were added to pilot verification before execution.
Frozen source `b4df995829657b2d488b3f0b9577b07b1cdb81ba998359f7bdaf539a3ca362d1`
and protocol were published at `fe90b89` before workflow-only `1bcd83f` executed.
All 165 pre-pilot tests passed independently, and both hosted CI checks were green.

After successful actual run 41666251738/job 126022255193, the reviewer separately
retrieved its original log, decoded all 12 payload chunks, verified canonical
SHA256 `b2da1da8f2217a02e888952bb376170306ea80dd40ab564bf13ee27553b2969a`
and matched the payload to `real_pilot.json`. All six recorded episodes and 54
scripted controls independently replayed; all six summary rows and individual
raw responses/token records were checked. Observed totals: 24 completed real
calls, 45,874 prompt/609 output tokens, 22 invalid action schemas, two valid
chosen no-ops, zero accepted reports/trades/skips, all EOS rather than truncation.

Review corrected an early interpretation that raw utility outputs were always
identical between incentives: one b-high invalid response changes. The report
therefore makes no raw-output identity or general zero-sensitivity claim. The
intended economic question remains unresolved because report capability failed.
The reviewer did not rerun real inference; replay/source/log/accounting checks
are distinguished from independent cold inference or broad scientific validation.
