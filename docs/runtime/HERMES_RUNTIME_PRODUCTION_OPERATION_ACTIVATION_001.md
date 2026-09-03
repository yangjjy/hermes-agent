# Hermes Runtime Production Operation Activation 001

Status: `HERMES_RUNTIME_PRODUCTION_OPERATION_ACTIVATION_PASS`

## Workflow authority

- Workflow: `asset-profile-query-v1`
- Mode: `MANUAL_ONLY`
- Cardinality: one asset per operation
- Operation class: `READ_ONLY`
- Runtime release: `AIOS_RUNTIME_BASELINE_V1_2` (`1.2.0`)
- Deployment: `personal-runtime-v1`
- Endpoint: `http://127.0.0.1:8643`
- Hermes client authority: `0bad55f21aa088a1ac0a91744fb80f18e1428bec`
- Production capability allow-list: `asset.profile` only

## Controlled production operation

The operation originated in the Hermes business workflow and used the
generic `RuntimeClient` over `POST /v1/invoke`. Hermes did not import
`runtime_app`, call `RuntimeHost`, invoke a Provider, read Enterprise Data,
or access repository/worktree paths.

- input: `asset_id=AUTH023_UNIT_0000001`
- `HERMES_OPERATION_ID`: `hermes-op-asset-profile-query-v1-20260903170209`
- `RUNTIME_REQUEST_ID`: `hermes-request-772e99a0193141679dedccca765d19d9`
- `RUNTIME_CORRELATION_ID`: `hermes-correlation-6c9408eb994b4ee4a6f37251df0e7b24`
- `RUNTIME_EXECUTION_ID`: `exec:ed82b5acc52d43bcb203362fc0290d3f`
- `RUNTIME_AUDIT_CORRELATION_ID`: `hermes-correlation-6c9408eb994b4ee4a6f37251df0e7b24`
- Runtime terminal: `COMPLETED / OK`
- business terminal: `SUCCESS`
- result status: `CODE_AUTHORITY_FOUNDATION`

The business response exposed only asset/result fields, operation identity,
workflow, status, and timestamp. Tokens, filesystem paths, Provider details,
and stack traces were not exposed.

## Audit and deduplication

Read-only inspection of the authorized Runtime State SQLite confirmed exactly
one record for this execution in each of `executions`, `attempts`, and
`audit`. The audit record contains `asset.profile`, `asset_master_data`,
`COMPLETED`, and the matching Runtime audit correlation ID. No replay or
second successful request was sent.

Hermes retained one business-operation summary in its local audit file;
Runtime remains the authoritative execution audit.

## Failure, retry, and readiness policy

The workflow rejects missing/blank asset IDs before invocation, requires the
explicit `asset.profile` allow-list, checks readiness and capability
availability, and surfaces Runtime failures without filesystem or Provider
fallback. It adds no retry layer: the underlying client remains zero-retry
by default and only permits bounded pre-send connection refusal retries;
ambiguous post-transmission outcomes are never resent.

Runtime overall state is `PARTIAL_READY`. This is accepted only because the
requested production-authorized capability is `AVAILABLE / OK`; all other
declared capabilities remain not production-authorized.

## Integrity and boundaries

Pre/post comparisons showed no drift in the five formal Instance contracts,
the published Wheel, the governed Asset Foundation CSV, the Enterprise Data
inventory, or Hermes production-entry configuration. Only authorized Runtime
State execution/audit records and Hermes business-operation audit state
changed.

The workflow remains `MANUAL_ONLY`. Cron, polling, batch scans,
Feishu/Aily, Dashboard, and scheduled business workloads remain disabled.
No Runtime source, Provider, formal Instance, Enterprise Data, or Hermes
Gateway/Desktop behavior was modified.
