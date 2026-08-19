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

function formatLeg(leg: LegEvent): string {
  if (leg.price === 0) {
    return `${leg.from_name} → ${leg.to_name}: нет тарифа`;
  }
  return `${leg.from_name} → ${leg.to_name}: ${leg.price} ${leg.currency} (${leg.mode})`;
}

function formatHotel(hotel: HotelEvent): string {
  if (hotel.min_price === 0) {
    return `${hotel.city}: нет тарифа жилья`;
  }
  return `${hotel.city}: ${hotel.min_price} ${hotel.currency} за пребывание (stay_total, ${hotel.nights} ноч.)`;
}

function sourceMark(source: "live" | "cache"): string {
  return source === "cache" ? "cache" : "live";
}

export function PriceStream({ events, error, streaming, aborted, onRetry }: Props) {
  const breakdown = events.find((item) => item.event === "breakdown") as
    | { event: "breakdown"; data: BreakdownEvent }
    | undefined;
  const checkout = events.find((item) => item.event === "checkout") as
    | { event: "checkout"; data: CheckoutEvent }
    | undefined;
  const done = events.find((item) => item.event === "done");
  const cacheFallback = events.find(
    (item) => item.event === "warning" && item.data.code === "cache_fallback",
  );
  const hasCacheSource = events.some(
    (item) =>
      (item.event === "leg" || item.event === "hotel") && item.data.source === "cache",
  );
  const is404 = error === "404 unknown cluster_id";

  return (
    <section className="price-stream">
      <h2>Поток цен</h2>
      {streaming ? <p className="loading-line">события SSE по мере прихода…</p> : null}
      {aborted ? <p className="hint">поток прерван</p> : null}
      {is404 ? (
        <div className="not-found">
          <h3>404</h3>
          <p>Неизвестный cluster_id. Это HTTP 404, не SSE warning.</p>
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
      <ol>
        {events.map((item, index) => (
          <li key={`${item.event}-${index}`} className="sse-item">
            <strong>{item.event}</strong>
            {item.event === "resolved" ? ` origin ${item.data.origin.name}` : null}
            {item.event === "leg" ? (
              <>
                {" "}
                {formatLeg(item.data)}{" "}
                <span className={`src src-${item.data.source}`}>
                  {sourceMark(item.data.source)}
                </span>
              </>
            ) : null}
            {item.event === "hotel" ? (
              <>
                {" "}
                {formatHotel(item.data)}{" "}
                <span className={`src src-${item.data.source}`}>
                  {sourceMark(item.data.source)}
                </span>
              </>
            ) : null}
            {item.event === "warning" ? ` ${item.data.code}: ${item.data.message}` : null}
            {item.event === "done" ? ` ${item.data.cluster_id}` : null}
          </li>
        ))}
      </ol>
      {hasCacheSource || cacheFallback ? (
        <p className="cache-stamp">
          источник: cache
          {cacheFallback && cacheFallback.event === "warning"
            ? ` · ${cacheFallback.data.message}`
            : ""}
          . Это не live без метки.
        </p>
      ) : events.some((item) => item.event === "leg") ? (
        <p className="cache-stamp">источник плеч: live</p>
      ) : null}
      {breakdown ? (
        <div className="breakdown">
          <p>транспорт: {breakdown.data.transport} {breakdown.data.currency}</p>
          <p>жильё: {breakdown.data.lodging} {breakdown.data.currency}</p>
          <p>итого: {breakdown.data.total} {breakdown.data.currency}</p>
          <p className="price-status">{breakdown.data.price_status}</p>
        </div>
      ) : done ? (
        <p>Поток завершён без раскладки — итог не готов.</p>
      ) : null}
      {checkout
        ? checkout.data.items.map((item, index) => (
            <a
              key={`${index}-${item.checkout_url}`}
              className="checkout"
              href={item.checkout_url}
              target="_blank"
              rel="noreferrer"
            >
              Оформить
            </a>
          ))
        : null}
    </section>
  );
}
