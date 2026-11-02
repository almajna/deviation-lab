# Cost and safety policy

Incremental monetary authorization: **$0** unless the human research director explicitly approves a specific charge and upper limit. This excludes existing subscriptions, computer, time and electricity; keep in mind coding subscriptions may have limits.

- No paid API keys or vendor accounts should be created by agents.
- No cloud resources or paid hosting unless explicitly approved.
- Data sampling before full dataset downloads; evaluate disk/bandwidth requirements, licenses, and access gates.
- Local deterministic Python tests and replay first. Free-tier static site later.
- SkyDiscover is optional. If a suitable local model or pre-existing paid inference is not available, deterministic Optuna/scipy/simple search must complete policy search.
- Log CPU/runtime/storage requirements for large jobs. Running untrusted code needs isolation.
- No continuous deployment or externally accessible endpoints without review.
