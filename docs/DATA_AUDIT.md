# DATASET GO/NO-GO GATE

**Status: NOT VERIFIED. Do not report empirical benchmark findings yet.**

## Candidate A — LLMRouterBench
- Source: https://github.com/ynulihao/LLMRouterBench
- Verify data access, formats, licensing, response-level quality, cost semantics, and overlap across model IDs.
- Some published global row counts refer to evaluation instances, not necessarily a complete matrix of multiple models for each prompt. Do not assume otherwise.

## Candidate B — RouterBench
- Source: https://huggingface.co/datasets/withmartian/routerbench
- Dataset card says 30k+ prompts and 11 models with prompt/response/cost/performance score; verify schemas and distribution rights.
- Files may require sizeable download. Sample first, avoid storing data in Git.

## Required audit artifacts
- Dataset source URL and commit/revision, content checksums, license terms and access restrictions.
- Actual column list and anonymized example record.
- Unique task IDs, model names, overlap matrix, missing outcomes rates, cost field units/estimation method.
- Held-out split policy and contamination/leakage checks.
- Minimum feasible paired tasks and chosen two-arm experiment (including what feature is known *before* allocation).
- A robust low-bandwidth sample path and a full-data optional path.
- Explicit yes/no on whether raw outputs can be redistributed in this repo.

## Gate outcome
Record `GO` only with evidence and a working loader/test. If neither candidate works, document a new source and remain in synthetic-only status without misleading release claims.
