# CURRENT STATE — Merch Forge (after migration session 01)

## Authoritative release
`055_Merch_Forge_RESEARCH_DRAFT_RC.zip`
SHA-256 `82783210db73ddfcdc579dd4bcbd148f92931c4a9bf03e30a71bb23fb57e97d8` · 289,737 bytes · one top-level folder · deterministic rebuild exact.

- Desktop `2.9.0-research-draft`; backend minimum unchanged `forge-app 0.2.70` (no backend change, no deployment).
- installer_generation `00000000000000100238` (054 was …100237), so it installs over 054 without the downgrade guard firing.
- Rollback: 054 (`c6ea5f50…8383`), then frozen 050 (`13aaf21c…187d`). Both untouched.

## What 055 adds
Discover → select niche → **Create concept draft**:
- Creates a LOCAL draft (`forge.research_concept_draft.v1`, key `rd-…`) in LocalCore state `research_drafts[]`.
- Provenance: contract, snapshot time, backend version, niche id field + value, SHA-256 of the exact niche row, raw row, score/confidence/category/audience, concept count, **only notes explicitly linked to the niche**, and snapshot-wide sources (labelled as such).
- Draft appears in Ideas with status "Research draft" (new filter entry) and uses the normal KEEP/EDIT/REGEN/SKIP owner review.
- Hook and visual direction are left empty and never invented. The Overview lists what is still missing.
- Edit tab saves local revisions (id + SHA-256 over all creative fields). A new revision resets the owner decision to UNDECIDED. Stale saves are rejected.
- A second click on identical research reuses the existing draft.
- Export brief (no dispatch) works and is bound to the current draft revision.
- Blocked for drafts: Generate (button disabled + handler guard), live Accept/Reopen/New iteration/Cancel, delivery/social/owner packages, server publication save. Load-Concept never sends an `rd-` key to the API.
- Local owner gates that already existed (local artwork import, exact local accept) work as for offline concepts. Nothing in them was widened.

## Proof — what is proven and how
| Item | Result | Environment |
|---|---|---|
| 054 restore: outer SHA, inner integrity 50/50, all .ps1 parse | PASS | Linux, PowerShell 7.4.6 |
| 052 Set-Busy owner-control refresh, 053 RU/ES labels intact | PASS (static + executed) | same |
| Static/package acceptance | **49/49 PASS** | same |
| Research-draft self-test (real Forge functions, stubbed WPF, isolated state, 3 processes: create / restart / 054 rollback) | **67/67 PASS**, 0 API calls, 0 network calls | same |
| Mutation check of the test (3 injected regressions: 052 refresh removed, Generate guard removed, constant revision id) | all 3 caught | same |
| Independent code review (separate agent) | 8 findings → all fixed and covered by tests | — |
| Integrity of final ZIP from fresh extraction | 52/52, no unlisted files | — |

## NOT proven (boundaries)
- **Native Windows PowerShell 5.1 + WPF execution of 055 is not proven.** No XamlReader load, no real clicks, no rendering check. XAML was only checked for well-formed XML, unique names and existing style keys.
- PowerShell 5.1–specific JSON behaviour (array serialization) was mitigated in code and is checked at the raw-JSON level, but only on PS 7.
- The provider-pipeline self-test (run by the Windows preflight) needs WPF and was not executed. Its inputs (LocalCore, GenerationProvider, WorkerBridge, Media, ImageValidation and the self-test script itself) are byte-identical to 054.
- No live Discover data was used. Tests use a labelled fixture with the forge.discover_snapshot.v1 shape. Real field names for niche ids and note→niche links are matched defensively (`niche_id`/`id`/`niche_key`/`key`/`slug`, notes by `niche_id`/`niche_key`/`niche_slug`/`niche_name`). If the live contract uses other names, drafts still work but match **zero** notes (fail-closed, never fuzzy).
- 051–054 native click/persistence proof is still outstanding, as before.

## Authority
No backend deployment, Supabase mutation, paid provider call, generation, acceptance, publication or external contact was performed or newly authorized.
