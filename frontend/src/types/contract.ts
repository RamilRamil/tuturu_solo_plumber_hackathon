export type ApiMode = "mock" | "live";
export type RadiusKm = 50 | 100 | 150;
export type DensityLabel = "dense" | "medium" | "rare" | "absent_in_region";
export type ProbeStatus = "sellable" | "not_sellable" | "misresolved";
export type HoursStatus = "open" | "closed" | "unknown";
export type BudgetScope = "transport" | "all";
export type PriceStatus = "fixture-confirmed" | "live";
export type SseEventName =
  | "resolved"
  | "leg"
  | "hotel"
  | "breakdown"
  | "checkout"
  | "warning"
  | "done";

export type Hub = {
  hub_id: string;
  name: string;
  region: string;
  lat: number;
  lon: number;
  probe_status: ProbeStatus;
};

export type PoiObject = {
  id: string;
  name: string;
  ingredient: string;
  lat: number;
  lon: number;
  significance: number;
  wikidata: string | null;
  start_date: { raw: string; from: number; to: number } | null;
  opening_hours: string | null;
  hours_status: HoursStatus;
};

export type Place = {
  cluster_id: string;
  title: string;
  hubs: Hub[];
  center: { lat: number; lon: number };
  diameter_km: number;
  coverage: { matched: string[]; missing: string[] };
  rarity: { rank: number; total_places_with_combo: number };
  objects: PoiObject[];
};

export type PlacesRequest = {
  ingredients: string[];
  radius_km: RadiusKm;
  limit?: number;
};

export type PlacesResponse = {
  total_found: number;
  places: Place[];
};

export type PriceRequest = {
  cluster_id: string;
  origin: string;
  days: number;
  month: string;
  adults: number;
  children_ages: number[];
  budget_scope: BudgetScope;
};

export type ResolvedEvent = {
  origin: {
    query: string;
    name: string;
    region: string;
    geo_id: string | null;
    guard: "ok" | "misresolved";
  };
  hubs: Array<{
    hub_id: string;
    query: string;
    name: string;
    region: string;
    guard: "ok" | "misresolved";
  }>;
};

export type LegEvent = {
  from_hub: string;
  to_hub: string;
  from_name: string;
  to_name: string;
  mode: string;
  modes: string;
  price: number;
  currency: string;
  duration_min: number | null;
  date: string;
  checkout_ref: Record<string, unknown>;
  source: "live" | "cache";
};

export type HotelEvent = {
  hub_id: string;
  city: string;
  min_price: number;
  currency: string;
  nights: number;
  price_basis: "stay_total";
  checkout_ref: Record<string, unknown>;
  source: "live" | "cache";
};

export type BreakdownEvent = {
  transport: number;
  lodging: number;
  total: number;
  currency: string;
  budget_scope: BudgetScope;
  price_status: PriceStatus;
};

export type CheckoutEvent = {
  items: Array<{
    kind: string;
    from_hub?: string;
    to_hub?: string;
    checkout_url: string;
  }>;
};

export type WarningEvent = {
  code: string;
  message: string;
  hub_id: string | null;
  leg: { from_hub: string; to_hub: string };
};

export type DoneEvent = {
  ok: boolean;
  cluster_id: string;
  price_status: PriceStatus;
};

export type SseEvent =
  | { event: "resolved"; data: ResolvedEvent }
  | { event: "leg"; data: LegEvent }
  | { event: "hotel"; data: HotelEvent }
  | { event: "breakdown"; data: BreakdownEvent }
  | { event: "checkout"; data: CheckoutEvent }
  | { event: "warning"; data: WarningEvent }
  | { event: "done"; data: DoneEvent };

export type Ingredient = {
  id: string;
  name_ru: string;
  group: string;
  density_label: DensityLabel | null;
  density_measured: number | null;
};

export type IngredientGroup = {
  id: string;
  name_ru: string;
};

export type RoutingGreyCode =
  | "no_route"
  | "misresolved"
  | "not_sellable"
  | "missing_price";

export type CardState = {
  grey: boolean;
  reason: string | null;
  code: RoutingGreyCode | null;
};

export type CoveragePayload = {
  loaded: string[];
  admin_level_4: string[];
  at: string | null;
  note: string | null;
  poi_count?: number;
};
