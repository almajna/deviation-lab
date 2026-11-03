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
