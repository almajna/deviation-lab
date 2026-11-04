# Claude Code project instructions

Follow `AGENTS.md` as the authoritative rules; it applies equally to Codex and Claude.
Before coding, read `docs/CONTRACTS.md`, the assigned issue and task brief in `docs/prompts/`.
Use a dedicated feature branch/worktree. Keep changes within the assigned ownership boundary. Never modify shared schemas unilaterally; propose a contract change to the integrator.
Provide working tests and exact reproducible commands. Report limitations and missing data plainly; do not hallucinate a passing result. Do not incur paid API expenses. Agents never commit to main, merge, enable auto-merge/merge queues or bypass review. A human merges after independent review, green CI and exact-head approval. Visibility changes and production publishing require separate human permission.

After every milestone, write an executive summary under 150 words: delivered/verified/blockers/next human decision.

## Agent skills

### Issue tracker

Issues live in this repo's GitHub Issues (`almajna/deviation-lab`) and are managed with the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Uses the five default labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human` and `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one root `GLOSSARY.md` plus `docs/adr/`, both created when first needed. See `docs/agents/domain.md`.
