# Results and evidence index

This index distinguishes evidence by origin. Results are scoped to their frozen protocols; publication here does not mean they generalize to deployment. Archived historical reports may describe the state of an earlier PR rather than current main.

| Category | Result and primary evidence | What it does not establish |
| --- | --- | --- |
| Genuine open-weight inference | [24-call Qwen2.5-7B game](AUTONOMOUS_ECONOMY.md): 24 valid reports, 0/6 profitable manipulations; [recorded receipt](../artifacts/llm_agents/autonomous_pool.json.gz). [Earlier 0.5B pilot](LLM_AGENT_PILOT_REPORT.md): 22/24 invalid actions. | General LLM behavior or real-world economic manipulation. |
| Controlled HTTP fixtures | [LiteLLM protocol](LITELLM_REALITY_PROTOCOL.md), [PR #39](https://github.com/almajna/deviation-lab/pull/39), and [preserved receipt provenance](../artifacts/litellm-reality/README.md). Verdict **INCONCLUSIVE**. | Real provider behavior, invoices, profit, prevalence, or production exploitation. |
| Synthetic experiments | [Adversarial lab](ADVERSARIAL_LAB.md) and [Phase 5 synthetic generalization](PHASE_5_RESULTS.md). Negative and null outcomes remain reported. | Evidence of real agents or real market outcomes. |
| Certified mathematical results | [Independent certificate evaluation](../artifacts/verification/REPORT.md), [proof manifest](../artifacts/verification/proof_manifest.json), and [checker semantics](INDEPENDENT_CERTIFICATE_CHECKER.md). 81 checked; 78 zero-gap; frozen speed criterion failed. | A universal theorem or independence from the shared engine and numeric routines. |
| Recorded outcomes + synthetic forecasts | [Exploratory benchmark](PHASE_5_RESULTS.md) and [data audit](DATA_AUDIT.md). No demonstrated market advantage in the tested configuration. | Live savings or a final held-out evaluation. |

## LiteLLM controlled HTTP study

Two attempts of [Actions run 41944311832](https://github.com/almajna/deviation-lab/actions/runs/41944311832), each with 39 cases and 936 scheduled requests, exercised LiteLLM commit `44b85d0c5c3093543b1f911c6808836f16dd3a58` against controlled loopback providers. The first execution's inflated-minus-honest B allocation gains were 0, 0 and +100 percentage points for seeds 7, 11 and 23. The independent rerun produced +65, +65 and +100 points, but one streaming comparative control differed by 100 points. The protocol required at least +50 points in every primary seed and at most 10 points difference in every paired control. Therefore the joint scientific verdict is **INCONCLUSIVE**, not PASS.

The nonstream recounting gateway matched honest allocation in the tested seeds, under the assumption of known tokenization and visible output. Shuffle matched across conditions. The cooldown receipts show a 429 and subsequent routing but do not directly observe cache expiry or re-entry. Only 27/39 provider sequences matched across attempts; timing and history affect interpretation. The [PR closeout](https://github.com/almajna/deviation-lab/pull/39) details quotas, safeguards and results.
