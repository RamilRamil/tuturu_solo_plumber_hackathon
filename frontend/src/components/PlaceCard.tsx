import { HoursStatus } from "./HoursStatus";
import { ETALON_PAIR_ID } from "../ids";
import type { CardState, Place } from "../types/contract";

type Props = {
  place: Place;
  selected: boolean;
  state: CardState;
  onSelect: (clusterId: string) => void;
};

function routingLabel(code: CardState["code"], reason: string | null): string {
  if (code === "no_route") return reason ? `no_route: ${reason}` : "no_route";
  if (code === "misresolved") return reason ? `misresolved: ${reason}` : "misresolved";
  if (code === "not_sellable") {
    return reason ? `not_sellable: ${reason}` : "not_sellable";
  }
  if (code === "missing_price") {
    return reason ? `missing_price: ${reason}` : "missing_price";
  }
  return reason ?? "";
}

export function PlaceCard({ place, selected, state, onSelect }: Props) {
  const onYourOwn = place.hubs.some((hub) => hub.probe_status === "not_sellable");
  const probeMisresolved = place.hubs.some((hub) => hub.probe_status === "misresolved");
  const isPair = place.cluster_id === ETALON_PAIR_ID;
  const classes = [
    "place-card",
    selected ? "selected" : "",
    state.grey ? "grey" : "",
    isPair ? "pair-card" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <article className={classes}>
      <button type="button" className="place-hit" onClick={() => onSelect(place.cluster_id)}>
        <header>
          <h3>{place.title}</h3>
          {isPair ? <span className="pair-mark">пара эталона</span> : null}
        </header>
        <ul className="hub-chips">
          {place.hubs.map((hub) => (
            <li key={hub.hub_id} className={`hub-chip probe-${hub.probe_status}`}>
              {hub.name}
              {hub.probe_status === "not_sellable" ? (
                <span className="chip-note">своим ходом</span>
              ) : null}
              {hub.probe_status === "misresolved" ? (
                <span className="chip-note">misresolved</span>
              ) : null}
            </li>
          ))}
        </ul>
        <p className="hubs">диаметр {place.diameter_km} км</p>
        <p className="coverage">
          покрытие: {place.coverage.matched.join(", ") || "—"}
          {place.coverage.missing.length > 0
            ? ` · нет: ${place.coverage.missing.join(", ")}`
            : ""}
        </p>
        <p className="rarity">
          rarity.rank {place.rarity.rank} / {place.rarity.total_places_with_combo}
        </p>
        <ul className="objects">
          {place.objects.map((obj) => (
            <li key={obj.id}>
              {obj.name} · {obj.ingredient} ·{" "}
              <HoursStatus status={obj.hours_status} openingHours={obj.opening_hours} />
            </li>
          ))}
        </ul>
        {onYourOwn ? (
          <p className="own">дальше своим ходом (probe_status=not_sellable)</p>
        ) : null}
        {probeMisresolved ? (
          <p className="own">probe misresolved — это не not_sellable</p>
        ) : null}
        {state.grey && (state.code || state.reason) ? (
          <p className={`grey-reason code-${state.code ?? "other"}`}>
            {routingLabel(state.code, state.reason)}
          </p>
        ) : null}
      </button>
    </article>
  );
}
