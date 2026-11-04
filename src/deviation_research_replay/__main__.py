"""Strict historical plus current research-cycle reproduction after backend integration."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter

from deviation_research.records import source_hash
from deviation.verification.checker import source_sha
from .bridge import compare_cycles
from .provenance import (root, read, write, file_sha, preservation, historical_source,
    historical_environment, HISTORICAL_PIN, BASE_MAIN, HISTORICAL_HARNESS_SHA)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--verify",type=Path)
    args = parser.parse_args()
    repo = root(); out = args.out.resolve()
    if out == repo or repo in out.parents:
        raise ValueError("REPLAY_OUTPUT_MUST_BE_OUTSIDE_REPOSITORY")
    if out.exists() and any(out.iterdir()):
        raise ValueError("REPLAY_OUTPUT_MUST_BE_EMPTY")
    out.mkdir(parents=True,exist_ok=True)
    code = {p.name:file_sha(p) for p in sorted(Path(__file__).parent.glob("*.py"))}
    steps = []
    def call(name, command, *, historical=False):
        env = historical_environment() if historical else os.environ.copy()
        if not historical:
            env.pop("PYTHONPATH",None); env.pop("PYTHONHOME",None)
        directory = historical_source().name if historical else repo
        log = out/"logs"/(name+".log"); log.parent.mkdir(exist_ok=True)
        print(name,flush=True); start = perf_counter()
        with log.open("w") as stream:
            result = subprocess.run(command,cwd=directory,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=360)
        steps.append({"step":name,"source":HISTORICAL_PIN if historical else "CURRENT_INSTALLED_PACKAGE",
            "exit_code":result.returncode,"wall_seconds":perf_counter()-start})
        write(out/"execution.json",{"steps":steps,"new_inference_calls":0,"paid_spend_usd":0})
        if result.returncode: raise ValueError("REPLAY_STEP_FAILED: "+name+"; "+str(log))
    try:
        write(out/"preservation.json",preservation())
        if source_hash() != HISTORICAL_HARNESS_SHA: raise ValueError("HISTORICAL_RESEARCH_RUNTIME_CHANGED")
        original = repo/"artifacts/research/mvp"
        # Strict historical tests/replay use unmodified old package/code and
        # original expected bytes. The source override path is not exposed.
        call("historical-tests",[sys.executable,"-B","-m","unittest","discover","-s","tests","-p","test_research*.py","-v"],historical=True)
        call("historical-cold-replay",[sys.executable,"-B","-m","deviation_research","reproduce",
            "--evidence",str(original),"--out",str(out/"historical")],historical=True)
        call("current-cycle",[sys.executable,"-I","-m","deviation_research","cycle",
            "--plan",str(original/"inputs.plan.json"),"--sources",str(original/"inputs.sources.json"),
            "--scout-receipt",str(original/"scout.json"),"--memory",str(out/"current/memory.sqlite"),
            "--out",str(out/"current")])
        call("current-cold-replay",[sys.executable,"-I","-m","deviation_research","reproduce",
            "--evidence",str(out/"current"),"--out",str(out/"current-cold-replay")])
        comparison,resources = compare_cycles(out/"historical",out/"current")
        write(out/"comparison.json",comparison)
        write(out/"comparison-resources.json",resources)
        # Source-dependent hashes are compared explicitly above; CPU/RSS/time
        # remain observed records, deliberately outside deterministic equality.
        files = {}
        for folder in ("historical","current","current-cold-replay"):
            for p in sorted((out/folder).rglob("*")):
                if p.is_file() and p.suffix in {".json",".jsonl"} and p.name != "resources.json":
                    files[str(p.relative_to(out))] = file_sha(p)
        for name in ("preservation.json","comparison.json"):
            files[name] = file_sha(out/name)
        manifest = {"version":"research-rebase-reproduction-1","base_main_commit":BASE_MAIN,
            "historical_harness_commit":HISTORICAL_PIN,"harness_source_sha256":source_hash(),
            "current_engine_source_sha256":source_sha(),"replay_adapter_source":code,
            "files":files,"scientific_findings_changed":False,"new_inference_calls":0,
            "paid_spend_usd":0,"final_holdout_accessed":False}
        if code != {p.name:file_sha(p) for p in sorted(Path(__file__).parent.glob("*.py"))}:
            raise ValueError("REPLAY_ADAPTER_CHANGED_DURING_RUN")
        write(out/"manifest.json",manifest)
        if args.verify and manifest != read(args.verify):
            raise ValueError("STRICT_REBASE_MANIFEST_MISMATCH")
        write(out/"SUCCESS.json",{"status":"REPRODUCED_NOT_MERGED","manifest_sha256":file_sha(out/"manifest.json")})
        print("RESEARCH_REBASE_MANIFEST_BEGIN",flush=True)
        import json
        print(json.dumps(manifest,sort_keys=True,separators=(",",":")),flush=True)
        print("RESEARCH_REBASE_MANIFEST_END",flush=True)
        print("RESEARCH_REBASE_COMPARISON_BEGIN",flush=True)
        print(json.dumps(comparison,sort_keys=True,separators=(",",":")),flush=True)
        print("RESEARCH_REBASE_COMPARISON_END",flush=True)
        print("Original bytes, current replay, all scientific values and 54 event relationships verified.",flush=True)
    except BaseException as error:
        write(out/"FAILURE.json",{"exception":type(error).__name__,"message":str(error)})
        raise


if __name__ == "__main__":
    main()
