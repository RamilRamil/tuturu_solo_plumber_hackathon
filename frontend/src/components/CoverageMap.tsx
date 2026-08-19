import { useEffect, useState } from "react";
import { fetchCoverage } from "../api/client";
import type { CoveragePayload, CoverageRegion } from "../types/contract";

type Props = {
  emptyPlaces: boolean;
  hasIngredients: boolean;
  onOffSubjects: (subjects: string[]) => void;
};

const REGION_NAME_RU: Record<string, string> = {
  moscow: "Москва",
  Moscow: "Москва",
  moscow_oblast: "Московская область",
  "Moscow oblast": "Московская область",
  yaroslavl_oblast: "Ярославская область",
  "Yaroslavl oblast": "Ярославская область",
  vladimir_oblast: "Владимирская область",
  "Vladimir oblast": "Владимирская область",
  tver_oblast: "Тверская область",
  "Tver oblast": "Тверская область",
  ryazan_oblast: "Рязанская область",
  "Ryazan oblast": "Рязанская область",
  tula_oblast: "Тульская область",
  "Tula oblast": "Тульская область",
  kaluga_oblast: "Калужская область",
  "Kaluga oblast": "Калужская область",
  ivanovo_oblast: "Ивановская область",
  "Ivanovo oblast": "Ивановская область",
  kostroma_oblast: "Костромская область",
  "Kostroma oblast": "Костромская область",
  belgorod_oblast: "Белгородская область",
  "Belgorod oblast": "Белгородская область",
  bryansk_oblast: "Брянская область",
  "Bryansk oblast": "Брянская область",
  voronezh_oblast: "Воронежская область",
  "Voronezh oblast": "Воронежская область",
  kursk_oblast: "Курская область",
  "Kursk oblast": "Курская область",
  lipetsk_oblast: "Липецкая область",
  "Lipetsk oblast": "Липецкая область",
  oryol_oblast: "Орловская область",
  "Oryol oblast": "Орловская область",
  smolensk_oblast: "Смоленская область",
  "Smolensk oblast": "Смоленская область",
  tambov_oblast: "Тамбовская область",
  "Tambov oblast": "Тамбовская область",
};

function ruName(slug: string | undefined, label: string): string {
  if (slug && REGION_NAME_RU[slug]) return REGION_NAME_RU[slug];
  if (REGION_NAME_RU[label]) return REGION_NAME_RU[label];
  return label || slug || "";
}

function regionKey(region: CoverageRegion): string {
  return region.slug || region.label;
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

export function CoverageMap({ emptyPlaces, hasIngredients, onOffSubjects }: Props) {
  const [data, setData] = useState<CoveragePayload | null>(null);
  const [offKeys, setOffKeys] = useState<string[]>([]);

  useEffect(() => {
    let cancelled = false;
    setData(null);
    fetchCoverage().then((payload) => {
      if (!cancelled) {
        setData(payload);
        setOffKeys([]);
        onOffSubjects([]);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [onOffSubjects]);

  const fromRegions = data && data.regions.length > 0 ? splitFromRegions(data.regions) : null;
  const fromLabels = data && !fromRegions ? splitFromLabels(data) : null;
  const loadedKeys = fromRegions
    ? fromRegions.loaded.map(regionKey)
    : fromLabels?.loaded ?? [];

  const subjectsForKeys = (keys: string[]): string[] =>
    keys
      .map((key) => {
        if (fromRegions) {
          const region = fromRegions.loaded.find((item) => regionKey(item) === key);
          if (!region) return "";
          return ruName(region.slug, region.label);
        }
        return ruName(undefined, key);
      })
      .filter(Boolean);

  const applyOffKeys = (next: string[]) => {
    setOffKeys(next);
    onOffSubjects(subjectsForKeys(next));
  };

  const toggleLoaded = (key: string) => {
    const next = offKeys.includes(key) ? offKeys.filter((item) => item !== key) : [...offKeys, key];
    applyOffKeys(next);
  };

  const turnAllOff = () => {
    applyOffKeys([...loadedKeys]);
  };

  const turnAllOn = () => {
    applyOffKeys([]);
  };

  if (!data) {
    return (
      <section className="coverage-panel">
        <h2>Покрытие данных</h2>
        <p className="mute">загрузка покрытия…</p>
      </section>
    );
  }

  const loadedCount = loadedKeys.length;
  const onCount = loadedKeys.filter((key) => !offKeys.includes(key)).length;
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
        {loadedCount > 0 ? ` · включено ${onCount}` : ""}
      </p>
      {loadedCount > 0 ? (
        <div className="coverage-bulk">
          <button
            type="button"
            className="text-btn"
            disabled={onCount === 0}
            onClick={turnAllOff}
          >
            выключить все
          </button>
          <button
            type="button"
            className="text-btn"
            disabled={offKeys.length === 0}
            onClick={turnAllOn}
          >
            включить все
          </button>
        </div>
      ) : null}
      <div className="coverage-legend">
        <span className="swatch loaded">залито</span>
        <span className="swatch off">выкл</span>
        {hasFailed ? <span className="swatch failed">сбой</span> : null}
        {hasHoles ? <span className="swatch hole">дыра ингеста</span> : null}
      </div>
      <ul className="coverage-list">
        {fromRegions
          ? fromRegions.loaded.map((region) => {
              const key = regionKey(region);
              const off = offKeys.includes(key);
              return (
                <li key={`loaded-${key}`} className={off ? "cov-item loaded off" : "cov-item loaded"}>
                  <button type="button" className="cov-item-btn" onClick={() => toggleLoaded(key)}>
                    {ruName(region.slug, region.label)}
                  </button>
                </li>
              );
            })
          : fromLabels?.loaded.map((name) => {
              const off = offKeys.includes(name);
              return (
                <li key={`loaded-${name}`} className={off ? "cov-item loaded off" : "cov-item loaded"}>
                  <button type="button" className="cov-item-btn" onClick={() => toggleLoaded(name)}>
                    {ruName(undefined, name)}
                  </button>
                </li>
              );
            })}
        {fromRegions
          ? fromRegions.failed.map((region) => (
              <li key={`failed-${region.slug || region.label}`} className="cov-item failed">
                {ruName(region.slug, region.label)}
              </li>
            ))
          : null}
        {fromRegions
          ? fromRegions.holes.map((region) => (
              <li key={`hole-${region.slug || region.label}`} className="cov-item hole">
                {ruName(region.slug, region.label)}
              </li>
            ))
          : fromLabels?.holes.map((name) => (
              <li key={`hole-${name}`} className="cov-item hole">
                {ruName(undefined, name)}
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
