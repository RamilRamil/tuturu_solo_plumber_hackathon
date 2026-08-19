import { formatMoney, humanizeWarning, noRouteRecovered } from "../format";
import type {
  BreakdownEvent,
  CheckoutEvent,
  HotelEvent,
  LegEvent,
  SseEvent,
} from "../types/contract";

type Props = {
  events: SseEvent[];
  error: string | null;
  streaming: boolean;
  aborted: boolean;
  onRetry: () => void;
};

type DetailRow = {
  event: string;
  text: string;
  dedupKey: string;
  count: number;
};

function formatLeg(leg: LegEvent): string {
  if (leg.price === 0) {
    return `${leg.from_name} → ${leg.to_name}: нет тарифа`;
  }
  return `${leg.from_name} → ${leg.to_name}: ${formatMoney(leg.price)} ${leg.currency} (${leg.mode})`;
}

function formatHotel(hotel: HotelEvent): string {
  if (hotel.min_price === 0) {
    return `${hotel.city}: нет тарифа жилья`;
  }
  return `${hotel.city}: ${formatMoney(hotel.min_price)} ${hotel.currency} за пребывание, не за ночь (${hotel.nights} ноч.)`;
}

function formatBreakdown(data: BreakdownEvent): string {
  return `${formatMoney(data.total)} ${data.currency} (транспорт ${formatMoney(data.transport)}, жильё ${formatMoney(data.lodging)})`;
}

function sourceMark(source: "live" | "cache"): string {
  return source === "cache" ? "cache" : "live";
}

function warningDedupKey(item: Extract<SseEvent, { event: "warning" }>, text: string): string {
  const from = item.data.leg?.from_hub ?? "";
  const to = item.data.leg?.to_hub ?? "";
  return `${item.data.code}|${from}|${to}|${text}`;
}

function shouldHideWarning(
  item: Extract<SseEvent, { event: "warning" }>,
  events: SseEvent[],
): boolean {
  if (item.data.recovered === true) return true;
  if (item.data.code !== "no_route" && item.data.code !== "stale_leg") return false;
  if (!noRouteRecovered(item, events)) return false;
  if (item.data.code === "stale_leg") {
    const fromHub = item.data.leg?.from_hub ?? "";
    const toHub = item.data.leg?.to_hub ?? "";
    const idx = events.indexOf(item);
    for (let i = idx + 1; i < events.length; i += 1) {
      const later = events[i];
      if (later.event !== "leg" || later.data.price <= 0) continue;
      if (later.data.from_hub === fromHub && later.data.to_hub === toHub) {
        return false;
      }
      return true;
    }
  }
  return true;
}

function visibleDetailRows(events: SseEvent[]): DetailRow[] {
  const rows: DetailRow[] = [];
  for (const item of events) {
    if (item.event === "warning") {
      if (shouldHideWarning(item, events)) continue;
      const { code, message } = item.data;
      const text = humanizeWarning(code, message);
      const dedupKey = warningDedupKey(item, text);
      const prev = rows[rows.length - 1];
      if (
        prev &&
        prev.event === "warning" &&
        (prev.dedupKey === dedupKey || prev.text === text)
      ) {
        prev.count += 1;
        continue;
      }
      rows.push({ event: "warning", text, dedupKey, count: 1 });
      continue;
    }
    let text = "";
    if (item.event === "resolved") text = `город выезда ${item.data.origin.name}`;
    else if (item.event === "leg") text = formatLeg(item.data);
    else if (item.event === "hotel") text = formatHotel(item.data);
    else if (item.event === "breakdown") text = formatBreakdown(item.data);
    else if (item.event === "done") text = item.data.ok ? "готово" : "без билета";
    rows.push({ event: item.event, text, dedupKey: "", count: 1 });
  }
  return rows;
}

const NO_TICKET_CODES = new Set(["no_route", "not_sellable", "missing_price", "no_price"]);

export function PriceStream({ events, error, streaming, aborted, onRetry }: Props) {
  const breakdown = events.find((item) => item.event === "breakdown") as
    | { event: "breakdown"; data: BreakdownEvent }
    | undefined;
  const checkout = events.find((item) => item.event === "checkout") as
    | { event: "checkout"; data: CheckoutEvent }
    | undefined;
  const done = events.find((item) => item.event === "done");
  const legs = events.filter(
    (item): item is Extract<SseEvent, { event: "leg" }> => item.event === "leg",
  );
  const hotels = events.filter(
    (item): item is Extract<SseEvent, { event: "hotel" }> => item.event === "hotel",
  );
  const cacheFallback = events.find(
    (item) => item.event === "warning" && item.data.code === "cache_fallback",
  );
  const hasCacheSource = events.some(
    (item) =>
      (item.event === "leg" || item.event === "hotel") && item.data.source === "cache",
  );
  const is404 = error === "404 unknown cluster_id";
  const checkoutItems = checkout?.data.items.filter((item) => item.checkout_url) ?? [];
  const blockingWarning = events.some(
    (item) => item.event === "warning" && NO_TICKET_CODES.has(item.data.code),
  );
  const noTicket =
    checkoutItems.length === 0 &&
    !streaming &&
    (Boolean(done) || blockingWarning);
  const detailRows = visibleDetailRows(events);
  const cacheFallbackText =
    cacheFallback && cacheFallback.event === "warning"
      ? humanizeWarning(cacheFallback.data.code, cacheFallback.data.message)
      : "";

  return (
    <section className="price-stream">
      <h2>Цена</h2>
      {aborted ? <p className="hint">поток прерван</p> : null}
      {is404 ? (
        <div className="not-found">
          <h3>404</h3>
          <p>Такого места в выдаче нет.</p>
          <button type="button" onClick={onRetry}>
            Повторить
          </button>
        </div>
      ) : error ? (
        <p className="error">
          {error}{" "}
          <button type="button" className="text-btn" onClick={onRetry}>
            повторить
          </button>
        </p>
      ) : null}
      {events.length === 0 && !streaming && !error ? (
        <p className="hint">После запроса цены появятся здесь.</p>
      ) : null}
      {breakdown ? (
        <div className="price-summary">
          <p className="price-total">
            {formatMoney(breakdown.data.total)} {breakdown.data.currency}
          </p>
          <p>транспорт: {formatMoney(breakdown.data.transport)} {breakdown.data.currency}</p>
          <p>жильё: {formatMoney(breakdown.data.lodging)} {breakdown.data.currency}</p>
          <p className="price-status">{breakdown.data.price_status}</p>
        </div>
      ) : null}
      {legs.length > 0 ? (
        <ul className="price-legs">
          {legs.map((item, index) => (
            <li key={`leg-${index}`}>
              {formatLeg(item.data)}{" "}
              <span className={`src src-${item.data.source}`}>
                {sourceMark(item.data.source)}
              </span>
            </li>
          ))}
        </ul>
      ) : null}
      {hotels.length > 0 ? (
        <ul className="price-hotels">
          {hotels.map((item, index) => (
            <li key={`hotel-${index}`}>
              {formatHotel(item.data)}{" "}
              <span className={`src src-${item.data.source}`}>
                {sourceMark(item.data.source)}
              </span>
            </li>
          ))}
        </ul>
      ) : null}
      {hasCacheSource || cacheFallback ? (
        <p className="cache-stamp">
          источник: cache
          {cacheFallbackText ? ` · ${cacheFallbackText}` : ""}
          . Это не live без метки.
        </p>
      ) : events.some((item) => item.event === "leg") ? (
        <p className="cache-stamp">источник плеч: live</p>
      ) : null}
      <div className="buy-cta">
        {checkoutItems.length > 0
          ? checkoutItems.map((item, index) => (
              <a
                key={`${index}-${item.checkout_url}`}
                className="checkout buy"
                href={item.checkout_url}
                target="_blank"
                rel="noreferrer"
              >
                Купить на Tutu
              </a>
            ))
          : streaming
            ? (
                <p className="buy-pending">считаем маршрут…</p>
              )
            : noTicket
              ? (
                  <p className="buy-none">до этого места билета нет</p>
                )
              : null}
      </div>
      {events.length > 0 ? (
        <details className="sse-details">
          <summary>подробности</summary>
          <ol>
            {detailRows.map((row, index) => (
              <li key={`${row.event}-${index}`} className="sse-item">
                <strong>{row.event}</strong>
                {row.text ? ` ${row.text}` : null}
                {row.count > 1 ? ` x${row.count}` : null}
              </li>
            ))}
          </ol>
        </details>
      ) : null}
    </section>
  );
}
