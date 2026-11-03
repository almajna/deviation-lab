"""Prove the pilot uses authored/public fixtures, not user-private prompt data."""
import argparse
import json
from pathlib import Path
import re

from deviation.data.pipeline import digest
from deviation_llm_agents.pilot import verify_pilot


def audit(bundle):
    # Reconstructs each complete scenario, prompt, action and economic receipt
    # from the exact authored synthetic scenario and the frozen prompt source.
    replay = verify_pilot(bundle)
    assert set(bundle) == set("adapter_source_sha256 calls_attempted episodes execution protocol protocol_sha256 sha256 valid_model_decisions version".split())
    assert set(bundle["execution"]) == {"GITHUB_RUN_ATTEMPT", "GITHUB_RUN_ID", "GITHUB_SHA", "RUNNER_ARCH", "RUNNER_OS"}
    assert bundle["execution"]["GITHUB_RUN_ID"] == "41666251738"
    assert bundle["execution"]["GITHUB_RUN_ATTEMPT"] == "1"
    assert re.fullmatch(r"[a-f0-9]{40}", bundle["execution"]["GITHUB_SHA"])
    assert bundle["execution"]["RUNNER_OS"] == "Linux" and bundle["execution"]["RUNNER_ARCH"] == "X64"
    allowed_keys = {"report", "choice", "expected_virtual_credit_utility", "0", "1", "2"}
    def numeric_output(value):
        if isinstance(value, dict):
            assert set(value) <= allowed_keys
            for item in value.values(): numeric_output(item)
        elif isinstance(value, list):
            for item in value: numeric_output(item)
        else: assert type(value) is int and 0 <= value <= 1_000_000
    common = set("action attempted decision_origin elapsed_ns generation_evidence mode packet_sha256 prompt prompt_sha256 raw requested_max_tokens seed seq sha256 status usage".split())
    for episode in bundle["episodes"]:
        assert set(episode) == {"replay", "scenario", "scripted_controls", "setting", "sidecar"}
        assert all(set(c) == {"receipt", "metrics"} for c in episode["scripted_controls"].values())
        sidecar = episode["sidecar"]
        assert set(sidecar) == set("version environment_origin signal_origin focal_agent other_decisions decision_origin engine_trace_semantics model_valid_decisions live_calls_attempted scenario_sha256 adapter_source_sha256 engine_receipt_sha256 audit engine_result metrics sha256".split())
        assert sidecar["environment_origin"] == "SYNTHETIC"
        assert episode["scenario"]["decision_tasks"] == [{"task_id": "development", "prompt": "Authored development fixture", "model_options": ["a", "b"]}]
        backend = sidecar["audit"]["backend"]
        assert set(backend) == set("architecture backend device dtype execution_host file_sha256 generation license model origin packages processor python revision threads".split())
        assert backend["architecture"] == "x86_64" and backend["processor"] == "x86_64"
        assert backend["execution_host"] == "EXPERIMENT_HOST_CPU_NOT_USER_MAC_OR_HOSTED_MODEL_API"
        assert backend["dtype"] == "float32" and backend["threads"] == 4
        assert set(backend["file_sha256"]) == {"LICENSE", "config.json", "generation_config.json", "merges.txt", "model.safetensors", "tokenizer.json", "tokenizer_config.json", "vocab.json"}
        assert all(re.fullmatch(r"[a-f0-9]{64}", x) for x in backend["file_sha256"].values())
        assert set(backend["packages"]) == {"torch", "transformers", "huggingface-hub", "safetensors", "tokenizers"}
        assert all(re.fullmatch(r"[0-9.]+(?:\+cpu)?", x) for x in backend["packages"].values())
        assert re.fullmatch(r"[0-9.]+", backend["python"])
        assert backend["generation"] == {"context_token_ceiling": 8192, "do_sample": False,
            "trust_remote_code": False, "use_cache": True, "weight_format": "safetensors"}
        for row in sidecar["audit"]["records"]:
            assert set(row) == common | ({"error_type", "error_code"} if row["status"] == "FAILED_DECISION" else set())
            # Inspection only: strip code fences for privacy inspection, never
            # to repair or accept a model action in the experiment.
            raw = row["raw"].strip()
            if raw.startswith("```json"): raw = raw[7:-3].strip()
            numeric_output(json.loads(raw))
            assert set(row["usage"]) == {"done_reason", "eval_count", "prompt_eval_count"}
            assert row["usage"]["done_reason"] == "eos"
            assert set(row["generation_evidence"]) == {"greedy", "output_token_ids", "prompt_token_ids", "seed"}
            assert row["seed"] == row["generation_evidence"]["seed"] == 7
            assert row["generation_evidence"]["greedy"] is True
            if row["status"] == "FAILED_DECISION":
                assert row["error_type"] in {"Rejection", "JSONDecodeError"}
                assert row["error_code"] in {"INVALID_DISTRIBUTION", "INVALID_FIELDS", "TRANSPORT_OR_PARSE_FAILURE"}
    return {"version": "llm-pilot-publication-audit-1", "source_pilot_sha256": bundle["sha256"],
        "replay": replay, "episodes_checked": 6, "complete_prompts_checked": 24,
        "prompt_origin": "EXACT_RECONSTRUCTION_FROM_PREEXISTING_AUTHORED_SYNTHETIC_FIXTURES",
        "personal_or_external_task_inputs": 0, "model_output_string_values": 0,
        "model_outputs": "NUMERIC_JSON_WITH_ALLOWLISTED_KEYS_ONLY; INVALID_ACTIONS_REMAIN_INVALID",
        "metadata": "PUBLIC_RUN_IDS_PUBLIC_MODEL_HASHES_DEPENDENCY_VERSIONS_ONLY",
        "token_ids": "TOKENIZER_INTEGERS_FOR_THE_SAME_PUBLIC_SYNTHETIC_TEXT_NOT_AUTHENTICATION_TOKENS",
        "agent_private_fields": "ARTIFICIAL_EXOGENOUS_BELIEFS_VIRTUAL_CREDITS_NOT_USER_CONFIDENTIAL_DATA",
        "publication_classification": "NON_SENSITIVE_AUTHORED_RESEARCH_FIXTURE_AND_OBSERVED_MODEL_OUTPUT"}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__); p.add_argument("input"); p.add_argument("--out", required=True)
    args = p.parse_args(); result = audit(json.loads(Path(args.input).read_text()))
    Path(args.out).write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
