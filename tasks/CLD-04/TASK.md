# Repair readiness during rollout

The orders process is alive before it can accept traffic. The liveness endpoint
returns HTTP 200 throughout startup, while the readiness endpoint returns HTTP 503
until dependencies are ready. The Deployment checks the wrong path for readiness.

Edit only the readiness HTTP path and port in `deployment.json`. Keep liveness,
readiness timing, two replicas, image, and application port. Use either the named
HTTP port or its numeric equivalent. The fixture in `inputs.json` describes endpoint
behavior and the evaluator replays it without running a cluster.
