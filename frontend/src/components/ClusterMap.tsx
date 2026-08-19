import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { INGREDIENT_NAME_RU } from "../catalog/ingredients";
import type { Place } from "../types/contract";

type Props = {
  place: Place | null;
};

const STYLE = "https://tiles.openfreemap.org/styles/liberty";
const FIT_PADDING = 56;
const FIT_MAX_ZOOM = 11;
const SINGLE_ZOOM = 10;

function isNamedPoi(name: unknown): boolean {
  return typeof name === "string" && name.trim().length > 0;
}

function poiDisplayName(name: unknown): string {
  return typeof name === "string" ? name.trim() : "";
}

function hoursLabel(status: string, openingHours: string | null): string {
  if (!openingHours) return "";
  if (status === "open") return "открыт";
  if (status === "closed") return "закрыт";
  return "";
}

function hubExtra(probeStatus: string): string {
  if (probeStatus === "not_sellable") return "своим ходом";
  if (probeStatus === "misresolved") return "город неверен";
  return "";
}

function isFinitePoint(lon: number, lat: number): boolean {
  return Number.isFinite(lon) && Number.isFinite(lat);
}

function clusterPoints(place: Place): [number, number][] {
  const points: [number, number][] = [];
  for (const hub of place.hubs) {
    if (isFinitePoint(hub.lon, hub.lat)) {
      points.push([hub.lon, hub.lat]);
    }
  }
  for (const obj of place.objects) {
    if (!isNamedPoi(obj.name)) continue;
    if (isFinitePoint(obj.lon, obj.lat)) {
      points.push([obj.lon, obj.lat]);
    }
  }
  return points;
}

function safePadding(map: maplibregl.Map): number {
  const box = map.getContainer();
  const span = Math.min(box.clientWidth, box.clientHeight);
  if (span < 32) return 0;
  const maxPad = Math.max(0, Math.floor(span / 4) - 8);
  return Math.min(FIT_PADDING, maxPad);
}

function flyToCenter(map: maplibregl.Map, place: Place, duration: number): void {
  if (!isFinitePoint(place.center.lon, place.center.lat)) return;
  map.flyTo({
    center: [place.center.lon, place.center.lat],
    zoom: SINGLE_ZOOM,
    essential: true,
    duration,
  });
}

function frameCluster(map: maplibregl.Map, place: Place | null, animate: boolean): void {
  if (!place) return;
  const points = clusterPoints(place);
  if (points.length === 0 && isFinitePoint(place.center.lon, place.center.lat)) {
    points.push([place.center.lon, place.center.lat]);
  }
  if (points.length === 0) return;
  const duration = animate ? 1000 : 0;
  try {
    map.stop();
    if (points.length === 1) {
      map.flyTo({
        center: points[0],
        zoom: SINGLE_ZOOM,
        essential: true,
        duration,
      });
      return;
    }
    const bounds = new maplibregl.LngLatBounds(points[0], points[0]);
    for (let i = 1; i < points.length; i += 1) {
      bounds.extend(points[i]);
    }
    map.fitBounds(bounds, {
      padding: safePadding(map),
      maxZoom: FIT_MAX_ZOOM,
      essential: true,
      duration,
    });
  } catch {
    flyToCenter(map, place, duration);
  }
}

export function ClusterMap({ place }: Props) {
  const rootRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const popupRef = useRef<maplibregl.Popup | null>(null);
  const placeRef = useRef(place);
  placeRef.current = place;

  useEffect(() => {
    if (!rootRef.current || mapRef.current) return;
    const container = rootRef.current;
    const map = new maplibregl.Map({
      container,
      style: STYLE,
      center: [39.63, 57.4],
      zoom: 6,
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    mapRef.current = map;

    const observer = new ResizeObserver(() => {
      map.resize();
    });
    observer.observe(container);

    return () => {
      observer.disconnect();
      popupRef.current?.remove();
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    let cancelled = false;
    let fly: (() => void) | undefined;

    const apply = () => {
      if (cancelled) return;
      const objectFeatures = place
        ? place.objects
            .filter((obj) => isNamedPoi(obj.name))
            .map((obj) => ({
              type: "Feature" as const,
              properties: {
                kind: "poi",
                name: poiDisplayName(obj.name),
                extra: INGREDIENT_NAME_RU[obj.ingredient] ?? obj.ingredient,
                hours: hoursLabel(obj.hours_status, obj.opening_hours),
              },
              geometry: { type: "Point" as const, coordinates: [obj.lon, obj.lat] },
            }))
        : [];
      const hubFeatures = place
        ? place.hubs.map((hub) => ({
            type: "Feature" as const,
            properties: {
              kind: "hub",
              name: hub.name,
              extra: hubExtra(hub.probe_status),
              hours: "",
            },
            geometry: { type: "Point" as const, coordinates: [hub.lon, hub.lat] },
          }))
        : [];

      const upsert = (
        id: string,
        features: typeof objectFeatures,
        color: string,
        radius: number,
      ) => {
        const geojson = { type: "FeatureCollection" as const, features };
        const source = map.getSource(id) as maplibregl.GeoJSONSource | undefined;
        if (source) {
          source.setData(geojson);
        } else {
          map.addSource(id, { type: "geojson", data: geojson });
          map.addLayer({
            id: `${id}-circle`,
            type: "circle",
            source: id,
            paint: {
              "circle-radius": radius,
              "circle-color": color,
              "circle-stroke-width": 2,
              "circle-stroke-color": "#fff8ee",
            },
          });
          map.on("click", `${id}-circle`, (event) => {
            const feature = event.features?.[0];
            if (!feature || feature.geometry.type !== "Point") return;
            const coords = feature.geometry.coordinates as [number, number];
            const name = String(feature.properties?.name ?? "");
            const extra = String(feature.properties?.extra ?? "");
            const hours = String(feature.properties?.hours ?? "");
            popupRef.current?.remove();
            popupRef.current = new maplibregl.Popup({ closeButton: true })
              .setLngLat(coords)
              .setHTML(
                `<strong>${name}</strong><div>${extra}</div>${hours ? `<div>${hours}</div>` : ""}`,
              )
              .addTo(map);
          });
        }
      };

      upsert("hubs", hubFeatures, "#1f4d3a", 10);
      upsert("objects", objectFeatures, "#e04e2a", 7);
      const clusterId = place?.cluster_id ?? "";
      fly = () => {
        if (cancelled) return;
        if ((placeRef.current?.cluster_id ?? "") !== clusterId) return;
        frameCluster(map, placeRef.current, true);
      };
      requestAnimationFrame(fly);
      map.once("idle", fly);
    };

    if (map.isStyleLoaded()) {
      apply();
    } else {
      map.once("load", apply);
    }
    return () => {
      cancelled = true;
      map.off("load", apply);
      if (fly) map.off("idle", fly);
    };
  }, [place]);

  return (
    <section className="map-wrap">
      <h2>{place ? place.title : "Карта"}</h2>
      <p className="map-caption">
        {place
          ? "Хабы и объекты выбранного кластера. Цен нет - это ещё не маршрут."
          : "Выберите карточку - на карте появятся точки кластера."}
      </p>
      <div ref={rootRef} className="map" />
    </section>
  );
}
