# Evaluator review guide

Inspect each task's prompt and reference fix before approving any benchmark claims.
A passing reference demonstrates the current checker against one representative
solution. Equivalent fixes can pass where the task contract permits them.

| Case | Reference fix | Example shortcut the checker rejects |
| --- | --- | --- |
| CLD-01 | Repair the output address and leave the resource intact. | Hard-code the values that happen to match the starter. |
| CLD-02 | Separate object reads from bucket listing and scope both to reports. | Allow all objects under the bucket or grant a different bucket. |
| CLD-03 | Select stable orders Pods and target the named HTTP port. | Expose the Service publicly or include the canary. |
| CLD-04 | Point readiness at the dedicated readiness path. | Remove readiness or change liveness to make deployment look healthy. |
| CLD-05 | Use four replicas and retain logs for seven days. | Drop below the retention floor or provision three replicas that miss peak load after a failure. |

The planned pass rule is all-or-nothing per case. The report retains each failed
condition for diagnosis. Review new candidate patterns before broadening a
checker or turning this development set into a published comparison.
