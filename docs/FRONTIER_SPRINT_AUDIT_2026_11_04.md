# Frontier sprint — numerical audit record

Companion to [the research decision](FRONTIER_SPRINT_2026_11_04.md), issue
[#36](https://github.com/almajna/deviation-lab/issues/36). This records fresh
verification of **previous synthetic experiments**, not a new experiment.

## Sources and observed results

| Input | Pin / check |
|---|---|
| Engine source | Main `f940faef2b46c7f9f51b4c636963b58c8c751153` |
| PR32 | `728e59fd7c9b3bcfc44cdee243c8cf4272c4abc0`; decompressed receipt SHA-256 `18e412239e25b6a33c86fe90fd02649a3893c3bca7792dbcef8824e52106226c` matched |
| PR35 sources/evidence | `57cab29e1b46604065d71830e17c114fe10e47ad`; archive SHA-256 `eb17cf71f5497c350655f970e26d0ac89da23582977825c402b71954fbe90360` matched |
| PR35 runner | [41931827430](https://github.com/almajna/deviation-lab/actions/runs/41931827430) metadata inspected; original runner log was not downloaded again in this sprint |

The audit agent ran complete PR32 receipt verification and the separate rational
checker: 24 calls, 24 valid actions, 18 episodes, zero profitable model cases.
It ran PR35 zero-inference engine replay and independent rational verification:
60 calls, 4,052 generated tokens, 36 valid final actions, 804 finite state-actions,
96 model/control rows, frozen verdict FAIL. All three arms have zero of six
discoveries and mean expected regret 186 virtual credits.

Targeted regression suites passed: 4 autonomous-economy tests, 22 producer
certificate tests, 25 independent-certificate tests (51 total). The certificate
suites used Python 3.12. The independent suite's historical synthetic-proof path
was redirected in scratch to exact Git-extracted fixtures; its source and checks
were unchanged. These results do not assert a full-suite or fresh full benchmark
run. Historical certificate timings were not remeasured.

Representative commands actually run:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3.12 -m unittest discover -s tests -p test_certified_attacks.py -v

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/tmp/deviation-frontier-sprint/src \
python3.12 /tmp/deviation-independent-audit/scripts/run_reasoning_plan.py verify \
/tmp/deviation-independent-audit/reasoning/raw.json \
/tmp/deviation-independent-audit/reasoning/scored.json

python3.12 /tmp/deviation-independent-audit/scripts/check_reasoning_plan.py \
/tmp/deviation-independent-audit/reasoning/raw.json \
/tmp/deviation-independent-audit/reasoning/scored.json \
/tmp/deviation-independent-audit/reasoning/replay-verdict.json
```

The regenerated PR35 verdict was byte-identical to its archived verdict. All
frozen source hashes were checked before successful replay.

## Independent engine, arithmetic and wallet challenge

Below is the exact successful inline invocation provided from the audit agent's
tool history. It was run from `/tmp/deviation-independent-audit`; it did not
originally exist as a standalone script. The imported engine is pinned main;
`run_reasoning_plan.py` and `check_reasoning_plan.py` are exact PR35 source;
`run_autonomous_economy.py` is the unchanged main source. The JSON inputs are
the explicitly synthetic PR35 archive, not dataset holdout records.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/tmp/deviation-frontier-sprint/src:/tmp/deviation-independent-audit/scripts python3.12 - <<'PY'
import json
from pathlib import Path
from fractions import Fraction
from run_reasoning_plan import CASES,PlanReports,fixture,A,B,ROUTE_A,ROUTE_B,run,metrics,prepare_game
from check_reasoning_plan import MENU,compute,scoring
from deviation.verification.checker import check
root=Path('/tmp/deviation-independent-audit/reasoning');scored=json.loads((root/'scored.json').read_text());ledgers=json.loads((root/'full_ledgers.json').read_text())
num=0;rows=0;used=set()
for state in scored['states']:
 case,bonus=state['case'],state['bonus'];a,rival,belief,outcome=CASES[case-1]
 s=fixture(belief,bonus,2000+10*case+bonus//200)
 s['experiment_id']='SYNTHETIC-reasoning-plan-v1';s['agents']['focal']['signals'][A]=a;s['agents']['competitor']['signals']={A:a,B:rival}
 for r in s['sealed_outcomes']:r['quality']=outcome[int(r['model_id']==ROUTE_B)]//2
 game=prepare_game(s,'controller','pool',scope='reports',public_report_model={'competitor':{A:a,B:rival}})
 check(game,state['proof'])
 for report in MENU:
  report=None if report is None else list(report)
  result=run(s,'pool',policies={'focal':PlanReports(a,report),'competitor':PlanReports(a,rival)})
  m=metrics(result,s);route,expected,realized=compute(report,a,rival,belief,outcome,bonus)
  assert m['allocation']==[ROUTE_B if route=='B' else ROUTE_A],(case,bonus,report,m['allocation'],route)
  assert Fraction(*m['expected_utility'])==expected and m['realized_utility']==realized
  num+=1
 for row in state['rows'].values():
  ledger=ledgers[row['receipt_sha256']];used.add(row['receipt_sha256']);events=ledger['trace']['events']
  summary=next(e['payload'] for e in events if e['type']=='economic_summary');balances=dict(summary['initial_balances'])
  for event in events:
   if event['type']=='ledger_transfer':
    t=event['payload'];balances[t['payer']]-=t['amount'];balances[t['payee']]+=t['amount']
  assert balances==summary['final_balances']
  assert balances['agent/focal']-40==scoring(a,outcome[0])+scoring(row['report'],outcome[1])
  assert balances['agent/competitor']-40==scoring(a,outcome[0])+scoring(rival,outcome[1])
  assert summary['controllers']['controller']['utility']==row['realized']
  rows+=1
assert set(ledgers)==used
print('Independent checker: 12 certificates passed; engine versus rational arithmetic:',num,'state-actions passed; reconstructed wallets and payout checks:',rows,'rows /',len(used),'unique receipts passed.')
PY
```

Observed output, exit code 0:

```text
Independent checker: 12 certificates passed; engine versus rational arithmetic: 804 state-actions passed; reconstructed wallets and payout checks: 96 rows / 60 unique receipts passed.
```

For reconstruction, retrieve only the named scripts and
`artifacts/llm_agents/reasoning_plan_v1.tar.gz` from the pinned PR35 revision,
verify the archive digest, and extract its five JSON files into the reasoning
directory above. Read the archive member names before extraction. Source bytes
must match the stored receipt hashes, including trailing newlines. Use the pinned
main source tree for `PYTHONPATH`; do not silently substitute a later engine.

## Retained preparation failures and limits

- Initial Python 3.9.6 certificate run passed 21/22 tests and failed a mock
  namespace-resolution test. This is an unsupported runtime. All 22 passed with
  documented Python 3.12; no test was weakened.
- Initial scratch source copies had an extra trailing newline and failed source
  identity verification. The newline was removed only where doing so matched the
  exact recorded SHA-256; successful replay used original bytes.
- Initial additional engine enumeration passed tuple reports to an interface that
  requires lists, failing its first allocation assertion. Converting the scratch
  audit inputs to lists produced the successful invocation above. No engine,
  historical receipt or frozen criterion changed.

These failures are audit preparation defects, not altered scientific outcomes.
The certificate package shares trusted engine/numeric primitives; the separate
rational formula reduces that dependency for these authored static-pool games.
Inference provenance remains runner-backed with the local model runtime trusted.
No cryptographic inference attestation or new model inference is claimed.

At the audit's last CI query, five listed workflows for PR31 and six for PR32 had
succeeded; PR35 had five successes and Python/shared-contract CI still running.
These are observations for those exact PR heads, not a claim about this sprint
PR's CI. Its current checks must be read from GitHub separately.
