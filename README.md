# DEVIATION

**A research laboratory for resource allocation, strategic behavior, and evidence.** DEVIATION asks what happens when participants can influence how scarce AI resources are allocated—and how much of that behavior can be checked rather than assumed.

The repository combines a deterministic economic simulator, prediction-market and non-market mechanisms, finite attack search and certificate checking, and small experiments with real open-weight models. It also contains a controlled offline study of routing in a pinned version of LiteLLM. These are distinct kinds of evidence, not a single demonstration of deployment impact.

## Research questions

- How do reporting and market mechanisms allocate limited resources when participants have different information and incentives?
- When can a strategic participant improve its modeled utility or redirect an allocation, and can a finite search certify the bound?
- Can open-weight models select useful actions in a controlled economic game?
- Can provider-reported token counts change subsequent choices in the actual LiteLLM router under controlled conditions?

## Findings at a glance

| Evidence | Finding | Boundary |
| --- | --- | --- |
| [Open-weight agents](docs/AUTONOMOUS_ECONOMY.md) | In a 24-call Qwen2.5-7B experiment, all reports were valid but there were **0/6 profitable manipulations** by the frozen definition. | One small synthetic game; virtual credits. A separate [0.5B pilot](docs/LLM_AGENT_PILOT_REPORT.md) produced 22 invalid responses in 24 calls. |
| [LiteLLM controlled HTTP study](docs/LITELLM_REALITY_PROTOCOL.md) | **INCONCLUSIVE**. Provider token counts reach the latency score; both runs observed a seed-specific shift, but the frozen success criteria were not met. | Loopback fixtures, not real providers or model inference. [Results and evidence](docs/RESULTS.md#litellm-controlled-http-study). |
| [Finite certificates](artifacts/verification/REPORT.md) | All 81 synthetic development certificates were checked; 78 had zero gaps. The preregistered practical speed criterion failed. | Guarantees apply only to specified finite subgames and shared trusted dependencies. |
| [Exploratory benchmark](docs/PHASE_5_RESULTS.md) | No market advantage was demonstrated in the tested configuration. | Recorded outcomes were combined with synthetic forecasts; the final holdout was not evaluated. |

See the **[results index](docs/RESULTS.md)** for source links, controls, negative findings, and evidence categories. These results do not establish provider profit, production exploitation, general model behavior, or a scientific breakthrough.

## How it fits together

1. **Inputs and information boundaries:** authored synthetic scenarios or audited recorded outcomes; agent decisions cannot access sealed outcomes.
2. **Mechanisms:** allocation, scoring and LMSR-style markets track reservations, credits and settlement.
3. **Search and checking:** bounded adversarial search produces replayable witnesses and, for supported finite subgames, independently checked bounds.
4. **Experiments:** stored model receipts, controlled router fixtures and synthetic benchmarks remain separately labeled.

Start with [simulator](docs/SIMULATOR.md), [markets](docs/MARKETS.md), [adversarial lab](docs/ADVERSARIAL_LAB.md), and [certificate checker](docs/INDEPENDENT_CERTIFICATE_CHECKER.md). The initial planning documents are historical; [status](docs/STATUS.md) describes the present state. The original README remains available as [historical evidence](docs/history/README-8521252.md).

## Quickstart

Requires Python 3.11 or newer. The core runtime uses the standard library; no paid API or model download is needed for these checks.

```sh
git clone https://github.com/almajna/deviation-lab.git
cd deviation-lab
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m deviation demo --out /tmp/deviation-demo.json
```

The demo is synthetic. To replay actual recorded model decisions without new inference:

```sh
gzip -dc artifacts/llm_agents/autonomous_pool.json.gz > /tmp/autonomous-pool.json
PYTHONPATH=src python3 scripts/run_autonomous_economy.py --verify /tmp/autonomous-pool.json
python3 scripts/check_autonomous_economy.py /tmp/autonomous-pool.json
```

For LiteLLM receipt verification and the distinction between replaying receipts and rerunning the router, see [evidence instructions](artifacts/litellm-reality/README.md). Fresh inference and the full router experiment have additional pinned dependencies and resource requirements; they are not part of the quickstart.

## Limitations and use

Synthetic signals, virtual credits and authored outcomes are not real-world prices or forecasts. Historical quality and cost fields have data and licensing limitations described in [the audit](docs/DATA_AUDIT.md). Exact certificates do not prove general incentive compatibility. Model behavior can vary across hardware and runtimes, and a receipt replay does not regenerate an inference. The project remains a research artifact, not a validated production decision system. See [status](docs/STATUS.md) and the [release checklist](docs/RELEASE_CHECKLIST.md).

Code is released under the [MIT license](LICENSE); assess third-party datasets and models under their own terms.
