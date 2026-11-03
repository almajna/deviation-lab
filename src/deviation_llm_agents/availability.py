"""Read-only runtime inventory; never downloads a model or reads outcome datasets."""
import importlib.util
from pathlib import Path
import platform
import shutil


def inventory():
    cache = Path.home() / ".cache/huggingface/hub/models--Qwen--Qwen3-0.6B"
    files = list(cache.rglob("*")) if cache.exists() else []
    weight_bytes = sum(p.stat().st_size for p in files if p.is_file() and
        (p.suffix in {".safetensors", ".gguf"} or (p.name == "pytorch_model.bin")))
    # HF blob names do not retain extensions; also check for weight-sized blobs.
    large_blobs = sum(p.is_file() and p.stat().st_size > 50_000_000 for p in files)
    return {"version": "llm-availability-1", "python": platform.python_version(),
        "architecture": platform.machine(),
        "runtime_packages": {name: importlib.util.find_spec(name) is not None
            for name in ["torch", "transformers", "mlx_lm", "llama_cpp"]},
        "runtime_commands": {name: shutil.which(name) is not None for name in ["ollama", "llama-cli"]},
        "inspected_cache": "Qwen/Qwen3-0.6B metadata cache only; not a full disk model inventory",
        "cache_named_weight_bytes": weight_bytes, "cache_blobs_over_50MB": large_blobs,
        "model_inference_calls": 0, "network_requests": 0,
        "conclusion": "INVENTORY_ONLY_NOT_SERVER_OR_INFERENCE_VERIFICATION"}
