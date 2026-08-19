import { HoursStatus } from "./HoursStatus";
import { INGREDIENT_NAME_RU } from "../catalog/ingredients";
import type { Place } from "../types/contract";

type Props = {
  place: Place | null;
};

function isNamedPoi(name: unknown): boolean {
  return typeof name === "string" && name.trim().length > 0;
}

function poiDisplayName(name: unknown): string {
  return typeof name === "string" ? name.trim() : "";
}

function ingredientLabel(id: string): string {
  return INGREDIENT_NAME_RU[id] ?? id;
}

export function PlaceDetails({ place }: Props) {
  if (!place) return null;

  const objectTotal = place.objects.length;
  const namedObjects = place.objects.filter((obj) => isNamedPoi(obj.name));

  return (
    <section className="place-details">
      <h2>Объекты</h2>
      <p className="map-caption">{place.title}</p>
      {objectTotal > 0 ? (
        <p className="objects-count">
          {namedObjects.length} of {objectTotal} named
        </p>
      ) : (
        <p className="empty-line">В этом кластере нет объектов с именами.</p>
      )}
      {namedObjects.length > 0 ? (
        <ul className="objects">
          {namedObjects.map((obj) => (
            <li key={obj.id}>
              {poiDisplayName(obj.name)}
              {" · "}
              {ingredientLabel(obj.ingredient)}
              <HoursStatus status={obj.hours_status} openingHours={obj.opening_hours} />
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
