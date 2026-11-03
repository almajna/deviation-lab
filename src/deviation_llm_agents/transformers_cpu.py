"""Optional real CPU inference. Imports/dependency downloads are never implicit in tests."""
import hashlib
from importlib.metadata import version
import platform
from pathlib import Path
import re


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1_048_576), b""): h.update(block)
    return h.hexdigest()


class TransformersCPU:
    # Local means inference executes on the experiment host (e.g. GitHub runner).
    origin = "LIVE_LOCAL_LLM"

    def __init__(self, config, cache_dir):
        if (config["model"] != "Qwen/Qwen2.5-0.5B-Instruct"
                or not re.fullmatch(r"[a-f0-9]{40}", config["revision"])
                or not re.fullmatch(r"[a-f0-9]{64}", config["weights_sha256"])
                or config["license"] != "Apache-2.0"):
            raise ValueError("UNREVIEWED_MODEL")
        # These are ordinary library imports; no upstream model Python is executed.
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from huggingface_hub import snapshot_download
        torch.set_num_threads(4)
        torch.set_num_interop_threads(1)
        torch.use_deterministic_algorithms(True)
        path = Path(snapshot_download(config["model"], revision=config["revision"],
            cache_dir=cache_dir, token=False,
            allow_patterns=["*.json", "*.safetensors", "*.txt", "LICENSE"]))
        files = {p.name: file_sha256(p) for p in sorted(path.iterdir()) if p.is_file()}
        if files.get("model.safetensors") != config["weights_sha256"]:
            raise ValueError("WEIGHT_HASH_MISMATCH")
        license_text = (path / "LICENSE").read_text()
        if "Apache License" not in license_text or "Version 2.0" not in license_text:
            raise ValueError("LICENSE_MISMATCH")
        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True, trust_remote_code=False)
        self.model = AutoModelForCausalLM.from_pretrained(path, local_files_only=True,
            trust_remote_code=False, use_safetensors=True, torch_dtype=torch.float32,
            attn_implementation="eager").to("cpu").eval()
        self.metadata = {"origin": self.origin, "backend": "transformers_cpu", "model": config["model"],
            "revision": config["revision"], "license": config["license"], "file_sha256": files,
            "execution_host": "EXPERIMENT_HOST_CPU_NOT_USER_MAC_OR_HOSTED_MODEL_API",
            "device": "cpu", "dtype": "float32", "threads": torch.get_num_threads(),
            "python": platform.python_version(), "architecture": platform.machine(),
            "processor": platform.processor(), "packages": {k: version(k)
                for k in ["torch", "transformers", "huggingface-hub", "safetensors", "tokenizers"]},
            "generation": {"do_sample": False, "use_cache": True, "context_token_ceiling": 8192,
                "trust_remote_code": False, "weight_format": "safetensors"}}

    def infer(self, messages, *, seed, max_tokens):
        torch = self.torch
        tokens = self.tokenizer.apply_chat_template(
            [{"role": role, "content": text} for role, text in messages.items()],
            tokenize=True, add_generation_prompt=True, return_tensors="pt")
        n = tokens.shape[1]
        if n + max_tokens > min(8192, self.model.config.max_position_embeddings):
            raise ValueError("MODEL_CONTEXT_EXCEEDED")
        torch.manual_seed(seed)
        with torch.inference_mode():
            outputs = self.model.generate(input_ids=tokens, attention_mask=torch.ones_like(tokens),
                max_new_tokens=max_tokens, do_sample=False, use_cache=True,
                pad_token_id=self.tokenizer.eos_token_id)
        generated = outputs[0, n:].tolist()
        return {"raw": self.tokenizer.decode(generated, skip_special_tokens=True),
            "usage": {"prompt_eval_count": n, "eval_count": len(generated),
                "done_reason": "eos" if generated and generated[-1] == self.tokenizer.eos_token_id else "length"},
            "generation_evidence": {"prompt_token_ids": tokens[0].tolist(), "output_token_ids": generated,
                "seed": seed, "greedy": True}}
