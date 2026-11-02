# Read-only merge investigation and enforcement proposal

Checked 2026-11-02. PRs [#3](https://github.com/almajna/deviation-lab/pull/3) and [#4](https://github.com/almajna/deviation-lab/pull/4) are merged and their commits are ancestors of synchronized main. Aggregate evidence: `artifacts/merge_governance_audit.json`.

## What the evidence establishes

| PR | Merge time UTC | Pacific | GitHub `merged_by` account | Merge commit |
|---|---|---|---|---|
| #3 | 2026-11-02 23:20:47 | 3:20:47 PM PST | `almajna` | `c9b4761c3416ee28cc80aa74f0301846b6d5b3af` |
| #4 | 2026-11-02 23:34:28 | 3:34:28 PM PST | `almajna` | `5b97cc7e7cc51f0194b1345fa0b4707e8be9c72d` |

Public REST PR metadata and both UI timelines agree on account attribution. Neither PR has a submitted GitHub review record through the connector. This does not negate the owner-reported external engineering reviews; it means those reviews were not enforced as GitHub approvals.

Current repository metadata says `allow_auto_merge=false`; both PRs have `auto_merge=null`. Main's branch endpoint says `protected=false`, required checks have enforcement `off` and no contexts. The settings UI lists no classic protection rule and says no rulesets have been created. The repository's only workflow runs tests with read-only contents permission and has no merge operation.

**Settings permit reviewless merges:** there is no enforced main review/CI barrier. This explains why an authorized account could merge those PRs without GitHub reviews. It does not identify the person, browser, token, client or other process using the `almajna` account. Available evidence does not reconstruct historical settings or prove a human click versus another authenticated client. No merge/auto-merge command was issued by this agent in this chat. Do not attribute intent or compromise without additional account audit evidence.

## Agent policy now recorded

`AGENTS.md` and `WORKFLOW.md` prohibit agent merge/auto-merge/merge-queue operations, main pushes, review dismissal and rule bypass. A human merges after independent review, passing CI and exact-head approval. Development authorization and a prior merge do not substitute for those approvals. CI retains read-only repository permission. These instructions govern cooperating agents; they do not revoke the owner's/app's GitHub permissions or technically stop an external client acting as the same account.

## Concrete proposal — not applied

`ops/github/main-ruleset.proposed.json` targets `refs/heads/main` with:

- active enforcement, empty bypass list (no administrator, account or app exemption);
- PR-only updates and one approving review, stale approval dismissal, last-push approval by another reviewer and conversation resolution;
- up-to-date passing `unit-smoke` check specifically from GitHub Actions app ID **15368** (verified on the current check run);
- no branch deletion or non-fast-forward pushes.

Keep repository auto-merge disabled; do not configure a merge queue. The proposal is based on the [GitHub ruleset API](https://docs.github.com/en/rest/repos/rules#create-a-repository-ruleset) and [protected branch behavior](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches). It is a reviewable payload, not an applied setting or tested enforcement claim.

**Owner decision needed before applying:** identify a separate authorized GitHub reviewer and approve the restrictions. GitHub author/last-pusher self-review is insufficient; another agent using the owner's identity is not a separate GitHub reviewer. No collaborator invitation or access change is made here. An administrator can still edit/remove protections; GitHub settings cannot establish which person controls a shared account. Keep a human-controlled merge credential/session separate from development automation for stronger separation.

After approval, a human applies the ruleset, rechecks effective main rules and confirms an unapproved PR cannot merge while an approved green exact-head PR can. Do not perform a test merge or try to bypass protection as a diagnostic. No settings changed, no protection is claimed active, and no money was spent.
