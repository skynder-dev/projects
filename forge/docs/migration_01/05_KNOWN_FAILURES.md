# KNOWN FAILURES / DO NOT REPEAT

1. **Old owner-review click bug:** controls were refreshed while `Busy=true` during live concept load, then never refreshed after Busy returned false. 052 patched `Set-Busy` to refresh owner-decision controls. Preserve/regression-test this.
2. **Localization/null-guard issue:** 053 fixed owner-review runtime localization and explicit EN/RU/ES action labels.
3. **False runtime claims:** static/package PASS is not Windows-native runtime proof. Never collapse those boundaries.
4. **Provider theatre:** fake fixtures and no-dispatch previews are not production image generation. Keep them clearly labeled.
5. **Policy/IP theatre:** prepared queries/packs are not legal clearance or Amazon acceptance.
6. **Endless prep artifacts:** do not respond to missing workflow by creating more sidecar compilers/planners unless they directly unblock executable product flow.
7. **Do not regress to 050 as current:** 050 is rollback. Current product apex is 054.
8. **Do not tie progress to GoDog/Tampermonkey/Supabase orchestration:** this migration is specifically intended to let the agent work directly on product files.
