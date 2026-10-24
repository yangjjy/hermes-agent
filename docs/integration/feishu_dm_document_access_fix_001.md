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

## Runtime acceptance and boundaries

Actual cloud-document and Wiki reads from a user-originated DM remain PENDING until observed after the bounded installation/reload. Unit and transport-mocked tests are not represented as live DM acceptance. Local deployment evidence records exact before/after file hashes and supervisor identity; no credential or document content belongs in this repository.

No AIOS Runtime Core, Provider, Instance, Enterprise Foundation, business database, automation job, or credential configuration changes. Existing plugin pauses and operational admission gates remain in effect.

Rollback: restore only the three backed-up integration files and reload the same aios-personal supervisor. Do not reset the repository or change unrelated overlays.
