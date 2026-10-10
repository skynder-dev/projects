MERCH FORGE · PRINT PRODUCTION BOUNDARY

Forge separates two things:
1) Local technical evidence: exact file SHA, native image decode, dimensions, transparent PNG/border facts.
2) Channel/template readiness: exact current Amazon Merch product-template dimensions and requirements.

The current Amazon Developer page directs creators to the current Merch best-practices and product-template resources. Those template dimensions are not hard-coded here.

To enable channel-bound print PASS:
- Copy Data\AmazonPrintProfile.template.json to a working file.
- Download the CURRENT product template from Amazon Merch on Demand.
- Hash that exact template file with SHA-256 and enter its hash.
- Enter the exact canvas width/height/DPI/product/template identifiers from the current template.
- Keep the Amazon source_refs; add a more specific current Amazon source if available.
- Set captured_at / valid_until and attested=true.
- Run Import Amazon Print Profile.vbs and select the filled JSON.

This is owner-attested external evidence, not independent verification and not a legal/policy opinion. Forge will never turn historical 15x18/300-DPI guidance into a current universal requirement by itself.

PUBLICATION VALIDITY WINDOW
A modern READY package records the exact Amazon profile validity window used to build it. The package must be created while that profile is valid, and a publication receipt is authoritative only when published_at is not later than that embedded profile valid_until. If the profile expires before manual publication, re-attest the current Amazon template and build a fresh READY package.
