# Restore read-only S3 access for one reporting prefix

A reporting role is denied when it lists or reads reports in `benchmark-orders`.
Edit its identity policy to allow listing with the `reports/` prefix and reading
objects under that prefix. Listing with no prefix or a neighboring prefix must
remain denied. Writes and deletes must remain denied, and the role must not gain
permissions on any other buckets or prefixes.

The fixture contains only this identity policy. Use explicit Allow statements
with exact S3 actions and resources. A listing statement must use a StringLike
condition on s3:prefix matching reports/*. Scalar or list forms are accepted for
Action, Resource, and the condition value. Keep the file named `policy.json`.
