import { ETALON_PAIR_ID } from "../ids";
import type { Place } from "../types/contract";

type CardState = {
  grey: boolean;
  reason: string | null;
};

type Props = {
  place: Place;
  selected: boolean;
  state: CardState;
  onSelect: (clusterId: string) => void;
};

function hoursLabel(status: string): string {
  if (status === "open") return "открыт";
  if (status === "closed") return "закрыт";
  return "неизвестно";
}

export function PlaceCard({ place, selected, state, onSelect }: Props) {
  const onYourOwn = place.hubs.some((hub) => hub.probe_status === "not_sellable");
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
        <p className="hubs">
          {place.hubs.map((hub) => hub.name).join(" · ")} · диаметр {place.diameter_km} км
        </p>
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
              {obj.name} · {obj.ingredient} · часы: {hoursLabel(obj.hours_status)}
            </li>
          ))}
        </ul>
        {onYourOwn ? <p className="own">дальше своим ходом</p> : null}
        {state.grey && state.reason ? <p className="grey-reason">{state.reason}</p> : null}
      </button>
    </article>
  );
}
