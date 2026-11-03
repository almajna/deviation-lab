# Free execution route checked for PR #24 resumption

The original Mac-host blocker persists: no installed runtime/model and a fresh
PyPI HTTP probe fails DNS. A second supported computation runtime resolves to
the same restricted Mac host, so it does not supply an alternate machine.

The repository connector reports `almajna/deviation-lab` is **public**. Current
GitHub documentation explicitly makes standard hosted runners free/unlimited
for public repositories, including `ubuntu-24.04` (four CPU cores, 16 GB RAM):

- https://docs.github.com/en/actions/reference/runners/github-hosted-runners
- https://docs.github.com/en/billing/concepts/product-billing/github-actions

This is the fastest available unattended route here because the existing PR
already executes standard-runner CI and can install dependencies/download public
weights there. It requires no paid API, account credit, external GPU, subscription
API entitlement, new service registration or user-operated notebook session.
No claim is made that it is the fastest hardware or fastest model everywhere.

Use a small instruct checkpoint: Qwen2.5-0.5B-Instruct, pinned upstream commit
`7ae557604adf67be50417f59c2c2f167def9a775` and weight SHA256
`fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe`.
Upstream [card](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct) and
[LICENSE](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct/blob/7ae557604adf67be50417f59c2c2f167def9a775/LICENSE)
declare Apache-2.0. The
[weight pointer](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct/blob/7ae557604adf67be50417f59c2c2f167def9a775/model.safetensors)
provides the expected SHA256; the runner checks it before loading. No training
data or benchmark labels are retrieved.

Cost controls: public-repository guard, exact standard runner, CPU-only torch,
20-minute timeout, read-only token, no persisted credentials/secrets, no artifact
upload or cache storage, no paid fallback. Downloads remain on the disposable
runner; synthetic-text evidence returns in ordinary job logs. No visibility
change is needed or made. Observe actual output before calling this live evidence.
