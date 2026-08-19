import { RADIUS_STEPS } from "../ids";
import type { RadiusKm } from "../types/contract";

type Props = {
  value: RadiusKm;
  totalFound: number | null;
  onChange: (value: RadiusKm) => void;
};

export function RadiusSlider({ value, totalFound, onChange }: Props) {
  const index = RADIUS_STEPS.indexOf(value);
  return (
    <section className="radius">
      <h2>Радиус</h2>
      <input
        type="range"
        min={0}
        max={2}
        step={1}
        value={index}
        aria-valuemin={50}
        aria-valuemax={150}
        aria-valuenow={value}
        onChange={(event) => {
          const next = RADIUS_STEPS[Number(event.target.value)];
          if (next) onChange(next);
        }}
      />
      <div className="radius-ticks">
        {RADIUS_STEPS.map((step) => (
          <button
            key={step}
            type="button"
            className={step === value ? "tick on" : "tick"}
            onClick={() => onChange(step)}
          >
            {step} км
          </button>
        ))}
      </div>
      <p className="total-found">
        Найдено мест: {totalFound === null ? "—" : totalFound}
      </p>
    </section>
  );
}
