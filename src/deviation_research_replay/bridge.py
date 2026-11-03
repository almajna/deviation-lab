"""Narrow compatibility evidence alongside separate strict source-local replays."""
from copy import deepcopy
import json
import re

from deviation.data.pipeline import digest
from deviation_research.records import sha
from .provenance import read, HISTORICAL_ENGINE_SHA, HISTORICAL_HARNESS_SHA


def require(ok, message):
    if not ok: raise ValueError(message)


def strict_equal(a, b, message):
    # Canonical encoding preserves int/float and string/numeric distinctions.
    require(json.dumps(a,sort_keys=True,ensure_ascii=False,allow_nan=False) ==
            json.dumps(b,sort_keys=True,ensure_ascii=False,allow_nan=False),message)


def _compare_result(old, new, old_source, current_source):
    """Not an authenticity checker: compare_cycles FIRST freshly checks new data."""
    expected = deepcopy(old); changes = []
    require(old["kind"] == new["kind"],"EXPERIMENT_KIND_CHANGED")
    require(len(old["rows"]) == len(new["rows"]),"CASE_COVERAGE_CHANGED")
    for i,(a,b) in enumerate(zip(expected["rows"],new["rows"])):
        if "certificate" in a:
            c = a["certificate"]
            require(c["source_sha256"] == old_source,"HISTORICAL_CERTIFICATE_SOURCE")
            require(c["sha256"] == digest({k:v for k,v in c.items() if k != "sha256"}),"HISTORICAL_CERTIFICATE_DIGEST")
            c["source_sha256"] = current_source
            c["sha256"] = digest({k:v for k,v in c.items() if k != "sha256"})
            strict_equal(c,b["certificate"],"CERTIFICATE_PROOF_OR_CONTEXT_CHANGED")
            for field in ("source_sha256","sha256"):
                changes.append({"path":["rows",i,"certificate",field],
                    "historical":old["rows"][i]["certificate"][field],"current":c[field]})
        if old["kind"] == "forecast_correlation":
            # The fresh current-source reviewer derives this ID from a real
            # engine replay; neither scalar value is trusted merely as a hash.
            for value in (a["receipt_sha256"],b["receipt_sha256"]):
                require(isinstance(value,str) and re.fullmatch("[0-9a-f]{64}",value),"RECEIPT_DIGEST_FORMAT")
            changes.append({"path":["rows",i,"receipt_sha256"],
                "historical":a["receipt_sha256"],"current":b["receipt_sha256"]})
            a["receipt_sha256"] = b["receipt_sha256"]
    strict_equal(expected,new,"SCIENTIFIC_RESULT_CHANGED")
    return changes


def _validate_events(rows):
    previous = None
    for i,row in enumerate(rows):
        require(row["seq"] == i and row["previous_sha256"] == previous,"EVENT_CHAIN_TOPOLOGY")
        require(row["sha256"] == sha({k:v for k,v in row.items() if k != "sha256"}),"EVENT_DIGEST")
        previous = row["sha256"]


def _replace_derived(value, mapping):
    if isinstance(value,dict): return {k:_replace_derived(v,mapping) for k,v in value.items()}
    if isinstance(value,list): return [_replace_derived(v,mapping) for v in value]
    return mapping.get(value,value) if isinstance(value,str) else value


def _compare_events(old, new, mapping):
    _validate_events(old); _validate_events(new)
    require(len(old) == len(new) == 54,"EVENT_COVERAGE_CHANGED")
    for a,b in zip(old,new):
        a = {k:v for k,v in a.items() if k not in {"sha256","previous_sha256"}}
        b = {k:v for k,v in b.items() if k not in {"sha256","previous_sha256"}}
        strict_equal(_replace_derived(a,mapping),b,"EVENT_SEMANTICS_CHANGED")


def verify_current_review(payload):
    from deviation_research.safety import run
    from deviation_research.records import source_hash
    from deviation.verification.checker import source_sha
    review, receipt = run("review",payload)
    require(receipt["harness_source_sha256"] == source_hash() and
            receipt["engine_source_sha256"] == source_sha(),"REVIEW_EXECUTED_SOURCE_CHANGED")
    return review,receipt


def compare_cycles(historical, current):
    from deviation.verification.checker import source_sha
    from deviation_research.records import source_hash
    old,new = read(historical/"summary.json"),read(current/"summary.json")
    for file in ("inputs.plan.json","inputs.sources.json","scout.json"):
        require((historical/file).read_bytes() == (current/file).read_bytes(),"REGISTERED_INPUT_CHANGED: "+file)
    require(old["sha256"] == sha({k:v for k,v in old.items() if k != "sha256"}),"HISTORICAL_SUMMARY_DIGEST")
    require(new["sha256"] == sha({k:v for k,v in new.items() if k != "sha256"}),"CURRENT_SUMMARY_DIGEST")
    old_frozen = read(historical/("preregistration-"+old["preregistration_sha256"]+".json"))
    new_frozen = read(current/("preregistration-"+new["preregistration_sha256"]+".json"))
    require(old_frozen["engine_source_sha256"] == HISTORICAL_ENGINE_SHA and
            old_frozen["harness_source_sha256"] == HISTORICAL_HARNESS_SHA,"HISTORICAL_PACKAGE_BINDING")
    require(source_hash() == HISTORICAL_HARNESS_SHA,"RESEARCH_RUNTIME_CHANGED")
    frozen = deepcopy(old_frozen); frozen["engine_source_sha256"] = source_sha()
    strict_equal(frozen,new_frozen,"FROZEN_PROTOCOL_OR_SOURCE_CHANGED")
    require(sha(old_frozen) == old["preregistration_sha256"] and
            sha(new_frozen) == new["preregistration_sha256"],"PREREGISTRATION_DIGEST")
    mapping = {HISTORICAL_ENGINE_SHA:source_sha(),old["preregistration_sha256"]:new["preregistration_sha256"]}
    expected = deepcopy(old); expected["preregistration_sha256"] = new["preregistration_sha256"]
    require(len(old["records"]) == len(new["records"]) == 4,"EXPERIMENT_COVERAGE_CHANGED")
    changes, resources = {},{}
    for i,(a,b) in enumerate(zip(old["records"],new["records"])):
        require(a["id"] == b["id"] and a["key"] == b["key"] and a["status"] == b["status"] == "completed","EXPERIMENT_IDENTITY_OR_FAILURE")
        before,after = historical/a["key"],current/b["key"]
        require((before/"plan.json").read_bytes() == (after/"plan.json").read_bytes(),"EXPERIMENT_PLAN_CHANGED")
        old_result,new_result = read(before/"result.json"),read(after/"result.json")
        require(a["result_sha256"] == sha(old_result) and b["result_sha256"] == sha(new_result),"RESULT_DIGEST")
        # Both source-local cold replays have passed before compatibility. This
        # additional independent review checks all current receipts/certificates
        # with normal current source binding, never expected_source overrides.
        reviewed, resource = verify_current_review({"plan":read(after/"plan.json"),"result":new_result})
        resources[a["id"]] = resource
        strict_equal(reviewed,read(after/"review.json"),"CURRENT_REVIEW_REPLAY_CHANGED")
        strict_equal(reviewed,b["review"],"SUMMARY_REVIEW_CHANGED")
        changes[a["id"]] = _compare_result(old_result,new_result,HISTORICAL_ENGINE_SHA,source_sha())
        old_review = deepcopy(read(before/"review.json")); old_review["result_sha256"] = sha(new_result)
        strict_equal(old_review,reviewed,"REVIEW_FINDING_CHANGED")
        expected["records"][i]["result_sha256"] = sha(new_result)
        expected["records"][i]["review"] = reviewed
        mapping[sha(old_result)] = sha(new_result)
    expected["sha256"] = sha({k:v for k,v in expected.items() if k != "sha256"})
    strict_equal(expected,new,"SUMMARY_FINDINGS_CHANGED")
    mapping[old["sha256"]] = new["sha256"]
    old_events = [json.loads(x) for x in (historical/"events.jsonl").read_text().splitlines()]
    new_events = [json.loads(x) for x in (current/"events.jsonl").read_text().splitlines()]
    _compare_events(old_events,new_events,mapping)
    return {"version":"research-source-rebinding-1","cases":{r["id"]:r["rows"] for r in new["records"]},
        "event_count":len(new_events),"findings":{r["id"]:r["review"]["criterion_status"] for r in new["records"]},
        "source_rebindings":changes,"verified_derived_digest_map":mapping,
        "scientific_values_changed":False,"new_inference_calls":0,"paid_spend_usd":0},resources
