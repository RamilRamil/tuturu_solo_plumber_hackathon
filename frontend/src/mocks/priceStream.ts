import {
  BACKUP_YAR_ID,
  CHECKOUT_URL_ETALON,
  ETALON_PAIR_ID,
  SUZDAL_ID,
  TORZHOK_ID,
  TVER_ID,
  VLADIMIR_ID,
} from "../ids";
import type { PriceRequest, SseEvent } from "../types/contract";

class HttpError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function delay(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const timer = window.setTimeout(resolve, ms);
    const onAbort = () => {
      window.clearTimeout(timer);
      reject(new DOMException("Aborted", "AbortError"));
    };
    if (signal.aborted) {
      onAbort();
      return;
    }
    signal.addEventListener("abort", onAbort, { once: true });
  });
}

function etalonEvents(req: PriceRequest): SseEvent[] {
  const lodging = req.budget_scope === "all" ? 1750 : 0;
  const transport = 2592;
  const total = req.budget_scope === "all" ? 4342 : transport;
  return [
    {
      event: "resolved",
      data: {
        origin: {
          query: req.origin,
          name: "Москва",
          region: "Москва",
          geo_id: null,
          guard: "ok",
        },
        hubs: [
          {
            hub_id: "Ярославль|Ярославская область",
            query: "Yaroslavl",
            name: "Ярославль",
            region: "Ярославская область",
            guard: "ok",
          },
          {
            hub_id: "Ростов|Ярославская область",
            query: "Rostov",
            name: "Ростов Великий",
            region: "Ярославская область",
            guard: "ok",
          },
        ],
      },
    },
    {
      event: "leg",
      data: {
        from_hub: "Москва|Москва",
        to_hub: "Ярославль|Ярославская область",
        from_name: "Москва",
        to_name: "Ярославль",
        mode: "railway",
        modes: "avia,railway,bus",
        price: 1035,
        currency: "RUB",
        duration_min: null,
        date: "2026-10-09",
        checkout_ref: {},
        source: "live",
      },
    },
    {
      event: "leg",
      data: {
        from_hub: "Ярославль|Ярославская область",
        to_hub: "Ростов|Ярославская область",
        from_name: "Ярославль",
        to_name: "Ростов Великий",
        mode: "railway",
        modes: "etrain,railway",
        price: 659,
        currency: "RUB",
        duration_min: null,
        date: "2026-10-09",
        checkout_ref: {},
        source: "live",
      },
    },
    {
      event: "leg",
      data: {
        from_hub: "Ростов|Ярославская область",
        to_hub: "Москва|Москва",
        from_name: "Ростов Великий",
        to_name: "Москва",
        mode: "railway",
        modes: "bus,railway",
        price: 898,
        currency: "RUB",
        duration_min: null,
        date: "2026-10-11",
        checkout_ref: {},
        source: "live",
      },
    },
    {
      event: "hotel",
      data: {
        hub_id: "Ярославль|Ярославская область",
        city: "Ярославль",
        min_price: 750,
        currency: "RUB",
        nights: 1,
        price_basis: "stay_total",
        checkout_ref: {},
        source: "live",
      },
    },
    {
      event: "hotel",
      data: {
        hub_id: "Ростов|Ярославская область",
        city: "Ростов Великий",
        min_price: 1000,
        currency: "RUB",
        nights: 1,
        price_basis: "stay_total",
        checkout_ref: {},
        source: "live",
      },
    },
    {
      event: "warning",
      data: {
        code: "hours_unknown",
        message: "opening_hours tag missing",
        hub_id: null,
        leg: { from_hub: "", to_hub: "" },
      },
    },
    {
      event: "breakdown",
      data: {
        transport,
        lodging,
        total,
        currency: "RUB",
        budget_scope: req.budget_scope,
        price_status: "fixture-confirmed",
      },
    },
    {
      event: "checkout",
      data: {
        items: [
          {
            kind: "leg",
            from_hub: "Москва|Москва",
            to_hub: "Ярославль|Ярославская область",
            checkout_url: CHECKOUT_URL_ETALON,
          },
        ],
      },
    },
    {
      event: "done",
      data: {
        ok: true,
        cluster_id: ETALON_PAIR_ID,
        price_status: "fixture-confirmed",
      },
    },
  ];
}

function backupEvents(req: PriceRequest): SseEvent[] {
  return [
    {
      event: "resolved",
      data: {
        origin: {
          query: req.origin,
          name: "Москва",
          region: "Москва",
          geo_id: null,
          guard: "ok",
        },
        hubs: [
          {
            hub_id: "Ярославль|Ярославская область",
            query: "Yaroslavl",
            name: "Ярославль",
            region: "Ярославская область",
            guard: "ok",
          },
        ],
      },
    },
    {
      event: "leg",
      data: {
        from_hub: "Москва|Москва",
        to_hub: "Ярославль|Ярославская область",
        from_name: "Москва",
        to_name: "Ярославль",
        mode: "railway",
        modes: "avia,railway,bus",
        price: 1035,
        currency: "RUB",
        duration_min: null,
        date: "2026-10-09",
        checkout_ref: {},
        source: "cache",
      },
    },
    {
      event: "hotel",
      data: {
        hub_id: "Ярославль|Ярославская область",
        city: "Ярославль",
        min_price: 750,
        currency: "RUB",
        nights: 2,
        price_basis: "stay_total",
        checkout_ref: {},
        source: "cache",
      },
    },
    {
      event: "warning",
      data: {
        code: "cache_fallback",
        message: "mcp_cache at 2026-08-19T13:44:53Z",
        hub_id: "Ярославль|Ярославская область",
        leg: { from_hub: "", to_hub: "" },
      },
    },
    {
      event: "breakdown",
      data: {
        transport: 1035,
        lodging: req.budget_scope === "all" ? 750 : 0,
        total: req.budget_scope === "all" ? 1785 : 1035,
        currency: "RUB",
        budget_scope: req.budget_scope,
        price_status: "fixture-confirmed",
      },
    },
    {
      event: "checkout",
      data: {
        items: [
          {
            kind: "leg",
            from_hub: "Москва|Москва",
            to_hub: "Ярославль|Ярославская область",
            checkout_url: CHECKOUT_URL_ETALON,
          },
        ],
      },
    },
    {
      event: "done",
      data: {
        ok: true,
        cluster_id: BACKUP_YAR_ID,
        price_status: "fixture-confirmed",
      },
    },
  ];
}

function warningStream(
  clusterId: string,
  code: "no_route" | "misresolved" | "not_sellable" | "missing_price",
  message: string,
  extra: SseEvent[] = [],
): SseEvent[] {
  return [
    {
      event: "resolved",
      data: {
        origin: {
          query: "Moscow",
          name: "Москва",
          region: "Москва",
          geo_id: null,
          guard: code === "misresolved" ? "misresolved" : "ok",
        },
        hubs: [
          {
            hub_id: clusterId.replace(/^c:/, ""),
            query: clusterId,
            name: clusterId,
            region: "",
            guard: code === "misresolved" ? "misresolved" : "ok",
          },
        ],
      },
    },
    ...extra,
    {
      event: "warning",
      data: {
        code,
        message,
        hub_id: clusterId.replace(/^c:/, ""),
        leg: { from_hub: "Москва|Москва", to_hub: clusterId.replace(/^c:/, "") },
      },
    },
    {
      event: "done",
      data: {
        ok: false,
        cluster_id: clusterId,
        price_status: "fixture-confirmed",
      },
    },
  ];
}

export async function emitMockPriceStream(
  req: PriceRequest,
  onEvent: (event: SseEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  let events: SseEvent[];
  if (req.cluster_id === ETALON_PAIR_ID) {
    events = etalonEvents(req);
  } else if (req.cluster_id === BACKUP_YAR_ID) {
    events = backupEvents(req);
  } else if (req.cluster_id === TORZHOK_ID) {
    events = warningStream(TORZHOK_ID, "no_route", "leg row no_route");
  } else if (req.cluster_id === VLADIMIR_ID) {
    events = warningStream(VLADIMIR_ID, "misresolved", "guard rejected destination");
  } else if (req.cluster_id === SUZDAL_ID) {
    events = warningStream(SUZDAL_ID, "not_sellable", "SSE not_sellable after origin");
  } else if (req.cluster_id === TVER_ID) {
    events = warningStream(TVER_ID, "missing_price", "no priced leg", [
      {
        event: "leg",
        data: {
          from_hub: "Москва|Москва",
          to_hub: "Тверь|Тверская область",
          from_name: "Москва",
          to_name: "Тверь",
          mode: "railway",
          modes: "railway",
          price: 0,
          currency: "RUB",
          duration_min: null,
          date: "2026-10-09",
          checkout_ref: {},
          source: "live",
        },
      },
    ]);
  } else {
    throw new HttpError(404, "unknown cluster_id");
  }

  await delay(1000, signal);
  onEvent(events[0]);
  await delay(2000, signal);
  onEvent(events[1]);
  for (let i = 2; i < events.length; i += 1) {
    await delay(1000, signal);
    onEvent(events[i]);
  }
}

export { HttpError };
