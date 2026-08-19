import { useEffect, useState } from "react";
import type { CoveragePayload } from "../types/contract";

type Props = {
  emptyPlaces: boolean;
  hasIngredients: boolean;
};

const FALLBACK: CoveragePayload = {
  loaded: ["Ярославская область"],
  admin_level_4: [
    "Владимирская область",
    "Вологодская область",
    "Ивановская область",
    "Костромская область",
    "Московская область",
    "Тверская область",
    "Ярославская область",
  ],
  at: "2026-08-19T13:44:53Z",
  note: "wave1 D3 uses Yaroslavl oblast extract (G7); not russia-latest",
  poi_count: 2084,
};

async function loadCoverage(): Promise<CoveragePayload> {
  const paths = ["/coverage.json", "/mocks/coverage.json"];
  for (const path of paths) {
    try {
      const res = await fetch(path);
      if (!res.ok) continue;
      const body = (await res.json()) as Partial<CoveragePayload> & {
        regions_loaded?: string[];
      };
      const loaded = body.loaded ?? body.regions_loaded ?? [];
      const admin = body.admin_level_4 ?? [];
      if (loaded.length === 0 && admin.length === 0) continue;
      return {
        loaded,
        admin_level_4: admin,
        at: body.at ?? null,
        note: body.note ?? null,
        poi_count: body.poi_count,
      };
    } catch {
      continue;
    }
  }
  return FALLBACK;
}

function isLoadedName(name: string, loaded: string[]): boolean {
  const n = name.toLowerCase();
  return loaded.some((item) => {
    const x = item.toLowerCase();
    if (n === x) return true;
    if (n.includes("ярослав") && (x.includes("ярослав") || x.includes("yaroslav"))) {
      return true;
    }
    if (x.includes("ярослав") && n.includes("yaroslav")) return true;
    return n.includes(x) || x.includes(n);
  });
}

export function CoverageMap({ emptyPlaces, hasIngredients }: Props) {
  const [data, setData] = useState<CoveragePayload | null>(null);

  useEffect(() => {
    let cancelled = false;
    loadCoverage().then((payload) => {
      if (!cancelled) setData(payload);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!data) {
    return (
      <section className="coverage-panel">
        <h2>Покрытие данных</h2>
        <p className="mute">загрузка coverage.json…</p>
      </section>
    );
  }

  const holes = data.admin_level_4.filter((name) => !isLoadedName(name, data.loaded));
  const loadedCount = data.loaded.length;

  return (
    <section className="coverage-panel">
      <h2>Покрытие данных</h2>
      <p className="coverage-count">
        данные загружены по {loadedCount}{" "}
        {loadedCount === 1 ? "области" : "областям"}
      </p>
      <div className="coverage-legend">
        <span className="swatch loaded">залито</span>
        <span className="swatch hole">дыра ингеста</span>
      </div>
      <ul className="coverage-list">
        {data.loaded.map((name) => (
          <li key={`loaded-${name}`} className="cov-item loaded">
            {name}
          </li>
        ))}
        {holes.map((name) => (
          <li key={`hole-${name}`} className="cov-item hole">
            {name}
          </li>
        ))}
      </ul>
      {emptyPlaces && hasIngredients ? (
        <p className="ingest-hole">
          Пустая фаза 1 вне залитых областей — дыра ингеста, не «таких мест нет».
        </p>
      ) : null}
      {data.note ? <p className="coverage-note">{data.note}</p> : null}
      {data.at ? <p className="coverage-note">снимок: {data.at}</p> : null}
    </section>
  );
}
