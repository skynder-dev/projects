# ResearchLocal source

This is the canonical source location for the existing Python research tools and
C# integration. It is additive: the Node reference engine in `reveng/src` and
the `app_overlay_g281` application overlay remain separate and unchanged.

## Provenance and scope

The base is the public, hash-verified
`.ci/test-only/production/reveng028/ResearchLocal` snapshot at commit
`3270642235a529a85187cf0e0fdf1e778482d204`. That directory remains historical
CI input, not the location for future application edits. The manifest at
`../RESEARCH_LOCAL_SOURCE_MANIFEST.json` records original identities, canonical
hashes, and reviewed changes. This source tree contains 67 Python application
files and 29 C# application files, plus separate tests and documentation.

Sanitized original source blobs supplied later are reconciled explicitly:

- The native `commercial_review.py` preserves question-identity aliases and
  distinct saved variants rather than silently deduplicating generic URLs.
  `RevEngLocalResearch.cs` adds read-only outcome/history presentation and rejects
  owner decisions on outcome rows. Those two files retain their original bytes.
- `AnalysisOutcomePresentation.cs` starts from the native original and adds
  reviewed bounded, read-only snapshot handling: local non-reparse paths, opened
  Windows handle identity, one byte buffer for hash/strict JSON/provenance, and an
  8 MiB limit before content reads. Input, result, receipt and queue reads use
  that path. Invalid/unconfirmed data remains unconfirmed, not successful empty.
- The API-capability addition carries only selected publisher-documentation
  claims into an explicitly requested synthesis attachment. It records no tested
  capabilities, execution observations, buyers or demand. It uses the real
  canonical `body_text(raw, expected_url)` identity checks and a bounded single
  raw read. Default request construction and current task-fit/admission gates
  are retained. No collection or model execution is triggered by this addition.
- The API author's older `commercial_review.py`, `source_context.py`, and
  `quote_contract.py` are not copied over newer canonical/native implementations.
  Their original Git blobs are preserved and identified in the manifest. The
  three before/after API integration files were used as minimal patch intent,
  not as drop-in replacements. Unchanged dependency blobs were verified exactly.

Two existing tests have corrected synthetic fixtures/expectations: the positive
hypothesis includes its required exact title quotation; URL tests distinguish
conservative saved variants from actual exact duplicates. Production validation
is not weakened. No runtime settings, captured source material, model
requests/responses, real saved workspace data, logs, archives, executables or
model weights are bundled.

## Offline tests

From the repository root, with Python 3.10 or later:

    python -I -B reveng/tests/test_researchlocal_offline.py --source reveng/ResearchLocal --include-existing-tests
    python -I -B reveng/tests/test_identity_portable.py reveng/ResearchLocal
    python -I -B reveng/tests/test_capability_portable.py --source reveng/ResearchLocal

The first suite combines 16 explicit offline contracts and 24 existing unit
tests. The second has 9 identity checks. The third has 15 capability contracts
and requires the real Beautiful Soup dependency. Missing dependencies are a
failure/unqualified prerequisite, never a substituted parser or silent skip.
Tests use explicit source paths; CI stages canonical source into an owned
work directory and verifies the source hashes before and after execution.

The portable harness prohibits network/process/model operations. Its test-only
event loop uses bounded selector polling instead of a socket self-pipe, avoiding
Windows' network-backed socketpair bootstrap without allowing loopback traffic.
Real asyncio tasks, timers and thread completion still execute. This does not
change the application's runtime event loop.

All test records are labelled synthetic unit inputs, not source captures or
product-quality evidence. These tests do not qualify live collection, semantic
correctness, market demand, real API capture/replay or GUI behavior. Native
compilation and execution are separate mandatory Windows checks, not inferred
from Python success. The existing HTML integration checks also require Beautiful
Soup; no test installs dependencies or silently falls back to historical source.

## Existing entrypoints

- `offline_entry.py` provides saved-workspace `check`, `compare`, `export` and
  archive `preview`. These require an existing valid workspace with its source
  records. Missing data is rejected. `init-demo` requires example data that is
  deliberately not included in this code-only import.
- `runtime_diagnostics.py` reports filesystem and optional-module availability.
  It does not load a model or prove a collector can execute successfully.
- `reveng_local_research.py` is the existing collection entrypoint. Its command
  line uses Windows `msvcrt` locking. It is not a portable Linux collector.
  Direct AI execution is disabled; importing/testing grants no permission for
  source capture or model execution.
- `LocalEntry` in `RevEngLocalResearch.cs` is the existing Windows Forms main.
  Existing non-GUI modes are `--diagnostics` and `--check-installation`.

Example read-only diagnostic command for an existing saved workspace:

    python -B reveng/ResearchLocal/runtime_diagnostics.py --root <existing-workspace>

## Windows build and GUI boundary

The existing source target uses .NET Framework, Windows Forms, System.Drawing
and System.Web.Extensions. An authorized Windows CI build can use the existing
compiler invocation with every verified application `.cs` file:

    csc.exe /nologo /target:winexe /main:LocalEntry /out:<owned-build-directory>/wrapper.exe /r:System.Windows.Forms.dll /r:System.Drawing.dll /r:System.Web.Extensions.dll <all-ResearchLocal-cs-files>

The separate presentation probe is not part of the application compile glob:

    csc.exe /nologo /target:exe /main:TestOutcome /out:<owned-build-directory>/TestOutcome.exe /r:<owned-build-directory>/wrapper.exe /r:System.Web.Extensions.dll reveng/tests/TestOutcome.cs
    <owned-build-directory>/TestOutcome.exe <fresh-owned-fixture-root>

The probe requires 40 assertions, including oversized input/receipt rejection,
owned file/directory/root links, handle/path mismatch and snapshot coherence.
All link targets are newly created synthetic fixtures. Inability to create a
link fails qualification rather than counting a skipped test as success. Use a
normal long Windows path: short-name/8.3 aliases may safely fail closed because
opened-handle paths are normalized. The reader is intentionally Windows-only
and fails closed if handle identity cannot be established.

GUI startup separately requires the exact pinned `RevEngResearch.Legacy.exe`.
The wrapper hashes that file and loads `RevEngForm` from it. That binary is not
included, so this is not a standalone GUI distribution. Compilation and headless
presentation tests do not demonstrate GUI startup or behavior. A modern .NET SDK
alone is not an equivalent build target.

Generated runtime material is deliberately ignored in this source directory.
Do not commit settings, saved evidence, logs, executables or model assets to make
a source-only checkout appear complete.
