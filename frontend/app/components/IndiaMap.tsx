"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

type StateSummary = { state:string; candidates:number; constituencies:number; seats:number; votes:number };
type Position = [number, number];
type GeoFeature = { type:"Feature"; properties:{ NAME_1?:string }; geometry:{ type:"Polygon"; coordinates:Position[][] } | { type:"MultiPolygon"; coordinates:Position[][][] } };
type GeoJson = { type:"FeatureCollection"; features:GeoFeature[] };

const API = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
const VIEW = { width: 760, height: 820, pad: 44 };
// Context-only outline west of Jammu and Kashmir. It is deliberately not
// joined to the seat data or colored as an Indian constituency.
const POK_CONTEXT: Position[] = [[73.2,35.8],[74.5,36.6],[76.2,36.4],[77.2,35.4],[76.9,34.3],[75.6,33.7],[74.1,34.1],[73.2,35.0]];

function stateKey(value:string) {
  return value.toLowerCase().replace(/&/g, "and").replace(/[^a-z0-9]/g, "").replace(/islands?$/, "").replace(/^nctof/, "").replace(/^orissa$/, "odisha").replace(/^uttaranchal$/, "uttarakhand");
}

function rings(geometry: GeoFeature["geometry"]): Position[][] {
  return geometry.type === "Polygon" ? geometry.coordinates : (geometry.coordinates as Position[][][]).flat();
}

function projectMap(geo: GeoJson) {
  const points = geo.features.flatMap(feature => rings(feature.geometry).flat());
  // Do not spread every coordinate into Math.min/Math.max: the detailed
  // GeoJSON contains enough points to exceed V8's argument-count limit.
  const bounds = points.reduce((result, [lon, lat]) => ({
    minLon: Math.min(result.minLon, lon),
    maxLon: Math.max(result.maxLon, lon),
    minLat: Math.min(result.minLat, lat),
    maxLat: Math.max(result.maxLat, lat),
  }), { minLon: Infinity, maxLon: -Infinity, minLat: Infinity, maxLat: -Infinity });
  const { minLon, maxLon, minLat, maxLat } = bounds;
  const scale = Math.min((VIEW.width - VIEW.pad * 2) / (maxLon - minLon), (VIEW.height - VIEW.pad * 2) / (maxLat - minLat));
  const offsetX = (VIEW.width - (maxLon - minLon) * scale) / 2;
  const offsetY = (VIEW.height - (maxLat - minLat) * scale) / 2;
  const projectPoint = ([lon, lat]: Position) => [offsetX + (lon - minLon) * scale, VIEW.height - offsetY - (lat - minLat) * scale] as const;
  const pathForPoints = (points:Position[]) => points.map(([lon, lat], index) => `${index ? "L" : "M"}${(offsetX + (lon - minLon) * scale).toFixed(2)},${(VIEW.height - offsetY - (lat - minLat) * scale).toFixed(2)}`).join(" ") + " Z";
  const pathFor = (feature:GeoFeature) => rings(feature.geometry).map(pathForPoints).join(" ");
  const labelPoint = (feature:GeoFeature) => {
    const featurePoints = rings(feature.geometry).flat();
    const featureBounds = featurePoints.reduce((result, [lon, lat]) => ({
      minLon: Math.min(result.minLon, lon), maxLon: Math.max(result.maxLon, lon),
      minLat: Math.min(result.minLat, lat), maxLat: Math.max(result.maxLat, lat),
    }), { minLon: Infinity, maxLon: -Infinity, minLat: Infinity, maxLat: -Infinity });
    return projectPoint([(featureBounds.minLon + featureBounds.maxLon) / 2, (featureBounds.minLat + featureBounds.maxLat) / 2]);
  };
  return { pathFor, pathForPoints, labelPoint, projectPoint };
}

function mapLabel(name:string) {
  return name.replace("Andaman and Nicobar", "Andaman & Nicobar").replace("Orissa", "Odisha").replace("Uttaranchal", "Uttarakhand");
}

function tone(seats:number, maximum:number) {
  const alpha = Math.max(.28, Math.min(.92, .28 + (seats / Math.max(maximum, 1)) * .64));
  return `rgba(98, 201, 149, ${alpha})`;
}

export default function IndiaMap({ year, states }: { year:number; states:StateSummary[] }) {
  const [geo, setGeo] = useState<GeoJson|null>(null);
  const [selected, setSelected] = useState<StateSummary|null>(null);
  const [hovered, setHovered] = useState<string|null>(null);
  const [winners, setWinners] = useState<{id:string; winner:string; constituency:string; party?:string; votes?:number|null; candidate_result_id?:string|null}[]>([]);
  const summaryByName = useMemo(() => new Map(states.map(item => [stateKey(item.state), item])), [states]);
  const projection = useMemo(() => geo ? projectMap(geo) : null, [geo]);
  const active = selected || (hovered ? summaryByName.get(stateKey(hovered)) : null) || states[0] || null;
  const maximum = Math.max(...states.map(item => item.seats), 1);

  useEffect(() => { fetch("/india-states.geojson").then(response => response.json()).then(setGeo).catch(() => setGeo(null)); }, []);
  useEffect(() => {
    if (!active) return;
    fetch(`${API}/api/winners?year=${year}&state=${encodeURIComponent(active.state)}&limit=100`).then(response => response.json()).then(data => setWinners(data.items || [])).catch(() => setWinners([]));
  }, [active?.state, year]);

  return <section className="atlas" aria-label={`Interactive India state map for ${year}`}>
    <div className="section-head atlas-head">
      <div><div className="eyebrow">Election map · {year}</div><h2>Every state, on the record.</h2><p className="section-copy">Hover for a preview, click to lock a state, then open its winners. Color intensity is official seats, not a visual estimate.</p></div>
      <div className="map-legend"><span className="legend-swatch"/> <span>Fewer seats</span><span className="legend-swatch strong"/> <span>More seats</span></div>
    </div>
    <div className="atlas-body">
      <div className="map-canvas" role="group" aria-label="Map of Indian states and union territories">
        {projection && geo ? <svg viewBox={`0 0 ${VIEW.width} ${VIEW.height}`} className="india-map" role="img" aria-label={`India political map showing ${year} Lok Sabha seats`}>
          {geo.features.map(feature => {
            const name = feature.properties.NAME_1 || "Unknown";
            const item = summaryByName.get(stateKey(name));
            const isActive = active && item && stateKey(active.state) === stateKey(item.state);
            return <path key={name} d={projection.pathFor(feature)} className={`map-state ${isActive ? "active" : ""}`} style={{fill:item ? tone(item.seats, maximum) : "rgba(167,184,187,.14)"}} onMouseEnter={() => setHovered(name)} onMouseLeave={() => setHovered(null)} onClick={() => item && setSelected(item)} tabIndex={item ? 0 : -1} onFocus={() => setHovered(name)} onKeyDown={event => { if (event.key === "Enter" && item) setSelected(item); }} aria-label={`${name}: ${item?.seats || 0} seats`} />;
          })}
          <path d={projection.pathForPoints(POK_CONTEXT)} className="map-disputed" aria-label="PoK disputed region context" />
          {(() => { const [x, y] = projection.projectPoint([75.3, 35.1]); return <text className="map-disputed-label" x={x} y={y}>PoK · disputed</text>; })()}
          {geo.features.map(feature => {
            const name = feature.properties.NAME_1 || "Unknown";
            const [x, y] = projection.labelPoint(feature);
            const label = mapLabel(name);
            const size = label.length > 18 ? 6.2 : label.length > 12 ? 7 : 8;
            return <text key={`label-${name}`} className="map-label" x={x} y={y} fontSize={size}>{label}</text>;
          })}
        </svg> : <div className="map-loading">Loading state boundaries…</div>}
        <div className="map-annotation" aria-label="PoK is shown as a disputed-region annotation only"><strong>PoK · disputed region</strong><span>No Lok Sabha seat data</span></div>
        {active && <div className="map-tooltip"><div className="eyebrow">{hovered || "Selected state"}</div><strong>{active.state}</strong><span>{active.seats} seats · {active.constituencies} constituencies</span></div>}
      </div>
      <aside className="atlas-side">
        <div className="atlas-side-kicker">{active?.state || "State detail"}</div>
        <div className="atlas-seat-number">{active?.seats ?? "—"}<small> seats</small></div>
        <div className="state-meta">{active ? `${active.constituencies} constituencies · ${active.candidates.toLocaleString("en-IN")} candidates` : "Select a state"}</div>
        {active && <><div className="atlas-side-rule"/><div className="eyebrow">All winners · {year}</div><div className="state-winner-count">{winners.length} constituencies in {active.state}</div><div className="atlas-winner-list">{winners.map(winner => <Link href={`/winners/${winner.id}`} key={winner.id}><span>{winner.constituency}</span><strong>{winner.winner}</strong><small>{winner.party || "Party not recorded"}</small></Link>)}</div></>}
      </aside>
    </div>
    <div className="atlas-caption"><span>Official ECI winner counts drive the choropleth.</span><span>{states.length} states and UTs · boundaries from <a href="https://github.com/geohacker/india/blob/master/state/india_state.geojson" target="_blank" rel="noreferrer">geohacker/india ↗</a></span></div>
  </section>;
}
