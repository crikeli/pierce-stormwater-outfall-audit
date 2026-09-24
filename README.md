# Pierce County Stormwater Outfall Audit (Demo)

Pierce County's Surface Water Management division maintains a countywide
inventory of stormwater drainage end points (outfalls and discharge
points), required by its NPDES Phase I Municipal Stormwater Permit. This
project audits that real, public inventory for completeness and internal
consistency, then uses the audited data to build a data-driven
inspection-priority score - which of the ~25,659 points should get
field-verified first.

**Live site: https://crikeli.github.io/pierce-stormwater-outfall-audit/**

## What this is - and isn't

An illustrative inspection-priority score built from real county data,
not an official Pierce County SWM work product. A high score means "verify
this first," not "this is a confirmed violation." Risk weights are
transparent and documented, not expert- or agency-calibrated.

**Finding:** 1,317 of 25,659 points (5.1%) are still flagged
`NPDES_PossibleOF`/`NPDES_PossibleDP`/`Unknown` - never confirmed as an
actual outfall vs. discharge point. Of the top 100 highest-priority points
by risk score, 100% are unconfirmed - a real, emergent result of the
scoring (the formula never looks at rank within the unconfirmed group),
not something built in by construction.

## Real data problems hit along the way

**`DrainsTo` and `GPSDate` are functionally unused fields.** Both exist
in the county's schema (and would enable real flow-path tracing and
field-verification tracking) but are populated for 2 of 25,659 and 2 of
25,659 records respectively - not a handful of stragglers, the fields
just aren't used in practice.

**`EditedOn` timestamps are a bulk-migration artifact, not a field-
verification signal.** Nearly the entire inventory (std of 0.6 years
across 25,658 records) was edited within the same 8-9 month window, ~8
years ago - reported honestly as a limited signal in the risk score
(weighted only 10%), not treated as if it tracked real inspection
recency.

**A duplicate-record bug in the water quality data, caught before it
biased anything.** The water quality monitoring layer looked like 146
real stations at first pass; it's actually 85 unique locations with up to
two rows each (different water-year reporting periods). Deduplicating by
station *name* still left two genuine duplicates - the same physical
station recorded under inconsistent spellings (`CanyonFallsCreek` vs
`CanyonfallsCreek`, `25MileCreek` vs `Twenty-fiveMileCreek`) at identical
coordinates. Fixed by deduplicating on the coordinate itself, the true
uniqueness key, not the name field - a name-based dedup would have
double-weighted those two locations in the nearest-station spatial join.

**A CRS bug during site-export, caught by an unexpected coordinate range.**
An early export script read a stale intermediate file that was still in
UTM meters and treated it as WGS84 lon/lat for the web map. Caught because
the resulting "coordinates" were four-to-seven-digit numbers, not
plausible lon/lat values - fixed by re-exporting from the notebook's own
correctly-reprojected output instead.

## The priority score

Each outfall gets a 0-100 score combining four percentile-ranked, real
factors: unconfirmed status (30%), the Water Quality Index of the nearest
real monitoring station (30%, lower WQI = higher risk), distance to
commercial/industrial zoning (25%, closer = higher risk), and time since
last edited (10%, weighted low given the bulk-migration caveat above),
plus a small tiebreaker for still-unresolved (`TBD`) ownership records
(5%).

## The web map stays light on purpose

The full inventory (25,659 points, ~7.7MB) only loads if a visitor
explicitly switches it on. By default the page loads the top 500
priority points (~150KB), water quality stations (~16KB), and a
simplified watershed boundary (~540KB) - well under 1MB, same
lazy-loading pattern used throughout this portfolio.

## Repo layout

```
notebooks/
  outfall_audit_and_priority.ipynb   # the full, executed analysis
data/
  build_static_site.py    # renders docs/index.html from the notebook's outputs
docs/
  index.html                # the deployed static site
  outfalls_priority.geojson, outfalls_all.geojson, watersheds.geojson, water_quality_sites.geojson
environment.yml
```

Raw fetches from Pierce County's GIS services (`data/*.geojson`) are
produced locally but git-ignored - the notebook regenerates them from
source on request.

## Setup

```bash
conda env create -f environment.yml
conda activate pierce-stormwater-outfall-audit
```

```bash
jupyter nbconvert --to notebook --execute --inplace notebooks/outfall_audit_and_priority.ipynb
python data/build_static_site.py
```

## Stack

geopandas, requests (Pierce County's ArcGIS REST services, paginated) -
Leaflet for the deployed static site, Esri World Imagery for basemap
context.
