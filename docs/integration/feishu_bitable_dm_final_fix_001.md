# Feishu Bitable DM minimal integration fix

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
5. Send the original Base URL in a real Hermes Feishu DM. Confirm actual calls to the two Bitable tools, application identity, five fields, terminal pagination and the observed source record count. Compare with the accepted source baseline; do not force the answer to 1,463 if the source changed.
6. Record all read failures, partial/unknown results and Docx/Wiki regression outcomes. Only a successful real DM permits PASS/CLOSED.
7. Verify MCP user refresh through its own native login and observed refresh lifecycle independently. A valid one-off token and synthetic tests are insufficient.

No enterprise database, AIOS Runtime Core, Provider, Authority or Cron change. No new Architecture Gate. Rollback removes only this source extension through the normal deployment rollback process; preserve all earlier document reads and profile pause controls.

## Source review state

Hermes PR #3 contains this candidate. Repository Actions is currently disabled; no remote CI pass or merge is claimed. Temporary CI enablement and restoration has been requested separately. Existing live installation, credentials and profile configuration are unchanged.
