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
