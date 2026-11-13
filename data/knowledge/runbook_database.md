# Database connectivity runbook

Symptoms: connection acquisition failures, database connection timeouts, query latency increases, API failures after database operations.

Investigation:
1. Inspect active, idle and waiting database connections.
2. Compare connection pool maximum size with concurrent worker count.
3. Identify long-running queries and lock waits.
4. Check database CPU, memory and connection limits.
5. Compare application timeout settings with database-side timeouts.
6. Review recent deployments and configuration changes.

Do not assume pool exhaustion from timeout messages alone. Validate with database metrics.

# Retry behavior runbook

Repeated retries can amplify an overloaded dependency. Check retry count, backoff strategy, concurrency, and whether failures are transient or permanent. Prefer bounded retries with exponential backoff and jitter.
