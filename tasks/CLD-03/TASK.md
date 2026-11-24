# Repair internal Kubernetes Service routing

The orders Service sends traffic to the wrong target port and its selector also
matches canary Pods. Restore routing to the stable Deployment's HTTP container
port while excluding canary and unrelated Pods. Clients still use port 80 through
a ClusterIP Service in the existing namespace.

Edit only `spec.selector` and the first port's `targetPort` in `service.json`.
The stock stable Deployment and label examples are provided in `inputs.json`.
The fixture image name is illustrative and provides no runnable container.
