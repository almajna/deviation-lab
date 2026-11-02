# One message to paste into Codex AFTER downloading the ZIP

I have created an existing public GitHub repository: https://github.com/almajna/deviation-lab. I have downloaded the prepared DEVIATION bootstrap package as `~/Downloads/deviation-bootstrap.zip` (if missing, ask me where I saved it).

Act as lead integrator and **install the bootstrap package in this existing repository**.

1. If the repository is not already cloned locally, clone it. Work in a new branch named `chore/bootstrap`, not on main.
2. Inspect the current README, LICENSE and .gitignore and preserve them.
3. List the ZIP contents, scan for conflicting files and then extract into the repository root (not into an extra nested folder). Do not overwrite pre-existing project files without showing me a diff and obtaining approval.
4. Read `START_HERE.md`, `AGENTS.md`, `docs/MASTER_PLAN.md`, `docs/SPEC.md`, `docs/RESEARCH.md`, `docs/CONTRACTS.md`, `docs/WORKFLOW.md`, `docs/ACCEPTANCE.md` and `docs/STATUS.md`.
5. Run `bash scripts/check.sh`; confirm synthetic reference behavior and all unit tests. Inspect `.github/workflows/ci.yml` and ensure it passes once pushed.
6. Verify that the project documentation is internally consistent. The packaged toy CLI is explicitly **not** a completed prediction market or research benchmark.
7. Create a commit and pull request into main if authenticated access permits. If not, leave the branch ready and give me exact commands. Do not merge or publish anything beyond the existing public repo without explicit approval.
8. When that bootstrap PR is merged and after I approve the research architecture, follow `docs/prompts/00_integrator.md` and prioritize `docs/prompts/01_data.md`.

Constraints: $0 incremental spend; no paid APIs; do not access my secrets; protect existing work; never fabricate experiment results. Return only: files installed, tests passed/failed, PR link if created, pending approval, and next task.
