import type { ApiMode } from "../types/contract";

type Props = {
  mode: ApiMode;
  onChange: (mode: ApiMode) => void;
};

export function ModeToggle({ mode, onChange }: Props) {
  return (
    <fieldset className="mode-toggle">
      <legend>Источник</legend>
      <label>
        <input
          type="radio"
          name="api-mode"
          checked={mode === "mock"}
          onChange={() => onChange("mock")}
        />
        mock
      </label>
      <label>
        <input
          type="radio"
          name="api-mode"
          checked={mode === "live"}
          onChange={() => onChange("live")}
        />
        live
      </label>
    </fieldset>
  );
}
