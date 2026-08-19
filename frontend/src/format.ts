import type { SseEvent } from "./types/contract";

export function formatKm(value: number): string {
  const rounded = Math.round(value * 10) / 10;
  if (!Number.isFinite(rounded)) return "0";
  if (Number.isInteger(rounded)) return String(rounded);
  return rounded.toFixed(1);
}

export function formatMoney(value: number): string {
  if (!Number.isFinite(value)) return "0";
  const sign = value < 0 ? "-" : "";
  const raw = String(Math.abs(value));
  if (raw.includes("e") || raw.includes("E")) {
    return `${sign}${raw}`;
  }
  const [intPart, fracPart] = raw.split(".");
  const grouped = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  if (fracPart === undefined) return `${sign}${grouped}`;
  return `${sign}${grouped}.${fracPart}`;
}

const WARNING_CODE_LABELS: Record<string, string> = {
  no_route: "нет прямого рейса на плечо",
  stale_leg: "взят обходной вариант",
  not_sellable: "дальше своим ходом",
  misresolved: "город определён неверно",
  missing_price: "цены на плечо нет",
  no_price: "цены на плечо нет",
  cache_fallback: "live недоступен, показан cache",
  child_fare_unverified: "детский тариф не проверен, считаем как взрослых",
  no_hotel: "цены на жильё нет",
};

function isRawCodeToken(text: string): boolean {
  return /^[a-z][a-z0-9_]*$/.test(text);
}

export function routingLabel(code: string | null | undefined, reason: string | null | undefined): string {
  if (code && WARNING_CODE_LABELS[code]) return WARNING_CODE_LABELS[code];
  const raw = (reason ?? "").trim();
  if (!raw) return "";
  if (WARNING_CODE_LABELS[raw]) return WARNING_CODE_LABELS[raw];
  if (isRawCodeToken(raw)) return raw.replace(/_/g, " ");
  return raw;
}

export function humanizeWarning(code: string, message: string): string {
  const trimmed = (message ?? "").trim();
  if (code === "cache_fallback") {
    if (trimmed && !isRawCodeToken(trimmed)) return trimmed;
    return WARNING_CODE_LABELS.cache_fallback;
  }
  if (WARNING_CODE_LABELS[code]) return WARNING_CODE_LABELS[code];
  if (trimmed && !isRawCodeToken(trimmed)) return trimmed;
  if (trimmed && WARNING_CODE_LABELS[trimmed]) return WARNING_CODE_LABELS[trimmed];
  if (trimmed && isRawCodeToken(trimmed)) return trimmed.replace(/_/g, " ");
  return code.replace(/_/g, " ");
}

export function noRouteRecovered(
  warning: Extract<SseEvent, { event: "warning" }>,
  events: SseEvent[],
): boolean {
  if (warning.data.recovered === true) return true;
  const idx = events.indexOf(warning);
  if (idx < 0) return false;
  const fromHub = warning.data.leg?.from_hub ?? "";
  const toHub = warning.data.leg?.to_hub ?? "";
  if (!fromHub && !toHub) return false;
  for (let i = idx + 1; i < events.length; i += 1) {
    const item = events[i];
    if (item.event !== "leg") continue;
    if (item.data.price <= 0) continue;
    if (fromHub && toHub && item.data.from_hub === fromHub && item.data.to_hub === toHub) {
      return true;
    }
    if (toHub && item.data.to_hub === toHub) return true;
  }
  return false;
}
