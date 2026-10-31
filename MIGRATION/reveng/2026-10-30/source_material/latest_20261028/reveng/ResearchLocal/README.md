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
hashes, and reviewed changes. This source tree contains 69 Python application
files and 30 C# application files, plus separate tests and documentation.

Sanitized original source blobs supplied later are reconciled explicitly:

- The native `commercial_review.py` preserves question-identity aliases and
  distinct saved variants rather than silently deduplicating generic URLs.
  `RevEngLocalResearch.cs` adds read-only outcome/history presentation and rejects
  owner decisions on outcome rows. Those two files were imported with their original bytes; follow-on changes are identified separately below and in the manifest.
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

## Unpublished follow-on core candidate

This follow-on is prepared against public commit
`97fc10f422399adcd20177df5129cc7b7d2f71e3`; it does not change that sealed baseline.
It fixes validator false positives and overly broad document routing, not model
quality or a supposed requirement to prove demand before proposing a hypothesis.
Single-report hypotheses and abstention were already allowed.

`price_experiment` is optional. Omit it or use `null` when a proposed amount or
currency is unspecified. A supplied object has exactly:

    {"status":"proposed_unverified","amount":10,"currency":"USD"}

The amount must be a finite nonnegative number, not a boolean or numeric string.
Zero means a proposed free test, never payment evidence. Currency is exactly
three uppercase letters: syntax only, not validation of an ISO currency,
exchange rate, jurisdiction, market price or purchase. No default amount or
currency is filled in. Arbitrary dollar amounts in narrative fields remain
rejected; a typed offer cannot exempt unsupported facts elsewhere.

The existing lexical fact guard now recognizes only complete, explicit
uncertainty clauses such as “There is no proven demand.” It still scans adjacent
positive claims. This is not a general negation parser, semantic truth test or
multilingual fact checker. Every accepted card remains an unvalidated hypothesis
with profit/sales/market scores unset. Proposed offers never establish a buyer,
payment, execution permission or independent demand.

A bounded, explicitly unverified offer projection is visible in comparison rows,
the existing isolated discussion preview, and the CSV's `unconfirmed` cell.
Malformed or oversized display values are withheld rather than rendered as
trusted money. The exact raw JSON remains preserved. No-offer projections match
the public baseline; adding a null field still changes the actual source-file
hash, which provenance correctly retains. Absent/null offers preserve the old
commercial review fingerprint; changing a proposed amount/currency invalidates
that review revision. Nothing is sent to Social or any external service.

Broad categories and a WordPress hostname no longer select specific baggage,
Safari, email or troubleshooting documents. Specific saved-source/proposal words
remain collection hints only. Ambiguous/unmapped tasks receive a reviewable
scope/discovery status, not an “alternatives absent” conclusion. Routing-policy
versions invalidate cached old routes without deleting saved source captures.
The original source priority and no-automatic-admission boundary remain intact.

Additional offline commands (also run with `-O`):

    python -I -B reveng/tests/test_hypothesis_contract.py --source reveng/ResearchLocal
    python -I -B reveng/tests/test_task_routing.py --source reveng/ResearchLocal
    python -I -B reveng/tests/test_price_experiment_projection.py --source reveng/ResearchLocal

These have 15, 12 and 7 tests respectively. Projection tests execute the real
comparison, preview, ZIP and CSV functions against fresh owned synthetic files.
The queue-signature portability check executes only the actual pure signature
functions, not the Windows queue worker. No Windows queue, GUI, model, live
collection, outreach, payment or installation is qualified by these tests.

## Unpublished saved-context selection/preparation proposal

This separate opt-in source proposal does not implement end-to-end cross-run
analysis. The unchanged collection/history path normally prepares only the new
or changed records from a capture. `analysis_jobs.prepare(..., saved_context=...)`
now has an explicit, read-only stage for comparing those records with selected
rows from existing sealed `analysis-inputs` files. It requires the current input
to already exist, plus exact input IDs, raw file SHA256 values, selected original
E-IDs and canonical row SHA256 values. It does not search a corpus, auto-select
related sources, alter collection novelty, recapture sources, or modify the
current job. Passing no selection (or `None`) preserves the public default
prepare body, input identity and output; compatibility tests pin these separately.

A selection has exactly `current_input` and `selected_inputs`. The current
locator contains `input_sha256` and `input_file_sha256`. Each selected locator
adds a nonempty `rows` list containing exactly `evidence_id` and `row_sha256`.
`saved_analysis_context.row_sha256` computes the latter from the complete saved
row with sorted, compact, finite JSON. Hashes provide byte identity, not a source
authenticity signature or semantic proof. Source expiry comes only from the
verified saved payload, never a caller-supplied override.

Bounds are four input files including the current input, 8 MiB per file, twelve
selected/current rows before deduplication, and 64 KiB for the exact complete
proposal. Exceeding a bound fails rather than clipping or substituting text.
Only the existing supported public source kinds/hosts are eligible; the existing
explicit packet projection omits unrelated extra record metadata. Public source
text remains untrusted and is not scrubbed or declared free of personal data.
File identity, reparse/symlink rejection, bounded reads, raw hashes and internal
payload hashes are checked. Unsupported file identity fails closed. Tests do not
qualify native Windows path behavior or every adversarial filesystem race.

Exact duplicate rows appear once while retaining every distinct saved origin.
Different rows retain distinct packet aliases even when their original E-IDs
collide. Original dates and source roles remain unchanged. Same-author relations
are recomputed across the selected rows; missing authors or absent detected
relations never establish independence. Selection itself does not establish
relatedness, task fit, a buyer, demand, payment or any financial fact.

The effective expiry is the minimum of all selected sealed input expiries,
including duplicate origins. Any expired selection is read-only comparison:
`proposal(...)` returns `EXPIRED_SELECTION_READ_ONLY` without a request. The
prepare stage refuses it. Expiry is rechecked after request construction; no TTL
is renewed. Unexpired selection builds the exact combined request using the
actual request builder, preserves observed text, and labels historical context.
An unfamiliar current request, including an existing optional API attachment,
fails rather than silently dropping or rewriting that attachment.

There is no qualified exact tokenizer/admission implementation in this source.
The opt-in prepare stage therefore always raises `TokenAdmissionRequired` with
its read-only `.proposal` before any prepared-input, run-file or queue write.
Its status is `TOKEN_ADMISSION_REQUIRED`, token count is unknown, and execution
is unauthorized. No character count, fake tokenizer, caller count or fallback
can admit it. The proposal is not connected to GUI selection or model dispatch.

    python -I -B reveng/tests/test_saved_analysis_context.py --source reveng/ResearchLocal
    python -I -B -O reveng/tests/test_saved_analysis_context.py --source reveng/ResearchLocal

The 20 tests use actual saved-history, preparation, packet and request modules
with explicitly synthetic owned inputs. They cover two-run delta selection,
identity/hash tampering, row collisions/deduplication, bounds, owned links,
unknown/same authors, TTL expiry, exact default compatibility and no-write stops.
They prove data-selection/preparation behavior only, not token admission,
queue/model execution, live source quality or GUI readiness.


## Unpublished collection/history and queue repairs (2026-10-25)

This isolated source candidate follows the sealed saved-context proposal; it does
not alter that baseline, existing immutable evidence, job IDs or owner decisions.
No live capture, model execution, installation, native GUI or publication is
qualified by the checks below. The saved-context `TokenAdmissionRequired`
boundary and default preparation compatibility pins remain unchanged.

Observation novelty uses the explicit `model_packet_semantics_v2` policy. It
hashes the actual projected packet except capture clocks, local E-ID aliases,
novelty labels and corpus-derived relations. Answer identity/author/URL, answer
links, truncation and all other projected source semantics now participate;
publication time remains source metadata, not a recapture clock. Unknown extra
record metadata and full provenance hashes remain in sealed inputs without
becoming model semantics. Repeated capture dates alone do not prepare a new job.

Migration is derived replay only: verified sealed inputs/snapshots are read,
never rewritten. Prepared semantic revisions are recomputed from their actual
rows, so old preparations remain recognized without creating repeat work. The
index carries the active policy and `revision_references` connecting current
semantic hashes to each original recorded hash/policy and immutable input or
snapshot ID. A single coarse legacy hash may map to several semantic revisions;
it is not a one-to-one alias. An unlabelled legacy record keeps its original
stored hash (or null when no hash was recorded). New snapshot rows explicitly
label their new revision policy. This changes comparison identity only, not
source authenticity, independence, analysis truth or authorization.

The top-level discovery cache in `reveng_local_research.collect` now localizes
malformed/unreadable/incorrectly shaped cache files before enrichment. Strict
JSON, source URL identity, checksum, finite expiry, consumed row fields and
UTF-8 serializability are checked before considering TTL. Bad bytes remain in
place; the source is reported unavailable with `retry=false`, no HTTP fallback,
and a `source_cache_errors` count. Healthy independent sources continue and
ordinary discovery summaries retain exact captured/failed counts. Valid expired
or absent cache retains the existing refresh path; offline mode still forbids
that refresh. Sparse title-only records and empty-title API posts remain valid.
Enrichment exceptions are source-local; cancellation still propagates. This is
not a universal answer-context, pricing or other collector-cache policy change.

When the independent research-card review pauses for budget, the candidate queue
publishes the already finished business reviews but retains `paused_budget` in
both progress and result, with research completed/eligible counts. Materialized
business signatures and completed research entries are reused on resume; no
completed-card recapture is introduced. The actual Python state flow is tested,
not native Windows locking or publication atomicity.

    python -I -B reveng/tests/test_collection_integrity.py --source reveng/ResearchLocal
    python -I -B -O reveng/tests/test_collection_integrity.py --source reveng/ResearchLocal

These 20 stdlib tests use owned synthetic records and enforce no network/model
operations. They execute actual history/prepare/replay, cache collection,
collect-only pipeline and candidate-to-research queue flows. Only transport and
native publication boundaries are explicitly intercepted in the relevant tests;
this does not qualify live capture or Windows behavior. The existing 103 nearby
stdlib contracts also run normally and under `-O`. The separate 15-case API
capability suite is not passed here: ten cases fail at the missing Beautiful Soup
prerequisite, with five passing; no dependency was installed or substituted.

## Unpublished answer-context cache repair

The StackExchange answer-enrichment checkpoint now distinguishes a genuinely
missing or valid expired cache from an unreadable, malformed, identity-mismatched
or checksum-invalid one. Validation uses the existing answer/question attachment
contract before TTL handling. Damaged bytes are preserved without an HTTP retry
or replacement, including when their claimed expiry has passed. A failure in
answer-cache directory setup is also enrichment-local. Valid fresh entries are
reused, and valid expired entries retain the normal refresh path; offline replay
still prohibits refresh.

A limited answer context does not discard a valid primary question. The original
question text, author, links and accepted-answer declaration remain intact;
answer text is unavailable/unknown and carries an explicit collection limitation.
The existing source error list records one `scope=answer_context` entry per batch
with `primary_observations_preserved=true`. Discovery summaries count distinct
whole-source failures in `failed_sources` and distinct answer-limited sources in
`enrichment_limited_sources`; the latter are not counted as lost primary sources.
Answer attachment is staged on copies before updating primary rows. Existing
article/question relations, answer selection and semantic-revision migration
are unchanged. Cancellation propagates; unrelated runtime errors are not relabelled
as damaged-cache limitations.

    python -I -B reveng/tests/test_answer_cache_integrity.py --source reveng/ResearchLocal
    python -I -B -O reveng/tests/test_answer_cache_integrity.py --source reveng/ResearchLocal

These 13 additional synthetic stdlib tests exercise real collection, the
collect-only pipeline and sealed analysis inputs with mocked transport and owned
temporary records. They do not qualify live capture, dependency installation,
model/tokenizer execution, native Windows or GUI behavior. Pricing and WordPress
checkpoint policies are not changed by this repair.

## Unpublished pricing-cache evidence preservation

The pricing collector validates a saved positive or negative checkpoint before
handling its expiry. Malformed/read failures, record checksum mismatches, invalid
negative-cache identity, and missing or damaged HTML receipts are source-local
errors, not ordinary fetch failures: their existing bytes are preserved, no HTTP
fallback is attempted, and no negative-cache replacement is written. Other
healthy pricing sources can still contribute their actual records. Missing
pricing evidence remains unknown/incomplete, never a zero price, revenue claim
or absence-of-competition conclusion.

Positive receipt integrity is checked independently of current parser policy.
An intact old parser contract still follows normal refresh, while a damaged old
checkpoint cannot use policy expiry as permission to replace evidence. Fresh
valid positive/negative entries keep existing reuse behavior; valid expired or
absent entries keep normal refresh and its existing negative-cache behavior for
new transport failures. Offline mode still forbids transport and replacement.
Failed-document receipts are checked for raw byte integrity, without claiming
that denied/non-source HTML is a valid pricing document. Fresh positive reuse
uses the already-verified receipt rather than reading it again. Required
provider/category identity is checked before downstream commercial review.
The actual HTML extractor and pricing interpretation are unchanged.

    python -I -B reveng/tests/test_price_cache_integrity.py --source reveng/ResearchLocal
    python -I -B -O reveng/tests/test_price_cache_integrity.py --source reveng/ResearchLocal

The 16 additional stdlib tests use owned synthetic evidence and mocked HTTP.
For successful refresh only, HTML extraction is an explicit boundary mock, not
an installed/substituted parser: receipt hashing, canonical HTML identity checks,
literal-price parsing, collector persistence and unknown-economics review use
actual source functions. Real Beautiful Soup/Crawl4AI extraction, live capture,
Windows and model execution remain unqualified.


## Unpublished proposed-offer native presentation (2026-10-26)

The Python comparison/preview/CSV projection already carried `price_experiment`,
but both native card views omitted it. The shared `PriceExperimentPresentation`
now appends a bounded offer label in `LocalResearchController.RenderCard` and
`EvidenceComparison.Describe`, using the same original saved card those views
already display. It neither modifies that card nor consumes an unverified
caller-supplied display label. No amount, currency, customer, payment or profit
is inferred. Missing/null offers add no line and preserve the prior display.
A displayed zero carries an explicit native-rounding caveat: it denotes a
proposed free-test hypothesis only if the original offer was exactly zero. The
parsed numeric value alone does not establish that condition. Invalid
shape/type/status/currency and non-finite values show a generic withheld notice;
raw malformed amount/currency text is not echoed.

Native amounts use invariant numeric formatting. Values at or above `1e64` are
conservatively withheld because the native JSON reader can coerce an oversized
integer into a short floating-point representation. This is a presentation bound,
not a monetary limit or a change to the Python acceptance contract: valid very
large exponent values may remain visible in Python exports but be withheld in
the native view. Cross-runtime lexical number identity is not claimed. In particular, the existing
JSON reader can round tiny positive or negative amounts to decimal zero and
round high-precision fractions; the formatter does not replace that reader or
claim to recover original numeric tokens. Ordinary nonzero values retain their
parsed numeric presentation. Original
saved bytes, revision identity, owner decisions and exports are unchanged.

The existing application build includes every `ResearchLocal/*.cs` file; include
`PriceExperimentPresentation.cs` when using a hand-maintained file list. The
canonical local CI harness also expands the `*.cs` glob. No project file exists
in this source-only candidate. A separate true native formatter probe can be
built without Forms or the unavailable legacy executable:

    csc.exe /nologo /target:exe /main:TestPriceExperimentPresentation /out:<owned-build-directory>/TestPriceExperimentPresentation.exe /r:System.Web.Extensions.dll reveng/ResearchLocal/PriceExperimentPresentation.cs reveng/tests/TestPriceExperimentPresentation.cs
    <owned-build-directory>/TestPriceExperimentPresentation.exe reveng/tests/price_ui_vectors.json

The native probe invokes the actual formatter with 18 shared JSON vectors, six
additional actual-JSON-reader precision cases, and CLR edge values. It has not been compiled or executed here: `csc`, `mcs`, `mono`, and
`dotnet` are absent. Whole-application compile and actual GUI rendering remain
separate unmet gates. The available check below tests the same 18 vectors against
the real Python projection and statically verifies the two actual native call
sites. Static assertions are not native execution or screenshot/UI acceptance.

    python -I -B reveng/tests/test_price_ui_contract.py --source reveng/ResearchLocal
    python -I -B reveng/tests/test_price_experiment_projection.py --source reveng/ResearchLocal

The first check fails on both missing call sites in the sealed baseline and
passes on this candidate. The existing seven Python projection/ZIP/CSV contracts
still pass. No network/model/PC operation, installation or publication was run.


## Unpublished saved owner-preference overlay (2026-10-26)

Keep/Reject storage and the main card renderer are unchanged. The comparison
previously showed only the separate evidence-review decision, leaving healthy
`review-notes.json` choices and any recorded note fields invisible. A read-only
`owner_preferences` overlay now captures that primary file, the existing protected
recovery file, and the retained previous-file state with separate byte/absence
pins. The existing exact `candidate_id` + `review_revision_hash` projection is
reused only for legacy candidates, the kind supported by the Keep/Reject editor.
A stale or unbound entry is retained for inspection with no current choice.
Missing, malformed, unavailable and recovery-conflicted states are distinct;
previous/protected copies are never restored or merged automatically. The
existing native recovery description still exposes local conflict copies.

The overlay is computed after the research/evidence chain and remains outside
ordinary comparison `inputs`, `rows`, source catalogs and research-review
revision snapshots. A consistent note update in the primary and its existing protected copy (or
primary alone when no protected copy exists) changes the preference pin, not
the source/card/evidence-review identities or an existing exact Keep choice. A
primary-only edit that differs from the protected copy remains a recovery
conflict with no current preference; that existing policy is not weakened.
Changes detected during preference capture reject the comparison snapshot.
Unavailable reads cannot establish byte identity or current preference authority.
This is bounded snapshot checking, not a claim of atomic cross-file transactions
or exhaustive filesystem-race qualification.

Native Compare always runs its existing full source-derived comparison verifier,
including when a stored chain is missing; file pins alone cannot verify a choice.
It verifies the separate pins and displays the preference independently
from evidence review. Existing comparison-state files require a normal local
rebuild before this new view loads. Isolated discussion export includes an
explicit `saved_owner_preference` when a preference/recovery file exists, never
replaces the evidence-chain `owner_decision`, and keeps readiness/authorization
false. It independently accepts `--expected-owner-preference` to reject an export
when the displayed preference snapshot became stale, without changing the
research-revision identity. No-notes previews preserve the old projection.
Archive previews read only their own archived notes and visibly label the result
historical; no current workspace decision or raw archive bytes are replaced.

    python -I -B reveng/tests/test_owner_preference_overlay.py --source reveng/ResearchLocal
    python -I -B -O reveng/tests/test_owner_preference_overlay.py --source reveng/ResearchLocal

The seventeen synthetic tests run actual comparison, declared-review append,
commercial revision, discussion-export guard and verified ZIP/archive-preview
functions. They cover current Keep/Reject, stale/source-changed choices,
absence/corruption/recovery, capture races, consistent primary/protected note revision invariance and
byte-exact archived notes, plus two static native verification/call-chain checks. Existing
40 offline core tests, seven projection/ZIP/CSV contracts and three price-UI
Python/static checks also pass. No GUI or native result is inferred from them.

The native probe is supplied but NOT compiled or executed here. Build the complete
application using the existing all-`ResearchLocal/*.cs` invocation, then run:

    csc.exe /nologo /target:exe /main:TestOwnerPreferencePresentation /out:<owned-build-directory>/TestOwnerPreferencePresentation.exe /r:<owned-build-directory>/wrapper.exe /r:System.Windows.Forms.dll /r:System.Drawing.dll /r:System.Web.Extensions.dll reveng/tests/TestOwnerPreferencePresentation.cs
    <owned-build-directory>/TestOwnerPreferencePresentation.exe

The persisted preference/recovery fixtures follow the existing save-record shape;
they do not qualify native DecisionStore.Save or its write ordering. That probe
invokes only the actual static presentation method, not Forms or the
legacy binary. The native toolchain remains absent; compilation, the probe, actual
GUI behavior, source collection and model execution are all unqualified. No
migration, new decision/approval system, ranking, admission, publication or
cross-product integration was added.


## Integrated offline CI qualification

The existing recovery-branch RevEng job builds every actual `ResearchLocal/*.cs`
file into the application assembly before invoking `reveng_followon.py`. The
follow-on harness verifies the owned source and exact test inventory, runs all
13 actual Python suites both normally and with `-O` under the existing offline
audit guard, then compiles and executes both native presentation probes against
that same `wrapper.exe`. The probes call actual static production formatters,
not GUI constructors or a substitute implementation. Assertion receipts and
nonzero exits are mandatory; a missing Windows compiler or assembly fails closed.

Each child check has a 90-second timeout and the unchanged hosted job retains its
15-minute limit. Shared Social/Forge execution and all workflow definitions are
unchanged. Existing pinned BeautifulSoup/PyYAML dependencies are reused; no model
packages, source capture, tokenizer downloads, credentials, caches or uploaded
artifacts are added. Native probes do not qualify interactive GUI behavior.

For restricted Linux review only, an explicit `--local-stdlib-only` command runs
12 suites in both modes and labels its result partial: API capability checks and
all native execution remain unqualified by that command. Hosted CI rejects this
flag. Local suite results or prior separate-stage passes never substitute for
actual hosted Python/native results on the exact integrated commit. Historical
stage qualification notes above retain their original scope and dates.

## Unpublished shared-source quotation-budget repair

Quotation validation retains the existing generic canonical-URL groups and adds
only question aliases established by the existing conservative report-identity
resolver over the complete observation inventory. Renamed slugs for a recognized,
metadata-consistent question now share one 25-word budget across cards and
question/answer fields. A row with conflicting source metadata or an ambiguous
fragment cannot split an already-shared URL group. Unknown sites and unsupported
question shapes do not acquire guessed cross-slug equivalence. Existing counts
are retained when a later inventory confirms an alias.

This changes budget accounting, not source records: E-IDs, saved variants,
original URLs, quotation text/ranges and answer attribution remain distinct.
The normal validator, recovered-result check and historical research review all
use the same quotation contract. Saved over-budget results remain held for
review and cannot silently become a repeat model request; source/result bytes
are not rewritten. Export remains a historical/reference projection, not an
admission gate: it preserves exact JSON and original field/URL locators rather
than replacing them with an internal budget key.

The existing `test_hypothesis_contract.py` suite now includes 15 additional
synthetic quotation regressions (30 tests total), already selected by the
unchanged guarded CI harness. They execute actual validation, saved-result
recovery/review and ZIP/CSV export with owned temporary data. They do not prove
semantic truth, source authenticity, live behavior or model quality.


## Unpublished API row isolation and versioned inline-text normalization

The existing public-API collector isolates malformed rows within its unchanged
first-five-item bound. Healthy records are retained; rejected row indices and
reasons are carried into source errors, cache reuse, immutable snapshots and the
prepared input. A partial source is counted separately from a failed source or
answer-enrichment limitation. All-rejected batches remain failures, not empty
healthy samples. Received response bytes are archived before parsing, including
invalid JSON, provider errors and backoff responses; no retry is introduced.

Original StackExchange question URLs must match the exact configured known site,
HTTPS original-question path and any supplied numeric question ID. Answers,
wrong hosts, ambiguous paths/queries and inconsistent source/site metadata are
not guessed into question identity. A valid legacy cache may lack question_id;
validation derives only for checking and never edits its saved bytes. A damaged
or identity-invalid cache remains a source-local error without replacement,
even when expired. Npm names are constrained to safe package URL segments, not
claimed as registry-authenticated packages. Unexpected parser exceptions remain
exceptions, not invented per-row validation reasons.

New HTML context uses `html-inline-v2`: inline tags do not insert whitespace into
words, amounts or URLs; block boundaries still separate text. Exact normalized
text, truncation lengths and hashes are recorded with the parser version. This
is plain source-text normalization, not browser layout, semantic interpretation
or verification of a price/payment claim.

Cache keys are deliberately unchanged. Existing primary and WordPress normalized
contexts are reused as recorded, without reparsing or invented capture times.
Raw answer checkpoints record the parser version under their existing checksum;
unversioned old checkpoints use the retained exact `html-fragment-spaces-v1`
policy. Unknown policies produce enrichment-local limitations with no fallback.
Valid expiry still permits ordinary new capture with the current parser. Sealed
inputs, snapshots, source rows and old response bytes are never migrated in place.
Parser provenance remains in source packets/manifests, but is excluded from the
model projection: a label alone is not source novelty. Changed normalized text
still produces a semantic revision through the existing history mechanism.

The existing guarded collection suite includes 30 added tests (50 total) for
actual fake-transport collection, partial-source preparation, identity rejection,
raw receipts, cache reuse, versioned answers and immutable history. The actual
BeautifulSoup WordPress parser remains untested in the restricted environment;
its legacy checkpoint reuse is tested without a parser substitute. Native GUI,
model execution and live source authenticity are not qualified.


## Buyer original-post normalization (local repair, not published)

New buyer-source reports normalize API HTML with the same versioned inline parser as original_context. Already-normalized WordPress context is treated as plain text, preserving literal angle brackets/entities. Quotes, monetary_source_text and hashes use that bounded normalized text; source length/truncation retains the original parser boundary (including prebounded WordPress context).

buyer_text_contract=2 labels only newly derived reports. Valid historical cached reports without this metadata remain unchanged, without automatic reparse, refreshed dates or recapture. Explicit unknown new policies are quarantined without retry/overwrite. Existing source identity, request budgets, payment-for-offer unknown status and quotation caps remain in force.

Tests use synthetic transport, never live HTTP/models. WordPress parser/identity seams are mocked where bs4 is unavailable; this does not qualify real WordPress parsing. Native Windows, GUI, installed behavior and hosted CI remain NOT_RUN.

## Unpublished local-tool deadline and uncertain-completion repair

PortableRuntime no longer reads Task.Result after an unchecked timed stream wait.
Both stdout and stderr must finish successfully before a receipt is returned.
Async readers avoid UI-context capture and reject oversized output rather than
returning truncated success. The per-stream ceiling is 8,388,608 UTF-16 characters,
matching the largest existing ledger/archive JSON receipt consumers; it is not
an 8 MiB UTF-8 byte limit. Existing 10/15/20/30-second tool deadlines are unchanged;
post-exit drain is bounded at 5 seconds, owned-process exit confirmation at 1 second,
and owned stream/handle cleanup at 1 second. These are requested waits, not a
measured native wall-clock guarantee.

Cleanup refers only to the Process object created by that invocation. There is
no PID lookup, descendant/global kill, external tool, automatic retry or deletion
of an output. Unconfirmed termination or cleanup is reported as unconfirmed, not
as a proven stop. A post-start timeout, stream fault/cancellation, output overflow
or nonzero exit can follow a committed mutation; they produce a typed unknown
operation result. Six existing mutating callers use conditional unknown-outcome
wording rather than declaring that nothing was saved/imported. A staged ledger
proposal is retained for manual reconciliation only on that unknown outcome.
Pre-start failures and normal successful receipts retain their existing behavior.

The actual in-process TestPortableRuntimeDrain.cs probe uses StringReader,
controlled TextReader/disposal seams and TaskCompletionSource tasks; it does not
launch Python, a Process, Forms, models or network calls. It is registered as the
third native probe in the existing application-bound CI plan. Five additional
Python assertions check only source/call-site/plan structure. No C# compiler or
runtime is available in this restricted workspace: the native probe, actual
Process cleanup, Windows/WPF/GUI behavior and wall-clock guarantees remain
NOT_RUN. Errors during receipt parsing or UI refresh after a successful Run are
outside this bounded helper repair and are not claimed solved.

## Unpublished phase-aware persistence reporting

The scoped caller follow-on distinguishes helper return, validated saved or
rejected receipt, and subsequent display/cleanup work. Invalid receipts after a
completed export/import/review tool remain unknown, not proof of no write. The
requested archive path is retained in that diagnostic. Before-start refusals
remain refusals; an explicit validated not-imported receipt remains a rejection.
Quotation and review callers now check their existing saved-status/policy fields
before presenting a confirmed save.

Ledger/comparison refresh functions return separate warnings. A validated saved
or rejected result is not replaced by a later refresh error or hidden by a later
success label. A completed ledger build followed by parsing/presentation failure
no longer claims that the catalog was not rewritten. These are outcome-reporting
changes, not a new transaction or persistence policy.

Staged quotation cleanup is one best-effort attempt after a known outcome. A
cleanup IO/access error retains the confirmed result and adds a warning with the
exact staging path; it cannot escape as a false save failure. Unknown outcomes
retain the staged proposal without a delete attempt. No automatic retry, receipt
rewriting, output deletion, new approval system or UI redesign was added.

TestOperationOutcome.cs calls the actual pure caller receipt/message/cleanup
methods without constructing Forms or launching a Process. Its owned temporary
staging cases include retained unknown, failed cleanup and ordinary deletion.
It is the fourth native probe in the existing actual-assembly plan, but native
compilation/execution remains NOT_RUN here. Four additional guarded Python
source/plan checks are not substitutes for that native probe or real persistence,
Windows/GUI, Process timing or end-to-end UI qualification.


## Local source integration (2026-10-28)

This candidate combines the sealed source-context and inherited quote-identity
repairs with buyer normalization, native runtime timeout and its phase-aware
caller correction.
Application and test-plan deltas are composed against the same exact baseline;
existing cache/history identity and admission boundaries remain unchanged.
Native drain probes are wired but remain unqualified until actually compiled and
executed. Local guarded Python/static checks cannot establish native Process or
GUI behavior. No publication, hosted CI, installation, model or live capture is
performed by this source-integration stage.
