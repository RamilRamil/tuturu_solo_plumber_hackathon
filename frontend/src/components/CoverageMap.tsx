import { useEffect, useState } from "react";
import { fetchCoverage } from "../api/client";
import type { ApiMode, CoveragePayload, CoverageRegion } from "../types/contract";

type Props = {
  mode: ApiMode;
  emptyPlaces: boolean;
  hasIngredients: boolean;
};

function regionName(region: CoverageRegion): string {
  return region.label || region.slug || "";
}

function splitFromRegions(regions: CoverageRegion[]): {
  loaded: CoverageRegion[];
  failed: CoverageRegion[];
  holes: CoverageRegion[];
} {
  return {
    loaded: regions.filter((region) => region.status === "loaded"),
    failed: regions.filter((region) => region.status === "failed"),
    holes: regions.filter((region) => region.status === "not_in_snapshot"),
  };
}

function splitFromLabels(data: CoveragePayload): {
  loaded: string[];
  holes: string[];
} {
  const loadedSet = new Set(data.loaded);
  const overlap = data.loaded.some((name) => data.admin_level_4.includes(name));
  const holes = overlap
    ? data.admin_level_4.filter((name) => !loadedSet.has(name))
    : [];
  return { loaded: data.loaded, holes };
}

export function CoverageMap({ mode, emptyPlaces, hasIngredients }: Props) {
  const [data, setData] = useState<CoveragePayload | null>(null);

  useEffect(() => {
    let cancelled = false;
    setData(null);
    fetchCoverage(mode).then((payload) => {
      if (!cancelled) setData(payload);
    });
    return () => {
      cancelled = true;
    };
  }, [mode]);

  if (!data) {
    return (
      <section className="coverage-panel">
        <h2>Покрытие данных</h2>
        <p className="mute">загрузка покрытия…</p>
      </section>
    );
  }

  const fromRegions = data.regions.length > 0 ? splitFromRegions(data.regions) : null;
  const fromLabels = fromRegions ? null : splitFromLabels(data);
  const loadedCount = fromRegions ? fromRegions.loaded.length : fromLabels?.loaded.length ?? 0;
  const hasFailed = Boolean(fromRegions && fromRegions.failed.length > 0);
  const hasHoles = fromRegions
    ? fromRegions.holes.length > 0
    : Boolean(fromLabels && fromLabels.holes.length > 0);

  return (
    <section className="coverage-panel">
      <h2>Покрытие данных</h2>
      <p className="coverage-count">
        данные загружены по {loadedCount}{" "}
        {loadedCount === 1 ? "области" : "областям"}
      </p>
      <div className="coverage-legend">
        <span className="swatch loaded">залито</span>
        {hasFailed ? <span className="swatch failed">сбой</span> : null}
        {hasHoles ? <span className="swatch hole">дыра ингеста</span> : null}
      </div>
      <ul className="coverage-list">
        {fromRegions
          ? fromRegions.loaded.map((region) => (
              <li key={`loaded-${region.slug || region.label}`} className="cov-item loaded">
                {regionName(region)}
              </li>
            ))
          : fromLabels?.loaded.map((name) => (
              <li key={`loaded-${name}`} className="cov-item loaded">
                {name}
              </li>
            ))}
        {fromRegions
          ? fromRegions.failed.map((region) => (
              <li key={`failed-${region.slug || region.label}`} className="cov-item failed">
                {regionName(region)}
              </li>
            ))
          : null}
        {fromRegions
          ? fromRegions.holes.map((region) => (
              <li key={`hole-${region.slug || region.label}`} className="cov-item hole">
                {regionName(region)}
              </li>
            ))
          : fromLabels?.holes.map((name) => (
              <li key={`hole-${name}`} className="cov-item hole">
                {name}
              </li>
            ))}
      </ul>
      {emptyPlaces && hasIngredients ? (
        <p className="ingest-hole">
          Пустая выдача вне залитых областей - дыра в данных, не «таких мест нет».
        </p>
      ) : null}
      {data.source === "static-fallback" ? (
        <p className="coverage-note">снимок со статики: /api/coverage недоступен</p>
      ) : null}
      {data.note ? <p className="coverage-note">{data.note}</p> : null}
      {data.at ? <p className="coverage-note">снимок: {data.at}</p> : null}
    </section>
  );
}
