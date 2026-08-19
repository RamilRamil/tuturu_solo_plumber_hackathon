import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { Place } from "../types/contract";

type Props = {
  place: Place | null;
};

const STYLE = "https://tiles.openfreemap.org/styles/liberty";

export function ClusterMap({ place }: Props) {
  const rootRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);

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
      map.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !place) return;

    const apply = () => {
      const features = place.objects.map((obj) => ({
        type: "Feature" as const,
        properties: { name: obj.name, ingredient: obj.ingredient },
        geometry: { type: "Point" as const, coordinates: [obj.lon, obj.lat] },
      }));
      const geojson = { type: "FeatureCollection" as const, features };
      const source = map.getSource("objects") as maplibregl.GeoJSONSource | undefined;
      if (source) {
        source.setData(geojson);
      } else {
        map.addSource("objects", { type: "geojson", data: geojson });
        map.addLayer({
          id: "objects-circle",
          type: "circle",
          source: "objects",
          paint: {
            "circle-radius": 7,
            "circle-color": "#c45c26",
            "circle-stroke-width": 2,
            "circle-stroke-color": "#f4efe4",
          },
        });
      }
      map.flyTo({ center: [place.center.lon, place.center.lat], zoom: 8, essential: true });
    };

    if (map.isStyleLoaded()) apply();
    else map.once("load", apply);
  }, [place]);

  return (
    <section className="map-wrap">
      <h2>Карта выбранного кластера</h2>
      <div ref={rootRef} className="map" />
    </section>
  );
}
