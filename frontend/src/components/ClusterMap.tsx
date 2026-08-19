import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { Place } from "../types/contract";

type Props = {
  place: Place | null;
};

const STYLE = "https://tiles.openfreemap.org/styles/liberty";

function hoursLabel(status: string, openingHours: string | null): string {
  if (!openingHours) return "unknown";
  if (status === "open" || status === "closed") return status;
  return "unknown";
}

export function ClusterMap({ place }: Props) {
  const rootRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const popupRef = useRef<maplibregl.Popup | null>(null);

  useEffect(() => {
    if (!rootRef.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: rootRef.current,
      style: STYLE,
      center: [39.63, 57.4],
      zoom: 6,
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    mapRef.current = map;
    return () => {
      popupRef.current?.remove();
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const apply = () => {
      const objectFeatures = place
        ? place.objects.map((obj) => ({
            type: "Feature" as const,
            properties: {
              kind: "poi",
              name: obj.name,
              extra: obj.ingredient,
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
              extra: hub.probe_status,
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
      if (place) {
        map.flyTo({ center: [place.center.lon, place.center.lat], zoom: 8.2, essential: true });
      }
    };

    if (map.isStyleLoaded()) apply();
    else map.once("load", apply);
    return () => {
      map.off("load", apply);
    };
  }, [place]);

  return (
    <section className="map-wrap">
      <h2>{place ? place.title : "Карта"}</h2>
      <p className="map-caption">
        {place
          ? "Хабы и объекты выбранного кластера. Цен нет — фаза 1."
          : "Выберите карточку — на карте появятся точки кластера."}
      </p>
      <div ref={rootRef} className="map" />
    </section>
  );
}
