import type { BudgetScope } from "../types/contract";

type Props = {
  enabled: boolean;
  origin: string;
  days: number;
  month: string;
  adults: number;
  childrenAges: string;
  budgetScope: BudgetScope;
  busy: boolean;
  onAbort: () => void;
  onOrigin: (value: string) => void;
  onDays: (value: number) => void;
  onMonth: (value: string) => void;
  onAdults: (value: number) => void;
  onChildrenAges: (value: string) => void;
  onBudgetScope: (value: BudgetScope) => void;
  onSubmit: () => void;
};

export function OriginForm({
  enabled,
  origin,
  days,
  month,
  adults,
  childrenAges,
  budgetScope,
  busy,
  onAbort,
  onOrigin,
  onDays,
  onMonth,
  onAdults,
  onChildrenAges,
  onBudgetScope,
  onSubmit,
}: Props) {
  return (
    <section className={enabled ? "origin" : "origin inactive"}>
      <h2>Откуда и цены</h2>
      {!enabled ? (
        <p>Сначала выберите карточку места. Город выезда - не вход поиска.</p>
      ) : null}
      <fieldset disabled={!enabled}>
        <label>
          Откуда
          <input value={origin} onChange={(event) => onOrigin(event.target.value)} />
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
        <label>
          Бюджет
          <select
            value={budgetScope}
            onChange={(event) => onBudgetScope(event.target.value as BudgetScope)}
          >
            <option value="transport">только транспорт</option>
            <option value="all">всё</option>
          </select>
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
