# Locale clicks preserve unsaved edits

**PREPARED — native execution NOT_RUN.** No PowerShell or .NET runtime is installed in the cloud workspace; nothing was installed. Static checks are not PowerShell parsing, WPF or Windows behavior proof.

The focused harness extracts **six actual pinned functions** via the PowerShell AST: `Get-PropertyValue`, `Set-UiLocale`, `Sync-LanguageSelector`, `Initialize-UiLocale`, `Test-CurrentIsResearchDraft` and `Restore-DynamicSurfacesAfterLocale`. It defines **41 ordered cases** under StrictMode 2.0.

Cases cover repeated same-locale EN/RU/ES actions with clean, creative-dirty, publication-dirty and both-dirty editors; normalized/unsupported locale input; different-locale dirty refusal and clean application with/without persistence; direct helper dirty preservation and clean reload/section restoration; nonresearch context; startup application for all three languages, fallback and existing registry. Sixteen creative/listing text fields, listing locale, both dirty flags, current concept identity and synthetic saved readiness/history are compared. Selector synchronization uses the real function against plain control-shaped objects.

## Explicit seams and limits

- `Apply-LocaleUi` is a seam that records application and invokes the **actual** dynamic helper. Static checks verify the production call chain. The real renderer, `Load-LocalPublicationUi`, WPF events, dispatcher, event reentrancy and visual output are **not executed**.
- `Open-ResearchDraftItem` is a deliberately destructive seam that overwrites synthetic editor text and clears both dirty flags, matching only the relevant existing reload effect. The actual loader/store/history/package files are not executed or used.
- Locale save/load, static registry registration, hints and portfolio/section rendering are bounded seams. All controls and saved state are synthetic memory objects. This does not establish disk persistence, restart, actual durable state, package integrity or publication behavior.
- No whole Workbench or module initializer is dot-sourced. Product mutation/network/process boundaries are guarded; guards are not an OS sandbox.

## Native use (not authorized or executed by this preparation)

Use only an already-installed stable PowerShell Core 7.5+ and an independently protected private staging/owned-process supervisor. Parameters: `-PackageRoot` (private app source copy), `-PinsPath`, fresh 32-hex `-RunId`, and fresh empty private `-RunRoot` outside source. The harness does not install runtimes, stage originals, establish ACLs, own a process tree, enforce a timeout or perform cleanup.

Before accepting any future result, the supervisor must support `forge.locale_edit_preservation.native_receipt.v1`, independently pin/rehash source/test/pin bytes and require exit zero plus a fresh complete matching nonce/path receipt, exact 41 case/six function identities in order, every case PASS and unchanged source/test/pin bytes. Missing, partial, stale or unsupported results are not PASS. No execution authority is granted here.
