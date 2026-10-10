# Merch Forge

Local-first Windows workbench (PowerShell + WPF) for turning market research into production-ready merch products.

| Path | What |
|---|---|
| `app/` | Current release tree (exactly what goes into the release ZIP). Run `START_0xx_MERCH_FORGE.vbs` on Windows. |
| `releases/` | Built release ZIPs + SHA-256. |
| `archive/` | Immutable reference ZIPs: 054 canonical, 050 frozen rollback, 050 prep packets. Never edit. |
| `docs/` | `CURRENT_STATE.md`, `NEXT_ACTION.md`, `WORKLOG.md`; `migration_01/` = handoff bundle from the previous environment. |
| `tools/` | Build/acceptance scripts. |

Rules: see `docs/migration_01/ALEX_AUTONOMOUS_WORK_CONTRACT.md` and `04_OWNER_RULES.md`. No paid generation, publishing or backend mutation without explicit owner authorization. Static/headless PASS is never a Windows runtime claim.

`app/` files are covered by `app/Merch_Forge_A5_Current/integrity.json` and checked byte-for-byte at startup; `.gitattributes` disables line-ending conversion so a Windows checkout stays valid.
