# Hermes Runtime Public API Integration 001

## Scope and authority

This Phase A integration is an external Hermes client for AIOS Runtime Baseline V1.2. Hermes uses only HTTP and does not import `runtime_app`, call `RuntimeHost` or a Provider directly, inspect Runtime SQLite, read Enterprise Data, or depend on AIOS repository/worktree layout.

- Runtime release: `AIOS_RUNTIME_BASELINE_V1_2`
- Public API: Host API v1
- Invocation: `POST /v1/invoke`
- Distribution: `aios-runtime-core 1.2.0`
- Validated Wheel SHA-256: `784f98da895765ffcee8ea74a93c564c29ee630bda2eaadb5324e833cb9f2710`
- Hermes source baseline: `c0738aacdfec09c03d4620ff4ba72b3b3c126902`

## Client contract

`hermes_cli.runtime_client.RuntimeClient` is generic. `RuntimeClientConfig` contains only `runtime_base_url`, a non-secret `credential_ref`, timeout, and an optional bounded transport retry count. The credential is supplied at runtime through a callable provider and is never logged or persisted by the client.

The client exposes `health_live()`, `health_ready()`, `capabilities()`, and `invoke(request)`. Invocation accepts the verified RuntimeRequest mapping and returns a typed `RuntimeResponse` preserving `request_id`, `correlation_id`, `execution_id`, `audit_correlation_id`, `status`, `code`, `result`, and `error`.

## Synthetic validation

A temporary synthetic Runtime Instance, Data root, and State root ran the published V1.2 Wheel on loopback. Hermes called, in order:

```text
GET /v1/health/live
GET /v1/health/ready (Bearer authentication)
GET /v1/capabilities (Bearer authentication)
POST /v1/invoke (Bearer authentication, application/json)
```

The synthetic `asset.profile` request returned `COMPLETED / OK`, preserved `execution_id=exec:5f8c001c5d2b4796968395e278953bed`, preserved `audit_correlation_id=hermes-synthetic-correlation-001`, and returned the synthetic authority status. No formal Instance, Enterprise Data, or Runtime State was accessed.

## Failure and retry semantics

The client maps non-success HTTP responses to explicit `RuntimeHTTPError` values, including `401 UNAUTHENTICATED`, `403 CAPABILITY_NOT_AUTHORIZED`, `404 ASSET_NOT_FOUND`, and `503 PROVIDER_*`. Not-ready responses, malformed JSON, and incomplete completed responses raise `RuntimeResponseError`; unavailable transport and timeout raise `RuntimeTransportError`.

Automatic retries default to zero. If configured, at most two retries are allowed only for a clear pre-transmission connection refusal. Timeouts and other uncertain transport failures are marked `ambiguous=True` and are never blindly retried, preserving the request and correlation IDs for caller reconciliation.

## Security and boundary result

Bearer credentials remain outside source control and evidence. Hermes configuration must not contain formal contract JSON, Enterprise Data paths, Provider bindings, Runtime State paths, or repository paths. No Runtime source change was required.

```text
HERMES_RUNTIME_PUBLIC_API_INTEGRATION_CONTRACT_PASS
HERMES_RUNTIME_SYNTHETIC_INVOCATION_PASS
HERMES_RUNTIME_FAIL_CLOSED_PASS
HERMES_RUNTIME_RETRY_SEMANTICS_REVIEW_PASS
HERMES_RUNTIME_AUDIT_CORRELATION_PASS
HERMES_RUNTIME_FORMAL_ACTIVATION_READY
```

Formal Hermes production jobs, scheduled business tasks, write capabilities, Feishu/Aily, Dashboard workflows, and production activation remain out of scope.
