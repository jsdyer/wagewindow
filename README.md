# Wage Window

[Open Wage Window](https://coolcode.ca/wagewindow/) searches the full ESDC Job Bank wage edition, compares occupations across Canadian regions, and puts a gross offer alongside published wage benchmarks.

<!-- coolcode:guide -->
Wage Window includes every occupation-region row in the ESDC Job Bank wage download, including unavailable estimates. Search by English/French occupation title or NOC code, compare any two regions, inspect low/median/high wages and their own reference periods, or compare a gross offer using your paid hours and weeks. Annual source wages remain annual; missing values stay missing. Optional private comparisons preserve the selected edition and assumptions, survive refreshes and export/import as JSON; current comparisons also export CSV. The official release is checked weekly; failed downloads retain the previous good edition with its original successful check date.
The raise calculator compares your old and current hourly-equivalent pay with all-items CPI for the exact selected province and months. Separate hours and weeks prevent a longer work week from masquerading as a raise.
<!-- /coolcode:guide -->

## Source and coverage

- [ESDC Job Bank wage data](https://open.canada.ca/data/en/dataset/adad580f-76b0-4502-bd05-20c125de9116), under the [Open Government Licence – Canada](https://open.canada.ca/en/open-government-licence-canada). Attribution: Employment and Social Development Canada / Job Bank. This independent tool is not an official government service.
- The newest annual CSV is discovered through public CKAN metadata. Only HTTPS resource URLs on `open.canada.ca` are selected; its observed official download redirect to `opencanada.blob.core.windows.net` is also allowed, with byte/row/time limits and required-column validation. No key is needed.
- The initial **2026** edition contains **44,376 rows: 516 occupations × 86 regions**, including Canada, provinces/territories and economic regions such as Halifax and Lower Mainland. Names/boundaries follow the dataset; city geography is not substituted for economic regions.
- All rows remain, including unpublished wages. Numeric blanks/NA remain `null`, not zero. No local estimate is silently replaced by a provincial/national one.
- `Annual_Wage_Flag_Salaire_annuel` determines annual versus hourly amounts. Conversions use the visitor's paid hours/week and weeks/year, excluding taxes, overtime, bonuses and benefits. No personal income percentile is inferred.
- `edition` is the annual release; row `reference_period` is the measurement period; `revision_date` is the publisher's revision; `checked_at` is our successful retrieval. Some annual occupations in the 2026 edition still use 2021 Census data. A new download is not a new measurement.
- The initial CSV has one out-of-order wage row (NOC 31101, PEI), whose median exceeds its high. Values are preserved and visibly flagged; derived offer comparison is withheld for that row. Future anomalies appear in `quality_warnings` and are never silently corrected.

The browser lazily loads one of ten NOC-prefix shards instead of the 18 MB original CSV. The normalized 2026 data totals approximately 2.75 MB. It retains every row key, low/median/high, annual flag, source, reference/revision dates, comments and benefits percentage. Unused average/quartile columns are not republished. Occupation/region/source/comment dictionaries are in the index.

## Privacy and saved comparisons

Offer, hours, queries and imported files stay in this browser. Public JSON is loaded from the project path. Optional Save writes to `coolcode:wagewindow:plans` in localStorage. Plans include their own estimates, reference periods, checked date, original source URL and assumptions, so later public updates never rewrite old plans. Refreshes preserve saves; private browsing, storage restrictions or clearing data may not. Export backups. Imports validate size/schema/numbers, accept earlier coverage and never fetch imported URLs. CSV export quotes cells and guards spreadsheet-formula prefixes. Shared hub metrics/report controls retain their existing behaviour.

## Expand or customize

1. Edit `web/config.json` for default NOC/regions, hours/week, weeks/year, saved-plan limit (up to 100) and stale-check days. Defaults do not cap coverage: all option counts derive from the source. Search accepts any published English/French title or NOC code.
2. Edit `config/sources.json` to adjust official metadata URL, download/timeout/row limits. Upstream column changes require parser/fixture review in `scripts/refresh.py`; new occupations or regions under the same schema require no UI code change.
3. Run `python3 scripts/refresh.py`. It selects the latest official annual CSV, validates the full download and stages all shards before publication. Failures preserve shards and `checked_at`, with separate `last_attempt_at`, `status: retained` and error class. Never use attempt time as proof of freshness. Explicit offline fixture options are `--fixture` and `--metadata-fixture`.
4. Run checks below, commit source/config/data to `main`, and inspect Pages plus live `/data/index.json`. Current public shards are deployed; old user exports remain readable without depending on current coverage. Catalogue/coverage changes follow the [CoolCode lifecycle](https://github.com/jsdyer/jsdyer.github.io/blob/main/docs/tool-lifecycle.md).

## Checks, schedule and operations

```sh
node --test tests/*.test.mjs
python3 -m unittest discover -s tests -v
python3 scripts/build.py
python3 -m pip install -r tests/browser-requirements.txt
CHROMIUM_PATH=/usr/bin/google-chrome python3 tests/browser_smoke.py
```

Builds are offline, publishing `web/` to ignored `dist/`. HTML, CSS, imports, index/config URLs share a content-derived version. Dynamic shard requests use the original CSV hash to align index/shard editions. Each shard also embeds that hash; an older open tab encountering a newer shard is asked to reload instead of mixing data dictionaries. Tests cover real source excerpts, annual/missing values, source anomalies, metadata selection, full-dataset counts, failure retention, offer math, persistence/import/export and mobile layout.

`.github/workflows/pages.yml` checks new editions at **08:43 UTC every Wednesday**, with `workflow_dispatch`. Push/PR builds use committed data. Scheduled/manual runs validate, commit data and deploy in the same workflow. `.github/workflows/schedule-guard.yml` renews the declared collector and itself. No API key, Worker endpoint or repository secret is needed.

Probe `/wagewindow/data/index.json`: `checked_at` successful freshness (warn after 16 days), `status`, `edition`, `row_count`, `occupation_count`, `region_count`, `published_median_count`, `annual_row_count`, `quality_warnings`. Check a listed shard such as `/wagewindow/data/2.json` returns JSON. Register the workflow/guard in the central watchdog and include this repo in its GitHub App installation when restricted to selected repositories.

## Raise and inflation comparison

Monthly all-items CPI comes from [Statistics Canada table 18-10-0004-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1810000401), not seasonally adjusted, 2002=100. Canada, all ten provinces and the three explicitly labelled territorial capital cities are available from 1990 where published. Capital-city values never stand in for a whole territory. The two chosen months must both have numeric values; missing data is not interpolated. CPI change is end/start−1; real hourly pay change is (new hourly/old hourly)/(end CPI/start CPI)−1. Each salary uses its own paid hours and weeks. This is a gross-pay purchasing-power comparison, not tax, investment or individual cost-of-living advice.

`config/cpi.json` defines exact source geographies and first month. Add another geography published in the same table, run `python scripts/refresh_cpi.py`, then test/build/publish as above. The weekly workflow refreshes CPI alongside wages. `web/data/cpi.json` has its own successful `checked_at`, geography-labelled values, published flags and vector IDs. Failed CPI retrieval/validation raises before replacing the old file and blocks the refresh deployment. Personal pay inputs are not saved or sent. Adapted from Statistics Canada under its [Open Licence](https://www.statcan.gc.ca/en/reference/licence).

## Ready-to-use example

[Registered Nurse Wages in Halifax and the Lower Mainland](https://coolcode.ca/wagewindow/nurse-wages-halifax-lower-mainland.html) opens this scenario in the same tool. See the published wage range for registered nurses and registered psychiatric nurses in Halifax and the Lower Mainland of BC. The comparison opens to NOC 31301. Enter your hours and offer to compare with the regional median.
