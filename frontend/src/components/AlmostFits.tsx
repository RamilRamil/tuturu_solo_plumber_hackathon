import { useEffect, useState } from "react";
import { PlaceCard } from "./PlaceCard";
import type { CardState, Place } from "../types/contract";

type Props = {
  places: Place[];
  selectedId: string | null;
  cardState: Record<string, CardState>;
  onSelect: (clusterId: string) => void;
};

export function AlmostFits({ places, selectedId, cardState, onSelect }: Props) {
  const top = places.slice(0, 5);
  const rest = places.slice(5);
  const idle = { grey: false, reason: null, code: null } as CardState;
  const [showRest, setShowRest] = useState(false);

  useEffect(() => {
    if (!selectedId) return;
    const hidden = places.slice(5);
    if (hidden.some((place) => place.cluster_id === selectedId)) {
      setShowRest(true);
    }
  }, [selectedId, places]);

  if (places.length === 0) return null;
  return (
    <section className="almost">
      <h3>Почти подходит</h3>
      <p className="almost-lead">
        Не хватает части бургера. Эти места всё равно можно выбрать.
      </p>
      {top.map((place) => (
        <PlaceCard
          key={place.cluster_id}
          place={place}
          selected={selectedId === place.cluster_id}
          state={cardState[place.cluster_id] ?? idle}
          onSelect={onSelect}
        />
      ))}
      {rest.length > 0 ? (
        <div className="more-places">
          {showRest ? (
            rest.map((place) => (
              <PlaceCard
                key={place.cluster_id}
                place={place}
                selected={selectedId === place.cluster_id}
                state={cardState[place.cluster_id] ?? idle}
                onSelect={onSelect}
              />
            ))
          ) : (
            <button type="button" className="show-more" onClick={() => setShowRest(true)}>
              Показать ещё ({rest.length})
            </button>
          )}
        </div>
      ) : null}
    </section>
  );
}
