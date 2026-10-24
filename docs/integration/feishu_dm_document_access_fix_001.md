# My Digital Archiver Feishu DM document access fix

Task: MY_DIGITAL_ARCHIVER_FEISHU_DM_DOCUMENT_ACCESS_FIX_001

## Cause and bounded change

The document/Drive tools previously obtained their SDK client exclusively from a thread-local set by the document-comment agent. Normal DM turns never received it, and worker-thread dispatch could also lose comment bindings. Existing DM errors confirmed this failure on the installed source baseline.

Bind the existing admitted Feishu adapter client for the lifetime of its serialized message turn. A ContextVar follows the existing Gateway/tool context-copying mechanisms and is reset on turn exit, including exceptions. There is no new credential source or global client fallback. Existing comment set_client calls remain supported.

The existing feishu_doc_read tool accepts a document token or a full HTTPS Feishu/Lark /docx/ or /wiki/ URL. Wiki nodes resolve through the same SDK tenant identity before the existing docx raw-content request. Permission failures and non-docx Wiki targets stop without fallback or permission expansion. User URLs are parsed locally, never used as transport endpoints.

## Validation

Baseline: 2acaf21a3fecd32ddef5e6a02462b65967c36ae6, verified against fork/main.

TDD RED: initial seven cases yielded five expected failures and two passes on the baseline. GREEN and regressions: 101 passed, zero failed across test_feishu_dm_documents.py (13), test_feishu_comment.py (9), test_feishu_profile_scope_hops.py (2), test_feishu.py (77). The canonical scripts/run_tests.sh ran in an independent source copy and disposable PM test environment with feishu/messaging extras. An initial incomplete environment had missing optional dependencies and a worktree-home guard failure; these were resolved through test-environment isolation, without changing production behavior or weakening guards.

Ruff checks for changed Python files and git diff --check passed.

## Historical runtime acceptance and boundaries (before Board closure)

At this historical checkpoint, cloud-document and Wiki reads from a user-originated DM were PENDING after the bounded installation/reload. The later Board closure below is the current Wiki-only acceptance state. Unit and transport-mocked tests are not represented as live DM acceptance. Local deployment evidence records exact before/after file hashes and supervisor identity; no credential or document content belongs in this repository.

No AIOS Runtime Core, Provider, Instance, Enterprise Foundation, business database, automation job, or credential configuration changes. Existing plugin pauses and operational admission gates remain in effect.

Rollback: restore only the three backed-up integration files and reload the same aios-personal supervisor. Do not reset the repository or change unrelated overlays.

## Installation and bounded runtime probe (2026-10-24)

Independent static review found no blocking or important issue in the changed paths, including background queue/context propagation. The tested three integration files were installed as a bounded overlay on the verified baseline, with byte-for-byte backups and a private deployment receipt. Installation hashes matched the source candidate; four protected configuration/runtime files remained unchanged. No generic update, reset, credential copy, or unrelated overlay replacement occurred.

Only the existing aios-personal Gateway was gracefully reloaded through its normal supervisor. A replacement process reached running/Feishu connected. The source repository main remains at the baseline; the overlay is explicitly recorded rather than represented as a clean main deployment.

A bounded read-only probe used the installed Hermes handler and existing aios-personal Bot credential source. A previously user-shared Wiki reference returned content; direct docx-token reading of the same underlying object also succeeded through the existing tool-worker context path. No credentials or document body are included in shared evidence. This is not evidence for a separate ordinary-document sharing ACL or a user-originated post-fix DM conversation.

HISTORICAL_LIVE_DM_ACCEPTANCE = PENDING_USER_ORIGINATED_DM

The user has been asked to send an authorized cloud-document URL and Wiki URL to My Digital Archiver in DM. Do not label the overall business acceptance complete until actual inbound DM/tool outcomes are correlated. No comment trigger is required.

## Architecture Board Wiki-only closure — 2026-10-24

Decision: `MY_DIGITAL_ARCHIVER_FEISHU_WIKI_DM_READ_VALIDATION_CLOSURE`, explicitly supplied by the user acting under Architecture Decision. The Board accepts actual full-Wiki-URL DM reading, correct title, WIKI-001, body parity, absence of client-context errors, and no archival/write action. Codex records that adjudication; this documentation update does not claim a new independent runtime test.

```text
MY_DIGITAL_ARCHIVER_FEISHU_WIKI_DM_READ=PASS
WIKI_DM_READ_CLOSURE=CLOSED
DOCUMENT_ARCHIVING=NOT_TESTED
ARCHIVE_RETRIEVAL=NOT_TESTED
ORDINARY_DOCX_DM_READ=NOT_TESTED
INTERNAL_WIKI_NODE_RESOLUTION=NOT_VERIFIED
WIKI_CLOSURE_BLOCKED_BY_DOCX_OR_INTERNAL_RESOLUTION=NO
ARCHIVE_TEST_EXECUTED=NO
ARCHIVE_RETRIEVAL_NEXT_STAGE=PENDING_TARGET_AND_OPERATION_SCOPE
```

The earlier pending status and incomplete Codex observation remain historical. The Wiki-only Board acceptance is current; neither a DOC-001 result nor verified internal Wiki-node tracing is claimed. Preserve the installed client and reader without further refactoring.

The next proposed DM → Wiki read → archive → retrieve validation requires an explicit archival target and operation scope before execution. No archival test, write, service restart, configuration change or broader automation is authorized or performed by this documentation closure. Shared evidence excludes document titles, links, bodies and credentials.
