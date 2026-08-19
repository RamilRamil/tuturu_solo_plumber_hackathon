import { useEffect, useState, type FormEvent } from "react";
import { fetchParse } from "../api/client";
import { GROUPS, GROUP_NAME_RU, INGREDIENTS, INGREDIENT_NAME_RU } from "../catalog/ingredients";
import type { DensityLabel, RadiusKm } from "../types/contract";

type Props = {
  selected: string[];
  onToggle: (id: string) => void;
  radiusKm: RadiusKm;
  onParsed: (ingredients: string[], radiusKm: RadiusKm | null) => void;
};

const DENSITY_TEXT: Record<DensityLabel, string> = {
  dense: "плотный",
  medium: "средний",
  rare: "редкий",
  absent_in_region: "нет в регионе",
};

function densityText(label: DensityLabel | null): string {
  if (!label) return "нет замера";
  return DENSITY_TEXT[label];
}

function asRadius(raw: number): RadiusKm | null {
  if (raw === 50 || raw === 100 || raw === 150) return raw;
  return null;
}

export function IngredientMenu({ selected, onToggle, radiusKm, onParsed }: Props) {
  const [editing, setEditing] = useState(selected.length === 0);
  const [phrase, setPhrase] = useState("");
  const [unmatched, setUnmatched] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (selected.length === 0) setEditing(true);
  }, [selected.length]);

  const chips = selected.map((id) => ({
    id,
    name: INGREDIENT_NAME_RU[id] ?? id,
  }));

  const submitPhrase = (event: FormEvent) => {
    event.preventDefault();
    const text = phrase.trim();
    if (!text || busy) return;
    setBusy(true);
    setUnmatched([]);
    fetchParse({ text, radius_km: radiusKm })
      .then((res) => {
        if (res.ingredients.length === 0) return;
        onParsed(res.ingredients, asRadius(res.radius_km));
        if (res.unmatched.length > 0) setUnmatched(res.unmatched);
        setPhrase("");
      })
      .catch(() => {
        // silent fallback: chips stay the primary path
      })
      .finally(() => setBusy(false));
  };

  return (
    <section className="menu">
      <div className="menu-head">
        <h2>Бургер</h2>
        {selected.length > 0 ? (
          <button
            type="button"
            className="change-btn"
            onClick={() => setEditing((open) => !open)}
          >
            {editing ? "Готово" : "Изменить"}
          </button>
        ) : null}
      </div>
      {!editing && selected.length > 0 ? (
        <ul className="ing-chips">
          {chips.map((chip) => (
            <li key={chip.id} className="ing-chip">
              {chip.name}
            </li>
          ))}
        </ul>
      ) : (
        <>
          {GROUPS.map((group) => (
            <div key={group.id} className="menu-group">
              <h3>{GROUP_NAME_RU[group.id] ?? group.name_ru}</h3>
              <div className="menu-grid">
                {INGREDIENTS.filter((item) => item.group === group.id).map((item) => {
                  const on = selected.includes(item.id);
                  const measured =
                    item.density_measured === null || item.density_measured <= 1
                      ? ""
                      : ` ${item.density_measured}`;
                  return (
                    <button
                      key={item.id}
                      type="button"
                      className={on ? "ing-card on" : "ing-card"}
                      onClick={() => onToggle(item.id)}
                    >
                      <span className="ing-name">{INGREDIENT_NAME_RU[item.id] ?? item.name_ru}</span>
                      <span className={`density density-${item.density_label ?? "none"}`}>
                        {densityText(item.density_label)}
                        {measured}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
          <form onSubmit={submitPhrase}>
            <label className="other-field">
              Другое
              <input
                type="text"
                value={phrase}
                disabled={busy}
                autoComplete="off"
                placeholder="например: храмы и музеи недалеко"
                onChange={(event) => setPhrase(event.target.value)}
              />
            </label>
            {unmatched.length > 0 ? (
              <p className="other-field">не распознали: {unmatched.join(", ")}</p>
            ) : null}
          </form>
        </>
      )}
    </section>
  );
}
