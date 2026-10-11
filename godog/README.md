# GoDog PC LOCAL 7.0.2

**Runtime and update source are PC-local.** `@updateURL http://127.0.0.1:43129/godog.meta.js`, `@downloadURL http://127.0.0.1:43129/godog.user.js`. GoDog itself does not make Supabase or GitHub calls. GitHub stores source as a backup/release lineage, not a live update backend.

The offline installer bundle `08_GODOG_PC_LOCAL_03_OFFLINE.zip` contains exact `current.user.js`, `server.py` (Python stdlib local read-only HTTP server), one-time `INSTALL_LOCAL.cmd` and `CHECK_LOCAL.cmd`. The bundle was delivered in the GoDog conversation. **The local server is not confirmed installed on the owner's PC; no claims about completed PC setup.** Installer copies the embedded source to `%LOCALAPPDATA%\\GoDog\\current.user.js` without any download, creates a hidden Windows Startup launcher for the local server. `UPDATE_FROM_FILE.cmd` accepts a new local file and does not contact the cloud.

The old Supabase `godog-relay` was used **once** to replace the managed Tampermonkey policy with 7.0.2. Relay command `a011e2a3-4316-401e-8c3e-f3e4f1347179` finished DONE with apply event and `present=true`. Managed script policy has 7.0.2 enabled and old Continuous Runner and Background Keepalive disabled. This is a policy response, not an observed Chrome DOM click proof. Old separate Relay processes may still poll Supabase: the entire former infrastructure has NOT been proven offline or stopped.

CI: https://github.com/skynder-dev/projects/actions/runs/38111959685 (direct buttons mock DOM PASS at 7.0.2). Local updater Python self-test `6/6 PASS` and actual loopback `/godog.meta.js`, `/godog.user.js`, `/health` PASS. The updater serves from loopback only, has no POST/write endpoint, no remote requests and no timers. The user-facing GO/AUTO/NEW/STOP implementation is in `GoDog_PC_LOCAL_01.user.js`; old layout CSS is preserved in `ui/6.0.26_PANEL_ORIGINAL.json`.

Constraints: ChatGPT itself still uses ChatGPT servers; only GoDog orchestration and updates are local. An isolated Windows PC cannot receive remote assistant code changes with zero communication; future updates must be placed in the PC's local folder by user-controlled file transfer or a separately authorized, infrequent remote channel. Never claim autonomous unattended remote delivery while disconnected.

