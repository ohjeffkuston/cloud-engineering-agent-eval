# Reduce a monthly cost spike and maintain capacity

A synthetic service is projected to cost $672 per month. Propose a plan at or
under $420. Capacity must still cover every peak scenario if one replica is
unavailable, and logs must be kept for at least seven days.

Edit `replicas` and `retention_days` in `plan.json` using positive integers.
The synthetic prices, measured per-replica capacity, and peak scenarios are
in `inputs.json`. Costs are a fixed charge plus replicas times replica price
plus retention days times daily retention price. Leave the dataset intact.
