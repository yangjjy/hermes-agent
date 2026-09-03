# Hermes Runtime Formal Read-Only Activation 001

Status: `HERMES_RUNTIME_FORMAL_READ_ONLY_ACTIVATION_PASS`

This evidence records the single formally authorized read-only request. No
Runtime source, Hermes production configuration, Instance contracts, or
Enterprise Data files were modified.

## Authorities

- Hermes integration source: `0bad55f21aa088a1ac0a91744fb80f18e1428bec`
- Runtime release: `AIOS_RUNTIME_BASELINE_V1_2` (distribution `1.2.0`)
- Wheel: `aios_runtime_core-1.2.0-py3-none-any.whl`
- Wheel SHA-256: `784f98da895765ffcee8ea74a93c564c29ee630bda2eaadb5324e833cb9f2710`
- Python: `3.9.25`
- Instance: `/Users/yangjiongjie/Documents/AIOS-instances/personal-runtime-v1`
- Data: `/Users/yangjiongjie/Documents/AIOS-data/personal-runtime-v1/business-data`
- State: isolated temporary State root (not formal State)

## Hermes boundary and request

The request used only `hermes_cli.runtime_client.RuntimeClient` and
`POST /v1/invoke`; no direct Host, Provider, SQLite, or CSV access was used
for invocation. The bearer token was read only from the temporary Host State
and is not recorded here.

Capability: `asset.profile`  
Provider: `asset_master_data` / `AssetQueryProviderAdapter`  
Mode: `READ` / `READ_ONLY`  
Asset: `AUTH023_UNIT_0000001`

The Host returned `PARTIAL_READY` with HTTP-ready status because unrelated
declared providers are unavailable; `asset.profile` itself was explicitly
`AVAILABLE` with code `OK`.

## Formal result

- status: `COMPLETED`
- code: `OK`
- execution_id: `exec:d51a53b29904474abfa53b1915cee083`
- audit_correlation_id: `hermes-formal-correlation-8f7dae9dccf94920badc57dec9aacef3`
- result asset_id: `AUTH023_UNIT_0000001`
- result status: `CODE_AUTHORITY_FOUNDATION`
- result fields included unit, floor, building, project and source registry identifiers

The single negative check used the same Hermes client with an unauthorized
capability and returned `403 CAPABILITY_NOT_AUTHORIZED`. No second successful
business request was sent.

## State and restart evidence

After graceful stop, the temporary State database contained exactly one
matching execution, one attempt, and one audit record; the audit record
contained the Hermes correlation ID. The Host was restarted exactly once,
then live/ready/capability checks passed (with the same intentional
`PARTIAL_READY` state), and the execution and attempt counts remained one.
The Host was stopped gracefully again. No replay occurred.

## Integrity

The following pre/post SHA-256 values were identical:

| Contract | SHA-256 |
|---|---|
| instance_manifest.json | `f3fa8f912b49b2a6f1b8d4766b7aa7cebaf9742cf73fa74201029b0c082d7fd0` |
| runtime_environment.json | `f5c5c976c1cfa30cf92258d7e8c955460ebf3de6d95271ebd7d1a0a92669a35e` |
| provider_bindings.json | `6be907308aa825f4ce424c8380714c0748d467ce7ddeb6216f2e39fc0642c9be` |
| capability_profile.json | `240627034967c35db22969e9ae00029fc8e13b2c32552522f27545cc87cf019b` |
| capability_provider_mapping.json | `9f32ae0b8b5c65be779de00fc18ee02d66a588c8c0786599caca115c43f6bddf` |

The governed Asset Foundation CSV remained SHA-256
`02bf986857d3ca23b78735e00d5a1260b2229da687960718bc486b91dbb19efb`.
The released Wheel hash remained unchanged and the formal Data inventory
remained unchanged (12 files). Only the isolated temporary State database
received the authorized audit/checkpoint/lifecycle records.

No formal CSV was opened or parsed by the Hermes client; CSV access occurred
only inside the approved Runtime Provider execution. No JobRuntime was
invoked by Hermes directly, and no formal Instance/Data/State file was
created, edited, or deleted.

## Result tokens

`HERMES_RUNTIME_FORMAL_AUDIT_CORRELATION_PASS`  
`HERMES_RUNTIME_FORMAL_FAIL_CLOSED_PASS`  
`HERMES_RUNTIME_FORMAL_NO_DUPLICATE_EXECUTION_PASS`  
`HERMES_RUNTIME_FORMAL_RESTART_PASS`  
`HERMES_RUNTIME_FORMAL_ENTERPRISE_DATA_READ_ONLY_PASS`  
`HERMES_RUNTIME_PRODUCTION_ENTRY_READY`
