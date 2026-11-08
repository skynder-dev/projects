# Demand → official facts → existing concept trial

No new dependencies, paid APIs or models. `gov_demand.py` produces `demand.json`
from analytics.usa.gov; demand ranks attention, not eligibility or availability.

From the repository root:

```powershell
python -I social/trial/demand_pick.py demand.json social/results/demand --per-channel 3
```

The picker sorts `views_30d` descending, takes up to three readable, unused
USA.gov/govpage pages per channel, and tries lower-ranked pages after a refusal.
`picks.json` includes `url`, `channel`, `views`, relative `bundle` and refusal
reasons. Each bundle retains the HTML snapshot, record, source-bound claims,
complete-unit selection and concept inputs. No model is called. Pass any selected
bundle directly to the existing trial (the trial itself calls your local model):

```powershell
python -I social/trial/concept_trial.py social social/results/trial --bundle social/results/demand/bundles/BUNDLE_ID
```

The pick's channel travels in the record, trial audience and phone card; title
heuristics are only a fallback for older bundles. `social/demand_used.json` is an
array of previously used URL strings. Selection does **not** mark a page used;
record a URL there after actual use. Duplicate URLs (including USA.gov's host
alias and a trailing slash) are skipped. Existing output directories can contain
older bundles; only entries in the newly written `picks.json` are current picks.

For a single source, run from `social`:

```powershell
python -m socialreel source --source govpage --url https://www.irs.gov/credits-deductions --out results/irs
```

The configured govpage allowlist is limited to `www.irs.gov`, `www.ssa.gov`,
`www.sba.gov`, `www.va.gov`, `www.hud.gov`, `www.fema.gov`, `www.fns.usda.gov`,
`www.medicare.gov`. HTTPS only, no credentials, query strings or fragments;
redirects must obey the same restrictions before following. Config may narrow
these hosts, not extend them. No crawl or linked-page fetches.

Only a single main/role=main with an H1 is read. Navigation, header, footer,
breadcrumbs, related blocks and search forms are excluded. Conditions in normal
content/accordions remain intact. Forms/login/payment/tools/calculators,
JS-dependent shells, invalid UTF-8, and main text below 250 characters or 45 words
are refused. Parsing is conservative and HTML formats are **not checked live**;
some legitimate pages will be skipped. Quotes are decoded HTML text_content with
structural locators, excerpt SHA-256 and an exact raw-snapshot SHA-256. No benefit
amount, deadline or personal eligibility is inferred. Core limits are unchanged;
if whole mandatory facts do not fit, the bundle is refused rather than clipped.

Tests use synthetic HTML only and forbid network. `--fixture` on `source` can
replay saved HTML offline. A failed new intake creates no record; snapshots of a
refused response may remain for inspection. Use a fresh output directory for
single-source attempts so an older bundle cannot be mistaken for a new result.
