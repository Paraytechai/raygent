Read-only access to ClickHouse Cloud. Every tool runs as the authenticated user or API key, so results only include the organizations, services, and data that identity can see.

Start with get_organizations, then get_services_list with the organizationId to find service IDs and types. Use get_service_details for one service.

For ClickHouse services: call list_databases, then list_tables with the database name, then run_select_query with the serviceId. Only SELECT statements are accepted. Add LIMIT clauses and raise timeoutSeconds for long-running queries.

For Managed Postgres services: use run_postgres_select_query for read-only SQL, list_postgres_slow_query_patterns then get_postgres_slow_query_pattern_details to investigate slow queries, and get_postgres_metrics for time-series metrics.

Other tools cover ClickPipes, backups, organization cost, and service signals. Tools that need a specific authentication type or organization feature are omitted from the tool list when unavailable.

Idle services may be woken automatically; if a tool reports the service is not awake, retry after a short wait. If a query reports the user lacks passwordless access, the user must be granted access to that service in ClickHouse Cloud first.