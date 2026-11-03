"""Prospective six-episode CPU pilot; no outcome datasets or paid endpoints."""
import argparse
import base64
from copy import deepcopy
import gzip
import hashlib
import json
import os
from pathlib import Path

from deviation.data.pipeline import digest
from deviation.markets.runner import run
from .experiments import Control, metrics, scenario, write_json
from .harness import Budget, LocalPolicy, replay_episode, run_episode, source_hash

PROTOCOL_SHA256 = "7b0c363fbe1495081a66c927821bab61790ca112e881b6b9e5ba5de742657e2e"


def validate_protocol(config):
    if digest(config) != PROTOCOL_SHA256: raise ValueError("UNREVIEWED_PILOT_PROTOCOL")


def run_pilot(config, backend, *, execution):
    validate_protocol(config)
    episodes = []
    for signal in config["signals"]:
        for condition in config["conditions"]:
            s = scenario(config["seed"], signal, condition["benefit"], config["fee"])
            policy = LocalPolicy(backend, Budget(max_calls=config["max_calls_per_episode"],
                max_tokens_per_call=config["max_new_tokens"]), seed=config["seed"], mode=condition["mode"])
            sidecar = run_episode(s, "focal", policy)
            controls = {}
            for mechanism in ["lmsr", "pool", "cheapest"]:
                for control in ["signal", "no_action", "directional_terminal"]:
                    receipt = run(s, mechanism, policies={"focal": Control(control)})
                    controls[mechanism + "/" + control] = {"receipt": receipt, "metrics": metrics(receipt, s)}
            episode = {"setting": {"signal": signal, **condition, "seed": config["seed"], "fee": config["fee"]},
                "scenario": s, "sidecar": sidecar, "replay": replay_episode(s, sidecar),
                "scripted_controls": controls}
            episodes.append(episode)
            print("PILOT_PROGRESS " + json.dumps({"setting": episode["setting"],
                "calls": sidecar["live_calls_attempted"], "valid": sidecar["model_valid_decisions"]}), flush=True)
    calls = sum(e["sidecar"]["live_calls_attempted"] for e in episodes)
    result = {"version": "llm-real-pilot-1", "protocol": deepcopy(config), "protocol_sha256": digest(config),
        "adapter_source_sha256": source_hash(), "execution": execution, "episodes": episodes,
        "calls_attempted": calls, "valid_model_decisions": sum(e["sidecar"]["model_valid_decisions"] for e in episodes)}
    result["sha256"] = digest(result)
    return result


def verify_pilot(bundle):
    if bundle["version"] != "llm-real-pilot-1" or bundle["adapter_source_sha256"] != source_hash():
        raise ValueError("PILOT_SOURCE_OR_VERSION_MISMATCH")
    if digest({k: v for k, v in bundle.items() if k != "sha256"}) != bundle["sha256"]:
        raise ValueError("PILOT_DIGEST_MISMATCH")
    if digest(bundle["protocol"]) != bundle["protocol_sha256"]: raise ValueError("PROTOCOL_MISMATCH")
    validate_protocol(bundle["protocol"])
    expected_settings = [{"signal": s, **c, "seed": 7, "fee": 2}
        for s in bundle["protocol"]["signals"] for c in bundle["protocol"]["conditions"]]
    if [e["setting"] for e in bundle["episodes"]] != expected_settings:
        raise ValueError("PILOT_SETTING_COVERAGE")
    calls = valid = 0
    backend_hashes = set()
    for e in bundle["episodes"]:
        setting = e["setting"]
        if e["scenario"] != scenario(setting["seed"], setting["signal"], setting["benefit"], setting["fee"]):
            raise ValueError("PILOT_SCENARIO_MISMATCH")
        if (len(e["sidecar"]["audit"]["records"]) != 4
                or e["sidecar"]["audit"]["budget"]["max_calls"] != 4
                or e["sidecar"]["audit"]["budget"]["max_tokens_per_call"] != 64
                or any(r["mode"] != setting["mode"] for r in e["sidecar"]["audit"]["records"])):
            raise ValueError("PILOT_DECISION_BUDGET_OR_MODE")
        if set(e["scripted_controls"]) != {m + "/" + c for m in ["lmsr", "pool", "cheapest"]
                for c in ["signal", "no_action", "directional_terminal"]}:
            raise ValueError("PILOT_CONTROL_COVERAGE")
        backend = e["sidecar"]["audit"]["backend"]
        backend_hashes.add(digest(backend))
        if e["sidecar"]["decision_origin"] == "LIVE_LOCAL_LLM":
            config = bundle["protocol"]
            if (backend.get("backend") != "transformers_cpu" or backend.get("model") != config["model"]
                    or backend.get("revision") != config["revision"] or backend.get("license") != config["license"]
                    or backend.get("file_sha256", {}).get("model.safetensors") != config["weights_sha256"]
                    or backend.get("device") != "cpu"):
                raise ValueError("PILOT_MODEL_IDENTITY_MISMATCH")
            for row in e["sidecar"]["audit"]["records"]:
                if row["usage"] is None: continue  # Failed/unknown usage is not successful inference evidence.
                evidence = row.get("generation_evidence", {})
                for key, usage_key in [("prompt_token_ids", "prompt_eval_count"), ("output_token_ids", "eval_count")]:
                    ids = evidence.get(key)
                    if not isinstance(ids, list) or not all(type(v) is int and v >= 0 for v in ids) or len(ids) != row["usage"][usage_key]:
                        raise ValueError("PILOT_TOKEN_EVIDENCE_MISMATCH")
        if replay_episode(e["scenario"], e["sidecar"]) != e["replay"]: raise ValueError("PILOT_REPLAY_MISMATCH")
        calls += e["sidecar"]["live_calls_attempted"]
        valid += e["sidecar"]["model_valid_decisions"]
        for key, record in e["scripted_controls"].items():
            mechanism, control = key.split("/")
            actual = run(e["scenario"], mechanism, policies={"focal": Control(control)})
            if actual != record["receipt"] or metrics(actual, e["scenario"]) != record["metrics"]:
                raise ValueError("SCRIPTED_CONTROL_REPLAY_MISMATCH")
    if len(backend_hashes) != 1: raise ValueError("PILOT_BACKEND_CHANGED")
    if calls != bundle["calls_attempted"] or valid != bundle["valid_model_decisions"]:
        raise ValueError("PILOT_COUNT_MISMATCH")
    return {"version": "llm-pilot-replay-1", "source_pilot_sha256": bundle["sha256"],
        "new_inference_calls": 0, "episodes_reproduced": len(bundle["episodes"])}


def log_bundle(bundle):
    raw = json.dumps(bundle, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    zipped = gzip.compress(raw, mtime=0)
    encoded = base64.b64encode(zipped).decode()
    print("PILOT_BUNDLE_SHA256 " + hashlib.sha256(raw).hexdigest(), flush=True)
    for i in range(0, len(encoded), 8000): print("PILOT_BUNDLE_CHUNK " + encoded[i:i+8000], flush=True)
    print("PILOT_BUNDLE_END", flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", default="experiments/llm_real_pilot.json")
    p.add_argument("--out", required=True)
    p.add_argument("--cache", default="/tmp/deviation-pilot-model")
    p.add_argument("--verify")
    args = p.parse_args()
    if args.verify:
        write_json(args.out, verify_pilot(json.loads(Path(args.verify).read_text()))); return
    config = json.loads(Path(args.config).read_text())
    validate_protocol(config)
    execution = {k: os.environ.get(k) for k in ["GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_SHA", "RUNNER_OS", "RUNNER_ARCH"]}
    from .transformers_cpu import TransformersCPU
    backend = TransformersCPU(config, args.cache)
    bundle = run_pilot(config, backend, execution=execution)
    write_json(args.out, bundle)
    log_bundle(bundle)


if __name__ == "__main__": main()
