import { PlaceCard } from "./PlaceCard";
import type { CardState, Place } from "../types/contract";

type Props = {
  places: Place[];
  selectedId: string | null;
  cardState: Record<string, CardState>;
  onSelect: (clusterId: string) => void;
};

export function AlmostFits({ places, selectedId, cardState, onSelect }: Props) {
  if (places.length === 0) return null;
  return (
    <section className="almost">
      <h3>Почти подходит</h3>
      <p className="almost-lead">
        Покрыт не весь бургер (coverage.missing). Не смешивается с полным топом.
      </p>
      {places.map((place) => (
        <PlaceCard
          key={place.cluster_id}
          place={place}
          selected={selectedId === place.cluster_id}
          state={cardState[place.cluster_id] ?? { grey: false, reason: null, code: null }}
          onSelect={onSelect}
        />
      ))}
    </section>
  );
}
