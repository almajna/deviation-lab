"""Offline oracle for small engineering cases ONLY; never a live policy."""
from copy import deepcopy
from deviation.contracts import ContractError, validate_allocation
from .policies import optimize


def offline_oracle(tasks, sealed_outcomes, artifact, run_config):
    if len(tasks) > 12:
        raise ContractError("small-case offline oracle limited to 12 tasks")
    values = {t["task_id"]: {} for t in tasks}
    for row in sealed_outcomes:
        if row["task_id"] in values:
            q = row["quality"]
            if isinstance(q, bool) or not isinstance(q, (int, float)) or not 0 <= q <= 1:
                raise ContractError("invalid oracle quality proxy")
            if row["model_id"] in values[row["task_id"]]:
                raise ContractError("duplicate oracle outcome")
            values[row["task_id"]][row["model_id"]] = q
    if any(set(values[t["task_id"]]) != set(t["model_options"]) for t in tasks):
        raise ContractError("oracle requires complete paired qualities")
    plan = {"schema_version": "0.2", "reservation_budget": run_config["reservation_budget"],
            "cost_unit": artifact["cost_unit"], "reservation_artifact_sha256": artifact["artifact_sha256"],
            "allocations": optimize(sorted(deepcopy(tasks), key=lambda t: t["task_id"]),
                                    artifact["reservations"], run_config["reservation_budget"], values)}
    validate_allocation(plan, artifact, tasks, run_config=run_config)
    return {"visibility": "OFFLINE_ORACLE_ONLY", "allocation_plan": plan}
