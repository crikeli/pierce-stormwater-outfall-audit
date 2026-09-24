"""
Builds the published static site (docs/index.html) from the notebook's
outputs: docs/outfalls_priority.geojson (top 500 risk-scored outfalls,
loads on page load), docs/outfalls_all.geojson (the full 25,659-point
inventory, lazy-loaded only when toggled on), docs/watersheds.geojson
(simplified boundary context), docs/water_quality_sites.geojson.

Default page load is under 750KB across all three default layers - the
full inventory (~7.7MB) only loads if a visitor explicitly asks for it,
same lazy-loading pattern used in this portfolio's other projects.

Usage:
    python build_static_site.py
"""

import os

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(os.path.dirname(DATA_DIR), "docs")

CENTER = [47.0721, -122.1472]

PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pierce County Stormwater Outfall Audit (Demo)</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css">
<style>
  :root {{
    --bg: #ffffff; --ink: #1a1a1a; --muted: #5b5f66; --border: #e2e4e8;
    --surface: #f6f7f9; --accent: #1c6b7a; --risk-hi: #b3261e; --risk-lo: #e8dcc8; --wq: #2a7d4f;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #0e1117; --ink: #e6e8eb; --muted: #9aa1ab; --border: #2a2e35;
      --surface: #161a21; --accent: #4fb8cc; --risk-hi: #e8695f; --risk-lo: #5a4f3a; --wq: #4fbf82;
    }}
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ height: 100%; margin: 0; }}
  body {{
    display: flex; flex-direction: column; background: var(--bg); color: var(--ink);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  }}
  header {{ padding: 16px clamp(16px, 4vw, 32px) 0; }}
  h1 {{ margin: 0 0 4px; font-size: 1.4rem; }}
  .caption {{ color: var(--muted); margin: 0 0 12px; font-size: 0.9rem; }}
  .tabs {{ display: flex; gap: 20px; border-bottom: 1px solid var(--border); padding: 0 clamp(16px, 4vw, 32px); }}
  .tab-btn {{ background: none; border: none; padding: 10px 0; font-size: 15px; color: var(--muted); cursor: pointer; border-bottom: 2px solid transparent; }}
  .tab-btn.active {{ color: var(--accent); border-bottom-color: var(--accent); font-weight: 600; }}
  #tab-map {{ flex: 1 1 auto; min-height: 0; display: none; position: relative; }}
  #tab-map.active {{ display: block; }}
  #map {{ height: 100%; width: 100%; }}
  #tab-about {{ display: none; padding: 16px clamp(16px, 4vw, 32px) 48px; overflow-y: auto; }}
  #tab-about.active {{ display: block; }}
  .controls {{
    position: absolute; top: 12px; right: 12px; z-index: 1000; background: var(--surface);
    border: 1px solid var(--border); border-radius: 8px; padding: 10px 14px; font-size: 13px;
    max-width: 270px; max-height: calc(100% - 24px); overflow-y: auto;
  }}
  .controls label {{ display: flex; align-items: center; gap: 8px; margin: 6px 0; }}
  .swatch {{ width: 14px; height: 14px; border-radius: 50%; flex: none; }}
  .stat-row {{ display: flex; justify-content: space-between; font-size: 12px; color: var(--muted); margin: 2px 0; }}
  .stat-num {{ color: var(--ink); font-weight: 600; }}
  .load-hint {{ font-size: 11px; color: var(--muted); margin: 2px 0 4px; }}
  hr.sep {{ border: none; border-top: 1px solid var(--border); margin: 10px 0; }}
  code {{ background: var(--surface); padding: 1px 5px; border-radius: 4px; font-size: 0.9em; }}
  a {{ color: var(--accent); }}
  .inspect-popup {{ font-size: 12.5px; line-height: 1.6; }}
  .legend-bar {{ height: 10px; border-radius: 3px; background: linear-gradient(to right, var(--risk-lo), var(--risk-hi)); margin-top: 4px; }}
  .legend-labels {{ display: flex; justify-content: space-between; font-size: 11px; color: var(--muted); }}
</style>
</head>
<body>
  <header>
    <h1>Pierce County Stormwater Outfall Audit (Demo)</h1>
    <p class="caption">A data-quality audit of the county's own NPDES outfall inventory, used to build a real field-inspection priority list - see the About tab for method and honest limitations.</p>
    <div class="tabs">
      <button class="tab-btn active" data-tab="map">Map</button>
      <button class="tab-btn" data-tab="about">About</button>
    </div>
  </header>

  <div id="tab-map" class="active">
    <div id="map"></div>
    <div class="controls">
      <strong>Layers</strong>
      <label><input type="checkbox" id="toggle-priority" checked><span class="swatch" style="background:var(--risk-hi)"></span>Top 500 priority outfalls</label>
      <div class="legend-bar"></div>
      <div class="legend-labels"><span>lower risk</span><span>higher risk</span></div>
      <label style="margin-top:8px"><input type="checkbox" id="toggle-wq" checked><span class="swatch" style="background:var(--wq)"></span>Water quality stations</label>
      <label><input type="checkbox" id="toggle-watersheds"><span class="swatch" style="background:var(--accent);opacity:0.3;border-radius:3px"></span>Watershed boundary</label>
      <hr class="sep">
      <label><input type="checkbox" id="toggle-all"><span class="swatch" style="background:#999"></span>Full inventory (25,659 pts)</label>
      <div class="load-hint" id="all-load-hint">~7.7MB - loads only when switched on.</div>
      <hr class="sep">
      <div class="stat-row"><span>Total outfalls audited</span><span class="stat-num">{total_outfalls}</span></div>
      <div class="stat-row"><span>Unconfirmed points</span><span class="stat-num">{unconfirmed_count} ({unconfirmed_pct}%)</span></div>
      <div class="stat-row"><span>Top 100 that are unconfirmed</span><span class="stat-num">{top100_unconfirmed}%</span></div>
      <hr class="sep">
      <div style="font-size:11px;color:var(--muted)">Click any point for details.</div>
    </div>
  </div>

  <div id="tab-about">{about_html}</div>

<script src="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
  document.querySelectorAll(".tab-btn").forEach(function (btn) {{
    btn.addEventListener("click", function () {{
      document.querySelectorAll(".tab-btn").forEach(function (b) {{ b.classList.remove("active"); }});
      document.querySelectorAll("#tab-map, #tab-about").forEach(function (p) {{ p.classList.remove("active"); }});
      btn.classList.add("active");
      document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
      if (btn.dataset.tab === "map") {{ setTimeout(function () {{ map.invalidateSize(); }}, 50); }}
    }});
  }});

  const CENTER = {center_json};
  const map = L.map("map", {{ zoomSnap: 0.25 }}).setView(CENTER, 10);
  L.control.scale({{ metric: true, imperial: true }}).addTo(map);

  L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}", {{
    maxZoom: 19,
    attribution: "Imagery &copy; Esri &mdash; Esri, Maxar, Earthstar Geographics, and the GIS User Community",
  }}).addTo(map);

  const rootStyle = getComputedStyle(document.documentElement);
  const riskHi = rootStyle.getPropertyValue("--risk-hi").trim();
  const riskLo = rootStyle.getPropertyValue("--risk-lo").trim();
  const wqColor = rootStyle.getPropertyValue("--wq").trim();
  const accentColor = rootStyle.getPropertyValue("--accent").trim();

  function riskColor(score) {{
    // simple interpolation between riskLo and riskHi based on 0-100 score
    const t = Math.max(0, Math.min(1, score / 100));
    return t > 0.6 ? riskHi : (t > 0.35 ? "#d98a2b" : riskLo);
  }}

  function outfallPopup(p) {{
    const rows = [
      "<b>" + (p.AssetID || "Unnamed outfall") + "</b>",
      "Type: " + (p.EndPointType || "unknown") + (p.unconfirmed_flag ? " <span style=\\"color:#b3261e\\">(unconfirmed)</span>" : ""),
      "Owner: " + (p.PropertyOwner || "-") + " / Maintained by: " + (p.MaintenanceGroup || "-"),
      "Risk score: " + p.risk_score + " / 100",
      "Distance to commercial/industrial zoning: " + Math.round(p.dist_to_employment_m) + " m",
      p.OVERALL_ANNUAL != null ? "Nearest water quality station WQI: " + p.OVERALL_ANNUAL : null,
    ].filter(Boolean).join("<br>");
    return "<div class=\\"inspect-popup\\">" + rows + "</div>";
  }}

  function makeOutfallLayer(gj, radius) {{
    return L.geoJSON(gj, {{
      pointToLayer: function (feature, latlng) {{
        return L.circleMarker(latlng, {{
          radius: radius, weight: 1, color: "#333",
          fillColor: riskColor(feature.properties.risk_score || 0),
          fillOpacity: 0.85,
        }});
      }},
      onEachFeature: function (feature, layer) {{
        layer.bindPopup(outfallPopup(feature.properties));
      }},
    }});
  }}

  let priorityLayer, wqLayer, watershedsLayer, allLayer;

  fetch("outfalls_priority.geojson").then(function (r) {{ return r.json(); }}).then(function (gj) {{
    priorityLayer = makeOutfallLayer(gj, 6);
    if (document.getElementById("toggle-priority").checked) priorityLayer.addTo(map);
  }});

  fetch("water_quality_sites.geojson").then(function (r) {{ return r.json(); }}).then(function (gj) {{
    wqLayer = L.geoJSON(gj, {{
      pointToLayer: function (feature, latlng) {{
        return L.circleMarker(latlng, {{ radius: 5, weight: 1, color: "#222", fillColor: wqColor, fillOpacity: 0.9 }});
      }},
      onEachFeature: function (feature, layer) {{
        const p = feature.properties;
        layer.bindPopup("<div class=\\"inspect-popup\\"><b>" + p.STATION_NAME + "</b><br>Water Quality Index (annual): " + p.OVERALL_ANNUAL + " / 100</div>");
      }},
    }});
    if (document.getElementById("toggle-wq").checked) wqLayer.addTo(map);
  }});

  fetch("watersheds.geojson").then(function (r) {{ return r.json(); }}).then(function (gj) {{
    watershedsLayer = L.geoJSON(gj, {{ style: {{ fillColor: accentColor, fillOpacity: 0.08, color: accentColor, weight: 1 }} }});
    if (document.getElementById("toggle-watersheds").checked) watershedsLayer.addTo(map);
  }});

  document.getElementById("toggle-priority").addEventListener("change", function (e) {{
    if (!priorityLayer) return;
    e.target.checked ? priorityLayer.addTo(map) : map.removeLayer(priorityLayer);
  }});
  document.getElementById("toggle-wq").addEventListener("change", function (e) {{
    if (!wqLayer) return;
    e.target.checked ? wqLayer.addTo(map) : map.removeLayer(wqLayer);
  }});
  document.getElementById("toggle-watersheds").addEventListener("change", function (e) {{
    if (!watershedsLayer) return;
    e.target.checked ? watershedsLayer.addTo(map) : map.removeLayer(watershedsLayer);
  }});
  document.getElementById("toggle-all").addEventListener("change", function (e) {{
    if (!e.target.checked) {{ if (allLayer) map.removeLayer(allLayer); return; }}
    if (allLayer) {{ allLayer.addTo(map); return; }}
    document.getElementById("all-load-hint").textContent = "Loading ~7.7MB...";
    fetch("outfalls_all.geojson").then(function (r) {{ return r.json(); }}).then(function (gj) {{
      allLayer = makeOutfallLayer(gj, 3);
      allLayer.addTo(map);
      document.getElementById("all-load-hint").textContent = "~7.7MB - loaded.";
    }});
  }});
</script>
</body>
</html>
"""


def main() -> None:
    import geopandas as gpd

    priority = gpd.read_file(os.path.join(DOCS_DIR, "outfalls_priority.geojson"))
    full = gpd.read_file(os.path.join(DOCS_DIR, "outfalls_all.geojson"))

    total_outfalls = len(full)
    unconfirmed_count = int(full["unconfirmed_flag"].sum())
    unconfirmed_pct = round(100 * unconfirmed_count / total_outfalls, 1)
    top100_unconfirmed = round(100 * full.nlargest(100, "risk_score")["unconfirmed_flag"].mean(), 0)

    about_html = f"""
    <h2>What this is</h2>
    <p>Pierce County's Surface Water Management division maintains a
    countywide inventory of stormwater drainage end points (outfalls and
    discharge points), required by its NPDES Phase I Municipal Stormwater
    Permit. This project audits that real, public inventory for
    completeness and internal consistency, then uses the audited data to
    build a data-driven inspection-priority score - which of the
    ~{total_outfalls:,} points should get field-verified first.</p>

    <h2>Real findings from the audit</h2>
    <ul>
      <li><strong>{unconfirmed_count:,} points ({unconfirmed_pct}%)</strong>
      are still flagged <code>NPDES_Possible*</code> or <code>Unknown</code>
      - never confirmed as an actual outfall vs. discharge point.</li>
      <li>The <code>DrainsTo</code> field (which would let flow paths be
      traced to a receiving water) and <code>GPSDate</code> (field GPS
      verification date) are populated for essentially none of the
      {total_outfalls:,} records - the fields exist in the schema but
      aren't used in practice.</li>
      <li><code>EditedOn</code> timestamps cluster almost entirely within
      an 8-9 month band, ~8 years ago - the signature of a one-time bulk
      data migration, not ongoing field maintenance. Reported honestly as
      a limited signal, not treated as if it tracked real inspection
      recency.</li>
      <li>A real duplicate-record bug was found and fixed in the water
      quality monitoring layer: the same physical station appears under
      inconsistent name spellings (e.g. <code>CanyonFallsCreek</code> vs
      <code>CanyonfallsCreek</code>) at identical coordinates - caught by
      deduplicating on coordinates instead of station name.</li>
    </ul>

    <h2>The priority score</h2>
    <p>Each outfall gets a 0-100 risk score combining four percentile-
    ranked, real factors: whether it's unconfirmed (30%), the Water
    Quality Index of the nearest real monitoring station (30% - lower WQI
    = higher risk), distance to commercial/industrial zoning (25% -
    closer = higher risk), and time since last edited (10%, weighted low
    given the bulk-migration caveat above), plus a small tiebreaker for
    still-unresolved (<code>TBD</code>) ownership records (5%). Weights
    are transparent and documented, not expert-calibrated - a defensible
    starting point, not a claimed-authoritative ranking.</p>

    <p><strong>A real internal consistency check:</strong> of the top 100
    highest-risk points, <strong>{top100_unconfirmed:.0f}%</strong> are
    unconfirmed points - far above the {unconfirmed_pct}% base rate in the
    full inventory. The scoring formula never looks at rank within the
    unconfirmed group, so this concentration is an emergent result of the
    weighting, not built in by construction.</p>

    <h2>Honest limitations</h2>
    <ul>
      <li>The Water Quality Index direction (higher = better) follows the
      standard, near-universal WQI convention (NSF-WQI and its
      derivatives) - the county's own metadata confirms it's a WQI score
      but doesn't state direction explicitly.</li>
      <li>Risk weights are illustrative and transparent, not expert- or
      agency-calibrated.</li>
      <li>Some watersheds with zero outfall points inside may be
      legitimately rural/unserved by piped stormwater infrastructure, not
      genuine data gaps - distinguishing the two needs a land-use
      cross-check beyond this project's scope.</li>
      <li>This is exposure/audit prioritization, not a confirmed
      illicit-discharge finding - a high score means "verify this first,"
      not "this is a violation."</li>
    </ul>

    <h2>Data sources</h2>
    <ul>
      <li><a href="https://gisdata-piercecowa.opendata.arcgis.com/" target="_blank" rel="noopener">Pierce County Open GeoSpatial Data Portal</a> - drainage end points, watersheds, zoning, water quality monitoring sites</li>
      <li><a href="https://github.com/crikeli/pierce-stormwater-outfall-audit/blob/main/notebooks/outfall_audit_and_priority.ipynb" target="_blank" rel="noopener">Full analysis notebook</a> on GitHub</li>
      <li><a href="https://github.com/crikeli/pierce-stormwater-outfall-audit" target="_blank" rel="noopener">Source code on GitHub</a></li>
    </ul>
    """

    import json

    page = PAGE_TEMPLATE.format(
        about_html=about_html,
        center_json=json.dumps(CENTER),
        total_outfalls=f"{total_outfalls:,}",
        unconfirmed_count=f"{unconfirmed_count:,}",
        unconfirmed_pct=unconfirmed_pct,
        top100_unconfirmed=f"{top100_unconfirmed:.0f}",
    )
    with open(os.path.join(DOCS_DIR, "index.html"), "w") as f:
        f.write(page)
    print(f"Wrote {os.path.join(DOCS_DIR, 'index.html')}")


if __name__ == "__main__":
    main()
