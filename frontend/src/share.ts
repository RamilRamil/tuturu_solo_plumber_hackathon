import { DEFAULT_RADIUS, RADIUS_STEPS } from "./ids";
import type { BudgetScope, RadiusKm } from "./types/contract";

export type ShareState = {
  ingredients: string[];
  radius_km: RadiusKm;
  cluster_id: string | null;
  origin: string | null;
  days: number | null;
  month: string | null;
  adults: number | null;
  children_ages: string | null;
  budget_scope: BudgetScope | null;
};

function isRadius(value: number): value is RadiusKm {
  return (RADIUS_STEPS as readonly number[]).includes(value);
}

function isBudget(value: string): value is BudgetScope {
  return value === "transport" || value === "all";
}

function push(parts: string[], key: string, value: string): void {
  parts.push(`${key}=${encodeURIComponent(value)}`);
}

export function encodeShare(state: ShareState): string {
  const parts: string[] = [];
  if (state.ingredients.length > 0) {
    push(parts, "ingredients", state.ingredients.join(","));
  }
  push(parts, "radius_km", String(state.radius_km));
  if (state.cluster_id) {
    push(parts, "cluster_id", state.cluster_id);
  }
  if (state.origin) push(parts, "origin", state.origin);
  if (state.days !== null) push(parts, "days", String(state.days));
  if (state.month) push(parts, "month", state.month);
  if (state.adults !== null) push(parts, "adults", String(state.adults));
  if (state.children_ages) push(parts, "children_ages", state.children_ages);
  if (state.budget_scope) push(parts, "budget_scope", state.budget_scope);
  return parts.length ? `?${parts.join("&")}` : "";
}

export function parseShare(search: string): ShareState {
  const raw = search.startsWith("?") ? search.slice(1) : search;
  const params = new URLSearchParams(raw);
  const ingredients = (params.get("ingredients") ?? "")
    .split(",")
    .map((id) => id.trim())
    .filter(Boolean);
  const radiusNum = Number(params.get("radius_km") ?? DEFAULT_RADIUS);
  const radius_km = isRadius(radiusNum) ? radiusNum : DEFAULT_RADIUS;
  const daysNum = Number(params.get("days"));
  const adultsNum = Number(params.get("adults"));
  const budgetRaw = params.get("budget_scope") ?? "";
  return {
    ingredients,
    radius_km,
    cluster_id: params.get("cluster_id"),
    origin: params.get("origin"),
    days: Number.isFinite(daysNum) && daysNum >= 1 ? daysNum : null,
    month: params.get("month"),
    adults: Number.isFinite(adultsNum) && adultsNum >= 1 ? adultsNum : null,
    children_ages: params.get("children_ages"),
    budget_scope: isBudget(budgetRaw) ? budgetRaw : null,
  };
}

export function shareHref(state: ShareState): string {
  return `${window.location.pathname}${encodeShare(state)}${window.location.hash}`;
}
