import { useEffect, useState } from "react";
import { PlaceCard } from "./PlaceCard";
import type { CardState, Place } from "../types/contract";

type Props = {
  places: Place[];
  selectedId: string | null;
  cardState: Record<string, CardState>;
  loading: boolean;
  hasIngredients: boolean;
  onSelect: (clusterId: string) => void;
};

export function PlaceList({
  places,
  selectedId,
  cardState,
  loading,
  hasIngredients,
  onSelect,
}: Props) {
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

  return (
    <div className="place-list">
      <h2>Места</h2>
      {loading ? (
        <p className="loading-line">
          {places.length > 0
            ? "обновляем выдачу по выбранным областям…"
            : "ищем кластеры без origin…"}
        </p>
      ) : null}
      {!loading && top.length === 0 ? (
        <p className="empty-line">
          {hasIngredients
            ? "Полного покрытия в ответе нет. Смотрите «почти подходит» или карту покрытия."
            : "Соберите бургер - запрос уйдёт без города выезда."}
        </p>
      ) : null}
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
    </div>
  );
}
