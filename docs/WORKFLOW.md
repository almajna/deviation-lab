# Codex + Claude Code coordination manual

## Roles and file ownership
- **Integrator (Codex)**: architecture, docs contracts, CI, PR triage, merge plans, final release. Owns `docs/CONTRACTS.md` and `docs/STATUS.md`; coordinates any shared-interface edit.
- **Research/data worker (Codex)**: `src/deviation/data/`, `src/deviation/evaluation/`, `data/` manifests and experiment scripts.
- **Markets/attack worker (Claude Code)**: `src/deviation/markets/`, `src/deviation/attacks/` and focused tests.
- **Frontend worker (Claude Code)**: `apps/web/`, visual tests, generated web assets; consumed schemas are read-only until approved.
- **Independent reviewer (fresh session/model)**: audit and reproduce from a clean checkout; does not silently fix the feature it is auditing.

## Coordination protocol
1. Integrator decomposes scope into GitHub issues with owner, branch name, dependencies, acceptance tests and affected files.
2. One agent per branch/worktree. Example after bootstrap merge:
   `git worktree add -b feat/data-audit ../deviation-data main`
   `git worktree add -b feat/web-arena ../deviation-web main`
3. Builders read `AGENTS.md` + assigned issue and prompt, then work only in owned paths. No agent should edit from another agent's worktree.
4. Every PR contains test log, evidence and limitations. CI must pass; reviewer challenges scientific assumptions. The human owner merges one at a time after exact-head approval; the integrator verifies the merge and rechecks dependent branches. Agents never merge, enable auto-merge or bypass review.
5. All shared data changes are PRs with a schema version bump and fixtures. Frontend uses fixture traces to avoid blocking, later replaces them with generated experiment traces.
6. `docs/STATUS.md` tracks only verified work; “I will do X” is not “X is done.”

## Running without constant supervision
Long-running coding sessions do not automatically coordinate themselves. If sessions are offline, stopped, throttled or lack GitHub permission, prompts cannot magically continue work. Keep active agent sessions, issue/PR records, CI, and notifications. Start with 2 implementation sessions plus integrator, not an uncontrolled swarm.

## Permissions boundaries
Default: code changes and local tests only; branch/PR creation allowed if authenticated and user approved. No direct main pushes, final merges, payments, GitHub settings changes, hosted publishing, external outreach or disclosure of private information without user approval. GitHub write access is not implied by screenshot/public URL.

Development agents do not invoke merge endpoints, enable merge queues/auto-merge, dismiss required reviews or add themselves/apps to bypass lists. CI retains read-only repository permissions. Scientific or contract approval must identify the exact current head; new substantive commits require re-review. A merged PR without recorded approval is not a scientific gate. See `MERGE_GOVERNANCE.md` for the read-only investigation and proposed repository protections, which are not yet applied.

## Human review gates
- Gate A: dataset and information-set scientific validity.
- Gate B: mechanism utility and settlement spec.
- Gate C: verified exploit and economic interpretation.
- Gate D: held-out research results and claims.
- Gate E: visual and final public release.

## Recommended PR template section headings
Problem, Files changed, Assumptions, Tests run, Example artifact, Known limitations, Scientific impact, Contract changes?, Cost incurred?, Human decisions needed?

## GitHub protection
Require CI, PR-based changes and no force pushes to main where available. Beware that one account can technically bypass some settings; a second independent reviewer is a process rule rather than a GitHub identity magically supplied by an LLM.
