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
};

function formatLeg(leg: LegEvent): string {
  if (leg.price === 0) {
    return `${leg.from_name} → ${leg.to_name}: нет тарифа`;
  }
  return `${leg.from_name} → ${leg.to_name}: ${leg.price} ${leg.currency} (${leg.mode})`;
}

function formatHotel(hotel: HotelEvent): string {
  return `${hotel.city}: ${hotel.min_price} ${hotel.currency} за пребывание (stay_total, ${hotel.nights} ноч.)`;
}

export function PriceStream({ events, error }: Props) {
  const breakdown = events.find((item) => item.event === "breakdown") as
    | { event: "breakdown"; data: BreakdownEvent }
    | undefined;
  const checkout = events.find((item) => item.event === "checkout") as
    | { event: "checkout"; data: CheckoutEvent }
    | undefined;
  const done = events.find((item) => item.event === "done");

  return (
    <section className="price-stream">
      <h2>Поток цен</h2>
      {error ? <p className="error">{error}</p> : null}
      <ol>
        {events.map((item, index) => (
          <li key={`${item.event}-${index}`}>
            <strong>{item.event}</strong>
            {item.event === "resolved" ? ` origin ${item.data.origin.name}` : null}
            {item.event === "leg" ? ` ${formatLeg(item.data)}` : null}
            {item.event === "hotel" ? ` ${formatHotel(item.data)}` : null}
            {item.event === "warning" ? ` ${item.data.code}: ${item.data.message}` : null}
            {item.event === "done" ? ` ${item.data.cluster_id}` : null}
          </li>
        ))}
      </ol>
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
        ? checkout.data.items.map((item) => (
            <a
              key={item.checkout_url}
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
