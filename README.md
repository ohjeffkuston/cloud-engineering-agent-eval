# Cloud Engineering Agent Eval

A five-case pilot for evaluating whether an agent can repair infrastructure without breaking the safeguards that make the fix safe to ship. The evaluator runs locally with Python 3.10+ and uses no credentials, live cloud resources, paid API calls, or external Python packages.

| Case | Incident | What must still hold |
| --- | --- | --- |
| [CLD-01](tasks/CLD-01/TASK.md) | Terraform output references a missing resource | Keep the module interface and derive the output from the existing resource. |
| [CLD-02](tasks/CLD-02/TASK.md) | An S3 reporting role cannot list or read its prefix | Preserve the read-only scope and block other prefixes and buckets. |
| [CLD-03](tasks/CLD-03/TASK.md) | A Kubernetes Service points at the wrong port and includes canaries | Keep the stable-only route and internal Service. |
| [CLD-04](tasks/CLD-04/TASK.md) | Kubernetes declares a warming app ready too early | Keep liveness, replica count, and readiness timing. |
| [CLD-05](tasks/CLD-05/TASK.md) | A synthetic workload exceeds its monthly budget | Absorb one unavailable replica at peak load and retain logs for seven days. |

## Run the checker

From the repository root, prepare one agent-visible working directory and check its starter.

```sh
python3 -m unittest discover -s tests -v
python3 benchmark.py prepare CLD-05 /tmp/cloud-finops-candidate
python3 benchmark.py score CLD-05 /tmp/cloud-finops-candidate/starter
```

The starter is expected to fail. Give the candidate only the prepared directory.
Ask it to read `TASK.md`, use `inputs.json` when present, and edit the file in
`starter/`. Run the same score command against its modified file. The checker
prints each condition, relevant metrics, and an aggregate pass result. It exits
with status 0 only when all checks pass.

Evaluators can also check the included reference fixes and review [why each
one passes](reference/REVIEW.md).

```sh
python3 benchmark.py score CLD-05 reference/CLD-05
```

The FinOps reference brings the modeled monthly cost from **$672 to $413**,
keeps seven days of logs, and supplies **360 requests per second after one
replica is unavailable**. The price and capacity inputs are synthetic.

## What this pilot verifies

The checks are scoped to the fixtures. Terraform checks the declared output
reference and preserves the module structure. The IAM checker exercises an
explicit identity-policy subset using fixed allow and deny scenarios. Kubernetes
checks Service routing and replays recorded HTTP readiness behavior as data.
The FinOps case calculates costs and peak capacity from its inputs. The checker evaluates candidate files as data. Separately, Terraform 1.12.2
was used to validate both CLD-01 fixtures and apply the built-in-provider
reference locally. Provider integration, IAM policy simulation in AWS, and
Kubernetes rollout validation are future coverage.

## Run a model comparison

Use a fresh candidate directory for each attempt. Keep the evaluator and
reference fixes outside the agent's tool workspace. Compare one agent and
a team with the same model, task inputs, tool permissions, and total token
budget. Count each agent's calls toward the team cap. Score each completed attempt once. Record the per-case
pass result, failed invariants, time, tokens, and estimated cost. Run repeat
trials before drawing conclusions. These five cases are a development set,
so use fresh cases for a held-out comparison.

Reference fixes and expected invariants are ready for human review. The bundled
tests are checker tests. No live model-comparison results are included.

[Terraform JSON syntax](https://developer.hashicorp.com/terraform/language/syntax/json) · [AWS S3 IAM policy examples](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_examples_s3_rw-bucket.html) · [Kubernetes readiness probes](https://kubernetes.io/docs/concepts/workloads/pods/probes/)

## License

The original project code, tasks, reference solutions, and documentation are available under the [MIT License](LICENSE).
