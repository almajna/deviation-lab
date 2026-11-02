# Scientific Gate A and contract approval

## Approval already received

On 2026-11-02 the owner accepted Phase 1 for limited exploratory engineering and approved the five assumptions in `RESEARCH.md`: noisy preference proxy quality, reported retrospective costs, train-only reservations with separate realized accounting, exploratory-only 247-task scope, and synthetic economic agents with sealed outcomes. Do not request those assumptions again. Historical Phase 1 artifacts remain unchanged; they are not final empirical qualification.

## This PR requires approval

Tracking issue: [#5](https://github.com/almajna/deviation-lab/issues/5). Independent engineering review and reproduction evidence: `GATE_A_REVIEW.md`.

Approve or request changes to **the exact current head** of the dedicated `codex/gate-a-contracts` PR: v0.2 interfaces, fixed train-only mean reservations/excluded fit groups, closed information/history rules, cost-versus-credit accounting, payoff receipts and explicit v0.1 migration. Synthetic tests are conformance evidence, not mechanism results or proof of incentive compatibility. The owner explicitly approves the head after independent review/passing CI; a human then merges. New substantive commits require renewed review.

The branch also contains a concrete **unapplied** main-protection proposal. Applying repository settings is separate from merging source files. Identify an independently authenticated GitHub reviewer with appropriate repository permissions first; one required approval otherwise blocks the owner's own PRs. Do not create accounts, invite collaborators, add bypass actors or change settings without that decision.

## Activation checklist — no self-approval

- Independent review linked to current head; no unresolved blockers.
- Full existing/contract tests and GitHub CI pass for that head.
- Explicit owner approval of that v0.2 head, not merely research assumptions or an unrelated merge.
- Human merge verified; approved commit is an ancestor of synchronized main.
- Only then create separate Phase 2/Phase 6 worktrees and dispatch `IMPLEMENTATION_HANDOFF.md`.

Until these conditions hold: no Phase 2 simulator, Phase 6 UI, market/attack integration or final evaluation. A conformance module/fixture does not complete an implementation milestone. A merged PR alone does not establish scientific approval. Agents never merge, enable auto-merge or bypass review.

## Remaining limits

Noisy proxy/lost judge-status details, retrospective costs, complete-case/source concentration and small sample remain limitations. Reservation feasibility is simulated, not a deployment guarantee. Synthetic utilities are modeled preferences, not observed economics. Gate B approves actual mechanism settlement math; Gate D approves frozen evaluation; release is separately gated. This approval permits engineering under limitations, not superiority claims. Spend remains $0.
