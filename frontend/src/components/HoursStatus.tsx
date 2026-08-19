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
  if (shown !== "open" && shown !== "closed") return null;
  const label = shown === "open" ? "открыт" : "закрыт";
  return (
    <span className={`hours hours-${shown}`} title={openingHours ?? ""}>
      {" · "}
      {label}
    </span>
  );
}
