# Retracted runs

| Run | Video SHA-256 | Why |
|---|---|---|
| 20261010_363998_small-business-transportation-te | 2406292c56f45ed14a6430882c5ee3c4019820f4ca66a7b9d5a621836eac4ba2 | Agency read from `synopsis.agencyName`, which held the grantor contact ("Lynn Bailey Grantor"), not the agency. Fixed: agency now comes from `agencyDetails`/`topAgencyDetails`; contact-like names are rejected. |
| 20261010_363902_ojjdp-fy-2026-community-and-scho | b87c295d96dcfed26312bd353c75bff9d9ba31987c2628c029a6fc69e111ec08 | Same unreliable agency field (correct by chance) and a boilerplate "purpose" quote ("This is a notice of funding opportunity…"). Regenerated with the fixed pipeline. |
