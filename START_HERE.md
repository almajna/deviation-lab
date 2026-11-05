> **Historical planning document.** For current project state and navigation, see [status](docs/STATUS.md) and the [README](README.md).

# DEVIATION — START HERE

This is a **repository bootstrap package**, not a claim that the research project is finished. It adds project instructions, scientific protocols, agent task briefs, a small working Python example, and CI to the existing repository at `https://github.com/almajna/deviation-lab`.

**It deliberately does not replace your existing `README.md`, `LICENSE`, or `.gitignore`.** The package does not contain private keys, paid APIs, or downloaded datasets. All examples are explicitly synthetic.

## Fastest install into your existing repository (Mac)

1. Download `deviation-bootstrap.zip` from the chat to Downloads.
2. Open Terminal and run:

```bash
cd ~/Downloads
git clone https://github.com/almajna/deviation-lab.git
cd deviation-lab
unzip -n ../deviation-bootstrap.zip
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m deviation demo --out /tmp/deviation_demo.json
# After checking the files:
git checkout -b chore/bootstrap
git add AGENTS.md CLAUDE.md COPY_TO_CODEX.md START_HERE.md pyproject.toml src tests docs scripts .github
git commit -m "Add DEVIATION research and agent bootstrap"
git push -u origin chore/bootstrap
```

Then open GitHub -> **Pull requests -> New pull request** (`chore/bootstrap` -> `main`). Review and merge. If `git`, GitHub authentication, or paths are unfamiliar, ask Codex to perform these commands *inside a clone of the repository*, using the downloaded ZIP; never paste credentials into a chat.

`unzip -n` will not overwrite existing files. If you've started development beyond the initial README/LICENSE/.gitignore, inspect conflicts before extracting. This package intentionally includes no `README.md`, `LICENSE`, or `.gitignore`.

## What to do with Codex and Claude

1. First merge this bootstrap package; or give Codex the ZIP and ask it to create a setup PR.
2. Give Codex **`docs/prompts/00_integrator.md`**. It should audit the scaffold, create GitHub issues, and complete the scientific design review **before** broad implementation.
3. Run **`docs/prompts/01_data.md`** on a separate branch. The dataset feasibility gate is non-negotiable.
4. After the data gate and interfaces are approved, work through numbered briefs in `docs/prompts/`. Each agent must read `AGENTS.md`, `docs/SPEC.md`, `docs/CONTRACTS.md`, `docs/ACCEPTANCE.md`.
5. Keep one main integrator. Builders work in separate worktrees/branches. A reviewer examines PRs independently.

**First Codex message:**

> Open this repository and read `START_HERE.md`, `AGENTS.md`, `docs/MASTER_PLAN.md`, `docs/SPEC.md`, `docs/RESEARCH.md`, and `docs/CONTRACTS.md`. Execute `docs/prompts/00_integrator.md`. Treat the existing repository as canonical. Work on a feature branch and prepare a PR; do not commit directly to main. No spending, publishing or external side effects without approval. Show evidence from tests.

## One-command local smoke checks

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m deviation demo --out /tmp/deviation_demo.json
```

The initial CLI runs a **tiny synthetic reference example only**. The actual scientific benchmark, live market and visualization are implementation milestones, not pre-built components.

## Where everything is stored

- `docs/MASTER_PLAN.md`: all milestones and dependencies.
- `docs/SPEC.md`: precisely what the software must do.
- `docs/RESEARCH.md`: scientific hypothesis, evaluation and uncertainty.
- `docs/DATA_AUDIT.md`: dataset acceptance gate.
- `docs/CONTRACTS.md`: shared data models, privacy boundaries and event logs.
- `docs/VISUAL_SPEC.md`: impressive but honest interactive UX.
- `docs/ACCEPTANCE.md`: evidence-based 100-point release rubric.
- `docs/WORKFLOW.md`: how Codex and Claude divide work safely.
- `docs/prompts/`: numbered, copy-ready task prompts.
- `AGENTS.md` + `CLAUDE.md`: permanent operating rules for coding agents.
- `docs/LEARNING_PATH.md`: what the human research director should learn.

## Important honesty rules

- Existing recorded LLM outputs are **not** evidence that simulated bidders are real autonomous LLM agents.
- Small exact attack search can prove a claim **within a finite modeled action space**, not universal incentive compatibility.
- Offline full-information outcome comparisons are possible when the dataset contains paired outcomes; a live deployment does **not** observe unselected counterfactuals.
- Release qualification 90/100 is an **internal checklist**. Nobody can guarantee an external 8.5/10 subjective impressiveness rating or a novel discovery.
