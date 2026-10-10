MERCH FORGE — LOCAL SALES CSV IMPORT

Purpose
- Populate local 7 / 30 / 90 day sales and royalty metrics without requiring the live backend.
- The import is local-only and does not claim marketplace synchronization.

Recognized columns (case-insensitive aliases)
Date: date | order date | sale date | transaction date | period
Units: units | units sold | quantity | qty | items sold
Royalty: royalty | royalties | earnings | amount | net earnings
Revenue (optional): revenue | sales revenue | gross sales | gross
Product title (optional): title | product title | design title
Product id (optional): asin | product id | listing id | sku

Rules
- A file is de-duplicated by SHA-256; importing the same file twice does not duplicate rows.
- Rows with an unparseable/missing date are retained but are NOT counted in 7/30/90 windows.
- Future-dated rows are not counted in 7/30/90 windows.
- No published-count, sales, revenue or royalty value is fabricated when source data is absent.

HARDENED LINKAGE RULES
- Performance counts ONLY rows whose product id matches a lineage-verified Forge publication receipt.
- Unmatched rows are retained as unlinked evidence but excluded from 7/30/90 metrics.
- Importing a later publication receipt re-runs linkage against existing rows.
