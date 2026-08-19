import { BACKUP_INGREDIENTS, ETALON_INGREDIENTS } from "../ids";
import type { PlacesRequest, PlacesResponse, RadiusKm } from "../types/contract";

function sameSet(a: string[], b: readonly string[]): boolean {
  if (a.length !== b.length) return false;
  const left = [...a].sort();
  const right = [...b].sort();
  return left.every((id, i) => id === right[i]);
}

function totalForRadius(base: number, radiusKm: RadiusKm): number {
  if (radiusKm === 50) return Math.max(1, base - 5);
  if (radiusKm === 150) return base + 6;
  return base;
}

export async function fetchMockPlaces(req: PlacesRequest): Promise<PlacesResponse> {
  const path = sameSet(req.ingredients, ETALON_INGREDIENTS)
    ? "/mocks/places-etalon.json"
    : sameSet(req.ingredients, BACKUP_INGREDIENTS)
      ? "/mocks/places-backup.json"
      : null;

  if (!path) {
    return { total_found: 0, places: [] };
  }

  const res = await fetch(path);
  const body = (await res.json()) as PlacesResponse;
  return {
    total_found: totalForRadius(body.total_found, req.radius_km),
    places: body.places,
  };
}
