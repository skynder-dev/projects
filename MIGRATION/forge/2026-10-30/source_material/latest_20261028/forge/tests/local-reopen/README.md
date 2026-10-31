# Exact local acceptance withdrawal regressions

**PREPARED — native execution NOT RUN.** `pwsh`, `powershell` and `dotnet` are absent in the cloud preparation workspace. No runtime was installed. Python/source checks do not prove PowerShell parsing, product behavior, WPF or Windows execution.

## Coverage contract

`Test-ForgeLocalReopen.ps1` loads **33 actual pinned production functions** by native PowerShell AST extraction under the Workbench's StrictMode 2.0 and defines **39 ordered cases**. It exercises the real shared acceptance control gate, real `Reopen-CurrentAcceptance` Domain route, exact local displayed-target helper, local mutation, review-history preservation/projection and current-readiness rejection after withdrawal.

Prepared cases cover local owners without server capability; local acceptance on research and nonresearch concepts; blank reason; cancel with unsaved listing data; exact confirmation identity; stale displayed state; new acceptance of identical artwork; legacy acceptance without an instance ID; exact revision/write-ID fences; confirmation-time navigation/creative or publication edits; rejected writes and simulated write race; single-write authority withdrawal; unchanged saved idea approval/owner decision/revision; detached immutable historical evidence with reason and prior package flags; retained artwork/archive bytes and publication receipts; saved JSON reload; postcommit UI and individual button-setter failures; commit-then-throw uncertainty; repeated action; missing artwork file; absent/null/empty/mixed-case valid legacy state tokens; invalid nonstring token; unreadable/duplicate state; corrupt history; and zero guarded external calls.

`LocalReopenDependencies.json` lists all actual functions and explicit seams. `LocalReopenFixtures.json` identifies synthetic inputs. `LocalReopenPins.json` pins the script, dependencies, fixture declaration, source files and exact ordered case/function identities.

## Explicit limits

- Read/write persistence is a **synthetic JSON store** with an explicitly simulated optimistic fence. Rejection, race and commit-then-throw are injections. This does not establish actual durable-store locks, atomic file replacement, recovery, multi-process concurrency or verification-error behavior.
- Controls are plain objects, confirmation answers are queued, and publication/status/stage refresh use bounded seams. A throwing `ScriptProperty` simulates one control setter. This is not WPF event wiring, native dialogs, visual QA, actual Windows execution or complete startup/restart.
- The saved-reload case reconstructs a detached view from synthetic JSON using actual draft conversion; it is not an application restart.
- Artwork/archive files contain preservation sentinel bytes, **not valid PNG or ZIP packages**. Exact byte preservation is checked, but decoding, package/receipt authority, server state and external publication are not tested.
- Existing idea approval remains unchanged. No approval function is called, and no new revision, model, provider, server API, generation synchronization, check automation or publication is authorized. Guarded boundary attempts are counted across the suite; even a swallowed attempt fails the final case. These guards are not an OS sandbox.

## Native execution boundary

Use only an already installed stable PowerShell Core **7.5+** with `ConvertFrom-Json -DateKind String`, under the previously reviewed private-staging/owned-process-tree supervisor. No installation, policy relaxation, legacy-host fallback, desktop interaction, network/provider/model call or publication is authorized by this harness.

The harness requires `-PackageRoot` (private app source copy), `-PinsPath`, fresh 32-hex `-RunId`, and an empty private `-RunRoot`. It is **not** a staging, ACL, isolation, process-tree, timeout or cleanup supervisor. The supervisor must independently protect and rehash originals/private copies, control process ownership and deadlines, and wire exact acceptance of `forge.local_reopen.native_receipt.v1` before execution can count as verified.

Require exit zero plus a fresh complete matching receipt: exact nonce/paths/hash sets, all 39 case identities and 33 function identities in order, every case PASS, no errors and unchanged sources/test/fixture/pin/sentinel bytes. Missing, stale, partial, mismatched, timed-out or unsupported results must be FAIL/BLOCKED, never a reused PASS. A passing focused receipt, if later obtained, still does not imply full-product or Windows readiness.
