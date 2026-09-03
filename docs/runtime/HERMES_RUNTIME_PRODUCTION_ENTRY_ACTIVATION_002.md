# Hermes Runtime Production Entry Activation 002

Status: `HERMES_RUNTIME_PRODUCTION_ENTRY_ACTIVATION_PASS`

## Authority

- Runtime release: `AIOS_RUNTIME_BASELINE_V1_2` (distribution `1.2.0`)
- Deployment: `personal-runtime-v1`
- Service: `com.aios.runtime.personal-runtime-v1`
- Endpoint: `http://127.0.0.1:8643`
- Wheel SHA-256: `784f98da895765ffcee8ea74a93c564c29ee630bda2eaadb5324e833cb9f2710`
- Hermes Runtime Client authority: `0bad55f21aa088a1ac0a91744fb80f18e1428bec`

Hermes uses the existing generic `RuntimeClient`; no second client or direct
Host/Provider integration was introduced.

## Production configuration

The non-secret profile is `~/.hermes/runtime-production.yaml` (SHA-256
`8223bffe24021d3272fa01b4d030f43737432c3114508f2631cf9e4b56c9ecff`). It
contains the fixed endpoint, `credential_reference: env:AIOS_RUNTIME_BEARER_TOKEN`,
10-second timeout, zero transport retries, release identity, and the explicit
allow-list containing only `asset.profile`. The bearer value was supplied
ephemerally for smoke validation and is not stored in source, configuration,
logs, or evidence.

## PARTIAL_READY policy

The production Host reports `PARTIAL_READY` because unrelated declared
providers are unavailable. Hermes accepts that state only when the requested
capability is explicitly allow-listed and reports `AVAILABLE / OK`.
`asset.profile` is `AVAILABLE / OK` through `asset_master_data`; all other
declared capabilities remain `NOT_PRODUCTION_AUTHORIZED`.

## Production smoke

Using the configured profile and generic Hermes client, without `POST
/v1/invoke`:

- `GET /v1/health/live`: `{status: alive}`
- `GET /v1/health/ready`: HTTP 200, `{status: ready, state: PARTIAL_READY}`
- `GET /v1/capabilities`: `asset.profile` `AVAILABLE / OK`

The endpoint was correlated to launchd service
`com.aios.runtime.personal-runtime-v1`, whose program is the deployed
site-packages venv and whose listener is `127.0.0.1:8643`. Hermes production
configuration was the only Hermes state changed; no scheduled jobs or
business workflows were enabled.

## Integrity and boundaries

No Runtime V1.2 source, deployment Wheel, formal Instance, Enterprise Data,
or formal State contract was altered by Hermes configuration. No business
invocation was made in this gate. Runtime remains the execution and audit
authority; Hermes retains only endpoint/configuration references and does not
fall back to files, Providers, source trees, or repository paths.

The deployment service and its one validated restart remain active. Scheduled
business workloads, Feishu/Aily, Dashboard, and bulk asset operations remain
disabled pending a separate authorization.
