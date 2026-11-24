"""Prepare and score the five-case cloud engineering pilot."""

import argparse
from copy import deepcopy
from fnmatch import fnmatchcase
import json
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parent
TASKS = ROOT / "tasks"
BUCKET = "arn:aws:s3:::benchmark-orders"
PREFIX = BUCKET + "/reports/"
OUTPUT_REFERENCE = "${terraform_data.service_settings.output}"


def read_json(path):
    def unique_pairs(fields):
        result = {}
        for name, value in fields:
            if name in result:
                raise ValueError(f"Duplicate key: {name}")
            result[name] = value
        return result

    def reject_constant(value):
        raise ValueError(f"Invalid JSON constant: {value}")

    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=unique_pairs,
        parse_constant=reject_constant,
    )


def substitute(candidate, starter, *paths):
    """Check that replacing the permitted fields restores the starter."""
    protected = deepcopy(candidate)
    for path in paths:
        target = protected
        original = starter
        for key in path[:-1]:
            target = target[key]
            original = original[key]
        target[path[-1]] = original[path[-1]]
    return json.dumps(protected, sort_keys=True) == json.dumps(starter, sort_keys=True)


def terraform(candidate, starter, inputs):
    output = ("output", "service_settings", "value")
    return [
        ("output references the declared resource", candidate["output"]["service_settings"]["value"] == OUTPUT_REFERENCE),
        ("module interface and resource are preserved", substitute(candidate, starter, output)),
    ], {}


def strings(value):
    values = [value] if isinstance(value, str) else value
    if not isinstance(values, list) or not values or any(not isinstance(item, str) for item in values):
        raise ValueError("Expected a string or a nonempty list of strings.")
    return values


def permitted(policy, action, resource, prefix=None):
    decisions = []
    for statement in policy["Statement"]:
        if not any(fnmatchcase(action.lower(), pattern.lower()) for pattern in strings(statement["Action"])):
            continue
        if not any(fnmatchcase(resource, pattern) for pattern in strings(statement["Resource"])):
            continue
        if "Condition" in statement:
            matches = statement["Condition"]["StringLike"]["s3:prefix"]
            if prefix is None or not any(fnmatchcase(prefix, pattern) for pattern in strings(matches)):
                continue
        decisions.append(statement["Effect"])
    return "Allow" in decisions and "Deny" not in decisions


def narrow_statement(statement):
    if statement.get("Effect") != "Allow":
        return False
    if "Sid" in statement and (
        not isinstance(statement["Sid"], str) or re.fullmatch(r"[A-Za-z0-9]+", statement["Sid"]) is None
    ):
        return False
    actions = set(strings(statement["Action"]))
    resources = set(strings(statement["Resource"]))
    fields = set(statement) - {"Sid"}
    basic = {"Effect", "Action", "Resource"}
    if actions == {"s3:GetObject"}:
        return fields == basic and resources == {PREFIX + "*"}
    if actions == {"s3:ListBucket"} and fields == basic | {"Condition"}:
        condition = statement["Condition"]
        return (
            resources == {BUCKET}
            and set(condition) == {"StringLike"}
            and set(condition["StringLike"]) == {"s3:prefix"}
            and set(strings(condition["StringLike"]["s3:prefix"])) == {"reports/*"}
        )
    return False


def iam(candidate, starter, inputs):
    return [
        ("representative reports can be read", all(
            permitted(candidate, "s3:GetObject", PREFIX + key) for key in ("daily.csv", "yearly/summary.csv")
        )),
        ("reports can be listed by prefix", all(
            permitted(candidate, "s3:ListBucket", BUCKET, prefix) for prefix in ("reports/", "reports/yearly/")
        )),
        ("root and neighboring prefixes stay inaccessible", not any(
            permitted(candidate, action, resource, prefix)
            for action, resource, prefix in (
                ("s3:ListBucket", BUCKET, None),
                ("s3:ListBucket", BUCKET, ""),
                ("s3:ListBucket", BUCKET, "reports-private/"),
                ("s3:GetObject", BUCKET + "/reports-private/hint.csv", None),
                ("s3:GetObject", "arn:aws:s3:::other-bucket/reports/daily.csv", None),
            )
        )),
        ("writes and deletes stay unavailable", not any(
            permitted(candidate, action, PREFIX + "daily.csv") for action in ("s3:PutObject", "s3:DeleteObject")
        )),
        ("every statement is confined to the allowed action and prefix", (
            set(candidate) == {"Version", "Statement"}
            and candidate["Version"] == "2012-10-17"
            and isinstance(candidate["Statement"], list)
            and all(narrow_statement(statement) for statement in candidate["Statement"])
        )),
    ], {}


def container(document):
    return document["spec"]["template"]["spec"]["containers"][0]


def resolved_port(target, workload):
    if type(target) is int:
        return target
    return next((port["containerPort"] for port in workload["ports"] if port["name"] == target), None)


def service(candidate, starter, inputs):
    selector = candidate["spec"]["selector"]
    target = candidate["spec"]["ports"][0]["targetPort"]
    targets = [
        pod["name"] for pod in inputs["pods"]
        if selector and all(pod["labels"].get(key) == value for key, value in selector.items())
    ]
    port = resolved_port(target, container(inputs["deployment"]))
    return [
        ("stable workload selected", "orders-stable" in targets),
        ("canary and unrelated workloads excluded", all(name == "orders-stable" for name in targets)),
        ("target resolves to the HTTP container port", port == 8080),
        ("service stays internal and existing fields are preserved", substitute(
            candidate, starter, ("spec", "selector"), ("spec", "ports", 0, "targetPort")
        )),
    ], {"selected_pods": targets, "resolved_port": port}


def readiness(candidate, starter, inputs):
    workload = container(candidate)
    probe = workload["readinessProbe"]["httpGet"]
    port = resolved_port(probe["port"], workload)
    ready = {
        state["name"]: (port == 8080 and 200 <= state["http"].get(probe["path"], 404) < 400)
        for state in inputs["states"]
    }
    http = ("spec", "template", "spec", "containers", 0, "readinessProbe", "httpGet")
    return [
        *((f"readiness agrees during {state['name']}", ready[state["name"]] == state["ready"])
          for state in inputs["states"]),
        ("liveness, replica count and other fields are preserved", substitute(
            candidate, starter, (*http, "path"), (*http, "port")
        )),
    ], {"ready_by_state": ready}


def finops(candidate, starter, inputs):
    replicas = candidate["replicas"]
    retention = candidate["retention_days"]
    if set(candidate) != set(starter) or any(type(v) is not int or v <= 0 for v in (replicas, retention)):
        raise ValueError("The plan must contain only replicas and retention_days as positive integers.")
    monthly_cost = (
        inputs["fixed_cost_usd"] + replicas * inputs["cost_per_replica_usd"]
        + retention * inputs["cost_per_retention_day_usd"]
    )
    available = max(0, replicas - inputs["unavailable_replicas"]) * inputs["replica_capacity_rps"]
    return [
        ("modeled monthly cost is at or below budget", monthly_cost <= inputs["max_cost_usd"]),
        ("all peak loads fit with one unavailable replica", all(load <= available for load in inputs["peak_scenarios_rps"])),
        ("minimum log retention is preserved", retention >= inputs["min_retention_days"]),
    ], {"monthly_cost_usd": monthly_cost, "capacity_after_failure_rps": available}


CASES = {
    "CLD-01": ("main.tf.json", terraform),
    "CLD-02": ("policy.json", iam),
    "CLD-03": ("service.json", service),
    "CLD-04": ("deployment.json", readiness),
    "CLD-05": ("plan.json", finops),
}


def prepare(case, target):
    source = TASKS / case
    if any(parent in (TASKS, ROOT / "reference") for parent in (target.resolve(), *target.resolve().parents)):
        raise ValueError("Use a separate directory for candidate files.")
    shutil.copytree(source, target)


def score(case, directory):
    path = TASKS / case
    name, check = CASES[case]
    try:
        file = directory / name
        if file.is_symlink() or not file.is_file() or {entry.name for entry in directory.iterdir()} != {name}:
            raise ValueError(f"The candidate directory must contain only {name}.")
        candidate = read_json(file)
        starter = read_json(path / "starter" / name)
        input_path = path / "inputs.json"
        inputs = read_json(input_path) if input_path.exists() else {}
        checks, metrics = check(candidate, starter, inputs)
    except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError) as error:
        checks, metrics = [(f"candidate can be evaluated ({error})", False)], {}
    return {
        "task": case,
        "passed": all(passed for _, passed in checks),
        "checks": [{"name": name, "passed": passed} for name, passed in checks],
        "metrics": metrics,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "score"):
        command = commands.add_parser(name)
        command.add_argument("case", choices=CASES)
        command.add_argument("directory", type=Path)
    args = parser.parse_args()
    if args.command == "prepare":
        try:
            prepare(args.case, args.directory)
        except (ValueError, OSError) as error:
            print(error, file=sys.stderr)
            return 1
        print(args.directory / "TASK.md")
        return 0

    result = score(args.case, args.directory)
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
