# AI-200 identity, governance, and monitoring study aid

> **Current-scope anchor:** The 2026 [AI-200 study guide](https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/ai-200) explicitly lists Key Vault rotation/retrieval, App Configuration storage/retrieval, distributed tracing with OpenTelemetry SDKs, and KQL analysis of logs/metrics under **Secure, monitor, and troubleshoot Azure solutions (20-25%)**. Identity, RBAC, Policy, locks, tags, and PIM are supplemental related context that supports secure implementation but is not named as a separate objective. This is an original study aid, not exam content.

## Exam scope and decision model

Expect applied decisions rather than product-name recall:

- Select an identity and credential path that minimizes secret ownership.
- Separate authentication (establishing identity) from authorization (permitted operation).
- Apply governance at the correct scope and distinguish prevention, reporting, remediation, and recovery.
- Protect secrets and cryptographic material while making configuration refreshable.
- Choose metrics, logs, Activity Log, traces, and alerts based on the question being answered.
- Use KQL to filter early, preserve useful dimensions, aggregate correctly, and avoid accidental row multiplication.

Official scope: [AI-200 study guide](https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/ai-200).

## Identity, authentication, and authorization

Microsoft Entra ID is the identity provider for users, applications, service principals, managed identities, tokens, and directory administration. A token proves an identity and carries claims; the target service still evaluates whether those claims authorize the requested action. MFA, conditional access, workload identity federation, and managed identities reduce credential risk but do not grant resource permissions by themselves.

Azure RBAC controls access to Azure resources through role definitions, assignments, principals, and scopes. A role assignment can target a management group, subscription, resource group, or resource, and inheritance flows downward. Data-plane access depends on the service's authorization model and the selected role; management-plane read access is not automatically permission to read data.

Entra directory roles (for example, User Administrator) administer directory objects and identity settings. App roles and delegated scopes are application-level permissions defined by an API. A client can authenticate successfully and still receive 403 because it lacks an Azure RBAC assignment, a data-plane permission, a consented scope, or a required application role.

## Managed identities

| Type | Lifecycle | Reuse | Good fit | Gotcha |
| --- | --- | --- | --- | --- |
| System-assigned | Tied to one Azure resource; removed with the resource | Usually no | A single app with simple ownership | Recreating the resource creates a different identity |
| User-assigned | Standalone Azure resource | Yes, across supported resources | Blue/green deployments and stable permissions | Its independent lifecycle requires deliberate cleanup |

Both types obtain tokens from Azure without the application storing a client secret. The identity still needs an appropriate role at the target scope. Prefer a user-assigned identity when several instances need the same stable principal; prefer system-assigned when lifecycle coupling is desirable. Workload identity federation is a related secretless pattern for external workloads, but it is not the same thing as a managed identity.

## RBAC vs Entra roles vs app permissions

| Question | Azure RBAC | Entra directory role | App role or delegated scope |
| --- | --- | --- | --- |
| Controls | Azure resource and supported data-plane operations | Directory administration | API authorization |
| Assigned to | User, group, service principal, managed identity | Directory principal | Client/service principal or signed-in user |
| Typical example | Key Vault Secrets User on one vault | Application Administrator | `Orders.Read` or `Orders.ReadWrite` |
| Scope | Management group to resource; service-specific data scope | Tenant/directory role scope | API and consent model |
| Common mistake | Giving Owner for a read task | Assuming it grants Azure resource access | Treating a feature flag as authorization |

Use groups and PIM for human elevation, narrowly scoped roles for workloads, and access reviews to remove stale access. `Owner` and `Contributor` are not substitutes for a purpose-built data-plane role.

## Policy, initiatives, locks, tags, and PIM

Azure Policy evaluates resource state and requests. `Deny` blocks a noncompliant request, `Audit` records noncompliance, `Modify` changes supported properties, and `DeployIfNotExists` can deploy a related resource or configuration when the assignment identity has the required permissions. A compliant create/update can trigger deployment after evaluation; existing noncompliant resources require a remediation task. An initiative groups policy definitions and parameters for consistent assignment. An exemption should document owner, reason, compensating control, and expiration.

Management groups organize subscriptions and are useful for applying a common policy baseline. Resource locks are an operational guardrail: `CanNotDelete` blocks deletion while allowing most writes; `ReadOnly` blocks writes and deletion. Locks can inherit, but an overly broad lock can block legitimate deployments. Locks do not replace RBAC and do not make data immutable in every service.

Tags are metadata for ownership, cost, environment, and classification. They are not an authorization boundary, and propagation is not universal; use policy or automation when child resources must be tagged. PIM provides eligible, time-bound, auditable elevation for supported roles. It does not automatically solve workload authorization or repair an incorrect role scope.

## Key Vault: objects, access, rotation, and network

| Object | Stores or performs | Typical use | Important distinction |
| --- | --- | --- | --- |
| Key | Cryptographic key material and operations | Encrypt, decrypt, sign, verify, wrap | Applications may use an operation without retrieving key material |
| Secret | Versioned opaque value | Password, token, connection string | Retrieval is a data-plane action |
| Certificate | X.509 certificate plus policy/lifecycle metadata | TLS and certificate management | May have an associated secret and renewal policy |

Use Azure RBAC for new Key Vault deployments; access policies remain supported as a legacy compatibility model. Control-plane authorization uses RBAC, while data-plane authorization uses the vault's configured model. A vault Reader can inspect resource metadata but does not necessarily read secret values. Rotation policy can create new key versions; secret and certificate rotation commonly requires automation to update the dependent service and verify that it can use the new version. Versionless references can follow a current version, but clients may cache values and need explicit refresh.

Soft delete supports recovery during a retention period. Purge protection prevents destructive purge during that period and is important for regulated or recovery-sensitive vaults. Private endpoints keep traffic on private connectivity, but they do not grant identity permission. Private DNS zones, correct links, routes, firewall settings, and authorization must all line up.

**Gotcha:** rotating a database password in Key Vault alone does not change the password in the database or force every client to reload it. Design a two-phase rotation, a rollback path, and an observable validation step.

## App Configuration

App Configuration is for centrally managed non-secret key-values, labels, feature flags, and references. Labels distinguish variants such as `Production` and `Staging`; they are not an access-control boundary. Feature flags support kill switches, targeting, and percentage rollout, but server-side authorization must remain independent.

| Concern | Key Vault | App Configuration |
| --- | --- | --- |
| Primary content | Secrets, keys, certificates | Non-secret settings and feature flags |
| Environment variants | Separate objects/versions or references | Labels and key-value selection |
| Secret handling | Secret value is protected and retrieved with data-plane permission | Store a Key Vault reference, not plaintext |
| Refresh | Version changes, client/runtime cache behavior | Provider registration, polling/cache, and optional sentinel |
| Network | Firewall/private endpoint/private DNS options | Endpoint/network controls plus identity |

A Key Vault reference contains a URI/reference; the runtime identity must still be authorized to resolve it. Dynamic refresh requires the client library/provider to register settings, poll or be triggered, and replace its cached view. A sentinel key is changed after a coherent set of settings is ready, allowing clients to refresh the set together. Never commit or log resolved secret values.

## Azure Monitor, Application Insights, and Log Analytics

Azure Monitor is the umbrella for metrics, logs, Activity Log, alerts, workbooks, and insights. Application Insights provides application telemetry such as requests, dependencies, exceptions, availability, and traces. Log Analytics provides a workspace-backed KQL experience over tables. A resource log must be routed to a destination before it is queryable there.

| Signal | Shape and question answered | Retention/query behavior | Example |
| --- | --- | --- | --- |
| Metrics | Numeric time series with dimensions; "how much/how often?" | Fast thresholding; time grain, aggregation, and dimensions matter | CPU percent by instance |
| Logs | Detailed records; "what happened and with which fields?" | KQL, table retention, richer context | Failed dependency with operation ID |
| Activity Log | Azure control-plane operations and service health/resource events | Subscription-level history; export for longer retention | Who changed a firewall rule? |

Use dimensions carefully: a metric alert can evaluate each dimension series separately, while high-cardinality dimensions can increase cost and noise. Scheduled-query alerts are appropriate when a KQL predicate, join, sequence, or count is required. Workbooks compose visualizations and queries; they do not replace the underlying telemetry store.

| Alert type | Best fit | Strength | Gotcha |
| --- | --- | --- | --- |
| Metric alert | Numeric threshold over a metric | Low latency and efficient evaluation | Limited context; aggregation and dimensions matter |
| Log-query alert | KQL condition over logs | Rich correlation, joins, and custom logic | Ingestion/query delay and query cost; schedule/window matter |

Include severity, evaluation window, frequency, dimensions, suppression/noise controls, an owner, a runbook, and a test. Protect sensitive fields and control workspace and workbook access.

## OpenTelemetry

OpenTelemetry (OTel) standardizes traces, metrics, and logs plus instrumentation/export pipelines. A trace represents a distributed operation; a span is one timed unit such as an HTTP request, database call, queue publish, or model invocation. Parent-child relationships and W3C `traceparent` propagate context across HTTP and messaging. A business correlation ID can help search, but it is not a trace ID.

Traces can be sampled; Application Insights metrics are not sampled. Supported SDKs can optionally drop logs associated with unsampled traces. Head sampling decides early and is cheap; general OpenTelemetry Collector architectures can implement tail sampling to retain completed slow or failed traces, but this requires buffering and collector capacity. Sampling can hide rare failures, so retain error signals and monitor exporter failure, queue pressure, and dropped telemetry. Avoid secrets and unbounded user input in attributes; high-cardinality dimensions harm cost and query performance.

## KQL operators and patterns

KQL is pipe-oriented and case-sensitive in many identifiers; it is not T-SQL. Common operators:

| Operator | Purpose | Example |
| --- | --- | --- |
| `where` | Filter rows early | `where TimeGenerated > ago(1h)` |
| `project` | Select/rename columns | `project TimeGenerated, Name, DurationMs` |
| `extend` | Compute columns | `extend IsSlow = DurationMs > 1000` |
| `summarize` | Aggregate and group | `summarize count() by bin(TimeGenerated, 5m)` |
| `join` | Combine related tables | `join kind=leftouter (...) on OperationId` |
| `union` | Stack tables | `union AppRequests, AppDependencies` |
| `parse` / `parse_json` | Extract structured fields | `extend code = tostring(parse_json(Properties).code)` |
| `make-series` | Build regularly binned time series | `make-series count() on TimeGenerated step 5m` |

Filter time early, project only needed columns, choose join kind deliberately, and aggregate before joining when possible. Many-to-many joins multiply rows. Handle missing values with `coalesce`, validate dynamic JSON types, and use `bin` for comparable time buckets.

```kusto
AppRequests
| where TimeGenerated > ago(1h) and Success == false
| summarize Failures=sum(ItemCount), LastSeen=max(TimeGenerated) by Name
| order by Failures desc
```

```kusto
AppDependencies
| where TimeGenerated > ago(30m)
| summarize p95=percentile(DurationMs, 95),
    Errors=sumif(ItemCount, Success == false)
    by bin(TimeGenerated, 5m), Target
| order by TimeGenerated asc
```

## Original scenarios and gotchas

1. **Blue/green identity:** Two slots need the same vault permissions during a swap. A user-assigned identity avoids granting a newly created system identity every time, but confirm both slots can attach it and that its lifecycle is governed.
2. **Policy versus lock:** A `ReadOnly` lock can stop a remediation deployment. Use policy to enforce HTTPS and reserve locks for destructive-operation protection.
3. **Secret rotation:** Update the consumer, not only the vault. Test old/new overlap, cache expiry, rollback, and alerting.
4. **Private vault outage:** A private endpoint with missing private DNS can look like an authorization failure. Check name resolution and route before changing roles.
5. **Feature flag security:** A client-visible flag can change behavior but must never be the only check for an admin operation.
6. **Trace gap:** A new worker that drops `traceparent` creates disconnected spans. Instrument producer and consumer boundaries and preserve baggage only when its contents are safe.
7. **Alert choice:** A CPU threshold belongs in a metric alert; "five failed payments followed by a dependency timeout for the same operation" belongs in a log-query alert.
8. **KQL join trap:** Joining request rows to multiple dependency rows duplicates request counts. Aggregate dependencies first or use a correlation-aware pattern.

## 100 true/false questions

1. A successful Entra token acquisition proves that the caller can read a secret from any Key Vault.
2. A system-assigned managed identity normally has a lifecycle coupled to its parent resource.
3. A user-assigned managed identity can be attached to more than one supported Azure resource.
4. Recreating a deleted resource with a system-assigned identity normally preserves the old principal object.
5. Workload identity federation can remove the need for a long-lived client secret in a supported external workload.
6. Authentication establishes identity, while authorization evaluates permitted actions.
7. An Azure RBAC assignment at a resource group can inherit to resources within that group.
8. A directory User Administrator role automatically grants Contributor access to Azure subscriptions.
9. An API scope or app role is defined by the protected API rather than by an unrelated Azure resource.
10. Granting `Owner` at subscription scope is the least-privilege choice for an app that only reads one vault secret.
11. A vault metadata Reader role necessarily permits reading secret values.
12. PIM can make eligible human access time-bound and auditable.
13. PIM automatically rotates an application's client credentials.
14. A management group can contain subscriptions and provide a policy assignment scope above them.
15. An initiative is a bundle of policy definitions that can share parameters.
16. An `Audit` policy effect by itself rejects a noncompliant create request.
17. Remediating existing noncompliant resources with `DeployIfNotExists` requires a remediation task and suitable assignment-identity permissions.
18. A policy exemption should be treated as permanent once a deployment is unblocked.
19. A `CanNotDelete` lock generally allows ordinary updates while blocking deletion.
20. A `ReadOnly` lock can interfere with writes required by a remediation deployment.
21. Resource locks are an authorization replacement that can grant a denied principal access.
22. Tags are useful metadata but are not a reliable security boundary.
23. Tags are guaranteed to propagate to every child resource created by every Azure service.
24. A policy initiative can standardize a baseline across multiple subscriptions under a management group.
25. A certificate object is identical to a plain Key Vault secret in lifecycle semantics.
26. Key Vault keys can support cryptographic operations without an application retrieving raw key material.
27. Key Vault secrets are versioned values that can be retrieved through data-plane authorization.
28. A key rotation policy guarantees that every dependent application immediately starts using the newest version.
29. Updating a password secret is sufficient to change the password accepted by the database that uses it.
30. Soft delete and purge protection address recovery and destructive purge risks, respectively.
31. Purge protection is the same control as an RBAC deny assignment.
32. A private endpoint can make Key Vault traffic private without granting the caller permission to read a secret.
33. Private DNS is often needed for clients to resolve a private endpoint name to its private address.
34. A Key Vault data-plane role can be correct while a missing route still prevents retrieval.
35. App Configuration labels can represent environment variants without creating separate stores.
36. An App Configuration feature flag is an authorization mechanism for an administrative API.
37. A Key Vault reference in App Configuration is intended to keep the plaintext secret out of the key-value.
38. Resolving a Key Vault reference requires the runtime identity to have suitable Key Vault access.
39. Registering a refresh strategy guarantees that every process instance instantly observes a changed setting.
40. A sentinel can coordinate refresh after a related group of settings is ready.
41. Storing a database password directly in App Configuration is preferable to using a Key Vault reference.
42. Azure Monitor includes metrics, logs, alerts, and visualization capabilities.
43. Application Insights is primarily an application observability experience, not a directory role system.
44. Log Analytics workspaces provide a common KQL query surface for routed logs.
45. A resource log is automatically queryable in every Log Analytics workspace without diagnostic settings.
46. Activity Log is designed chiefly for Azure control-plane history such as resource writes.
47. Application request telemetry and Activity Log answer exactly the same operational question.
48. A workbook is a visualization and analysis surface rather than the canonical storage location for telemetry.
49. Metrics are generally numeric time series and can include dimensions.
50. Logs are always cheaper and lower latency than metrics for threshold alerts.
51. A metric alert is usually a better fit than KQL when the condition is a simple CPU threshold.
52. A scheduled-query alert can express a correlation condition that requires KQL.
53. Adding an unconstrained high-cardinality metric dimension is always harmless to cost and noise.
54. An alert runbook and owner are useful even when the alert query is technically correct.
55. Exporting Activity Log can support retention beyond the default viewing period.
56. OTel traces, metrics, and logs are all observability signals.
57. A trace is composed of spans that represent timed operations.
58. A span's parent relationship is irrelevant to distributed trace reconstruction.
59. W3C `traceparent` can carry trace context across an HTTP boundary.
60. A business correlation ID is guaranteed to have the same semantics as an OTel trace ID.
61. Head sampling can discard a trace before later evidence shows that it was slow.
62. Tail sampling can make decisions after a trace's spans have been observed, at the cost of buffering.
63. Sampling reduces volume but can hide rare failures if error retention is not designed.
64. High-cardinality user input is a safe default for OTel metric labels.
65. An exporter that is backpressured can contribute to dropped telemetry and should be monitored.
66. KQL uses pipes to pass the result of one operator to the next.
67. Putting a selective time `where` near the start of a KQL query often reduces work.
68. `project` is primarily used to aggregate rows into groups.
69. `extend` can calculate a derived column without removing the existing columns.
70. `summarize count() by Name` returns one aggregate row per distinct Name.
71. `join` always preserves exactly one output row for each left-side row.
72. A many-to-many join can multiply rows and inflate a later count.
73. `union` combines rows from multiple inputs rather than matching columns by a key.
74. `parse_json` is useful when a column contains JSON represented as a dynamic value or string.
75. `make-series` can create regularly stepped time buckets for time-series analysis.
76. `bin(TimeGenerated, 5m)` helps align events to comparable five-minute buckets.
77. Filtering after an expensive many-table join is always equivalent in cost to filtering before it.
78. `coalesce` can provide a fallback when an expected value is null.
79. KQL `summarize` can calculate percentiles such as p95 for latency.
80. A KQL query that returns rows proves that an alert rule has the correct evaluation window and severity.
81. A system-assigned identity is usually the simpler choice when exactly one resource owns the identity lifecycle.
82. A user-assigned identity is often useful when blue/green instances need stable permissions.
83. Assigning a role at subscription scope is always safer than assigning it at a vault scope.
84. A policy `Deny` can prevent a new noncompliant configuration but does not automatically repair every existing resource.
85. A lock can block an operator who otherwise has sufficient RBAC permission to delete the resource.
86. A tag named `Owner=Finance` does not itself grant Finance permission to operate a resource.
87. A rotation runbook should include validation of the dependent consumer and a rollback or overlap strategy.
88. A private endpoint removes the need to configure private DNS and network routes.
89. A sentinel should be changed before the related settings are safely available to consumers.
90. Feature flag targeting can affect behavior without replacing authorization checks.
91. A metric alert and a log-query alert can have different detection latency because their data paths differ.
92. Querying a workspace table is a substitute for enabling diagnostic settings on the resource.
93. Preserving `traceparent` through a queue consumer can connect producer and consumer spans.
94. Sampling policy should consider errors and rare slow traces, not only average volume.
95. Putting secrets in span attributes is acceptable if the trace backend has RBAC.
96. `summarize` before a join can help prevent one-to-many detail rows from inflating an aggregate.
97. A left outer join can retain unmatched rows from its left input.
98. A workbook can combine multiple queries and visualizations for an operational audience.
99. A successful metric alert evaluation proves that the underlying logs contain the same data.
100. Least privilege includes choosing an appropriate role, scope, and duration rather than only choosing a principal.

## Answer key

1. **F** - Token issuance authenticates; Key Vault data-plane authorization is still required.
2. **T** - The system identity is created and removed with its parent resource.
3. **T** - A user-assigned identity is independent and reusable.
4. **F** - Recreating the resource normally creates a new system identity.
5. **T** - Federation exchanges trusted external assertions without a stored long-lived secret.
6. **T** - Authentication is who; authorization is what the identity may do.
7. **T** - RBAC assignments inherit down the resource hierarchy.
8. **F** - Entra directory roles do not automatically grant Azure RBAC access.
9. **T** - The API owns its scopes and app roles.
10. **F** - A narrowly scoped data-plane read role is more appropriate.
11. **F** - Metadata Reader and secret-value access are distinct.
12. **T** - PIM supports eligible, time-bound elevation and auditing.
13. **F** - Credential rotation requires a separate lifecycle process.
14. **T** - Management groups sit above subscriptions.
15. **T** - Initiatives group policies and commonly share parameters.
16. **F** - Audit records; it does not itself deny the request.
17. **T** - Existing resources need a remediation task, and the policy assignment identity needs the required deployment permissions.
18. **F** - Exemptions should have a reason, owner, controls, and expiry.
19. **T** - CanNotDelete blocks deletion but generally permits updates.
20. **T** - ReadOnly blocks writes, including some remediation writes.
21. **F** - Locks do not grant access or replace authorization.
22. **T** - Tags describe resources; they do not enforce access.
23. **F** - Propagation varies and often needs policy or automation.
24. **T** - Initiative assignments can establish a multi-subscription baseline.
25. **F** - Certificates include certificate-specific policy and lifecycle metadata.
26. **T** - Key operations can be performed without exposing raw key material.
27. **T** - Secrets have versions and require data-plane permission to read.
28. **F** - Consumers may cache or require explicit version/refresh behavior.
29. **F** - The database must be updated and clients must reload/validate.
30. **T** - Soft delete aids recovery; purge protection blocks purge during retention.
31. **F** - Purge protection is a vault safeguard, not an RBAC deny assignment.
32. **T** - Private networking and identity authorization are separate controls.
33. **T** - DNS must resolve the service name through the private endpoint path.
34. **T** - Correct authorization cannot overcome missing connectivity.
35. **T** - Labels select environment/version variants within a store.
36. **F** - Feature flags control behavior, not permission.
37. **T** - The key-value contains a reference rather than the secret plaintext.
38. **T** - The resolving runtime identity needs Key Vault data access.
39. **F** - Polling/cache and process timing mean refresh is not instantaneous.
40. **T** - A sentinel can signal that a coherent set is ready.
41. **F** - Sensitive values belong in Key Vault; App Configuration can reference them.
42. **T** - Monitor spans these telemetry and visualization capabilities.
43. **T** - Application Insights focuses on application performance/telemetry.
44. **T** - Log Analytics provides the workspace KQL experience.
45. **F** - Diagnostic settings or another routing path are needed.
46. **T** - Activity Log records Azure management/control-plane activity.
47. **F** - Request telemetry and control-plane history answer different questions.
48. **T** - Workbooks visualize and analyze data stored/queryable elsewhere.
49. **T** - Metrics are numeric series and may be dimensioned.
50. **F** - Metrics are commonly more efficient for thresholds; logs provide richer context.
51. **T** - A native numeric metric threshold is the natural metric-alert case.
52. **T** - KQL alerts can join, correlate, and count contextual events.
53. **F** - High cardinality can increase cost, series count, and alert noise.
54. **T** - Ownership and response instructions make alerts actionable.
55. **T** - Export destinations can provide longer-term Activity Log retention.
56. **T** - These are the standard OTel signal families used here.
57. **T** - Spans are timed units that compose a trace.
58. **F** - Parent relationships are essential to reconstructing distributed work.
59. **T** - `traceparent` is the W3C HTTP trace-context header.
60. **F** - A business ID is supplementary and has different semantics.
61. **T** - Head sampling decides before later latency/error evidence exists.
62. **T** - Tail sampling waits for evidence and therefore buffers state.
63. **T** - Lower volume can omit rare events without error-aware policy.
64. **F** - Unbounded cardinality is costly and harms telemetry systems.
65. **T** - Export pressure can cause drops and should be observable.
66. **T** - KQL operators are chained with pipes.
67. **T** - Early selective filtering commonly reduces scanned and processed data.
68. **F** - `project` selects columns; `summarize` aggregates.
69. **T** - `extend` adds computed columns while retaining existing columns.
70. **T** - The grouping key produces an aggregate row for each distinct Name.
71. **F** - Matching multiplicity can produce multiple output rows per left row.
72. **T** - Many-to-many matches multiply combinations.
73. **T** - `union` stacks input rows.
74. **T** - `parse_json` extracts fields from JSON content.
75. **T** - `make-series` creates regular time steps.
76. **T** - `bin` aligns timestamps to fixed intervals.
77. **F** - Filtering early can substantially reduce join cost.
78. **T** - `coalesce` returns the first usable non-null value.
79. **T** - Percentile aggregations such as p95 are supported.
80. **F** - Rule frequency, window, severity, and data delay are separate configuration concerns.
81. **T** - Lifecycle coupling is simple for one owning resource.
82. **T** - Stable identity permissions can span deployment instances.
83. **F** - Narrow resource scope is usually safer than broad subscription scope.
84. **T** - Deny prevents requests; remediation of existing state is separate.
85. **T** - A lock can override an otherwise authorized destructive operation.
86. **F** - A tag has no inherent authorization effect.
87. **T** - Safe rotation validates the consumer and plans overlap/rollback.
88. **F** - DNS, routes, and other network configuration remain necessary.
89. **F** - Change the sentinel after the related values are ready.
90. **T** - Targeting changes rollout behavior, not authorization.
91. **T** - Metrics and logs have different ingestion and evaluation paths.
92. **F** - Routing/diagnostic settings determine whether resource logs arrive.
93. **T** - Context propagation connects the span trees across the queue boundary.
94. **T** - Error-aware sampling avoids losing the most useful evidence.
95. **F** - RBAC does not make secret attributes safe; redact them.
96. **T** - Pre-aggregation can avoid one-to-many join multiplication.
97. **T** - Left outer joins retain unmatched left-side rows.
98. **T** - Workbooks can assemble queries and visualizations.
99. **F** - Metrics and logs are separate signals and may differ in coverage/timing.
100. **T** - Least privilege is role plus scope plus appropriate duration.

## Official Microsoft Learn links

- [AI-200 study guide](https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/ai-200)
- [Microsoft Entra ID fundamentals](https://learn.microsoft.com/en-us/entra/fundamentals/whatis)
- [Managed identities](https://learn.microsoft.com/en-us/entra/identity/managed-identities-azure-resources/overview)
- [Workload identity federation](https://learn.microsoft.com/en-us/entra/workload-id/workload-identity-federation)
- [Azure RBAC](https://learn.microsoft.com/en-us/azure/role-based-access-control/overview)
- [Microsoft Entra roles](https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/permissions-reference)
- [Azure Policy](https://learn.microsoft.com/en-us/azure/governance/policy/overview)
- [Resource locks](https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/lock-resources)
- [Privileged Identity Management](https://learn.microsoft.com/en-us/entra/id-governance/privileged-identity-management/pim-configure)
- [Key Vault overview](https://learn.microsoft.com/en-us/azure/key-vault/general/overview)
- [Configure cryptographic key auto-rotation](https://learn.microsoft.com/en-us/azure/key-vault/keys/how-to-configure-key-rotation)
- [Soft delete and purge protection](https://learn.microsoft.com/en-us/azure/key-vault/general/soft-delete-overview)
- [Key Vault Private Link](https://learn.microsoft.com/en-us/azure/key-vault/general/private-link-service)
- [App Configuration overview](https://learn.microsoft.com/en-us/azure/azure-app-configuration/overview)
- [Labels and key-values](https://learn.microsoft.com/en-us/azure/azure-app-configuration/concept-key-value)
- [Feature flags](https://learn.microsoft.com/en-us/azure/azure-app-configuration/concept-feature-management)
- [Key Vault reference refresh](https://learn.microsoft.com/en-us/azure/azure-app-configuration/reload-key-vault-secrets-dotnet)
- [Azure Monitor overview](https://learn.microsoft.com/en-us/azure/azure-monitor/overview)
- [Application Insights overview](https://learn.microsoft.com/en-us/azure/azure-monitor/app/app-insights-overview)
- [OpenTelemetry for Azure Monitor](https://learn.microsoft.com/en-us/azure/azure-monitor/app/opentelemetry-overview)
- [Log Analytics overview](https://learn.microsoft.com/en-us/azure/azure-monitor/logs/log-analytics-overview)
- [Azure Activity Log](https://learn.microsoft.com/en-us/azure/azure-monitor/essentials/activity-log)
- [Azure Monitor alerts](https://learn.microsoft.com/en-us/azure/azure-monitor/alerts/alerts-overview)
- [Azure workbooks](https://learn.microsoft.com/en-us/azure/azure-monitor/visualize/workbooks-overview)
- [Kusto Query Language](https://learn.microsoft.com/en-us/kusto/query/?view=microsoft-fabric)
- [KQL quick reference](https://learn.microsoft.com/en-us/kusto/query/kql-quick-reference)
