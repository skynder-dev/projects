# social - полный статический реестр модулей Python

Чтение AST/docstrings, без импорта/исполнения модулей. Список символов - навигация, не подтверждение функциональности.

## `social/socialreel/__init__.py`

Social: real topic -> grounded claims -> Reel package -> verified 1080x1920 MP4.

Symbols: 

## `social/socialreel/__main__.py`

Нет module docstring.

Symbols: `main`, `write_index`

## `social/socialreel/claims.py`

Claim ledger built deterministically from official fields, plus the grounding validator.  No LLM ever creates a claim. Writers may only *cite* claims; the validator rejects any number, amount or date in the script that is not carried by a cited claim.

Symbols: `_src`, `first_sentence`, `build_claims`, `audience_score`, `_f`, `extract_tokens`, `allowed_tokens`, `_money_ok`, `validate_script`

## `social/socialreel/common.py`

Shared helpers: hashing, stable JSON, dates, paths.

Symbols: `PipelineError`, `sha256_bytes`, `sha256_file`, `stable_json`, `write_json`, `write_text`, `read_json`, `utc_now`, `parse_date`, `_safe_date`, `human_date`, `money`, `_exact`, `_trim`, `slug`, `strip_html`

## `social/socialreel/concept_admission.py`

Local pinned-Qwen admission only. No network, transport, truncation or fallback.

Symbols: `fail`, `admit`

## `social/socialreel/concept_core.py`

Pure concept inputs/schema/request admission, never dispatch or generation.  Extracted from the published concept_first source. Missing pinned tokenizer assets fail closed. Structural checks do not establish semantic idea quality.

Symbols: `authorized`, `digest`, `language_contract`, `inputs`, `schema`, `validate`, `project_source`, `build_request`

## `social/socialreel/concept_decision_ledger.py`

Read-only integrity checks for saved editorial decision history.  No selection eligibility or source/context freshness is established here. Full decision writes remain blocked on canonical source-binding integration.

Symbols: `digest`, `ledger`

## `social/socialreel/concept_excerpt_evidence.py`

Explicit excerpt evidence mode; bound ledger validation, no transport or claims.

Symbols: `checked`, `source_inputs`, `keys`

## `social/socialreel/concept_locks.py`

Owned advisory file locks for concept storage only.

Symbols: `MutationBusy`, `motion_lock`

## `social/socialreel/concept_owner_context.py`

Small explicit owner editorial revision; never source evidence or approval.

Symbols: `digest`, `_read`, `read`, `save`

## `social/socialreel/concept_storage.py`

Atomic concept-only JSON storage; no runtime or default output directory.

Symbols: `write_json`, `atomic_bytes`

## `social/socialreel/concept_store.py`

Storage primitives only. Explicit owned root, no enqueue/worker/model methods.  This does not establish research provenance or register imported source jobs.

Symbols: `ConceptStore`

## `social/socialreel/grants.py`

Grants.gov live connector (public, keyless API) + normalization.  Raw API responses are saved byte-for-byte; every downstream claim points back to the snapshot file and the JSON field it came from.

Symbols: `GrantsGovClient`, `_safe`, `_list`, `_num`, `_bool`, `top_agency`, `normalize`, `from_fixture`, `clean_agency`, `is_closing_after`

## `social/socialreel/json_contract.py`

Bounded generated-schema vocabulary, strict JSON; no semantic approval.

Symbols: `strict_loads`, `equal`, `check_schema`, `validate_node`

## `social/socialreel/pipeline.py`

End-to-end run: live topic -> claims -> script -> voice -> video -> verification -> hashed package.

Symbols: `family`, `score_record`, `discover_live`, `discover_fixture`, `run`, `_fe`, `script_md`, `review_md`, `rebuild`

## `social/socialreel/render.py`

Deterministic vertical-video renderer: Pillow frames piped into ffmpeg (H.264 + AAC, 1080x1920).  This is Social's built-in renderer (the "equivalent local adapter" in the DONE definition). It also writes a MediaEngine handoff folder (stills + per-segment narration + timeline) so the same package can be re-rendered by MediaEngine on Windows without changing Social.

Symbols: `font`, `_text_w`, `wrap`, `fit`, `background`, `Block`, `layout`, `compose_segment`, `_ease`, `draw_progress`, `build_audio`, `render_video`, `_fade`

## `social/socialreel/source_documents.py`

Deterministic text normalization for pinned official dependency bytes.

Symbols: `Text`, `normalized_text`, `_normalize_cached`, `normalized_text`

## `social/socialreel/source_excerpt_model_view.py`

Lossless model view over a hash-bound source excerpt ledger; no consumer I/O.

Symbols: `sha`, `prompt_bytes`, `expanded_rows`, `compact`, `verify_view`, `build_request`

## `social/socialreel/source_excerpt_projection.py`

Pure bounded OJP source quotation projection. No claims, summaries or inference.

Symbols: `encoded`, `digest`, `_failed`, `project`

## `social/socialreel/topic_intent.py`

Explicit finite catalog intent; no keyword, model or source-language inference.

Symbols: `requested`, `validate_record`

## `social/socialreel/verify.py`

Technical acceptance of the final MP4 using ffprobe/ffmpeg (no trust in the renderer's own report).

Symbols: `probe`, `verify_video`, `contact_sheet`, `asr_check`

## `social/socialreel/voice.py`

Narration: text normalization for speech + TTS backends.  Backends, best first: piper (local neural TTS, free) -> espeak-ng (robotic, free). `silent_test` exists only for unit tests; acceptance rejects any video made with it.

Symbols: `speech_text`, `_ordinal`, `wav_duration`, `Voice`, `PiperVoice`, `EspeakVoice`, `SilentTestVoice`, `make_voice`

## `social/socialreel/writer.py`

Script writers.  * template: deterministic, provider-free, always available. * llm: Anthropic Claude via HTTPS, only when config allows spend AND a key is present. Both outputs go through claims.validate_script; an invalid LLM script falls back to template.

Symbols: `short_applicant`, `_agency_phrase`, `template_script`, `_join`, `_clip`, `_description`, `llm_available`, `_call_anthropic`, `llm_script`, `write_script`
