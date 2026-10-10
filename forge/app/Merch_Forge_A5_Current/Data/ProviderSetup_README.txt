MERCH FORGE — IMAGE PROVIDER SETUP

Default behavior remains fail-closed and uses the manual artwork bridge.

Automatic provider path packaged in this release:
  openai_image_api → OpenAI Image API → local worker → SHA-256 + PNG dimension/alpha verified result import

The provider is NOT enabled by the package. No API key is embedded.
Run “Configure Image Provider.vbs” to choose a render profile and local daily paid-request ceiling. The key is protected for the current Windows user via Windows secure-string/DPAPI storage. OPENAI_API_KEY is also supported for managed deployments. Leaving the key field blank keeps an existing stored key.

PROFILES
  Draft: gpt-image-2.5-flare · 1024x1024 · medium · 2 variants
  Final: gpt-image-2.5-sunburst · 2048x2048 · high · 3 variants
Both require transparent PNG output.

BEFORE SPENDING MONEY
1. Run “Test Image Provider.vbs”. LOCAL only: no network, no image generation.
2. Optional: run “Test Image Provider Online.vbs”. This makes ONE authenticated GET to the OpenAI model-metadata endpoint to verify credential/model access. It does NOT call /images/generations and does NOT create an image.
3. In Forge, every Generate click shows exact provider/profile/model/size/quality/count and today’s paid-request count before confirmation.

COST / RETRY SAFETY
- Each generation job permits exactly ONE provider request.
- There is NO automatic paid retry.
- A per-Windows-user daily paid-request ceiling is enforced both before job creation and again inside the worker under a single-dispatch lock. Ambiguous attempts count because they may have been billed.
- Pre-request dollar cost is intentionally not guessed: image cost depends on token usage. Provider response usage is recorded when returned.
- HTTP redirects are denied.

RECOVERY / VALIDATION
- A worker attempt journal is written before dispatch.
- Completed response metadata, OpenAI request id and usage (when present) are recorded.
- Generated assets must decode as PNG at the exact requested dimensions and contain an alpha channel.
- Result import requires exact job SHA, attempt journal, revision identity, prompt identity, dimensions, alpha-channel presence and asset SHA-256.
- Provider-generated artwork is NEVER accepted automatically. Exact owner Accept remains a separate action.

Official contracts validated 2026-10-01:
  https://developers.openai.com/api/docs/guides/image-generation
  https://developers.openai.com/api/reference/resources/models/methods/retrieve
  https://developers.openai.com/api/docs/pricing

017 provenance hardening
- Draft/Final default to dated GPT Image 2.5 snapshots for reproducible output behavior.
- Every generation job binds the exact provider registry SHA, provider contract version, and owner-config fingerprint.
- Result/import/accept/package preserve model, profile, request ID, prompt SHA, revised prompt, result/attempt SHA, and usage when returned.
- Moving aliases remain allowlisted only for legacy-config migration; saving the config again pins the dated snapshot.

018 prompt/print guard
- Prompt compiler is versioned as forge.prompt.apparel.v2 and its template SHA is stored with every generation lineage.
- Exact slogan text is requested verbatim exactly once; no extra text is allowed by the compiler.
- Generated PNG validation now requires all sampled canvas border to be genuinely transparent, not merely an alpha-capable pixel format.


FIRST LIVE SAFETY
Before the first verified completed billable OpenAI image attempt, Forge permits only the Smoke profile (Flare / 1024x1024 / medium / 1 image) and requires the daily paid-request ceiling to be exactly 1. Draft and Final become eligible only after that exact live result has also passed Forge import and produced a valid generation_import_receipt.v4. Internal mock attempts never unlock production profiles.
