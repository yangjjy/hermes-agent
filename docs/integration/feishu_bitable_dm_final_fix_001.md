# Feishu Bitable DM minimal integration fix

## Bounded CI corrections and desktop test timing — 2026-10-27

The operator authorized a minimal test-only correction after the existing desktop Git integration test exceeded Vitest's default 5-second total budget on two separate CI runs. No isolation defect or production update defect is claimed.

Before correction:
- The exact unchanged test failed twice with Test timed out in 5000ms; one CI measurement was 6,576ms.
- An instrumented isolated run passed in 2,063ms. Its two real Python CLI calls took 1,556ms and 291ms; real Git operations were retained.
- The evidence supports an aggregate integration-test budget mismatch on shared runners. It does not establish the precise CI scheduling cause.

Correction:
- Only that single existing test receives a 15,000ms total budget. All assertions, real Git operations, platform conditions and cleanup remain unchanged.
- The default timeout and all other test timeouts are unchanged.
- No production update logic, Runtime, Provider, Base roles/members or credentials are modified.

Local validation after correction:
- Target update-ui file: 9/9 passed.
- Entire tests-js suite: 34 files passed; 203 tests passed, 3 pre-existing platform skips.
- Process observation: target run observed 18 test processes; full regression observed 262. No observed process or target temporary directory remained after completion.
- Earlier local broad-run errors from missing root dependencies, Python command lookup and non-canonical temporary paths were environmental failures, not passing evidence. They were resolved only in the isolated test environment before the successful full regression.
- Repository static checks: 11 passed; git diff --check passed.

The two earlier PR-specific CI fixes are limited to installing the existing Feishu extra in the test environment and adding the newly declared feishu_bitable toolset to the current metrics schema enum. The existing exact-value test was reproduced failing before the enum correction and passing afterward. The five Python regression files passed 68 tests.

Remote CI must actually pass on the final candidate before merge. This local evidence does not certify remote CI, deployment or real Bot DM acceptance. Temporary Actions enablement is authorized only for PR #3, with the recorded original disabled configuration restored after verification.

## Native authorization and advanced-role readback — 2026-10-26

The operator explicitly authorized the minimum collaborator-read scope and completed the native browser flow. The old CLI Device Flow returned 20001; its cause is unresolved and it was not used as proof of permission denial. No CLI token was copied.

A later inspection found the native access token expired. The installed native refresh method successfully refreshed that expired session before the read-only role/member calls. This proves recovery from an observed expired session in this bounded invocation; automatic refresh by the continuously running MCP process remains unobserved.

The target Base returned two custom roles: 仅看视图的客户 and 普通用户. Both member-list responses succeeded with items=[], total=0 and has_more=false. My Digital Archiver was not found in these returned custom roles. This does not establish the application's default/system-role membership or all access paths. Both returned role definitions expose allow_add_record=true and allow_delete_record=true for the target table; do not assign the Bot to either based on its display name. No role/member/permission mutation occurred.

The earlier missing collaborator scope is superseded by this successful readback. A subsequent single Bot field-read probe, using app cli_a9e67013acb8dbcc and tenant_access_token, again returned 1254302 RolePermNotAllow. No source record body was read. Bot data-read authorization is still denied; real DM acceptance remains unverified. Source changes are tracked through PR #3; consult its actual checks and merge state. Deployment and live DM acceptance remain separate. The operator must confirm the exact application read-only role/table scope; no write grant is proposed.

## MCP native authentication follow-up — 2026-10-26

The operator completed the original MCP native OAuth login. No CLI token or authentication store was copied.

Actual verification:
- Native user login succeeded.
- A bounded MCP useUAT=true field read succeeded.
- The installed native LarkAuthHandlerLocal.refreshToken method completed one real refresh.
- The access-token reference changed, the native local reference was updated, and refreshed metadata plus a refresh credential were persisted.
- A separate process reloaded a valid native session.
- A post-refresh read through the connected MCP server succeeded; field metadata matched the pre-refresh read.

This establishes a real bounded refresh/persistence/readback lifecycle. It does not certify observed natural-expiry automatic triggering or indefinite unattended availability. Those remain NOT_OBSERVED / NOT_CERTIFIED, respectively.

Current target field API response: **6 fields**, all returned with is_hidden=false, including **统一社会信用代码** in addition to the historical five-field baseline. No source field or record was changed by this task. Record this as a baseline difference; do not silently assert a five-field live result or substitute the old capture for current metadata.

Bot application access, Bot role membership, source CI and real Hermes DM acceptance are unchanged and separate from this MCP user result. The collaborator-read decision and subsequent successful role inspection are recorded in the latest addendum above. Temporary GitHub Actions enablement for PR #3 was subsequently authorized; original settings must be restored.

---


Task: AIOS_HERMES_BITABLE_DM_FINAL_FIX_001
Date: 2026-10-26 (Asia/Shanghai)
Status: SOURCE_CANDIDATE / NOT_DEPLOYED / LIVE_DM_NOT_ACCEPTED

## Problem and change

The task-marked DM entered aios-personal but had no Bitable reader available. It called aios_runtime_read with empty arguments and was rejected with RUN_ID_INVALID. This was not a successful Bitable read or evidence of a Runtime Core defect.

Extend the existing Feishu service-gated tools with only:

- feishu_bitable_read_fields: field IDs, names and types from the specified Base/table/view.
- feishu_bitable_read_records: bounded full pagination, unique source-ID counting and count-only output. Record bodies and company names are not returned.

Both use tools.feishu_lark.get_client() and build_request(), reusing the admitted turn-scoped native client and tenant_access_token. No new client, token store, credential fallback or connector is introduced. Reads use GET only, 200 items per page and a hard 32-page limit. Permission failures, repeated/missing cursors, duplicate IDs, changing totals and incomplete envelopes stop without claiming a complete count. Transport failures are sanitized and not retried.

The existing platform-native tool recovery makes the scoped toolset available even when Feishu explicitly enables only aios_runtime. No terminal/file toolset or expanded MCP server list is needed. Existing Docx/Wiki and comment implementations remain unchanged.

## Verification

- RED: the new test file failed collection on the admitted source baseline because the Bitable module did not exist. Environment permission failures before that are not counted as RED.
- Focused coverage includes existing-client identity, schema visibility under the Runtime-only profile, tenant-only request construction, invalid URLs, eight synthetic pages totaling 1,463 records, no body leakage, duplicate IDs/cursors, missing cursors, API denial and sanitized transport failures.
- Docx/Wiki, comment and toolset regressions run separately from live acceptance.
- The upstream per-file test runner was used with only its scratch-directory function redirected from the inaccessible /var/tmp to the permitted temporary directory. Test subprocesses, assertions and per-file isolation were retained. No runner source change is included.
- Repository scripts/check and git diff --check are required before publication. Local test counts and final commit are recorded in the task receipt.

Synthetic 1,463-record replay is not a live Bot acceptance result.

## Actual permissions and authentication remain separate

The actual app identity is My Digital Archiver, app ID cli_a9e67013acb8dbcc. Prior same-resource probes returned five fields as user and 1254302 RolePermNotAllow as bot. The administrator confirmed read access; native Base metadata confirmed advanced permissions and returned two role entries. After the execution approval service recovered, the read-only membership calls were executed but Feishu denied both with 99991679: the user authorization lacks one of bitable:app, bitable:app:readonly, or base:collaborator:read. Bot membership and target-table permission mapping remain unverified; missing-member results are UNKNOWN, not false. Only the smallest collaborator-read scope has been proposed for user consent. This patch does not grant or alter permissions.

The separate native MCP user store had no active session, and native login did not complete. Existing CLI user authentication and its accepted complete capture are retained. The installed MCP refresh method passed six isolated checks in the prior receipt, but live refresh and long-term authentication are not certified. This Bitable tool does not substitute CLI/MCP user credentials for Bot identity.

[Previous correlated evidence](https://github.com/yangjjy/AIOS/pull/23) remains valid until replaced by new real observations.

## Bounded deployment and live validation

1. Verify this source against the fork main and preserve the approved installed overlay, especially the existing turn-scoped Docx/Wiki client fixes. Do not copy an entire checkout over the installation.
2. Deploy only the reviewed Bitable module and toolset extension after normal source checks and the required execution approval. This task does not report installation as completed.
3. Use a fresh session/approved reload boundary. Do not mutate a conversation's cached historical tool schemas or clear user history to force the new surface.
4. Independently establish the exact Bot advanced-role read permission. Submit any precise role adjustment for approval; do not grant write access or broaden sharing.
5. Send the original Base URL in a real Hermes Feishu DM. Confirm actual calls to the two Bitable tools, application identity, actual current field metadata, terminal pagination and the observed source record count. Compare with the accepted source baseline; do not force the answer to 1,463 if the source changed.
6. Record all read failures, partial/unknown results and Docx/Wiki regression outcomes. Only a successful real DM permits PASS/CLOSED.
7. Verify MCP user refresh through its own native login and observed refresh lifecycle independently. A valid one-off token and synthetic tests are insufficient.

No enterprise database, AIOS Runtime Core, Provider, Authority or Cron change. No new Architecture Gate. Rollback removes only this source extension through the normal deployment rollback process; preserve all earlier document reads and profile pause controls.

## Source review state

Hermes PR #3 contains this candidate. The original repository Actions state is disabled. Temporary PR #3 CI enablement and restoration are authorized; report actual CI and merge outcomes separately. Existing live installation, credentials and profile configuration are unchanged.
