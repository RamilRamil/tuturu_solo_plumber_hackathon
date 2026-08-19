import { streamLivePrice } from "./price";
import type {
  CoveragePayload,
  CoverageRegion,
  CoverageRegionStatus,
  CoverageSource,
  PlacesRequest,
  PlacesResponse,
  PriceRequest,
  RadiusKm,
  SseEvent,
} from "../types/contract";

const STATIC_COVERAGE_PATHS = ["/coverage.json", "/mocks/coverage.json"];

const COVERAGE_FALLBACK: CoveragePayload = {
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
  regions: [],
  at: "2026-08-19T13:44:53Z",
  note: "wave1 D3 uses Yaroslavl oblast extract (G7); not russia-latest",
  poi_count: 2084,
  source: "static",
};

function asStringList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string");
}

function regionStatus(raw: unknown): CoverageRegionStatus | null {
  if (typeof raw !== "string") return null;
  if (raw === "loaded" || raw === "ok") return "loaded";
  if (raw === "failed") return "failed";
  if (
    raw === "not_in_snapshot" ||
    raw === "not-in-snapshot" ||
    raw === "not_loaded" ||
    raw === "not-loaded"
  ) {
    return "not_in_snapshot";
  }
  return null;
}

function parseRegions(raw: unknown, loadedLabels: string[]): CoverageRegion[] {
  if (!Array.isArray(raw)) return [];
  const regions: CoverageRegion[] = [];
  for (const item of raw) {
    if (!item || typeof item !== "object") continue;
    const rec = item as Record<string, unknown>;
    const label = typeof rec.label === "string" ? rec.label : "";
    const slug = typeof rec.slug === "string" ? rec.slug : undefined;
    if (!label && !slug) continue;
    const exactHit =
      (label && loadedLabels.includes(label)) ||
      (slug !== undefined && loadedLabels.includes(slug));
    const status = regionStatus(rec.status) ?? (exactHit ? "loaded" : "not_in_snapshot");
    const region: CoverageRegion = { label: label || slug || "", status };
    if (slug) region.slug = slug;
    regions.push(region);
  }
  return regions;
}

function normalizeCoverage(body: unknown, source: CoverageSource): CoveragePayload {
  const rec = body && typeof body === "object" ? (body as Record<string, unknown>) : {};
  const loadedDirect = asStringList(rec.loaded);
  const loaded = loadedDirect.length > 0 ? loadedDirect : asStringList(rec.regions_loaded);
  const admin_level_4 = asStringList(rec.admin_level_4);
  const regions = parseRegions(rec.regions, loaded);
  const loadedFromRegions = regions
    .filter((region) => region.status === "loaded")
    .map((region) => region.label);
  return {
    loaded: loaded.length > 0 ? loaded : loadedFromRegions,
    admin_level_4,
    regions,
    at: typeof rec.at === "string" ? rec.at : null,
    note: typeof rec.note === "string" ? rec.note : null,
    poi_count: typeof rec.poi_count === "number" ? rec.poi_count : undefined,
    source,
  };
}

async function fetchStaticCoverage(source: CoverageSource): Promise<CoveragePayload | null> {
  for (const path of STATIC_COVERAGE_PATHS) {
    try {
      const res = await fetch(path);
      if (!res.ok) continue;
      const body: unknown = await res.json();
      const parsed = normalizeCoverage(body, source);
      if (parsed.loaded.length === 0 && parsed.admin_level_4.length === 0 && parsed.regions.length === 0) {
        continue;
      }
      return parsed;
    } catch {
      continue;
    }
  }
  return null;
}

export async function fetchCoverage(): Promise<CoveragePayload> {
  try {
    const res = await fetch("/api/coverage");
    if (res.ok) {
      const body: unknown = await res.json();
      return normalizeCoverage(body, "api");
    }
  } catch {
    // live API failed; explicit static fallback below
  }
  const fallback = await fetchStaticCoverage("static-fallback");
  if (fallback) return fallback;
  return { ...COVERAGE_FALLBACK, source: "static-fallback" };
}

export async function fetchPlaces(req: PlacesRequest): Promise<PlacesResponse> {
  const res = await fetch("/api/places", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    throw new Error(`places failed: ${res.status}`);
  }
  return (await res.json()) as PlacesResponse;
}

export type ParseRequest = {
  text: string;
  radius_km?: RadiusKm;
};

export type ParseResponse = {
  ingredients: string[];
  radius_km: number;
  unmatched: string[];
};

const PARSE_TIMEOUT_MS = 6000;

export async function fetchParse(req: ParseRequest): Promise<ParseResponse> {
  const res = await fetch("/api/parse", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
    signal: AbortSignal.timeout(PARSE_TIMEOUT_MS),
  });
  if (!res.ok) {
    throw new Error(`parse failed: ${res.status}`);
  }
  return (await res.json()) as ParseResponse;
}

export async function streamPrice(
  req: PriceRequest,
  onEvent: (event: SseEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  await streamLivePrice(req, onEvent, signal);
}
