# Persistent project instructions — all coding agents

Read, in order: `START_HERE.md`, `docs/MASTER_PLAN.md`, `docs/SPEC.md`, `docs/RESEARCH.md`, `docs/CONTRACTS.md`, `docs/ACCEPTANCE.md`, `docs/WORKFLOW.md`, `docs/STATUS.md`.

## Mission
Build DEVIATION, an adversarial benchmark for resource-allocation mechanisms in AI systems, and a remarkable **evidence-driven** interactive replay laboratory. Favor a narrow, rigorous, beautiful finished artifact over an expansive unfinished platform.

## Non-negotiable rules

1. **Zero paid spend** by default. No paid API, hosted GPU, domain, or service without explicit user approval. Do not assume subscriptions include programmatic APIs.
2. No model training or real-time LLM swarms are required. Cache/reuse public evaluated outcomes. Keep synthetic data visibly labeled.
3. Never conflate recorded outputs, synthetic private signals, real autonomous LLM agents, and actual deployment forecasts.
4. Never access answer labels, post-outcome information, or future market events during allocation/forecast formation. Audit the information boundary.
5. Implement agent utility, transfers, market-maker losses, cost budgets, and counterfactual visibility explicitly. Avoid calling a mechanism truthful or incentive-compatible without supporting proof under stated assumptions.
6. Deterministic experiment config + versioned event logs + seeds; replay must reproduce outputs bit-for-bit where practicable.
7. Evaluation must include meaningful non-market baselines and frozen held-out tasks. Do not optimize against the final test split.
8. Do not invent results, citations, downloads, performance numbers, screenshots, or agent execution statuses.
9. Never overwrite the existing MIT license or README without explaining/obtaining review. Review third-party dataset licenses separately.
10. Do not push to `main`, merge PRs, change GitHub visibility, publish public claims, or incur monetary charges without authorization.
11. Do not execute AI-generated code, untrusted benchmark solutions, or user submissions outside an appropriate sandbox.
12. Keep heavyweight data and secrets out of Git. Prefer public reproducible download manifests.

## Delivery contract
Every PR must provide: issue link, scope, file ownership, test commands/results, limitations, sample output artifact if applicable, and proposed next action. Failing CI = incomplete. A 'done' message without independent evidence is not proof.

## Collaboration
Codex integrator is the default owner of shared contracts and integration. Separate branches/worktrees for research, market/attack engineering, and visuals. Do not silently change shared contracts. Independent reviewer must challenge design/results and avoid authoring the same feature before review. Follow `docs/WORKFLOW.md`.

## Escalate to human
Research assumption changes, privacy/security risks, dataset restrictions, external spending, benchmark changes after freezing, and release approval. Routine local reversible decisions should be made by the agent and logged in `docs/DECISIONS.md`.

## First gate
Do not begin the market, attack, or visual backend integration until `docs/DATA_AUDIT.md` shows actual schema and pair coverage (or a documented fallback) and `docs/CONTRACTS.md` is approved.
