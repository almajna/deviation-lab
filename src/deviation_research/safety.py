"""OS isolation for fixed experiment entry points. No arbitrary command interface."""
from pathlib import Path
import json
import os
import platform
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import time

RUNNERS = {"lmsr_baseline", "fee_sensitivity", "certificate_ablation", "forecast_correlation", "review", "isolation_probe"}
LIMITS = dict(wall_seconds=35, cpu_seconds=25, memory_mb=768, file_bytes=2_000_000, output_bytes=1_000_000)


class SandboxError(RuntimeError):
    def __init__(self, message, receipt=None):
        super().__init__(message)
        self.receipt = receipt


def _limits():
    resource.setrlimit(resource.RLIMIT_CPU, (LIMITS["cpu_seconds"], LIMITS["cpu_seconds"]+1))
    resource.setrlimit(resource.RLIMIT_FSIZE, (LIMITS["file_bytes"], LIMITS["file_bytes"]))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    if platform.system() == "Linux":
        cap = LIMITS["memory_mb"]*1024**2
        resource.setrlimit(resource.RLIMIT_AS, (cap, cap))


def backend():
    if platform.system() == "Darwin" and shutil.which("sandbox-exec"):
        return "seatbelt"
    if platform.system() == "Linux" and shutil.which("bwrap"):
        return "bubblewrap"
    raise SandboxError("OS sandbox unavailable; refusing execution (macOS sandbox-exec or Linux bubblewrap required)")


def run(runner, payload, *, wall_seconds=None):
    if runner not in RUNNERS:
        raise SandboxError("runner is not allowlisted")
    wall = min(LIMITS["wall_seconds"], LIMITS["wall_seconds"] if wall_seconds is None else wall_seconds)
    if wall <= 0:
        raise SandboxError("cycle wall budget exhausted")
    kind = backend()
    started = time.monotonic()
    before_cpu = resource.getrusage(resource.RUSAGE_CHILDREN)
    def usage(status, stdout="", stderr=""):
        after_cpu = resource.getrusage(resource.RUSAGE_CHILDREN)
        receipt = {"backend": kind, "limits": LIMITS, "status": status,
                "wall_seconds": time.monotonic()-started,
                "supervisor_reaped_cpu_seconds": after_cpu.ru_utime+after_cpu.ru_stime-before_cpu.ru_utime-before_cpu.ru_stime,
                "worker_cpu_seconds": None, "worker_peak_rss_kib": None,
                "inference_calls": 0, "paid_spend_usd": 0,
                "stdout_tail": stdout[-2000:], "stderr_tail": stderr[-2500:],
                "memory_limit_enforced": platform.system() == "Linux"}
        path = out/"worker-resources.json"
        if path.exists() and path.stat().st_size <= 2048:
            receipt.update(json.loads(path.read_text()))
        return receipt
    # Stage only Python packages and explicit JSON input. No repository data,
    # credentials, git checkout, source downloads, or final cohort is mounted.
    with tempfile.TemporaryDirectory(prefix="deviation-research-worker-") as temp:
        base = Path(temp).resolve()
        src, out = base/"src", base/"out"
        src.mkdir(); out.mkdir()
        for module in ("deviation", "deviation_research"):
            origin = Path(__import__(module).__file__).resolve().parent
            shutil.copytree(origin, src/module, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        (base/"input.json").write_text(json.dumps(payload, allow_nan=False))
        command = [sys.executable, "-B", "-s", "-m", "deviation_research.worker", runner,
                   str(base/"input.json"), str(out/"result.json")]
        if kind == "seatbelt":
            # System/runtime reads only; all user and repository files excluded.
            reads = ["/System", "/usr", "/bin", "/sbin", "/opt/homebrew", "/Library/Apple",
                     "/private/var/db/dyld", "/private/etc", str(base), sys.prefix, sys.base_prefix]
            profile = '(version 1) (allow default) (deny network*) (deny file-read*) (deny file-write*)\n'
            profile += '(allow file-read* '+" ".join('(subpath '+json.dumps(p)+')' for p in reads)+')\n'
            profile += '(allow file-read* (subpath "/dev") (literal "/private/tmp"))\n'
            profile += '(allow file-write* (subpath '+json.dumps(str(out))+') (literal "/dev/null"))\n'
            (base/"sandbox.sb").write_text(profile)
            command = ["sandbox-exec", "-f", str(base/"sandbox.sb")]+command
        else:
            mounts = []
            for p in ("/usr", "/bin", "/sbin", "/lib", "/lib64", "/opt", "/etc/ld.so.cache", sys.prefix, sys.base_prefix):
                if Path(p).exists():
                    mounts += ["--ro-bind", p, p]
            command = ["bwrap", "--unshare-all", "--die-with-parent", "--new-session", *mounts,
                       "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp", "--ro-bind", str(base), str(base),
                       "--bind", str(out), str(out), "--chdir", str(base), "--"]+command
        environment = {"PATH": "/usr/bin:/bin", "PYTHONPATH": str(src), "PYTHONHASHSEED": "0",
                       "PYTHONDONTWRITEBYTECODE": "1", "HOME": str(out), "TMPDIR": str(out), "LANG": "C.UTF-8"}
        # File-backed logs are capped by RLIMIT_FSIZE; no unbounded pipe buffer.
        with (out/"stdout.log").open("wb") as stdout, (out/"stderr.log").open("wb") as stderr:
            remaining = wall-(time.monotonic()-started)
            if remaining <= 0:
                raise SandboxError("worker staging exhausted wall budget", usage("STAGING_TIMEOUT"))
            process = subprocess.Popen(command, cwd=base, env=environment, stdout=stdout, stderr=stderr,
                                       start_new_session=True, preexec_fn=_limits)
            try:
                code = process.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                raise SandboxError("worker wall timeout", usage("WALL_TIMEOUT",
                    (out/"stdout.log").read_text(errors="replace"), (out/"stderr.log").read_text(errors="replace")))
        if code:
            error = (out/"stderr.log").read_text(errors="replace")[-2500:]
            raise SandboxError(f"sandbox worker exit {code}: {error}", usage("EXIT_"+str(code),
                (out/"stdout.log").read_text(errors="replace"), error))
        result = out/"result.json"
        if not result.exists() or result.stat().st_size > LIMITS["output_bytes"]:
            raise SandboxError("missing or oversized result", usage("INVALID_OUTPUT"))
        envelope = json.loads(result.read_text())
        receipt = usage("COMPLETED")
        receipt.update({k: envelope[k] for k in ("harness_source_sha256", "engine_source_sha256")})
        return envelope["value"], receipt
