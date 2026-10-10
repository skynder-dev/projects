MERCH FORGE — LOCAL SALES CSV IMPORT

Purpose
- Populate local 7 / 30 / 90 day sales and royalty metrics without requiring the live backend.
- The import is local-only and does not claim marketplace synchronization.

Recognized columns (case, spaces and punctuation are ignored: "Units Sold" = "units_sold")
Date: date | purchase date | order date | sale date | transaction date | shipment date | period | period start | day
Units: units | units sold | net units | quantity | qty | items sold | purchased | sold
Royalty: royalty | royalties | net earnings | earnings | amount | any column starting with "royalt" (e.g. "Royalty (USD)")
Revenue (optional): revenue | sales revenue | gross sales | gross | any column starting with "revenue"
Product title (optional): title | product title | design title | name
Product id: asin | product asin | product id | listing id | sku | any column starting with "asin"

Formats
- Separator: comma or semicolon (detected from the header line).
- Amounts: 4.50 | 4,50 | $1,234.56 | 1.234,56 EUR | (0.35) for a negative amount.
- Dates: 2026-10-05 | 2026-10-05T10:00:00Z | 10/5/2026 (US month/day, as Amazon.com reports) | 5.10.2026 (day.month).
  Anything else is not guessed: the row is kept but not counted, and the status bar says how many rows had no date or no ASIN.

ПО-РУССКИ: колонки узнаются по смыслу (дата, ASIN, штуки, роялти); разделитель — запятая или точка с запятой;
суммы с запятой (4,50) понимаются; даты — 2026-10-05, 10/5/2026 (месяц/день, как в отчётах Amazon.com) или 5.10.2026.
Строки без даты или без ASIN не считаются, их число показывается после импорта.

Rules
- A file is de-duplicated by SHA-256; importing the same file twice does not duplicate rows.
- Rows with an unparseable/missing date are retained but are NOT counted in 7/30/90 windows.
- Future-dated rows are not counted in 7/30/90 windows.
- No published-count, sales, revenue or royalty value is fabricated when source data is absent.

HARDENED LINKAGE RULES
- Performance counts ONLY rows whose product id matches a lineage-verified Forge publication receipt.
- Unmatched rows are retained as unlinked evidence but excluded from 7/30/90 metrics.
- Importing a later publication receipt re-runs linkage against existing rows.
