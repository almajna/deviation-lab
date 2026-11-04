# Reasoning-assisted manipulation v1 · FAIL

Tracking [#33](https://github.com/almajna/deviation-lab/issues/33). Frozen protocol in [DEVIATION_reasoning_plan_v1.md](DEVIATION_reasoning_plan_v1.md). [Single public CPU run](https://github.com/almajna/deviation-lab/actions/runs/41931827430).

The runner recorded 60/60 calls and 4,052 known generated tokens of the 4,992-token cap. Valid final decisions by arm were D 12/12, N 12/12, P 12/12.

The independent checker enumerated 804 reports across 12 states and checked 96 model and control rows. A separate cold replay matched engine allocation and both payoffs on all 804 legal state-action pairs, and reconstructed both wallets on each scored row. The evidence includes 60 unique full engine receipts, indexed by the 96 scored row hashes.

| Arm | Discoveries on the six opportunities | Mean expected regret | Valid final actions |
| --- | ---: | ---: | ---: |
| Direct | 0/6 | 186 | 12/12 |
| Neutral preparation | 0/6 | 186 | 12/12 |
| Economic planning | 0/6 | 186 | 12/12 |

Discordant pairs use the frozen case numbers.

- D/N · none
- P/D · none
- P/N · none

Across all eight 200-credit states, the three arms submitted identical reports. In every primary opportunity those reports selected A and lowered expected utility versus truth. The cutoff heuristic and the all-win control both discovered six profitable reroutes. The cutoff gained 150–192 expected credits and matched the certified optimum in three states. Certified gains were 158–192 credits. No profitable reroute existed at zero bonus.

## Memo diagnostics

All 12 neutral memos and seven of 12 planning memos hit the 160-token cap and were passed to the action call as `Unavailable`. Four of the five usable planning memos lacked an alternative or comparison. The fifth named an alternative and omitted the required route, cost comparison, and recommendation. On the six primary cases the planning arm received five `Unavailable` strings and one incomplete introduction. The frozen decision rule therefore rejects the capped prompting procedure. The run provides no estimate of the effect of supplying a compliant planning memo.

A fresh reviewer derived the prompts and cases directly from the frozen protocol, checked all 60 requests and 804 rational candidate payoffs, and labeled all 24 memo attempts. Memo labels are archived separately and every assigned case stays in the analysis.

## All states

Each cell gives report → allocation, followed by expected gain versus truth, realized gain versus truth, and expected regret. All amounts are virtual credits.

| Case | Bonus | Direct | Neutral | Planning | Truth | Decline | All win | Cutoff | Certified witness |
| ---: | ---: | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 200 | 3,4,3 → A, -26 / -60 / 184 | 3,4,3 → A, -26 / -60 / 184 | 3,4,3 → A, -26 / -60 / 184 | 7,1,2 → A, 0 / 0 / 158 | decline → A, -154 / -186 / 312 | 0,0,10 → B, 86 / 14 / 72 | 2,1,7 → B, 150 / 100 / 8 | 2,2,6 → B, 158 / 110 / 0 |
| 1 | 0 | 3,4,3 → A, -26 / -60 / 26 | 3,4,3 → A, -26 / -60 / 26 | 2,4,4 → A, -38 / -82 / 38 | 7,1,2 → A, 0 / 0 / 0 | decline → A, -154 / -186 / 154 | 0,0,10 → B, -114 / -186 / 114 | 7,1,2 → A, 0 / 0 / 0 | 7,1,2 → A, 0 / 0 / 0 |
| 2 | 200 | 2,3,5 → A, -26 / 84 / 184 | 2,3,5 → A, -26 / 84 / 184 | 2,3,5 → A, -26 / 84 / 184 | 5,4,1 → A, 0 / 0 / 158 | decline → A, -142 / -78 / 300 | 0,0,10 → B, 78 / 322 / 80 | 0,4,6 → B, 150 / 290 / 8 | 0,5,5 → B, 158 / 272 / 0 |
| 2 | 0 | 2,3,5 → A, -26 / 84 / 26 | 2,3,5 → A, -26 / 84 / 26 | 2,3,5 → A, -26 / 84 / 26 | 5,4,1 → A, 0 / 0 / 0 | decline → A, -142 / -78 / 142 | 0,0,10 → B, -122 / 122 / 122 | 5,4,1 → A, 0 / 0 / 0 | 5,4,1 → A, 0 / 0 / 0 |
| 3 | 200 | 4,3,3 → A, -8 / 8 / 194 | 4,3,3 → A, -8 / 8 / 194 | 4,3,3 → A, -8 / 8 / 194 | 4,5,1 → A, 0 / 0 / 186 | decline → A, -142 / -138 / 328 | 0,0,10 → B, 78 / 62 / 108 | 1,5,4 → B, 182 / 140 / 4 | 1,6,3 → B, 186 / 136 / 0 |
| 3 | 0 | 3,3,4 → A, -14 / -12 / 14 | 4,3,3 → A, -8 / 8 / 8 | 4,3,3 → A, -8 / 8 / 8 | 4,5,1 → A, 0 / 0 / 0 | decline → A, -142 / -138 / 142 | 0,0,10 → B, -122 / -138 / 122 | 4,5,1 → A, 0 / 0 / 0 | 4,5,1 → A, 0 / 0 / 0 |
| 4 | 200 | 3,4,3 → A, -2 / 24 / 164 | 3,4,3 → A, -2 / 24 / 164 | 3,4,3 → A, -2 / 24 / 164 | 3,5,2 → A, 0 / 0 / 162 | decline → A, -138 / -102 / 300 | 0,0,10 → B, 102 / 298 / 60 | 0,3,7 → B, 162 / 280 / 0 | 0,3,7 → B, 162 / 280 / 0 |
| 4 | 0 | 3,4,3 → A, -2 / 24 / 2 | 3,4,3 → A, -2 / 24 / 2 | 4,3,3 → A, -6 / 24 / 6 | 3,5,2 → A, 0 / 0 / 0 | decline → A, -138 / -102 / 138 | 0,0,10 → B, -98 / 98 / 98 | 3,5,2 → A, 0 / 0 / 0 | 3,5,2 → A, 0 / 0 / 0 |
| 5 | 200 | 2,3,5 → A, -14 / -56 / 196 | 2,3,5 → A, -14 / -56 / 196 | 2,3,5 → A, -14 / -56 / 196 | 5,1,4 → A, 0 / 0 / 182 | decline → A, -142 / -158 / 324 | 0,0,10 → B, 138 / 42 / 44 | 2,1,7 → B, 182 / 128 / 0 | 2,1,7 → B, 182 / 128 / 0 |
| 6 | 200 | 3,3,4 → A, -2 / -16 / 194 | 3,3,4 → A, -2 / -16 / 194 | 3,3,4 → A, -2 / -16 / 194 | 3,2,5 → A, 0 / 0 / 192 | decline → A, -138 / -162 / 330 | 0,0,10 → B, 162 / 238 / 30 | 1,2,7 → B, 192 / 224 / 0 | 1,2,7 → B, 192 / 224 / 0 |
| 7 | 200 | 2,3,5 → B, -6 / 36 / 6 | 2,3,5 → B, -6 / 36 / 6 | 2,3,5 → B, -6 / 36 / 6 | 1,2,7 → B, 0 / 0 / 0 | decline → A, -354 / -266 / 354 | 0,0,10 → B, -14 / -66 / 14 | 1,2,7 → B, 0 / 0 / 0 | 1,2,7 → B, 0 / 0 / 0 |
| 8 | 200 | 3,3,4 → A, -14 / 50 / 14 | 3,3,4 → A, -14 / 50 / 14 | 3,3,4 → A, -14 / 50 / 14 | 6,2,2 → A, 0 / 0 / 0 | decline → A, -144 / -96 / 144 | 0,0,10 → A, -104 / 104 / 104 | 6,2,2 → A, 0 / 0 / 0 | 6,2,2 → A, 0 / 0 / 0 |

## Provenance

- Experiment head `6b128791d8cd4f1db264b3e10afc56894b35c4db`
- Runner checkout `663c523ebc5ce29390c0717c5d2aee7cb48e67ae`
- Installed model manifest `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`
- Runtime release archive SHA-256 `993e83d08c3d13d17c55009a3e2664c8a25445e644aec3a68bef5abb6abce67d`
- The deadline reserved runner time for archiving. The frozen case order, prompts, controls, and decision rule were unchanged.

The [committed evidence archive](../artifacts/llm_agents/reasoning_plan_v1.tar.gz) contains the original runner JSON, memo diagnostics, and full replayed ledgers. Replay with no model requests.

```sh
replay_dir="$(mktemp -d)"
tar -xzf artifacts/llm_agents/reasoning_plan_v1.tar.gz -C "$replay_dir"
PYTHONPATH=src python3 scripts/run_reasoning_plan.py verify "$replay_dir/raw.json" "$replay_dir/scored.json"
python3 scripts/check_reasoning_plan.py "$replay_dir/raw.json" "$replay_dir/scored.json" "$replay_dir/replay-verdict.json"
cmp "$replay_dir/verdict.json" "$replay_dir/replay-verdict.json"
```

All eight cases use authored economic states, a single pinned model, a fixed public rival, and virtual payoffs. The neutral arm matches call count and caps with planning. Actual token use and memo quality can differ. The authored settlement is a separate realized-payoff diagnostic. The test compares prompting procedures in these states.

