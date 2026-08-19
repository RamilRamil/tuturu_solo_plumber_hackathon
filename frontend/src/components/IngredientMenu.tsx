import { useEffect, useState } from "react";
import { GROUPS, GROUP_NAME_RU, INGREDIENTS, INGREDIENT_NAME_RU } from "../catalog/ingredients";
import type { DensityLabel } from "../types/contract";

type Props = {
  selected: string[];
  onToggle: (id: string) => void;
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

export function IngredientMenu({ selected, onToggle }: Props) {
  const [editing, setEditing] = useState(selected.length === 0);

  useEffect(() => {
    if (selected.length === 0) setEditing(true);
  }, [selected.length]);

  const chips = selected.map((id) => ({
    id,
    name: INGREDIENT_NAME_RU[id] ?? id,
  }));

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
          <label className="other-field">
            Другое
            <input type="text" disabled placeholder="отключено (нет LLM-матчинга)" />
          </label>
        </>
      )}
    </section>
  );
}
