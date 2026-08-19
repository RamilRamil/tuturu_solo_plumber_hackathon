import type { HoursStatus as HoursStatusValue } from "../types/contract";

type Props = {
  status: HoursStatusValue;
  openingHours: string | null;
};

function resolveStatus(
  status: HoursStatusValue,
  openingHours: string | null,
): HoursStatusValue {
  if (openingHours === null || openingHours === "") {
    return "unknown";
  }
  if (status === "open" || status === "closed" || status === "unknown") {
    return status;
  }
  return "unknown";
}

export function HoursStatus({ status, openingHours }: Props) {
  const shown = resolveStatus(status, openingHours);
  const label =
    shown === "open" ? "открыт" : shown === "closed" ? "закрыт" : "неизвестно";
  return (
    <span className={`hours hours-${shown}`} title={openingHours ?? ""}>
      {label}
    </span>
  );
}
