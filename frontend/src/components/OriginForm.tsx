type Props = {
  enabled: boolean;
  origin: string;
  originNeed: boolean;
  days: number;
  month: string;
  adults: number;
  childrenAges: string;
  busy: boolean;
  onAbort: () => void;
  onOrigin: (value: string) => void;
  onDays: (value: number) => void;
  onMonth: (value: string) => void;
  onAdults: (value: number) => void;
  onChildrenAges: (value: string) => void;
  onSubmit: () => void;
};

export function OriginForm({
  enabled,
  origin,
  originNeed,
  days,
  month,
  adults,
  childrenAges,
  busy,
  onAbort,
  onOrigin,
  onDays,
  onMonth,
  onAdults,
  onChildrenAges,
  onSubmit,
}: Props) {
  return (
    <section className={enabled ? "origin" : "origin inactive"}>
      <h2>Откуда и цены</h2>
      {!enabled ? (
        <p>Сначала выберите карточку места. Город выезда - не вход поиска.</p>
      ) : null}
      <fieldset disabled={!enabled}>
        <label className={originNeed ? "origin-field need" : "origin-field"}>
          Откуда едете (для цен)
          <input
            value={origin}
            autoComplete="off"
            onChange={(event) => onOrigin(event.target.value)}
          />
          <span className="origin-field-hint">город выезда не влияет на подбор мест</span>
          {originNeed ? <span className="origin-need">укажите город выезда</span> : null}
        </label>
        <label>
          Дни
          <input
            type="number"
            min={1}
            value={days}
            onChange={(event) => onDays(Number(event.target.value))}
          />
        </label>
        <label>
          Месяц
          <input value={month} onChange={(event) => onMonth(event.target.value)} />
        </label>
        <label>
          Взрослые
          <input
            type="number"
            min={1}
            value={adults}
            onChange={(event) => onAdults(Number(event.target.value))}
          />
        </label>
        <label>
          Возрасты детей
          <input
            value={childrenAges}
            placeholder="например 5, 8"
            onChange={(event) => onChildrenAges(event.target.value)}
          />
        </label>
        <button type="button" disabled={!enabled || busy} onClick={onSubmit}>
          {busy ? "стрим…" : "Запросить цены"}
        </button>
        <button
          type="button"
          className="abort"
          disabled={!busy}
          onClick={onAbort}
        >
          Прервать
        </button>
      </fieldset>
    </section>
  );
}
