# Bounded DEVIATION research harness

Issue [#26](https://github.com/almajna/deviation-lab/issues/26). Additive package `deviation_research`, stacked on #25/#23. Existing approved engines, source-bound certificates, dataset rules, simulation event schemas and final cohort are unchanged.

This is executable deterministic research orchestration over reviewed templates. It does not contain a live LLM scientist, unrestricted code generator, semantic novelty oracle or a guarantee of discovery. No inference is required. New methods require an adapter, scientific review and sandbox tests; a paper or repository discovered online is never executed.

## Run

Python 3.11+, the existing local package, and an OS sandbox are required. Linux needs `bubblewrap` with working unprivileged user namespaces (CI uses Ubuntu 22.04). macOS supports `sandbox-exec` where the host permits it. Sandboxing failure stops each job and retains the failure; there is no unsafe fallback.

```sh
python -m pip install --no-deps .
python -I -m deviation_research scout --out /tmp/scout.json
python -I -m deviation_research cycle --memory /tmp/research-memory.sqlite --out /tmp/research-cycle
python -I -m deviation_research reproduce --evidence /tmp/research-cycle --out /tmp/research-reproduced
python -I -m deviation_research export --memory /tmp/research-memory.sqlite --out /tmp/research-events.jsonl
DEVIATION_REQUIRE_SANDBOX=1 python -m unittest discover -s tests -p 'test_research*.py' -v
```

Reuse the memory path for later sessions. Successful, negative, failed and interrupted reservations all prevent silent retries. Reproduction deliberately uses a fresh memory. Never edit an executed plan to make it pass; retain the original and preregister a materially different question. An interrupted `running` record is intentionally not retried automatically; inspect its event history first. This process runs when invoked; it is not an always-on background agent.

## Research stages

| Stage | Executable behavior | Boundary |
|---|---|---|
| Scout | Three topic queries across arXiv Atom, Semantic Scholar Graph, Crossref proceedings and GitHub repository search | At most 12 requests, five seconds per request, 65 seconds total, 600 KB per response; failures/rate limits saved |
| Gap finder | Rank three authored, different questions on five declared 1–5 dimensions; explicit prior-art overlap and repository capability gaps | Scores are heuristic judgments, not novelty probabilities; search hits do not establish absence of prior art |
| Designer | Validate falsifiable criteria, baselines, information boundaries and seeds; freeze plan/source/code hashes before execution | Synthetic development only, no assumption changes, no data-path or arbitrary-code input |
| Engineer | Fixed adapters for published LMSR mathematics, fees, bounds, correlated forecast errors | No source downloads, generated submissions, model calls or held-out data mounted |
| Reviewer | Separate sandbox process, analytic replay, Agent 2 certificate checker and executable witness verification | Shared engine remains trusted; automated gates are not independent scientific peer review |
| Memory | Transactional SQLite reservations plus hash-chained append-only events and JSONL export | Durable when the database is retained; hashes are integrity checks, not identity signatures |
| Orchestrator | Preregister, rank, reserve, execute, retain all outputs, review and reject | Four jobs, 240-second cycle wall budget; later invocation skips previously reserved ideas |

Online results are discovery candidates. The checked-in source registry records bibliography identity, verification URL/date/method and identity digest from actual primary-source reads. It stores metadata and original notes, not redistributed papers. Identity digests detect accidental substitution; they cannot establish the authenticity or correctness of a source or prevent a malicious editor from rehashing a forgery. Discovered sources require primary-source reading before they can support a plan. The MVP's experiments use the explicitly reviewed source snapshot, so rate limits or search outages cannot silently alter the scientific plan.

## Architecture references and prior art

AI Scientist-v2: [paper](https://arxiv.org/abs/2504.08066), [code](https://github.com/SakanaAI/AI-Scientist-v2). Adapt hypothesis/experiment/review staging and bounded exploration; replace unrestricted code generation/inference with allowlisted deterministic adapters.

PaperBench: [paper](https://arxiv.org/abs/2504.01848), [OpenAI](https://openai.com/index/paperbench/), [code](https://github.com/openai/frontier-evals/tree/main/project/paperbench). Adapt explicit replication rubrics and separate execution/reproduction/grading. No PaperBench tasks, copyrighted source trees, API judges or PaperBench scores are used.

`research/sources.json` gives real citations for LMSR, decision-market incentives, neural-verification bounds, simple forecast aggregation and recent LLM-market work. Those settings are not interchangeable. LMSR cost-function mathematics is reproduced; beta-CROWN/SDP-CROWN and decision-market incentive mechanisms are only prior-art references. Existing DEVIATION #25 already finds negative overall speed results; this harness does not turn them into a breakthrough.

## Preregistered first cycle

`research/plan.json` fixes all questions, seeds 13/29/47, success/failure rules and baselines before running. The published baseline evaluates 243 combinations of liquidity, three-coordinate inventory and unit buys. A 70-digit Decimal implementation of `C(q)=b log(sum exp(q_k/b))` is compared with the engine's independently implemented dyadic signed-ceiling charges and subsidy. Numerical samples check the `b log(3)` worst-loss expression; the mathematical inequality follows `C(q) >= max(q)`, and finite sampling is not a proof for all inputs. This is a meaningful standard-method reproduction, not an entire empirical paper replication.

The three questions are fee sensitivity of outside-incentive attacks (18 cases), endpoint-bound ablation (12 cases), and market versus pooling under shared/independent belief perturbations (36 matched mechanism runs). Exact enumeration, memoized DP, beam, signal-following/no-action controls and non-market allocators apply where meaningful. Three seeds and two synthetic decision tasks do not support population inference. Fee changes also affect the honest prefix, so this is a generator-level comparison rather than an isolated causal effect on a frozen game. Correlation varies prescribed forecast-error perturbations, not measured human/LLM private information.

## Isolation and resource accounting

Every experiment and review runs in a fresh directory with only the two Python packages and explicit JSON input. The dataset directory, git checkout, host user files and source downloads are absent. Linux bubblewrap unshares network, process and mount namespaces; only system runtimes and the staged source are read-only mounted, with one writable output directory. macOS Seatbelt denies network and all file access except runtime/staged reads and output writes. Clean environments remove API keys. CPU 25 seconds, worker wall 35 seconds, file 2 MB, JSON output 1 MB, descriptor and core-dump caps apply. Linux address space is capped at 768 MB; macOS has no equivalent enforced address-space cap here and reports that limitation. The parent checks the remaining cycle budget before each worker and kills the worker process group on timeout. Logs and JSON remain bounded. These are practical OS controls, not a microVM or proof against kernel vulnerabilities.

The parent needs access to its selected plan, source registry, memory and output directory. It has no arbitrary experiment-path parameter and never reads the final holdout. CI network access is confined to the scout; workers have none. Dependency installation uses existing standard-library code; `bubblewrap` is infrastructure only. GitHub Actions is scoped to this public repository, read-only permissions and a 12-minute job. Do not use this workflow in a billed/private environment without checking the spending constraint.

## Events for a future frontend

Research events have their own version `research-events-1`; simulation contracts are unchanged. Every JSONL event contains monotone `seq`, `kind`, `entity`, `parents`, `payload`, `previous_sha256` and canonical `sha256`. Links connect source IDs → hypothesis hash → frozen plan hash → experiment key → result hash → review/rejection. Logical ordering is deterministic; wall-time resources are separate artifacts. The frontend must display `SYNTHETIC`, `NOT_ESTABLISHED` novelty and pending scientific review, and must preserve negative and failure records. No UI integration is included.

## Verification and current limits

CI executes OS canary isolation (outside-file read/write and internet blocked), forged-result rejection, plan/citation/assumption tampering, failed-job retention and duplicate suppression. It reproduces every result, review and event in a fresh process. Historical source-bound experiments remain verified by the inherited workflows. Unit tests and numerical gates are author evidence; independent scientific review remains required and must report its actual status.

Full-text semantic reading, open-ended idea invention, arbitrary public-code reproduction, optimized literature retrieval and a live scientist model are future work requiring a suitable free backend and further sandbox/claims review. The MVP offers a safe extensible execution/memory boundary and honest small experiments, not automatic breakthrough certification.
