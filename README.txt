TEST-ONLY CI SNAPSHOT — NO PRODUCTION ACTIVATION

Prepared for the separately authorized public review branch. These
three new workflows do not modify existing production workflows. Every workflow
uses GitHub-hosted windows-2022, contents:read and checkout credentials disabled.
No secrets, result branches, self-hosted runners, paid API or production dispatch.
Dependency setup downloads Python packages; tests themselves forbid service/model
calls. Pinned lightweight dependencies: Pillow12.3.0, beautifulsoup4 4.15.0.
No Crawl4AI/browser/model runtime or weights are shipped or required.

Layout
.github/workflows/test-only-*.yml : proposed GitHub workflows (three files)
.ci/test-only/production/         : candidate code copies; four machine-default path sanitizations only
.ci/test-only/harness/            : explicitly adapted offline test harness
.ci/test-only/fixtures/           : synthetic data only; no historical responses
.ci/test-only/CANDIDATE_PINS.json : exact candidate/archive and source hashes
FILE_MANIFEST.json               : exact complete package inventory (except self)
SENSITIVE_DATA_REVIEW.json       : scan rules, scope and remaining review limits
LOCAL_VALIDATION.json            : actual local test outcomes, not Actions results

Local entrypoints (Python3.11 on Windows)
python -B .ci/test-only/harness/verify_files.py
python -X utf8 -B .ci/test-only/harness/run.py social246
python -X utf8 -B .ci/test-only/harness/run.py reveng028
python -X utf8 -B .ci/test-only/harness/run.py forgeAlphaZero

Scope
Social: config + partial override, exact owner_ru resource, selected job transfer,
LocalBridge, new-interpreter reopening. Synthetic media-integrity/freshness stubs
are explicit. This does NOT qualify generated media or verified source packages.
Forge: actual AlphaZero save gate237 checks, in-memory handler45 checks and causal
contract9 checks. Synthetic Russian creative fixture; no historical owner prompt,
model result, image, state, provider credentials or approval is copied.
RevEng: semantic revision and technical clock stability, unknown versus false,
real bs4 synthetic WordPress parser, real offline candidate queue race/retry/crash
recovery, C# wrapper compilation and three static native owner-pin checks.
Model-result late completion is NOT qualified by this synthetic suite; the private
historical proof029 is deliberately excluded. Wave/Crawl4AI real-capture suites,
full GUI/installation and all model/GPU execution are not included.

Portable copies use temp roots. No absolute task path in shipped code/harness.
Four source files have machine-specific runtime defaults replaced by non-operational
relative placeholders only in these CI copies. SOURCE_SANITIZATION.json records
original and CI hashes. Original candidate archives and sources are unchanged.
The harness supplies owned temp runtime paths; no machine model path is exposed.
Only current cooperating writers are covered by publication tests. No OS hostile
code sandbox or protection against deliberate manual bypass is claimed.

LOCAL_VALIDATION.json records local preparation only, before hosted execution.
Hosted run status belongs to the corresponding PR checks. No production installation
or account billing change is part of this test-only package.
