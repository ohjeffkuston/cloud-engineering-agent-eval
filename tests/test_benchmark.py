from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import benchmark as b


class BenchmarkTests(unittest.TestCase):
    def candidate(self, case, transform):
        name, _ = b.CASES[case]
        solution = deepcopy(b.read_json(b.ROOT / "reference" / case / name))
        transform(solution)
        with TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / name).write_text(json.dumps(solution), encoding="utf-8")
            return b.score(case, folder)

    def test_starters_fail_and_references_pass(self):
        for case in b.CASES:
            with self.subTest(case=case):
                self.assertFalse(b.score(case, b.TASKS / case / "starter")["passed"])
                self.assertTrue(b.score(case, b.ROOT / "reference" / case)["passed"])

    def test_preserve_terraform_behavior_beyond_current_values(self):
        def hardcode(data):
            data["output"]["service_settings"]["value"] = {"service": "orders", "environment": "staging"}

        self.assertFalse(self.candidate("CLD-01", hardcode)["passed"])

    def test_iam_rejects_broader_permissions(self):
        def widen(data):
            data["Statement"][0]["Resource"] = b.BUCKET + "/*"

        def overgrant(data):
            data["Statement"].append({
                "Effect": "Allow", "Action": "s3:GetObject",
                "Resource": "arn:aws:s3:::other-project/reports/*",
            })

        self.assertFalse(self.candidate("CLD-02", widen)["passed"])
        self.assertFalse(self.candidate("CLD-02", overgrant)["passed"])

    def test_service_disallows_public_type_and_accepts_numeric_port(self):
        def public(data):
            data["spec"]["type"] = "LoadBalancer"

        def numeric(data):
            data["spec"]["ports"][0]["targetPort"] = 8080

        self.assertFalse(self.candidate("CLD-03", public)["passed"])
        self.assertTrue(self.candidate("CLD-03", numeric)["passed"])

    def test_readiness_probe_cannot_be_removed(self):
        def remove(data):
            del b.container(data)["readinessProbe"]

        self.assertFalse(self.candidate("CLD-04", remove)["passed"])

    def test_finops_rejects_cheaper_unsafe_plans_and_accepts_alternative(self):
        self.assertFalse(self.candidate("CLD-05", lambda data: data.update(replicas=3))["passed"])
        self.assertFalse(self.candidate("CLD-05", lambda data: data.update(retention_days=6))["passed"])
        alternate = self.candidate("CLD-05", lambda data: data.update(retention_days=8))
        self.assertTrue(alternate["passed"])
        self.assertEqual(alternate["metrics"]["monthly_cost_usd"], 418)

    def test_prepared_files_exclude_evaluator_and_reference(self):
        with TemporaryDirectory() as temp:
            folder = Path(temp) / "task"
            b.prepare("CLD-05", folder)
            self.assertEqual({path.name for path in folder.iterdir()}, {"TASK.md", "inputs.json", "starter"})
            self.assertFalse(b.score("CLD-05", folder / "starter")["passed"])


if __name__ == "__main__":
    unittest.main()
