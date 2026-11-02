# Data inputs

`source_manifest.json` pins public Phase 1 inputs, byte bounds, and checksums. It contains no raw rows. See `docs/DATA_AUDIT.md` for reproduction and scientific limitations.

Keep downloaded bytes outside Git, for example `/tmp/deviation-data-cache`. Do not commit raw questions, answers, outputs, pickle, credentials, or heavyweight archives. `tests/fixtures/llmrouterbench_mock.json` is explicitly synthetic.

The internal `data-audit-1` record is not an approved shared experiment schema. Technical ingestion passing does not change the empirical NO-GO gate.
