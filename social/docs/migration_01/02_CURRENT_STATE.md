# Current state

Migration boundary: 2026-10-09.

## Known-good

- Contract: `SOCIAL_REAL_REELS_V1`.
- Grants.gov live connector/research path proven.
- 1 live topic path proven.
- 3 research packs were prepared.
- Earlier durable state reported 12 grounded claims and 3 prepared generation requests.
- Previous research pack scores were 70/70/70.
- Generation runtime `social-reel-package-generate` v3 existed.
- No provider attempt had succeeded.
- No fake package is accepted.
- MediaEngine now has proven vertical/social rendering capability and a proven semantic FolderToReel path.

## Counters that matter

- LIVE TOPIC: 1/1
- RESEARCH PACKS: 3/3
- REAL REEL PACKAGES: 0/3
- FINISHED MEDIAENGINE REEL: 0/1

These counters are the authoritative product truth for migration.

## Legacy blocker

The old implementation required a server-side OpenAI API key. Runtime health reported no supported key source present.

This is now classified as a LEGACY IMPLEMENTATION BLOCKER, not an owner blocker.

Claude should not wait for the owner to buy/configure another API path merely to generate text. Claude itself may create the package content from grounded research. If a later production architecture needs a provider, document that separately after the first real end-to-end Reel exists.

## MediaEngine handoff

MediaEngine is a separate project and its accepted/stable code must not be casually mutated from Social.

Use the downstream contract as a consumer:
- target vertical format: Social HD / 1080x1920 where appropriate
- preserve exact package identity
- keep factual source/claim lineage
- render to a playable video
- verify final output

Historical MediaEngine acceptance evidence is included only as a handoff reference.
