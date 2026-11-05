"""Exercise pinned, unmodified LiteLLM against a loopback HTTP fixture provider."""
import argparse
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import threading
import time
import traceback

from check_litellm_reality import allocation_summary, check


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


class Provider:
    def __init__(self, config, condition, mode, encoding):
        self.config, self.condition, self.mode = config, condition, mode
        self.encoding = encoding
        self.completion_tokens = len(encoding.encode(config["response_text"]))
        self.prompt_tokens = len(encoding.encode(config["messages"][0]["content"])) + 7
        self.receipts = []
        self.counts = {"A": 0, "B": 0}
        self.lock = threading.Lock()

    def respond(self, handler):
        provider = handler.path.split("/")[1]
        if provider not in self.counts or not handler.path.endswith("/chat/completions"):
            handler.send_error(404)
            return
        body = json.loads(handler.rfile.read(int(handler.headers["Content-Length"])))
        with self.lock:
            self.counts[provider] += 1
            ordinal = self.counts[provider]
        identifier = f"chatcmpl-{provider}-{ordinal}"
        factor = self.config["inflation_factor"] if provider == "B" and self.condition != "honest" else 1
        raw = {"prompt_tokens": self.prompt_tokens, "completion_tokens": self.completion_tokens * factor}
        raw["total_tokens"] = sum(raw.values())
        forwarded = dict(raw)
        if self.condition == "defended":
            forwarded["completion_tokens"] = len(self.encoding.encode(self.config["response_text"]))
            forwarded["total_tokens"] = forwarded["prompt_tokens"] + forwarded["completion_tokens"]
        fail = self.mode == "cooldown" and provider == "B" and ordinal == self.config["B_error_ordinal"]
        receipt = {"provider": provider, "ordinal": ordinal, "id": identifier,
                   "received_utc": datetime.now(timezone.utc).isoformat(), "request": body,
                   "raw_usage": raw, "forwarded_usage": forwarded, "status": 429 if fail else 200,
                   "configured_delay_seconds": self.config["provider_delay_seconds"][provider]}
        with self.lock:
            self.receipts.append(receipt)
        started = time.perf_counter()
        time.sleep(self.config["provider_delay_seconds"][provider])
        if fail:
            payload = json.dumps({"error": {"message": "Controlled provider quota refusal", "type": "rate_limit_error", "code": "rate_limit_exceeded"}}).encode()
            handler.send_response(429)
            handler.send_header("Content-Type", "application/json")
            handler.send_header("Content-Length", str(len(payload)))
            handler.send_header("Retry-After", str(self.config["cooldown_seconds"]))
            handler.end_headers()
            handler.wfile.write(payload)
        elif body.get("stream"):
            handler.send_response(200)
            handler.send_header("Content-Type", "text/event-stream")
            handler.send_header("Connection", "close")
            handler.end_headers()
            base = {"id": identifier, "object": "chat.completion.chunk", "created": 1, "model": self.config["model"]}
            chunks = [dict(base, choices=[{"index": 0, "delta": {"role": "assistant", "content": self.config["response_text"]}, "finish_reason": None}]),
                      dict(base, choices=[{"index": 0, "delta": {}, "finish_reason": "stop"}]),
                      dict(base, choices=[], usage=forwarded)]
            for chunk in chunks:
                handler.wfile.write(("data: " + json.dumps(chunk) + "\n\n").encode())
                handler.wfile.flush()
            handler.wfile.write(b"data: [DONE]\n\n")
            handler.wfile.flush()
            handler.close_connection = True
        else:
            payload = json.dumps({"id": identifier, "object": "chat.completion", "created": 1,
                                  "model": self.config["model"], "choices": [{"index": 0,
                                  "message": {"role": "assistant", "content": self.config["response_text"]},
                                  "finish_reason": "stop"}], "usage": forwarded}).encode()
            handler.send_response(200)
            handler.send_header("Content-Type", "application/json")
            handler.send_header("Content-Length", str(len(payload)))
            handler.end_headers()
            handler.wfile.write(payload)
        receipt["server_elapsed_seconds"] = time.perf_counter() - started


async def run_case(config, mode, condition, seed):
    import litellm
    import tiktoken
    from litellm.integrations.custom_logger import CustomLogger

    class Observer(CustomLogger):
        def __init__(self):
            self.events = []

        async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
            usage = getattr(response_obj, "usage", None)
            self.events.append({"kind": "success", "id": getattr(response_obj, "id", None),
                                "start": start_time.isoformat(), "end": end_time.isoformat(),
                                "usage": usage.model_dump() if usage is not None else None})

        async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time):
            self.events.append({"kind": "failure", "start": start_time.isoformat(), "end": end_time.isoformat()})

    litellm.telemetry = False
    observer = Observer()
    litellm.callbacks = [observer]
    provider = Provider(config, condition, mode, tiktoken.get_encoding(config["tokenizer"]))

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            provider.respond(self)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    deployments = []
    for name in ("A", "B"):
        deployments.append({"model_name": "offline-group", "model_info": {"id": name},
                            "litellm_params": {"model": "openai/" + config["model"],
                            "api_base": f"http://127.0.0.1:{server.server_port}/{name}/v1",
                            "api_key": "offline-fixture", "max_retries": 0,
                            "tpm": config["limited_B_tpm"] if name == "B" and mode == "tpm" else config["high_tpm"],
                            "rpm": config["limited_B_rpm"] if name == "B" and mode == "rpm" else config["high_rpm"]}})
    router = litellm.Router(model_list=deployments, routing_strategy="simple-shuffle" if mode == "shuffle" else "latency-based-routing",
                            num_retries=0, max_fallbacks=0, timeout=5, allowed_fails=0,
                            cooldown_time=config["cooldown_seconds"], disable_cooldowns=False,
                            enable_pre_call_checks=True)
    selector = getattr(router, "lowestlatency_logger", None)
    if selector is not None:
        selector.test_flag = True  # Observational counter already supplied by upstream.
    random.seed(seed)
    rows = []
    case = {"mode": mode, "condition": condition, "seed": seed, "rows": rows,
            "actual_completion_tokens": provider.completion_tokens, "prompt_tokens": provider.prompt_tokens,
            "routing_args": selector.routing_args.model_dump() if selector is not None else None,
            "router_type": str(type(router._core)), "config": deployments}
    traced = {}
    files = {"lowest_latency.py", "convert_dict_to_response.py", "gpt_transformation.py", "router_python_core.py"}

    def trace(frame, event, arg):
        filename = frame.f_code.co_filename
        if event == "call" and Path(filename).name in files:
            key = filename + ":" + frame.f_code.co_name
            traced[key] = traced.get(key, 0) + 1

    sys.setprofile(trace)
    try:
        for index in range(config["warmup_requests"] + config["measured_requests"]):
            stream = mode == "stream" or (mode == "cold_stream" and index >= config["warmup_requests"])
            phase = "warmup" if index < config["warmup_requests"] else "measured"
            before = len(provider.receipts)
            observed_before = len(observer.events)
            logged_before = selector.logged_success if selector is not None else 0
            row = {"index": index, "phase": phase, "stream": stream,
                   "started_utc": datetime.now(timezone.utc).isoformat(), "error": None,
                   "provider": None, "response_id": None, "ttft_seconds": None}
            started = time.perf_counter()
            content = ""
            try:
                options = {"stream_options": {"include_usage": True}} if stream else {}
                response = await router.acompletion(model="offline-group", messages=config["messages"],
                                                    stream=stream, max_tokens=config["max_tokens"], **options)
                if stream:
                    async for chunk in response:
                        row["response_id"] = chunk.id
                        if chunk.choices:
                            delta = chunk.choices[0].delta.content or ""
                            if delta and row["ttft_seconds"] is None:
                                row["ttft_seconds"] = time.perf_counter() - started
                            content += delta
                else:
                    row["response_id"] = response.id
                    content = response.choices[0].message.content
                    row["returned_usage"] = response.usage.model_dump()
            except Exception as error:
                row["error"] = {"type": type(error).__name__, "message": str(error)[:1200]}
            row["client_seconds"] = time.perf_counter() - started
            deadline = time.monotonic() + config["max_callback_wait_seconds"]
            while time.monotonic() < deadline:
                source_done = selector is None or row["error"] is not None or selector.logged_success > logged_before
                if source_done and (len(observer.events) > observed_before or len(provider.receipts) == before):
                    break
                await asyncio.sleep(0.01)
            if row["error"] is None and selector is not None and selector.logged_success <= logged_before:
                raise RuntimeError("REAL_CALLBACK_DID_NOT_COMPLETE")
            endpoints = deepcopy(provider.receipts[before:])
            if len(endpoints) > 1:
                raise RuntimeError("UNEXPECTED_SDK_RETRY")
            row["endpoint"] = endpoints[0] if endpoints else None
            row["provider"] = endpoints[0]["provider"] if endpoints else None
            row["content_sha256"] = sha(content.encode())
            row["callbacks"] = deepcopy(observer.events[observed_before:])
            row["latency_cache"] = deepcopy(selector.router_cache.get_cache(key="offline-group_map") or {}) if selector else None
            rows.append(row)
        case["summary"] = allocation_summary(rows)
    finally:
        sys.setprofile(None)
        case["source_calls"] = traced
        case["source_file_sha256"] = {name: sha(Path(name).read_bytes()) for name in {k.rsplit(":", 1)[0] for k in traced}}
        router.retire()
        server.shutdown()
        server.server_close()
    return case


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("experiments/litellm_reality_v1.json"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--case", nargs=3, metavar=("MODE", "CONDITION", "SEED"))
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    revision = subprocess.check_output(["git", "-C", str(args.source), "rev-parse", "HEAD"], text=True).strip()
    if revision != config["source_commit"]:
        raise ValueError("WRONG_SOURCE_REVISION")
    subprocess.run(["git", "-C", str(args.source), "diff", "--exit-code"], check=True)
    if args.case:
        mode, condition, seed = args.case
        try:
            case = asyncio.run(run_case(config, mode, condition, int(seed)))
        except Exception:
            case = {"mode": mode, "condition": condition, "seed": int(seed), "failure": traceback.format_exc()}
        write(args.out, case)
        return 1 if case.get("failure") else 0
    planned = [(mode, condition, seed) for mode in config["primary_modes"]
               for seed in config["seeds"] for condition in config["conditions"]]
    planned += [(mode, condition, config["diagnostic_seed"]) for mode in config["diagnostic_modes"] for condition in config["conditions"]]
    bundle = {"protocol_sha256": sha(args.config.read_bytes()), "runner_sha256": sha(Path(__file__).read_bytes()),
              "source_commit": revision, "uv_lock_sha256": sha((args.source / "uv.lock").read_bytes()),
              "python": sys.version, "workflow_sha": os.environ.get("EXPERIMENT_GITHUB_SHA"),
              "run_id": os.environ.get("EXPERIMENT_RUN_ID"), "run_attempt": os.environ.get("EXPERIMENT_RUN_ATTEMPT"),
              "cases": []}
    started = time.monotonic()
    for mode, condition, seed in planned:
        path = args.out.parent / "cases" / f"{mode}-{condition}-{seed}.json"
        if time.monotonic() - started > config["max_run_seconds"]:
            raise TimeoutError("FROZEN_WALL_LIMIT")
        result = subprocess.run([sys.executable, __file__, "--config", str(args.config), "--source", str(args.source),
                                 "--out", str(path), "--case", mode, condition, str(seed)],
                                timeout=config["max_case_seconds"], capture_output=True, text=True)
        write(path.with_suffix(".execution.json"), {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
        case = json.loads(path.read_text()) if path.exists() else {"mode": mode, "condition": condition, "seed": seed, "failure": result.stderr[-5000:]}
        bundle["cases"].append(case)
        write(args.out, bundle)
        print(mode, condition, seed, case.get("summary", case.get("failure")), flush=True)
        if result.returncode:
            raise RuntimeError("CASE_FAILED_PRESERVED")
    requests = sum(bool(row["endpoint"]) for case in bundle["cases"] for row in case["rows"])
    if requests > config["max_provider_requests"]:
        raise ValueError("PROVIDER_REQUEST_LIMIT")
    bundle["checked"] = check(bundle, config)
    write(args.out, bundle)
    print(json.dumps(bundle["checked"], sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
