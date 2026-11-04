# Bounded DEVIATION research harness

For the historical sample after main's backend integration, run `python -I -m deviation_research_replay --out /tmp/research-reproduction --verify artifacts/research/rebase/manifest.json`. See [RESEARCH_HARNESS_REBASE.md](RESEARCH_HARNESS_REBASE.md). Direct `deviation_research reproduce` still strictly reproduces freshly generated current-source cycles; it deliberately rejects the historical sample under a different package fingerprint.

Issue [#26](https://github.com/almajna/deviation-lab/issues/26). Additive package `deviation_research`, stacked on #25/#23. Existing approved engines, source-bound certificates, dataset rules, simulation event schemas and final cohort are unchanged.

This is executable deterministic research orchestration over reviewed templates. It does not contain a live LLM scientist, unrestricted code generator, semantic novelty oracle or a guarantee of discovery. No inference is required. New methods require an adapter, scientific review and sandbox tests; a paper or repository discovered online is never executed.

## Run

Python 3.11+, the existing local package, and an OS sandbox are required. Linux needs `bubblewrap` with working unprivileged user namespaces (CI uses Ubuntu 22.04). macOS supports `sandbox-exec` where the host permits it. Sandboxing failure stops each job and retains the failure; there is no unsafe fallback.

```sh
python -m pip install --no-deps .
python -I -m deviation_research scout --out /tmp/scout.json
python -I -m deviation_research cycle --memory /tmp/research-memory.sqlite --out /tmp/research-cycle
python -I -m deviation_research cycle --online --memory /tmp/research-memory.sqlite --out /tmp/next-research-cycle
python -I -m deviation_research reproduce --evidence /tmp/research-cycle --out /tmp/research-reproduced
python -I -m deviation_research export --memory /tmp/research-memory.sqlite --out /tmp/research-events.jsonl
python -I -m deviation_research inspect --memory /tmp/research-memory.sqlite
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

Online results are discovery candidates. `cycle --online` runs the bounded scout, persists all request receipts and candidate events, and then ranks/executes the reviewed plans. The default cycle imports the actual captured `research/scout.json`; `--scout-receipt` imports another bounded capture. Reproduction reuses the original capture and frozen full plan/registry, including custom inputs. The checked-in source registry records bibliography identity, verification URL/date/method and identity digest from actual primary-source reads. It stores metadata and original notes, not redistributed papers. Identity digests detect accidental substitution; they cannot establish the authenticity or correctness of a source or prevent a malicious editor from rehashing a forgery. Discovered sources require primary-source reading before they can support a plan. The MVP's experiments use the explicitly reviewed source snapshot, so rate limits or search outages cannot silently alter the scientific plan. A process timer bounds DNS/streaming as well as socket operations. This POSIX scout is a main-thread command.

## Architecture references and prior art

AI Scientist-v2: [paper](https://arxiv.org/abs/2504.08066), [code](https://github.com/SakanaAI/AI-Scientist-v2). Adapt hypothesis/experiment/review staging and bounded exploration; replace unrestricted code generation/inference with allowlisted deterministic adapters.

PaperBench: [paper](https://arxiv.org/abs/2504.01848), [OpenAI](https://openai.com/index/paperbench/), [code](https://github.com/openai/frontier-evals/tree/main/project/paperbench). Adapt explicit replication rubrics and separate execution/reproduction/grading. No PaperBench tasks, copyrighted source trees, API judges or PaperBench scores are used.

`research/sources.json` gives real citations for LMSR, decision-market incentives, neural-verification bounds, simple forecast aggregation and recent LLM-market work. Those settings are not interchangeable. LMSR cost-function mathematics is reproduced; beta-CROWN/SDP-CROWN and decision-market incentive mechanisms are only prior-art references. Existing DEVIATION #25 already finds negative overall speed results; this harness does not turn them into a breakthrough.

## Preregistered first cycle

`research/plan.json` fixes all questions, seeds 13/29/47, success/failure rules and baselines before running. The published baseline evaluates 243 combinations of liquidity, three-coordinate inventory and unit buys. A 70-digit Decimal implementation of `C(q)=b log(sum exp(q_k/b))` is compared with the engine's independently implemented dyadic signed-ceiling charges and subsidy. Numerical samples check the `b log(3)` worst-loss expression; the mathematical inequality follows `C(q) >= max(q)`, and finite sampling is not a proof for all inputs. This is a meaningful standard-method reproduction, not an entire empirical paper replication.

Independent review correctly identified that signed-ceiling unit-buy charges all equal one, limiting that original grid's conformance value. The original 243 cells/criteria remain intact. A separately preregistered `signed-lmsr-diagnostic-1` supplement adds 21 transitions with inventories, multi-share buys/sales, permutations and common translations over three liquidities. Its own criterion checks unrounded potential differences, positive/zero/negative signed-ceiling charges and agreement with certified dyadic intervals. Its status is reported separately, never relabeled as part of the earlier preregistration.

The three questions are fee sensitivity of outside-incentive attacks (18 cases), endpoint-bound ablation (12 cases), and market versus pooling under shared/independent belief perturbations (36 matched mechanism runs). Exact enumeration, memoized DP, beam, signal-following/no-action controls and non-market allocators apply where meaningful. Three seeds and two synthetic decision tasks do not support population inference. Fee changes also affect the honest prefix, so this is a generator-level comparison rather than an isolated causal effect on a frozen game. Correlation varies prescribed forecast-error perturbations, not measured human/LLM private information.

The unmodified market schedule can leave no final controlled suffix for some fee seeds. Such declared cells are attempted, independently confirmed and retained as `UNSUPPORTED_NO_CONTROLLED_TERMINAL_SUFFIX`. They are not replaced by favorable seeds or a changed schedule. An increasing fee/gain pair already falsifies a universal monotonicity condition, so it is `REJECTED_ON_EVALUATED_CELLS` with `PARTIAL_UNSUPPORTED_CASES` coverage. Missing cases cannot hide an observed counterexample. `NOT_EVALUABLE_ON_REGISTERED_GRID` applies only when missing cells prevent deciding the criterion and no decisive observed counterexample exists. Exploratory nulls and unsupported cases are normal research outputs; an invalid numeric receipt, failed worker or missing declared cell remains a CI failure.

## Isolation and resource accounting

Every experiment and review runs in a fresh directory with only the two Python packages and explicit JSON input. The dataset directory, git checkout, host user files and source downloads are absent. Linux bubblewrap unshares network, process and mount namespaces; only system runtimes and the staged source are read-only mounted, with one writable output directory. macOS Seatbelt denies network and all file access except runtime/staged reads and output writes. Clean environments remove API keys. CPU 25 seconds, worker wall 35 seconds, file 2 MB, JSON output 1 MB, descriptor and core-dump caps apply. Linux address space is capped at 768 MB; macOS has no equivalent enforced address-space cap here and reports that limitation. The parent checks the remaining cycle budget before each worker and kills the worker process group on timeout. Logs and JSON remain bounded. These are practical OS controls, not a microVM or proof against kernel vulnerabilities.

The parent needs access to its selected plan, source registry, memory and output directory. It has no arbitrary experiment-path parameter and never reads the final holdout. CI network access is confined to the scout; workers have none. Dependency installation uses existing standard-library code; `bubblewrap` is infrastructure only. GitHub Actions is scoped to this public repository, read-only permissions and a 12-minute job. Do not use this workflow in a billed/private environment without checking the spending constraint.

## Events for a future frontend

Research events have their own version `research-events-1`; simulation contracts are unchanged. Every JSONL event contains monotone `seq`, `kind`, `entity`, `parents`, `payload`, `previous_sha256` and canonical `sha256`. Links connect source IDs → hypothesis hash → frozen plan hash → experiment key → result hash → review/rejection. Logical ordering is deterministic; wall-time resources are separate artifacts. The frontend must display `SYNTHETIC`, `NOT_ESTABLISHED` novelty and pending scientific review, and must preserve negative and failure records. No UI integration is included.

## Verification and current limits

CI executes OS canary isolation (outside-file read/write and internet blocked), forged-result rejection, plan/citation/assumption tampering, failed-job retention and duplicate suppression. It reproduces every result, review and event in a fresh process. Historical source-bound experiments remain verified by the inherited workflows. Unit tests and numerical gates are author evidence; independent scientific review remains required and must report its actual status.

Full-text semantic reading, open-ended idea invention, arbitrary public-code reproduction, optimized literature retrieval and a live scientist model are future work requiring a suitable free backend and further sandbox/claims review. The MVP offers a safe extensible execution/memory boundary and honest small experiments, not automatic breakthrough certification.

Resource receipts distinguish actual worker self-reported CPU/peak RSS from the parent's reaped-supervisor CPU counter: the bubblewrap supervisor counter alone is not a reliable measure of descendant compute. Python exceptions retain worker usage through an exit hook. Hard-killed workers may have no worker usage record; receipts leave those measurements null while retaining elapsed wall time, limits, exit/timeout status and bounded logs.

## Retained initial execution

Plan/code were published prospectively at `ce59d6d4074f93b51ed27207144343594d68650d`. [Initial CI run](https://github.com/almajna/deviation-lab/actions/runs/41693085210) passed isolation and the 243-cell LMSR baseline but exposed adapter schema errors in the three direction jobs. `artifacts/research/initial/` retains the actual summary and a bounded base64-encoded gzip-tar capture of results/failures/network receipts. Correcting numeric-payoff/allocation encoding and reservation/evaluation field names does not change the frozen seeds, hypotheses or criteria. The explicit fresh execution after these fixes is an infrastructure retry, not hidden favorable-result selection. Semantic execution identity now ignores titles, rankings and survey prose. Automated support attaches only to the machine-readable criterion; arbitrary narrative claims still require scientific review.
