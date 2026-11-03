"""Ollama adapter: trusted local server, installed pinned model, no pulls/tools."""
import json
import re
from urllib.parse import urlsplit
from urllib.request import build_opener, ProxyHandler, HTTPRedirectHandler, Request
from .adapter import strict_json


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("REDIRECT_FORBIDDEN")


class OllamaLocal:
    origin = "LIVE_LOCAL_LLM"

    def __init__(self, manifest, endpoint="http://127.0.0.1:11434", timeout=30):
        if set(manifest) != {"model", "digest", "source", "license"}:
            raise ValueError("MODEL_MANIFEST_FIELDS")
        if not all(isinstance(v, str) and v.strip() for v in manifest.values()):
            raise ValueError("MODEL_MANIFEST_FIELDS")
        if ("cloud" in manifest["model"].lower() or not re.fullmatch(r"[0-9a-f]{64}", manifest["digest"])
                or not manifest["source"].startswith("https://")):
            raise ValueError("REQUIRE_PINNED_LOCAL_WEIGHTS")
        url = urlsplit(endpoint)
        if (url.scheme != "http" or url.hostname != "127.0.0.1" or url.username or url.password
                or url.path or url.query or url.fragment or not url.port):
            raise ValueError("LITERAL_LOOPBACK_ENDPOINT_REQUIRED")
        if not isinstance(timeout, (int, float)) or not 0 < timeout <= 60:
            raise ValueError("INVALID_TIMEOUT")
        self.endpoint, self.timeout, self.manifest = endpoint, timeout, dict(manifest)
        self.opener = build_opener(ProxyHandler({}), NoRedirect())
        tags = self.request("/api/tags")
        model = next((m for m in tags["models"] if m["name"] == manifest["model"]), None)
        if model is None or model.get("digest") != manifest["digest"]:
            raise ValueError("MODEL_MISSING_OR_DIGEST_CHANGED")
        show = self.request("/api/show", {"model": manifest["model"]})
        if any("remote" in k.lower() or "cloud" in k.lower() for k in set(model) | set(show)):
            raise ValueError("REMOTE_MODEL_FORBIDDEN")
        if model.get("size", 0) <= 0 or model.get("details", {}).get("format") != "gguf":
            raise ValueError("LOCAL_WEIGHT_METADATA_REQUIRED")
        if not show.get("license"):
            raise ValueError("MODEL_LICENSE_MISSING")
        self.metadata = {"origin": self.origin, "manifest": dict(manifest),
            "server_version": self.request("/api/version")["version"],
            "installed_model": model, "model_license": show["license"],
            "trust_boundary": "TRUSTED_LOCAL_SERVER_NOT_REMOTE_EXECUTION_ATTESTATION",
            "endpoint": endpoint, "timeout_seconds": timeout}

    def request(self, path, body=None):
        raw = None if body is None else json.dumps(body, allow_nan=False).encode()
        req = Request(self.endpoint + path, data=raw, headers={"Content-Type": "application/json"})
        with self.opener.open(req, timeout=self.timeout) as response:
            content = response.read(1_048_577)
        if path == "/api/chat":
            self.last_inference_response = {"http_body": content.decode("utf-8", errors="replace"),
                "read_limit_exceeded": len(content) > 1_048_576}
        if len(content) > 1_048_576: raise ValueError("SERVER_RESPONSE_TOO_LARGE")
        return strict_json(content)

    def infer(self, messages, *, seed, max_tokens):
        self.last_inference_response = None
        # Recheck before every generation. This cannot eliminate server-side TOCTOU.
        tags = self.request("/api/tags")
        if not any(m.get("name") == self.manifest["model"] and m.get("digest") == self.manifest["digest"]
                   for m in tags["models"]):
            raise ValueError("MODEL_DIGEST_CHANGED")
        data = self.request("/api/chat", {"model": self.manifest["model"], "stream": False,
            "messages": [{"role": k, "content": v} for k, v in messages.items()],
            "format": "json", "options": {"seed": seed, "temperature": 0,
                "num_predict": max_tokens, "num_ctx": 16384}})
        if not isinstance(data, dict) or not isinstance(data.get("message"), dict):
            raise ValueError("INVALID_SERVER_ENVELOPE")
        if data.get("model") != self.manifest["model"] or data.get("done") is not True:
            raise ValueError("INCOMPLETE_OR_DIFFERENT_MODEL")
        if data["message"].get("tool_calls"): raise ValueError("TOOLS_FORBIDDEN")
        raw = data["message"]["content"]
        if not isinstance(raw, str): raise ValueError("NON_TEXT_RESPONSE")
        usage = {k: data.get(k) for k in ["prompt_eval_count", "eval_count", "total_duration", "done_reason"]}
        for key in ["prompt_eval_count", "eval_count"]:
            if type(usage[key]) is not int or usage[key] < 0: raise ValueError("MISSING_TOKEN_USAGE")
        # Keep raw response and observed usage even for a server cap violation.
        return {"raw": raw, "usage": usage}
