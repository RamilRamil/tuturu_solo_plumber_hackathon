import { PlaceCard } from "./PlaceCard";
import type { Place } from "../types/contract";

type CardState = {
  grey: boolean;
  reason: string | null;
};

type Props = {
  places: Place[];
  selectedId: string | null;
  cardState: Record<string, CardState>;
  onSelect: (clusterId: string) => void;
};

export function PlaceList({ places, selectedId, cardState, onSelect }: Props) {
  const full = places.filter((place) => place.coverage.missing.length === 0);
  const almost = places.filter((place) => place.coverage.missing.length > 0);
  const top = full.slice(0, 5);
  const rest = full.slice(5);

  return (
    <div className="place-list">
      <h2>Места</h2>
      {top.length === 0 && almost.length === 0 ? (
        <p>Соберите бургер — запрос уйдёт без origin.</p>
      ) : null}
      {top.map((place) => (
        <PlaceCard
          key={place.cluster_id}
          place={place}
          selected={selectedId === place.cluster_id}
          state={cardState[place.cluster_id] ?? { grey: false, reason: null }}
          onSelect={onSelect}
        />
      ))}
      {rest.length > 0 ? (
        <section className="more-places">
          <h3>Ещё в порядке ответа (ниже пятого, кликабельны)</h3>
          {rest.map((place) => (
            <PlaceCard
              key={place.cluster_id}
              place={place}
              selected={selectedId === place.cluster_id}
              state={cardState[place.cluster_id] ?? { grey: false, reason: null }}
              onSelect={onSelect}
            />
          ))}
        </section>
      ) : null}
      {almost.length > 0 ? (
        <section className="almost">
          <h3>Почти подходит</h3>
          {almost.map((place) => (
            <PlaceCard
              key={place.cluster_id}
              place={place}
              selected={selectedId === place.cluster_id}
              state={cardState[place.cluster_id] ?? { grey: false, reason: null }}
              onSelect={onSelect}
            />
          ))}
        </section>
      ) : null}
    </div>
  );
}
