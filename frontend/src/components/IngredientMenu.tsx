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
  return (
    <section className="menu">
      <h2>Бургер</h2>
      {GROUPS.map((group) => (
        <div key={group.id} className="menu-group">
          <h3>{GROUP_NAME_RU[group.id] ?? group.name_ru}</h3>
          <div className="menu-grid">
            {INGREDIENTS.filter((item) => item.group === group.id).map((item) => {
              const on = selected.includes(item.id);
              const measured =
                item.density_measured === null ? "" : ` ${item.density_measured}`;
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
    </section>
  );
}
