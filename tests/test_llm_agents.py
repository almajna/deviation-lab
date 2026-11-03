"""Offline instrument tests. Scripted transports are never real LLM evidence."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from deviation.data.pipeline import digest
from deviation.markets.runner import _prepare, packet, run
from deviation_llm_agents.adapter import (abstain, certificate_problem, decode,
    encode, prompt, strict_json, validate_packet)
from deviation_llm_agents.experiments import Control, metrics, scenario
from deviation_llm_agents.harness import Budget, LocalPolicy, RecordedPolicy, run_episode, replay_episode
from deviation_llm_agents.local import OllamaLocal


def initial_packet():
    s = scenario()
    public = {k: v for k, v in s.items() if k != "sealed_outcomes"}
    _, artifact, _, _, e = _prepare(public)
    actor, mid = sorted(e.tokens)[0]
    return packet(e, public, actor, mid, "lmsr", artifact)


class TestBackend:
    origin = "SCRIPTED_TRANSPORT_TEST"
    metadata = {"origin": origin, "model": "NO_MODEL_TEST_FIXTURE"}

    def __init__(self, raw=None, error=None, tokens=10):
        self.raw, self.error, self.tokens, self.calls = raw, error, tokens, 0

    def infer(self, messages, *, seed, max_tokens):
        self.calls += 1
        if self.error: raise self.error
        p = json.loads(messages["user"])["packet"]
        raw = self.raw if self.raw is not None else encode({"report": p["own_signal"]} if p["stage"] == "REPORT_COMMIT" else {"choice": 0})
        return {"raw": raw, "usage": {"prompt_eval_count": 20, "eval_count": self.tokens}}


class LLMHarnessTests(unittest.TestCase):
    def test_roundtrip_strict_action_and_identity_binding(self):
        p = initial_packet(); validate_packet(p)
        out = decode('{"report":[1,1,8]}', p)
        self.assertEqual(out["actor"], p["agent_id"])
        self.assertEqual(out["counts"], [1, 1, 8])
        self.assertIsNone(decode('{"decline":true}', p))
        for bad in ['{"report":[true,1,8]}', '{"report":[0,0,11]}', '{"report":[1,1,8],"actor":"other"}',
                    '{"report":[1,1,8],"report":[0,0,10]}', '```json\n{"decline":true}\n```',
                    '{"decline":1}', 'null', '[1,1,8]', '{"report":[NaN,1,9]}', '__import__("os")']:
            with self.subTest(raw=bad), self.assertRaises((ValueError, TypeError)):
                decode(bad, p)

    def test_budget_caps_count_failed_attempts_and_never_retry(self):
        b = TestBackend(error=OSError("offline")); policy = LocalPolicy(b, Budget(max_calls=1))
        p = initial_packet()
        self.assertIsNone(policy.act(p)); self.assertIsNone(policy.act(p))
        audit = policy.audit()
        self.assertEqual(b.calls, 1)
        self.assertEqual(audit["calls_attempted"], 1)
        self.assertEqual(audit["unknown_usage_calls"], 1)
        self.assertEqual([r["status"] for r in audit["records"]], ["FAILED_DECISION", "BUDGET_EXHAUSTED_NO_INFERENCE"])
        self.assertFalse(audit["records"][1]["attempted"])

    def test_prompt_and_response_budget_and_server_token_violation(self):
        p = initial_packet()
        for budget in [Budget(max_calls=0), Budget(max_prompt_bytes=0), Budget(max_response_bytes=0)]:
            backend = TestBackend(); policy = LocalPolicy(backend, budget)
            policy.act(p); self.assertEqual(backend.calls, 0)
        for budget, backend in [(Budget(max_response_bytes=1), TestBackend()),
                                (Budget(max_tokens_per_call=2), TestBackend(tokens=3))]:
            policy = LocalPolicy(backend, budget); policy.act(p)
            self.assertEqual(policy.records[0]["status"], "FAILED_DECISION")
            self.assertIsNotNone(policy.records[0]["raw"])
            self.assertIsNotNone(policy.records[0]["usage"])
        for value in [-1, True, 0.5]:
            with self.assertRaises(ValueError): Budget(max_calls=value)

    def test_unknown_and_nested_hidden_packet_fields_fail(self):
        p = initial_packet()
        for path in [[], ["limits"], ["markets", p["market_id"]], ["public_tasks", 0], ["history", 0, "payload"]]:
            bad = deepcopy(p); target = bad
            for key in path: target = target[key]
            target["sealed_outcomes"] = [{"quality": 1}]
            with self.subTest(path=path), self.assertRaises(ValueError): validate_packet(bad)
        bad = deepcopy(p); bad["history"][0]["payload"]["q"] = {"answer": 1}
        with self.assertRaises(ValueError): validate_packet(bad)
        bad = deepcopy(p); bad["own_utility_view"]["development"]["hidden"] = 99
        with self.assertRaises(ValueError): validate_packet(bad)

    def test_private_future_and_post_settlement_history_rejected(self):
        p = initial_packet()
        for key, value in [("visibility", "PRIVATE"), ("seq", p["seq"]), ("time_step", p["seq"]), ("stage", "SETTLED")]:
            bad = deepcopy(p); bad["history"][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): validate_packet(bad)

    def test_real_test_and_replay_origins_are_distinct(self):
        s = scenario(); policy = LocalPolicy(TestBackend())
        sidecar = run_episode(s, "focal", policy)
        self.assertEqual(sidecar["model_valid_decisions"], 0)
        self.assertEqual(sidecar["live_calls_attempted"], 0)
        self.assertEqual(sidecar["decision_origin"], "SCRIPTED_TRANSPORT_TEST")
        self.assertEqual(sidecar["engine_result"]["trace"]["agent_origin"], "SYNTHETIC")
        replay = replay_episode(s, sidecar)
        self.assertEqual(replay["new_inference_calls"], 0)
        self.assertEqual(replay["execution_origin"], "RECORDED_DECISION_REPLAY")
        self.assertEqual(replay["engine_receipt_sha256"], sidecar["engine_receipt_sha256"])

    def test_invalid_outputs_remain_failure_not_model_noop(self):
        sidecar = run_episode(scenario(), "focal", LocalPolicy(TestBackend(raw="send code!")))
        self.assertTrue(all(r["status"] == "FAILED_DECISION" for r in sidecar["audit"]["records"]))
        self.assertEqual(sidecar["model_valid_decisions"], 0)
        self.assertTrue(all(c["model_id"] is not None for c in sidecar["engine_result"]["allocation_plan"]["allocations"]))
        replay_episode(scenario(), sidecar)

    def test_outcome_mutation_cannot_affect_prompts_or_commands(self):
        a = scenario(); b = deepcopy(a)
        for row in b["sealed_outcomes"]: row.update(quality=0.5, cost_decimal="0.00009")
        first = run_episode(a, "focal", LocalPolicy(TestBackend()))
        second = run_episode(b, "focal", LocalPolicy(TestBackend()))
        self.assertEqual(first["engine_result"]["allocation_plan"], second["engine_result"]["allocation_plan"])
        for one, two in zip(first["audit"]["records"], second["audit"]["records"]):
            for key in ["prompt", "action", "packet_sha256"]: self.assertEqual(one[key], two[key])

    def test_recorded_actions_require_exact_context_and_source_hash(self):
        s = scenario(); sidecar = run_episode(s, "focal", LocalPolicy(TestBackend()))
        bad = deepcopy(sidecar); bad["audit"]["records"][0]["raw"] = '{"decline":true}'
        with self.assertRaisesRegex(ValueError, "SIDECAR_HASH"): replay_episode(s, bad)
        bad["sha256"] = digest({k: v for k, v in bad.items() if k != "sha256"})
        with self.assertRaisesRegex(ValueError, "RECORDED_DECISION_HASH"): replay_episode(s, bad)
        p = initial_packet(); policy = RecordedPolicy(sidecar["audit"])
        p["own_cash"] += 1
        with self.assertRaisesRegex(ValueError, "CONTEXT"): policy.act(p)

    def test_rehashed_false_provenance_and_budget_counters_rejected(self):
        s = scenario(); good = run_episode(s, "focal", LocalPolicy(TestBackend()))
        changes = [("decision_origin", "LIVE_LOCAL_LLM"), ("model_valid_decisions", 999999),
            ("live_calls_attempted", 999999), ("engine_receipt_sha256", "a" * 64)]
        for key, value in changes:
            bad = deepcopy(good); bad[key] = value
            bad["sha256"] = digest({k:v for k,v in bad.items() if k != "sha256"})
            with self.subTest(key=key), self.assertRaises(ValueError): replay_episode(s, bad)
        for key in ["calls_attempted", "response_bytes_received", "unknown_usage_calls", "prompt_bytes_sent"]:
            bad = deepcopy(good); bad["audit"][key] = 999999
            bad["sha256"] = digest({k:v for k,v in bad.items() if k != "sha256"})
            with self.subTest(key=key), self.assertRaises(ValueError): replay_episode(s, bad)

    def test_malformed_backend_usage_always_retains_attempt_and_raw_response(self):
        class Bad(TestBackend):
            def infer(self, *args, **kwargs): return {"raw": '{"choice":0}', "usage": None}
        policy = LocalPolicy(Bad()); policy.act(initial_packet())
        self.assertEqual(policy.records[0]["raw"], '{"choice":0}')
        self.assertEqual(policy.records[0]["status"], "FAILED_DECISION")
        self.assertEqual(policy.audit()["unknown_usage_calls"], 1)
        class Nonfinite(TestBackend):
            def infer(self, *args, **kwargs):
                return {"raw": '{"choice":0}', "usage": {"eval_count": 3, "prompt_eval_count": 2, "total_duration": float("nan")}}
        policy = LocalPolicy(Nonfinite()); policy.act(initial_packet())
        self.assertEqual(policy.records[0]["status"], "FAILED_DECISION")
        self.assertEqual(policy.records[0]["error_code"], "NONCANONICAL_USAGE")

    def test_oversized_context_is_refused_before_inference(self):
        with self.assertRaisesRegex(ValueError, "UNSUPPORTED_CONTEXT_LIMIT"):
            Budget(max_prompt_bytes_per_call=8193)
        p = initial_packet(); p["public_tasks"][0]["prompt"] = "x" * 20000
        backend = TestBackend(); policy = LocalPolicy(backend)
        policy.act(p)
        self.assertEqual(backend.calls, 0)
        self.assertEqual(policy.records[0]["status"], "INPUT_TOO_LARGE_NO_INFERENCE")

    def test_truthful_capability_mode_is_separate_from_utility_mode(self):
        p = initial_packet()
        self.assertNotEqual(prompt(p, mode="truthful"), prompt(p, mode="utility"))
        with self.assertRaises(ValueError): prompt(p, mode="bogus")

    def test_certificate_adapter_is_outcome_free_and_horizon_explicit(self):
        p = initial_packet(); context = certificate_problem(p)
        self.assertFalse(context["outcome_access"])
        self.assertEqual(context["scope"], "NO_FUTURE_POLICY_MODEL")
        context["information"]["own_cash"] = -1
        self.assertGreater(p["own_cash"], 0)

    def test_scripted_controls_use_real_engine_and_independent_payoff_checker(self):
        s = scenario(benefit=200)
        for mechanism in ["lmsr", "pool", "cheapest"]:
            records = {k: run(s, mechanism, policies={"focal": Control(k)}) for k in ["signal", "no_action", "directional_terminal"]}
            for r in records.values():
                m = metrics(r, s); self.assertTrue(m["cash_conserved"])
                self.assertEqual(m["realized_utility"], r["trace"]["events"][-1]["payload"]["controllers"]["controller"]["utility"])
            if mechanism == "cheapest":
                self.assertEqual(len({digest(r["allocation_plan"]) for r in records.values()}), 1)

    def test_cli_live_is_explicit_and_bad_manifest_does_not_call_network(self):
        with tempfile.TemporaryDirectory() as d:
            manifest = Path(d)/"model.json"; manifest.write_text('{}')
            r = subprocess.run([sys.executable, "-m", "deviation_llm_agents", "live", "--model-manifest", str(manifest), "--out", str(Path(d)/"out.json")], capture_output=True)
            self.assertNotEqual(r.returncode, 0)
            artifact = json.loads((Path(d)/"out.json").read_text())
            self.assertEqual(artifact["status"], "BLOCKED_BEFORE_INFERENCE")
            self.assertEqual(artifact["inference_calls_attempted"], 0)


class OllamaTests(unittest.TestCase):
    manifest = {"model": "local:test", "digest": "a"*64, "source": "https://example.org/model", "license": "TEST_FIXTURE"}

    @staticmethod
    def response(path, body=None):
        if path == "/api/tags": return {"models": [{"name": "local:test", "digest": "a"*64, "size": 100, "details": {"format": "gguf"}}]}
        if path == "/api/show": return {"license": "TEST_FIXTURE"}
        if path == "/api/version": return {"version": "TEST_FIXTURE"}
        if path == "/api/chat": return {"model": "local:test", "done": True, "message": {"content": '{"choice":0}'}, "eval_count": 4, "prompt_eval_count": 10}
        raise AssertionError(path)

    def test_remote_redirect_or_cloud_endpoint_refused_before_network(self):
        for endpoint in ["https://127.0.0.1:11434", "http://localhost:11434", "http://1.2.3.4:11434", "http://127.0.0.1:11434/api", "http://user:pass@127.0.0.1:11434", "http://127.0.0.1:11434?x=1"]:
            with self.subTest(endpoint=endpoint), self.assertRaises(ValueError): OllamaLocal(self.manifest, endpoint)
        bad = dict(self.manifest, model="model:cloud")
        with self.assertRaises(ValueError): OllamaLocal(bad)

    def test_local_manifest_digest_and_generation_options(self):
        calls = []
        def handle(path, body=None):
            calls.append((path, body)); return self.response(path, body)
        with patch.object(OllamaLocal, "request", side_effect=handle):
            b = OllamaLocal(self.manifest)
            reply = b.infer({"system": "test", "user": "test"}, seed=9, max_tokens=50)
        self.assertEqual(reply["raw"], '{"choice":0}')
        chat = next(body for path, body in calls if path == "/api/chat")
        self.assertFalse(chat["stream"])
        self.assertEqual(chat["options"]["temperature"], 0)
        self.assertEqual(chat["options"]["num_predict"], 50)
        self.assertNotIn("tools", chat)
        self.assertFalse(any("pull" in path for path, _ in calls))

    def test_changed_digest_or_remote_model_metadata_rejected(self):
        for kind in ["digest", "remote"]:
            def handle(path, body=None):
                r = self.response(path, body)
                if path == "/api/tags":
                    if kind == "digest": r["models"][0]["digest"] = "b"*64
                    else: r["models"][0]["remote_host"] = "https://example.org"
                return r
            with self.subTest(kind=kind), patch.object(OllamaLocal, "request", side_effect=handle), self.assertRaises(ValueError):
                OllamaLocal(self.manifest)


if __name__ == "__main__": unittest.main()
