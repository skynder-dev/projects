# Backup restore, rollback and coherent capture regressions

**PREPARED — native execution NOT_RUN.** `pwsh`, `powershell` and `dotnet` are absent in the preparation workspace; no runtime was installed. Python checks establish source shape, ordering and exact bytes, not PowerShell parsing or Windows behavior.

The focused native suite extracts pinned production function ASTs rather than loading the whole Workbench or module initializers. It uses the **actual LocalCore writer, strict JSON/envelope readers, mutation lock, restore context, file operations, backup ZIP creator/verifier and restore installer** against fresh synthetic files. No synthetic success writer substitutes for the successful restore case. Injected failures are explicit wrappers; the commit-then-throw case executes the original writer before throwing.

Cases cover older backup after a newer write identity, contention, stage tampering, missing/unsupported target state, asset failure, precommit refusal, real commit followed by error, synthetic foreign state replacement, rollback failure, pending cancellation/recovery/marker race, normal read/write guard, foreign marker preservation, vanished/busy files and inventory growth during capture, restrictive source sharing, non-restorable mixed recovery preimages, immutable JSON/history/archive bytes, relocated live artwork/acceptance pointers, malformed/missing current-state recovery, normal capture refusing invalid/missing primary, repeated recovery-only controls and recovery refresh refusal. The final pins enumerate exact case/function identities.

## Explicit limits and seams

- All workspace records/assets are synthetic. Artwork bytes are sentinels, not production PNGs; there is no actual package build, marketplace validation, generation, approval issuance or publication. Existing manual-restore approval semantics are preserved, not broadened.
- UI confirmation, status/logging and one recovery-surface hiding helper are seams. A focused WPF case creates controls without showing a window. It is not the full Workbench event loop, visual QA, startup/restart or end-to-end recovery.
- Fault wrappers simulate post-write, precommit, postcommit, rollback and noncooperating foreign mutation. They are not a real process crash or an actual multi-process concurrency run. Windows file-sharing behavior is prepared for testing, **not verified here**.
- Marker/journal/preimage code is intended to fail closed after interruption; no claim of power-loss durability or atomicity across arbitrary filesystem failures is made. The supported recovery action is an explicitly confirmed verified restore, preserving raw conflicting/interrupted bytes, not automatic replay or silent marker deletion.
- Automatic helper source now uses the already-running Core host and existing strict parser dependency closure; no helper process is launched by this harness. Its process-level execution remains untested.

## Native runner boundary

A separately authorized already-installed stable Windows PowerShell **Core 7.5+ in STA mode** is required. Use independently protected private source staging and an owned-process-tree/timeout supervisor. Parameters are `-PackageRoot`, `-PinsPath`, fresh 32-hex `-RunId`, and a fresh empty private `-RunRoot` outside sources. This harness is not that supervisor and grants no installation, PC, execution or publication authorization.

Accept no result without exit zero and a fresh complete `forge.backup_transaction.native_receipt.v1` receipt matching exact nonce, paths, hashes, case/function identities and every PASS, plus independent source/test/pin preservation checks. Missing, stale, partial, unsupported or timed-out results are not PASS.
