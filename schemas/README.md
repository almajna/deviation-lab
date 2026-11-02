# Shared contract index

`contracts-v0.2.json` is a versioned component/field index, **not JSON Schema**. Normative strict conformance checks are in `src/deviation/contracts.py`; semantics/approval state are in `docs/CONTRACTS.md`.

The synthetic pack covers public/private boundaries, reservations, allocation receipts, realized-cost reports, virtual ledgers and completed replay. Its migration fixture preserves v0.1 and requires new receipts, rather than relabeling old costs as reservations. Phase 1 audit artifacts and legacy demo are unchanged. Validators prepare for Phase 2; they are not an implemented simulation.
