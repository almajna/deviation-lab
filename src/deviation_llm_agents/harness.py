"""Prompt-bound decision recording and byte-reproducible economic replay."""
from copy import deepcopy
from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path
import time

from deviation.data.pipeline import digest
from deviation.markets.policies import SignalFollowing
from deviation.markets.runner import run
from .adapter import abstain, decode, encode, prompt, validate_packet


def source_hash():
    root = Path(__file__).parent
    return digest({p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.glob("*.py"))})


@dataclass(frozen=True)
class Budget:
    max_calls: int = 16
    max_prompt_bytes: int = 1_000_000
    max_response_bytes: int = 131072
    max_tokens_per_call: int = 128
    max_prompt_bytes_per_call: int = 8192

    def __post_init__(self):
        for v in asdict(self).values():
            if type(v) is not int or v < 0: raise ValueError("INVALID_BUDGET")
        if not 1 <= self.max_tokens_per_call <= 2048: raise ValueError("INVALID_TOKEN_CAP")
        if self.max_prompt_bytes_per_call > 8192: raise ValueError("UNSUPPORTED_CONTEXT_LIMIT")


class LocalPolicy:
    """Only backend calls constitute inference; every skipped decision is explicit."""
    def __init__(self, backend, budget=Budget(), *, seed=7, mode="utility"):
        if backend.origin not in {"LIVE_LOCAL_LLM", "SCRIPTED_TRANSPORT_TEST"}: raise ValueError("INVALID_ORIGIN")
        if mode not in {"utility", "truthful"}: raise ValueError("INVALID_PROMPT_MODE")
        self.backend, self.budget, self.seed, self.mode = backend, budget, seed, mode
        self.records, self.calls, self.prompt_bytes, self.response_bytes = [], 0, 0, 0

    def act(self, packet):
        validate_packet(packet)
        messages = prompt(packet, mode=self.mode)
        size = len(encode(messages).encode())
        row = {"seq": len(self.records), "decision_origin": self.backend.origin,
            "prompt": messages, "prompt_sha256": digest(messages), "packet_sha256": digest(packet),
            "seed": self.seed, "mode": self.mode, "requested_max_tokens": self.budget.max_tokens_per_call,
            "attempted": False, "raw": None, "usage": None, "elapsed_ns": 0, "status": None,
            "action": abstain(packet)}
        if size > self.budget.max_prompt_bytes_per_call:
            row["status"] = "INPUT_TOO_LARGE_NO_INFERENCE"
        elif (self.calls >= self.budget.max_calls or self.prompt_bytes + size > self.budget.max_prompt_bytes
                or self.response_bytes >= self.budget.max_response_bytes):
            row["status"] = "BUDGET_EXHAUSTED_NO_INFERENCE"
        else:
            row["attempted"] = True
            self.calls += 1
            self.prompt_bytes += size
            start = time.monotonic_ns()
            try:
                reply = self.backend.infer(messages, seed=self.seed, max_tokens=self.budget.max_tokens_per_call)
                if not isinstance(reply, dict): raise ValueError("INVALID_BACKEND_ENVELOPE")
                row["raw"], row["usage"] = reply.get("raw"), reply.get("usage")
                if not isinstance(row["raw"], str): raise ValueError("INVALID_BACKEND_TEXT")
                self.response_bytes += len(row["raw"].encode())
                try: encode(row["usage"])
                except (ValueError, TypeError):
                    row["usage"] = None
                    raise ValueError("NONCANONICAL_USAGE")
                if not isinstance(row["usage"], dict): raise ValueError("INVALID_BACKEND_USAGE")
                for key in ["eval_count", "prompt_eval_count"]:
                    if type(row["usage"].get(key)) is not int or row["usage"][key] < 0:
                        raise ValueError("INVALID_BACKEND_USAGE")
                if self.response_bytes > self.budget.max_response_bytes:
                    raise ValueError("RESPONSE_BUDGET_EXCEEDED")
                if row["usage"].get("eval_count", 0) > self.budget.max_tokens_per_call:
                    raise ValueError("SERVER_TOKEN_CAP_EXCEEDED")
                row["action"] = decode(row["raw"], packet)
                row["status"] = "VALID_MODEL_DECISION" if self.backend.origin == "LIVE_LOCAL_LLM" else "VALID_TEST_DECISION"
            except (ValueError, TypeError, KeyError, OSError, AttributeError) as exc:
                row["status"] = "FAILED_DECISION"
                # Do not dump arbitrary exception text (could contain private paths/tokens).
                row["error_type"] = type(exc).__name__
                row["error_code"] = str(exc) if isinstance(exc, ValueError) and str(exc).isupper() else "TRANSPORT_OR_PARSE_FAILURE"
            finally:
                row["elapsed_ns"] = time.monotonic_ns() - start
                # Preserve bounded raw HTTP evidence even for malformed server JSON.
                evidence = getattr(self.backend, "last_inference_response", None)
                if evidence is not None: row["transport_response"] = deepcopy(evidence)
        row["sha256"] = digest(row)
        self.records.append(row)
        return deepcopy(row["action"])

    def audit(self):
        return {"decision_origin": self.backend.origin, "backend": deepcopy(self.backend.metadata),
            "budget": asdict(self.budget), "calls_attempted": self.calls,
            "prompt_bytes_sent": self.prompt_bytes, "response_bytes_received": self.response_bytes,
            "unknown_usage_calls": sum(r["attempted"] and not valid_usage(r["usage"]) for r in self.records),
            "records": deepcopy(self.records)}


def valid_usage(usage):
    return (isinstance(usage, dict) and all(type(usage.get(k)) is int and usage[k] >= 0
            for k in ["eval_count", "prompt_eval_count"]))


def validate_audit(audit):
    """Recompute counters and origin consistency; hashes do not authenticate a server."""
    expected = {"decision_origin", "backend", "budget", "calls_attempted", "prompt_bytes_sent",
        "response_bytes_received", "unknown_usage_calls", "records"}
    if not isinstance(audit, dict) or set(audit) != expected: raise ValueError("AUDIT_FIELDS")
    origin = audit["decision_origin"]
    if origin not in {"LIVE_LOCAL_LLM", "SCRIPTED_TRANSPORT_TEST"} or audit["backend"].get("origin") != origin:
        raise ValueError("ORIGIN_DISAGREEMENT")
    budget = Budget(**audit["budget"])
    calls = sent = received = unknown = 0
    for seq, row in enumerate(audit["records"]):
        if row["seq"] != seq or type(row["attempted"]) is not bool or row["decision_origin"] != origin:
            raise ValueError("RECORD_ORIGIN_OR_SEQUENCE")
        if digest({k: v for k, v in row.items() if k != "sha256"}) != row["sha256"]:
            raise ValueError("RECORDED_DECISION_HASH_MISMATCH")
        size = len(encode(row["prompt"]).encode())
        permitted = (size <= budget.max_prompt_bytes_per_call and calls < budget.max_calls
            and sent + size <= budget.max_prompt_bytes and received < budget.max_response_bytes)
        if row["requested_max_tokens"] != budget.max_tokens_per_call or row["attempted"] != permitted:
            raise ValueError("BUDGET_ATTEMPT_DISAGREEMENT")
        if row["attempted"]:
            calls += 1; sent += size
            if isinstance(row["raw"], str): received += len(row["raw"].encode())
            if not valid_usage(row["usage"]): unknown += 1
            if row["status"] not in {"FAILED_DECISION", "VALID_MODEL_DECISION" if origin == "LIVE_LOCAL_LLM" else "VALID_TEST_DECISION"}:
                raise ValueError("RECORD_STATUS_ORIGIN")
            if row["status"].startswith("VALID_") and (not valid_usage(row["usage"])
                    or row["usage"]["eval_count"] > budget.max_tokens_per_call or received > budget.max_response_bytes):
                raise ValueError("VALID_STATUS_WITH_INVALID_BUDGET_OR_USAGE")
        elif (row["status"] != ("INPUT_TOO_LARGE_NO_INFERENCE" if size > budget.max_prompt_bytes_per_call else "BUDGET_EXHAUSTED_NO_INFERENCE")
                or row["raw"] is not None or row["usage"] is not None):
            raise ValueError("SKIPPED_INFERENCE_DISAGREEMENT")
    if [calls, sent, received, unknown] != [audit[k] for k in ["calls_attempted", "prompt_bytes_sent", "response_bytes_received", "unknown_usage_calls"]]:
        raise ValueError("AUDIT_COUNTER_DISAGREEMENT")


class RecordedPolicy:
    """Only exact prompt-bound decisions replay; never inference or fresh evidence."""
    def __init__(self, audit):
        self.audit_data, self.cursor = deepcopy(audit), 0

    def act(self, packet):
        if self.cursor >= len(self.audit_data["records"]): raise ValueError("MISSING_RECORDED_DECISION")
        row = self.audit_data["records"][self.cursor]
        if digest({k: v for k, v in row.items() if k != "sha256"}) != row["sha256"]:
            raise ValueError("RECORDED_DECISION_HASH_MISMATCH")
        if row["packet_sha256"] != digest(packet) or row["prompt"] != prompt(packet, mode=row["mode"]):
            raise ValueError("RECORDED_CONTEXT_MISMATCH")
        if row["prompt_sha256"] != digest(row["prompt"]): raise ValueError("PROMPT_HASH_MISMATCH")
        if row["status"] in {"VALID_MODEL_DECISION", "VALID_TEST_DECISION"}:
            expected = decode(row["raw"], packet)
        elif row["status"] in {"FAILED_DECISION", "BUDGET_EXHAUSTED_NO_INFERENCE", "INPUT_TOO_LARGE_NO_INFERENCE"}:
            expected = abstain(packet)
        else: raise ValueError("UNKNOWN_RECORDED_STATUS")
        if row["action"] != expected: raise ValueError("RECORDED_ACTION_MISMATCH")
        self.cursor += 1
        return deepcopy(expected)


def run_episode(scenario, focal_agent, policy, mechanism="lmsr"):
    if scenario["data_kind"] != "SYNTHETIC": raise ValueError("SYNTHETIC_ENVIRONMENT_ONLY")
    if focal_agent not in scenario["agents"]: raise ValueError("UNKNOWN_FOCAL_AGENT")
    others = {a: SignalFollowing() for a in scenario["agents"]}
    others[focal_agent] = policy
    result = run(deepcopy(scenario), mechanism, policies=others)
    audit = policy.audit()
    validate_audit(audit)
    statuses = [r["status"] for r in audit["records"]]
    live = audit["decision_origin"] == "LIVE_LOCAL_LLM"
    from .experiments import metrics
    sidecar = {"version": "llm-agent-1", "environment_origin": "SYNTHETIC",
        "signal_origin": "EXOGENOUS_SYNTHETIC_BELIEFS", "focal_agent": focal_agent,
        "other_decisions": "SCRIPTED_SIGNAL_FOLLOWING", "decision_origin": audit["decision_origin"],
        "engine_trace_semantics": "UNCHANGED_SYNTHETIC_ECONOMIC_TRANSITIONS_NOT_AGENT_PROVENANCE",
        "model_valid_decisions": statuses.count("VALID_MODEL_DECISION") if live else 0,
        "live_calls_attempted": audit["calls_attempted"] if live else 0,
        "scenario_sha256": digest(scenario), "adapter_source_sha256": source_hash(),
        "engine_receipt_sha256": result["sha256"], "audit": audit, "engine_result": result,
        "metrics": metrics(result, scenario, focal_agent)}
    sidecar["sha256"] = digest(sidecar)
    return sidecar


def replay_episode(scenario, sidecar):
    if sidecar.get("version") != "llm-agent-1": raise ValueError("INVALID_VERSION")
    if digest({k: v for k, v in sidecar.items() if k != "sha256"}) != sidecar["sha256"]:
        raise ValueError("SIDECAR_HASH_MISMATCH")
    if sidecar["adapter_source_sha256"] != source_hash(): raise ValueError("SOURCE_MISMATCH")
    if digest(scenario) != sidecar["scenario_sha256"]: raise ValueError("SCENARIO_MISMATCH")
    validate_audit(sidecar["audit"])
    origin = sidecar["audit"]["decision_origin"]
    live = origin == "LIVE_LOCAL_LLM"
    expected_valid = sum(r["status"] == "VALID_MODEL_DECISION" for r in sidecar["audit"]["records"])
    if (sidecar["decision_origin"] != origin or sidecar["model_valid_decisions"] != expected_valid
            or sidecar["live_calls_attempted"] != (sidecar["audit"]["calls_attempted"] if live else 0)
            or sidecar["engine_receipt_sha256"] != sidecar["engine_result"]["sha256"]
            or sidecar["environment_origin"] != "SYNTHETIC"
            or sidecar["signal_origin"] != "EXOGENOUS_SYNTHETIC_BELIEFS"
            or sidecar["other_decisions"] != "SCRIPTED_SIGNAL_FOLLOWING"
            or sidecar["engine_trace_semantics"] != "UNCHANGED_SYNTHETIC_ECONOMIC_TRANSITIONS_NOT_AGENT_PROVENANCE"):
        raise ValueError("SIDECAR_PROVENANCE_DISAGREEMENT")
    policy = RecordedPolicy(sidecar["audit"])
    policies = {a: SignalFollowing() for a in scenario["agents"]}
    policies[sidecar["focal_agent"]] = policy
    actual = run(deepcopy(scenario), sidecar["engine_result"]["mechanism"], policies=policies)
    from .experiments import metrics
    if sidecar["metrics"] != metrics(actual, scenario, sidecar["focal_agent"]):
        raise ValueError("METRICS_MISMATCH")
    if policy.cursor != len(sidecar["audit"]["records"]) or actual != sidecar["engine_result"]:
        raise ValueError("ECONOMIC_REPLAY_MISMATCH")
    return {"version": "llm-replay-1", "execution_origin": "RECORDED_DECISION_REPLAY",
        "new_inference_calls": 0, "source_sidecar_sha256": sidecar["sha256"],
        "engine_receipt_sha256": actual["sha256"]}
