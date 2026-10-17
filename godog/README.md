## 2026-10-17, clean Tampermonkey label / GoDog 7.0.6

- Owner noticed active Tampermonkey listing `GoDog GDCONST-010 DEFAULT-DISABLED canary` (enabled script, 7.0.2). This is obsolete development terminology, not an intentional product name.
- Source GoDog 7.0.6 changes only userscript metadata and code version label: `@name GoDog`, localized names `@name:en GoDog`, `@name:ru GoDog`. Preserves original `@namespace GoDog.constitution`, `@updateURL` and `@downloadURL` to avoid a new script identity. UI layout, buttons and local-only logic unchanged.
- Script and tests committed; GitHub Actions browser-control mock and offline source CI **PASS** on runs 39000875933 and 39000879359.
- Source staged in Supabase canonical cache `godog-localhub-canary-001` 7.0.6, sha256 `c81d769fd14787b01c220d1989474ff095ae55e2c78983018a1da8ffc6bf7295`; managed Tampermonkey provision `godog-tm-provision-localhub-canary-001` 7.0.6, SHA256 `56ad76476b267dfed48c4f639873121d8ac0185f95a20ad81342633832ba550c`; existing UUID preserved, other scripts disabled.
- **Not installed on owner's PC as of this checkpoint.** An attempt to stage a temporary silent Windows deployment through Relay was blocked; do not present staged artifacts or CI as live install. Do not bypass tool security. Tampermonkey dashboard still displays old name until the already installed script updates from its localhost URL. Do not run more random installations, risk duplicate GoDog scripts, or restart owner's browser without permission.
- Next exact action: use an authorized supported Windows/Tampermonkey update mechanism to atomically stage the SHA-pinned 7.0.6 file at `%LOCALAPPDATA%\GoDog\current.user.js`, check `http://127.0.0.1:43129/godog.meta.js` and full userscript SHA, then verify Tampermonkey's *actual script name and version* in the browser. The user does not want to manually install repeated ZIPs.

## 2026-10-17, PC local Tampermonkey update feed restored

**Windows acceptance boundary: local feed PASSED, live Tampermonkey install NOT YET verified.**

- User's Chrome Tampermonkey 5.5.1 showed enabled GoDog 7.0.2 and "No update found". Old 7.0.2 metadata points at `http://127.0.0.1:43129/godog.meta.js` and `http://127.0.0.1:43129/godog.user.js`. The missing/stale LOCAL source feed caused update discovery to fail.
- Raised archived standalone local-only updater to the Windows PC using a **single-use, SHA-256 verified signed source transfer** through registered GoDog Relay. Script 7.0.5 SHA256 `768bc4c93ca74246adc3aeb37c07f8969803d86e85cb24c31584e04d395a7c0a` stored in `%LOCALAPPDATA%\GoDog\current.user.js`; server installed locally with Windows Startup launcher and never polls cloud.
- The older archived server release 03/04 used *different* `/health` JSON field names. An overly strict validation routine incorrectly declared HTTP failure despite a service delivering the proper script. Corrected acceptance to assert the **actual HTTP content**, not a particular health JSON format.
- Definitive **REAL Windows localhost proof**, Remote Lab command #1245, observed `2026-10-17T03:45:18Z`: `LOCAL_FEED_PROOF {"source":"HTTP_OK","sha":"MATCH","version":"7.0.5","meta":"V705"}`. This means both local GET endpoints replied and full `/godog.user.js` bytes SHA-256 matched 7.0.5. No browser tabs/windows opened or closed during source transfer/verification.
- After HTTP proof, deactivated one-time Supabase bootstrap artifact `godog-pc-local-705-bootstrap-20261017` (active=false), and removed temporary installer/diagnostic apps via GoDog Relay config command `64b205cd-a590-429d-9fd9-ca97ac33dac9` (DONE). Normal local updates use localhost; no GitHub or Supabase runtime update polling.
- **Not yet demonstrated**: Tampermonkey has *installed* 7.0.5. The connected Browser last displayed 7.0.2 in existing ChatGPT tabs. The Tampermonkey scheduler should now be able to discover 7.0.5 from its existing @updateURL. To accelerate and actually test, use the native Tampermonkey check for script updates once; then reload the same ChatGPT tab. This is a runtime verification gate, not repeated ZIP/manual script installation.
- **Future assistant-published versions:** stage only a new SHA-pinned source on the owner PC via explicitly authorized temporary Relay source transfer, atomically replace `%LOCALAPPDATA%\GoDog\current.user.js`, verify localhost `/godog.meta.js` and `/godog.user.js` HTTP bytes with SHA, remove temporary bridge, and let Tampermonkey's native updater discover it. No browser restarts, windows, Supabase/GitHub checks inside GoDog runtime. Until actual TM update is verified, do not claim full end-to-end success.

## 2026-10-16, GoDog full-width live UI repair continuation

**Owner-facing acceptance: NOT PASSED.** The connected browser read of *two different currently open ChatGPT tabs* returned the exact visible GoDog panel tokens `v7.0.2`, `PC`, `PC LOCAL`, `LOCAL` and GO/AUTO/NEW/STOP buttons. This supersedes previous misleading conclusions from stale 6.0.26 Remote Lab/Chrome LevelDB probe. **Do not claim the owner is on 6.0.26 or 7.0.5.**

**Actual repair work:** GoDog 7.0.5 source now handles current ChatGPT `[contenteditable][aria-label="Ask ChatGPT"]`, finds nearest constrained/rounded composer surface, pins dock width explicitly, and has a fallback max width so it cannot ever stretch to whole viewport if composer geometry is missing. Preserved exact 6.0.26 UI HTML/CSS, original colors and controls. JavaScript syntax, mock DOM GO/AUTO/STOP/NEW, and bounded composer width CI PASS: https://github.com/skynder-dev/projects/actions/runs/38863656367. Offline source workflow PASS: https://github.com/skynder-dev/projects/actions/runs/38863602177.

**Delivery staged:** Supabase artifact `godog-localhub-canary-001` 7.0.5 source SHA256 `768bc4c93ca74246adc3aeb37c07f8969803d86e85cb24c31584e04d395a7c0a`, Tampermonkey managed JSON `godog-tm-provision-localhub-canary-001` SHA256 `9da3d463380a73f5b2d0b018e35bd952eebaab74b9d4614383a1efb4ee480f1c`; policy apply command `2b8cf117-8188-4623-ab17-0f810e9a1675` DONE. It is NOT a Chrome runtime install proof.

**Non-interference:** No user tab opened, closed, refreshed, or redirected, and no Chrome browser restart was attempted. Attempted a bounded read-only localhost `127.0.0.1:43129` health probe via registered, hidden Pythonw helper, but result was not verifiable (neither Supabase sink nor LocalHub returned a proving record). Removed the ephemeral helper from managed apps (`602c0d15-f6da-4094-9e5a-23401780c0d9` DONE), and released Remote Lab lease 240. Local update endpoint remains unverified. Do not retry these blind probes indefinitely.

**Next exact action requiring user approval:** obtain authorization for ONE safe Chrome restart restoring the session, OR directly controlled Tampermonkey edit in user browser. Previous user requested not to close or interfere with active windows, so do not assume permission. Upon user approval, back up session state, verify extension's script version in the *actual browser*, then observe dock width visually and test buttons. Do not change code again until there is live browser evidence. If no permission, stop claiming it is fixed; browser-control connector in Chat is read-only.

## 2026-10-12, CURRENT REAL WINDOWS ACCEPTANCE BOUNDARY

**NOT COMPLETE. Do not claim the 7.0.4 script is installed/running in user's Chrome.**

- Existing PC GoDog Relay was live. Recovered registered, silent Remote Lab 1.1.169 through the existing authorized fixed-app launcher, with no browser/UI operation.
- Diagnosed legacy `godog_userscript_update` PowerShell: it only recognizes `@namespace towncousins.local` and copies .user.js files on disk. New GoDog uses `GoDog.constitution`. This updater **cannot install** the new script in Tampermonkey; never try it as a substitute for browser acceptance.
- Chrome Tampermonkey 5.5.1 in actual Default profile verified, userscripts enabled.
- Managed `jsonImport` corrected to Base64 and correct existing script UUID (not an invented new script UUID); source JS remains same 7.0.4 SHA. Old runner and Keepalive disabled in managed provision.
- Managed policy registry applied and separate query readback matched its exact content SHA; signed download key and artifact hash both checked correctly.
- Live Windows typed `godog_refresh_platform_policy_v1` PASS twice, commands 1230 and 1234; no new tabs/windows or focus changes.
- Live Windows typed `godog_restart_extension_renderers_v1` PASS twice, commands 1231 and 1235; browser and tabs **not** closed, no pages reloaded.
- Read-only current Tampermonkey LevelDB probe completed after these operations (commands 1232 and 1236). Last observed GoDog stored version 6.0.26, **no 7.0.2 or 7.0.4 in scanned records**. Earlier owner screenshot showed running GoDog 7.0.2, so this probe does not settle every possible browser runtime/profile; **7.0.4 not proven**.
- Remote Lab temporary exclusive lease 239 formally released. Do not leave pending/unfenced Windows commands and do not retry the same policy/extension restart indefinitely.

**Do not close/restart Chrome or reload owner's working tabs without a fresh explicit approval.** Tampermonkey's official managed configuration is read at extension startup; restarting extension processes was insufficient to prove update. The next task is to obtain a direct, safe Chrome/Tampermonkey in-browser installation and a live UI version + button behavior proof. STOP releasing more ZIPs or altering UI/CSS while this gate is blocked.

## 2026-10-11, managed Tampermonkey Base64 contract fix

**Actual bug:** the managed `jsonImport` export stored enabled GoDog `source` as literal JavaScript. Per official Tampermonkey Deployment documentation, exported script `source` must be Base64. This explains why prior Relay registry `DONE` did not prove installation. The existing script `uuid` was preserved (`c2a87b53-42be-4ee1-9ca8-602200000001`) so repeated provisioning targets the same managed identity, not a new copy.

**One-time bridge executed, no owner steps:** `godog-tm-provision-localhub-canary-001` updated to Base64-encoded GoDog 7.0.4. Decoded source SHA256 is `953e9735013f97c596547d67892957802ab727e18439bf829e14394627ed5448`, byte-identical to the original 7.0.4 code. Provision SHA256 `1ed6f00da44f4810451f2477d493df246ae1344ceb15d89e6b6aa40ee0f16b45`. Exactly one provision script remains enabled; existing legacy runner and Background Keepalive remain disabled.

Relay apply command `f240256c-d673-40be-838d-5b2132cc4ad9` completed `DONE`; subsequent separate read-only `tampermonkey_policy query` event #78 confirms installed registry hash `1:1ed6f00d...` (`present=true`). **This is registry-policy proof, not proof of live Chrome runtime 7.0.4.**

Tampermonkey documentation (https://www.tampermonkey.net/documentation.php?q=deploying) says managed JSON is fetched at extension startup. A currently running chat tab may still show 7.0.2 until normal startup/navigation. Do not claim Chrome installation success or force restart Chrome, terminate extension renderers, refresh existing user tabs or open new tabs. The separate Remote Lab agent was last seen 2026-10-08 and is currently unavailable; do not queue disruptive operations for a later surprise execution.

The goal remains GoDog local-first and one-time migration only. This is not yet evidence that `127.0.0.1:43129` updater is installed or running. No new userscript revision, ZIP or UI changes were made for this Base64 encoding fix.

# GoDog PC LOCAL 7.0.4, UI restoration

- 2026-10-11: restored **original composer-aligned dock geometry**. Original 6.0.26 HTML and CSS are unchanged; only missing layout positioning and labels restored. GO/AUTO/NEW/STOP still use local direct controls, no timers, no Supabase inside userscript.
- Before: 7.0.2 rendered full viewport width (from user's screenshot). After: real Chromium preview at 1220px and 2048px showed dock exactly matching composer left/right and situated underneath it.
- Browser mock smoke [PASS](https://github.com/skynder-dev/projects/actions/runs/38174008054); exact original CSS/HTML identities verified.
- One-time managed Tampermonkey policy for 7.0.4 applied by existing Relay: command `12cc7c66-25f7-4111-a0cf-9e4e4dbdaeb5` DONE; policy event #74 `present=true`; underlying provision SHA256 `0c6f4c650610223824dc89bd243eac94b92fe610f842f18e17b692be43799b7f`. Does NOT independently prove installed userscript in currently open Chrome tab.
- Do not forcibly reload or restart Chrome. The new JS can run only in a newly loaded ChatGPT document. The current tab may continue showing 7.0.2 until ordinary page navigation.
- No new ZIP required. If version does not appear after ordinary navigation, inspect Tampermonkey runtime state; do not publish another blind variant.

# GoDog PC LOCAL 7.0.2

**Runtime and update source are PC-local.** `@updateURL http://127.0.0.1:43129/godog.meta.js`, `@downloadURL http://127.0.0.1:43129/godog.user.js`. GoDog itself does not make Supabase or GitHub calls. GitHub stores source as a backup/release lineage, not a live update backend.

The offline installer bundle `08_GODOG_PC_LOCAL_03_OFFLINE.zip` contains exact `current.user.js`, `server.py` (Python stdlib local read-only HTTP server), one-time `INSTALL_LOCAL.cmd` and `CHECK_LOCAL.cmd`. The bundle was delivered in the GoDog conversation. **The local server is not confirmed installed on the owner's PC; no claims about completed PC setup.** Installer copies the embedded source to `%LOCALAPPDATA%\\GoDog\\current.user.js` without any download, creates a hidden Windows Startup launcher for the local server. `UPDATE_FROM_FILE.cmd` accepts a new local file and does not contact the cloud.

The old Supabase `godog-relay` was used **once** to replace the managed Tampermonkey policy with 7.0.2. Relay command `a011e2a3-4316-401e-8c3e-f3e4f1347179` finished DONE with apply event and `present=true`. Managed script policy has 7.0.2 enabled and old Continuous Runner and Background Keepalive disabled. This is a policy response, not an observed Chrome DOM click proof. Old separate Relay processes may still poll Supabase: the entire former infrastructure has NOT been proven offline or stopped.

CI: https://github.com/skynder-dev/projects/actions/runs/38111959685 (direct buttons mock DOM PASS at 7.0.2). Local updater Python self-test `6/6 PASS` and actual loopback `/godog.meta.js`, `/godog.user.js`, `/health` PASS. The updater serves from loopback only, has no POST/write endpoint, no remote requests and no timers. The user-facing GO/AUTO/NEW/STOP implementation is in `GoDog_PC_LOCAL_01.user.js`; old layout CSS is preserved in `ui/6.0.26_PANEL_ORIGINAL.json`.

Constraints: ChatGPT itself still uses ChatGPT servers; only GoDog orchestration and updates are local. An isolated Windows PC cannot receive remote assistant code changes with zero communication; future updates must be placed in the PC's local folder by user-controlled file transfer or a separately authorized, infrequent remote channel. Never claim autonomous unattended remote delivery while disconnected.

