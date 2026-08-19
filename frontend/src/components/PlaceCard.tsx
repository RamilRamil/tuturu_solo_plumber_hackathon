import { INGREDIENT_NAME_RU } from "../catalog/ingredients";
import { ETALON_CLUSTER_ID } from "../ids";
import type { CardState, Place } from "../types/contract";

type Props = {
  place: Place;
  selected: boolean;
  state: CardState;
  onSelect: (clusterId: string) => void;
};

function ingredientLabel(id: string): string {
  return INGREDIENT_NAME_RU[id] ?? id;
}

function routingLabel(code: CardState["code"], reason: string | null): string {
  if (reason) return reason;
  if (code === "no_route") return "Билета по этому плечу нет";
  if (code === "misresolved") return "Город определён неверно";
  if (code === "not_sellable") return "Дальше своим ходом";
  if (code === "missing_price") return "Цены на плечо нет";
  return "";
}

export function PlaceCard({ place, selected, state, onSelect }: Props) {
  const onYourOwn = place.hubs.some((hub) => hub.probe_status === "not_sellable");
  const probeMisresolved = place.hubs.some((hub) => hub.probe_status === "misresolved");
  const isEtalon = place.cluster_id === ETALON_CLUSTER_ID;
  const covered = place.coverage.matched.length;
  const coverageTotal = covered + place.coverage.missing.length;
  const classes = [
    "place-card",
    selected ? "selected" : "",
    state.grey ? "grey" : "",
    onYourOwn ? "on-foot" : "",
    isEtalon ? "etalon-card" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <article className={classes}>
      <button type="button" className="place-hit" onClick={() => onSelect(place.cluster_id)}>
        <header>
          <h3>{place.title}</h3>
          {onYourOwn ? <span className="own-mark">дальше своим ходом</span> : null}
        </header>
        <ul className="hub-chips">
          {place.hubs.map((hub) => (
            <li key={hub.hub_id} className={`hub-chip probe-${hub.probe_status}`}>
              {hub.name}
              {hub.probe_status === "not_sellable" ? (
                <span className="chip-note">своим ходом</span>
              ) : null}
              {hub.probe_status === "misresolved" ? (
                <span className="chip-note">город неверен</span>
              ) : null}
            </li>
          ))}
        </ul>
        <p className="hubs">диаметр {place.diameter_km} км</p>
        <p className="coverage">
          покрытие {covered}/{coverageTotal}
          {place.coverage.matched.length > 0
            ? ` · есть: ${place.coverage.matched.map(ingredientLabel).join(", ")}`
            : ""}
          {place.coverage.missing.length > 0
            ? ` · нет: ${place.coverage.missing.map(ingredientLabel).join(", ")}`
            : ""}
        </p>
        <p className="rarity">
          редкость {place.rarity.rank}/{place.rarity.total_places_with_combo}
        </p>
        {onYourOwn ? (
          <p className="own">
            {state.reason
              ? `Дальше своим ходом: ${state.reason}`
              : "Дальше своим ходом: билета до этого узла нет"}
          </p>
        ) : null}
        {probeMisresolved ? (
          <p className="own">Город определён неверно - это не «своим ходом».</p>
        ) : null}
        {state.grey && (state.code || state.reason) && !onYourOwn ? (
          <p className={`grey-reason code-${state.code ?? "other"}`}>
            {routingLabel(state.code, state.reason)}
          </p>
        ) : null}
      </button>
    </article>
  );
}
