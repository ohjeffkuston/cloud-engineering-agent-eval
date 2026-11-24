# Restore a Terraform module output

The module fails validation after an output was wired to a resource address that does not exist.
Repair the `service_settings` output in `main.tf.json`. It must forward the output of
the existing `terraform_data.service_settings` resource, so downstream callers keep
receiving the service and environment from the declared configuration.

Edit only that output's value. Preserve the output name, locals, and resource address.
The exercise uses Terraform's built-in provider and needs no cloud account.
