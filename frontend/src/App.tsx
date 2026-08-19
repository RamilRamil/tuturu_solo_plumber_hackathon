import { useEffect, useMemo, useRef, useState } from "react";
import { fetchPlaces, streamPrice } from "./api/client";
import { AlmostFits } from "./components/AlmostFits";
import { ClusterMap } from "./components/ClusterMap";
import { CoverageMap } from "./components/CoverageMap";
import { IngredientMenu } from "./components/IngredientMenu";
import { ModeToggle } from "./components/ModeToggle";
import { OriginForm } from "./components/OriginForm";
import { PlaceList } from "./components/PlaceList";
import { PriceStream } from "./components/PriceStream";
import { RadiusSlider } from "./components/RadiusSlider";
import { DEFAULT_RADIUS, ETALON_INGREDIENTS } from "./ids";
import { HttpError } from "./mocks/priceStream";
import { encodeShare, parseShare, shareHref, type ShareState } from "./share";
import type {
  ApiMode,
  BudgetScope,
  CardState,
  PlacesResponse,
  RadiusKm,
  RoutingGreyCode,
  SseEvent,
} from "./types/contract";

function parseAges(raw: string): number[] {
  return raw
    .split(",")
    .map((part) => Number(part.trim()))
    .filter((n) => Number.isFinite(n) && n > 0);
}

function defaultApiMode(): ApiMode {
  const env = import.meta.env.VITE_API_MODE_DEFAULT;
  if (env === "live" || env === "mock") return env;
  return import.meta.env.PROD ? "live" : "mock";
}

function bootShare(): ShareState {
  if (typeof window === "undefined") {
    return {
      ingredients: [...ETALON_INGREDIENTS],
      radius_km: DEFAULT_RADIUS,
      cluster_id: null,
      origin: null,
      days: null,
      month: null,
      adults: null,
      children_ages: null,
      budget_scope: null,
    };
  }
  return parseShare(window.location.search);
}

function noRouteRecovered(
  warning: Extract<SseEvent, { event: "warning" }>,
  events: SseEvent[],
): boolean {
  if (warning.data.recovered === true) return true;
  const idx = events.indexOf(warning);
  if (idx < 0) return false;
  const fromHub = warning.data.leg?.from_hub ?? "";
  const toHub = warning.data.leg?.to_hub ?? "";
  if (!fromHub && !toHub) return false;
  for (let i = idx + 1; i < events.length; i += 1) {
    const item = events[i];
    if (item.event !== "leg") continue;
    if (item.data.price <= 0) continue;
    if (fromHub && toHub && item.data.from_hub === fromHub && item.data.to_hub === toHub) {
      return true;
    }
    if (toHub && item.data.to_hub === toHub) return true;
  }
  return false;
}

function routingGreyFromEvents(events: SseEvent[]): CardState {
  const warnings = events.filter(
    (item): item is Extract<SseEvent, { event: "warning" }> => item.event === "warning",
  );
  const resolved = events.find(
    (item): item is Extract<SseEvent, { event: "resolved" }> => item.event === "resolved",
  );
  const legs = events.filter(
    (item): item is Extract<SseEvent, { event: "leg" }> => item.event === "leg",
  );
  const done = events.find(
    (item): item is Extract<SseEvent, { event: "done" }> => item.event === "done",
  );
  const byCode = (code: RoutingGreyCode) =>
    warnings.find((item) => item.data.code === code);

  const misWarn = byCode("misresolved");
  const guardMis =
    resolved &&
    (resolved.data.origin.guard === "misresolved" ||
      resolved.data.hubs.some((hub) => hub.guard === "misresolved"));
  if (misWarn || guardMis) {
    return {
      grey: true,
      reason: misWarn?.data.message ?? "guard rejected destination",
      code: "misresolved",
    };
  }

  const noRouteOpen = warnings.filter(
    (item) => item.data.code === "no_route" && !noRouteRecovered(item, events),
  );
  if (noRouteOpen.length > 0) {
    return { grey: true, reason: noRouteOpen[0].data.message, code: "no_route" };
  }

  const notSellable = byCode("not_sellable");
  if (notSellable) {
    return { grey: true, reason: notSellable.data.message, code: "not_sellable" };
  }

  const missing = warnings.find(
    (item) => item.data.code === "missing_price" || item.data.code === "no_price",
  );
  if (missing) {
    return { grey: true, reason: missing.data.message, code: "missing_price" };
  }

  if (done) {
    const hasFare = legs.some((item) => item.data.price > 0);
    if (!hasFare) {
      return { grey: true, reason: "no priced leg", code: "missing_price" };
    }
  }

  return { grey: false, reason: null, code: null };
}

export function App() {
  const boot = bootShare();
  const [mode, setMode] = useState<ApiMode>(defaultApiMode);
  const [selectedIngredients, setSelectedIngredients] = useState<string[]>(
    boot.ingredients.length > 0 ? boot.ingredients : [...ETALON_INGREDIENTS],
  );
  const [radiusKm, setRadiusKm] = useState<RadiusKm>(boot.radius_km);
  const [placesRes, setPlacesRes] = useState<PlacesResponse | null>(null);
  const [placesError, setPlacesError] = useState<string | null>(null);
  const [placesLoading, setPlacesLoading] = useState(false);
  const [placesNonce, setPlacesNonce] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [cardState, setCardState] = useState<Record<string, CardState>>({});
  const [origin, setOrigin] = useState(boot.origin ?? "Москва");
  const [days, setDays] = useState(boot.days ?? 3);
  const [month, setMonth] = useState(boot.month ?? "2026-10");
  const [adults, setAdults] = useState(boot.adults ?? 1);
  const [childrenAges, setChildrenAges] = useState(boot.children_ages ?? "");
  const [budgetScope, setBudgetScope] = useState<BudgetScope>(
    boot.budget_scope ?? "transport",
  );
  const [sseEvents, setSseEvents] = useState<SseEvent[]>([]);
  const [sseError, setSseError] = useState<string | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [aborted, setAborted] = useState(false);
  const [shareFlash, setShareFlash] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const wantedClusterRef = useRef<string | null>(boot.cluster_id);
  const shareClusterRef = useRef<string | null>(boot.cluster_id);

  const places = placesRes?.places ?? [];
  const fullPlaces = places.filter((place) => place.coverage.missing.length === 0);
  const almostPlaces = places.filter((place) => place.coverage.missing.length > 0);
  const selectedPlace = useMemo(
    () => places.find((place) => place.cluster_id === selectedId) ?? null,
    [places, selectedId],
  );
  const emptyPlaces =
    !placesLoading && selectedIngredients.length > 0 && places.length === 0 && !placesError;
  const shareClusterId = selectedId ?? wantedClusterRef.current;

  useEffect(() => {
    if (selectedIngredients.length === 0) {
      setPlacesRes(null);
      setPlacesError(null);
      setPlacesLoading(false);
      setSelectedId(null);
      return;
    }
    let cancelled = false;
    setPlacesLoading(true);
    setSelectedId(null);
    fetchPlaces(mode, {
      ingredients: selectedIngredients,
      radius_km: radiusKm,
      limit: 20,
    })
      .then((res) => {
        if (cancelled) return;
        setPlacesRes(res);
        setPlacesError(null);
        setCardState({});
        setSseEvents([]);
        setSseError(null);
        setAborted(false);
        const ids = new Set(res.places.map((place) => place.cluster_id));
        const wanted = wantedClusterRef.current;
        setSelectedId(wanted && ids.has(wanted) ? wanted : null);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setPlacesError(err instanceof Error ? err.message : "places failed");
        setPlacesRes(null);
        setSelectedId(null);
      })
      .finally(() => {
        if (!cancelled) setPlacesLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [mode, selectedIngredients, radiusKm, placesNonce]);

  useEffect(() => {
    const next = encodeShare({
      ingredients: selectedIngredients,
      radius_km: radiusKm,
      cluster_id: shareClusterId,
      origin,
      days,
      month,
      adults,
      children_ages: childrenAges || null,
      budget_scope: budgetScope,
    });
    const url = `${window.location.pathname}${next}${window.location.hash}`;
    window.history.replaceState(null, "", url);
  }, [
    selectedIngredients,
    radiusKm,
    selectedId,
    shareClusterId,
    origin,
    days,
    month,
    adults,
    childrenAges,
    budgetScope,
  ]);

  const toggleIngredient = (id: string) => {
    setSelectedIngredients((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id],
    );
  };

  const startPrice = () => {
    if (!selectedPlace) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setStreaming(true);
    setAborted(false);
    setSseEvents([]);
    setSseError(null);
    setCardState({});
    const clusterId = selectedPlace.cluster_id;
    streamPrice(
      mode,
      {
        cluster_id: clusterId,
        origin,
        days,
        month,
        adults,
        children_ages: parseAges(childrenAges),
        budget_scope: budgetScope,
      },
      (event) => {
        setSseEvents((prev) => {
          const next = [...prev, event];
          const grey = routingGreyFromEvents(next);
          setCardState(grey.grey ? { [clusterId]: grey } : {});
          return next;
        });
      },
      controller.signal,
    )
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        if (err instanceof HttpError && err.status === 404) {
          setSseError("404 unknown cluster_id");
          return;
        }
        setSseError(err instanceof Error ? err.message : "price failed");
      })
      .finally(() => {
        setStreaming(false);
      });
  };

  const abortPrice = () => {
    abortRef.current?.abort();
    setStreaming(false);
    setAborted(true);
  };

  const handleSelect = (clusterId: string) => {
    if (streaming) abortPrice();
    wantedClusterRef.current = clusterId;
    setSelectedId(clusterId);
  };

  const copyShare = async () => {
    const href = shareHref({
      ingredients: selectedIngredients,
      radius_km: radiusKm,
      cluster_id: shareClusterId,
      origin,
      days,
      month,
      adults,
      children_ages: childrenAges || null,
      budget_scope: budgetScope,
    });
    const absolute = `${window.location.origin}${href}`;
    try {
      await navigator.clipboard.writeText(absolute);
      setShareFlash(true);
      window.setTimeout(() => setShareFlash(false), 1600);
    } catch {
      setShareFlash(false);
    }
  };

  const unknownFromShare =
    Boolean(shareClusterRef.current) &&
    !placesLoading &&
    places.length > 0 &&
    !places.some((place) => place.cluster_id === shareClusterRef.current) &&
    selectedPlace === null;

  return (
    <div className="app">
      <header className="topbar">
        <div>
          <p className="kicker">инверсия: сначала места, потом origin</p>
          <h1>Бургер</h1>
          <p className="lede">
            Конструктор поездки: интересы и радиус → кластеры без цен → один
            кластер → origin и живой поток маршрута.
          </p>
        </div>
        <div className="topbar-actions">
          <button type="button" className="share-btn" onClick={() => void copyShare()}>
            {shareFlash ? "ссылка скопирована" : "Поделиться"}
          </button>
          <ModeToggle mode={mode} onChange={setMode} />
        </div>
      </header>

      <div className="layout">
        <aside className="rail">
          <IngredientMenu selected={selectedIngredients} onToggle={toggleIngredient} />
          <RadiusSlider
            value={radiusKm}
            totalFound={placesRes?.total_found ?? null}
            onChange={setRadiusKm}
          />
          <CoverageMap
            mode={mode}
            emptyPlaces={emptyPlaces}
            hasIngredients={selectedIngredients.length > 0}
          />
        </aside>

        <main className="main">
          {placesError ? (
            <p className="error">
              {placesError}{" "}
              <button
                type="button"
                className="text-btn"
                onClick={() => setPlacesNonce((n) => n + 1)}
              >
                повторить
              </button>
            </p>
          ) : null}
          {emptyPlaces ? (
            <p className="ingest-hole banner">
              Пустая выдача. Вне залитых областей это дыра ингеста, не отсутствие
              комбинации.
            </p>
          ) : null}
          {unknownFromShare ? (
            <div className="not-found">
              <h3>404</h3>
              <p>cluster_id из ссылки нет в текущей выдаче.</p>
            </div>
          ) : null}

          <div className="stage">
            <PlaceList
              places={fullPlaces}
              selectedId={selectedId}
              cardState={cardState}
              loading={placesLoading}
              hasIngredients={selectedIngredients.length > 0}
              onSelect={handleSelect}
            />
            <ClusterMap place={selectedPlace} />
          </div>

          <AlmostFits
            places={almostPlaces}
            selectedId={selectedId}
            cardState={cardState}
            onSelect={handleSelect}
          />

          <OriginForm
            enabled={selectedPlace != null}
            origin={origin}
            days={days}
            month={month}
            adults={adults}
            childrenAges={childrenAges}
            budgetScope={budgetScope}
            busy={streaming}
            onAbort={abortPrice}
            onOrigin={setOrigin}
            onDays={setDays}
            onMonth={setMonth}
            onAdults={setAdults}
            onChildrenAges={setChildrenAges}
            onBudgetScope={setBudgetScope}
            onSubmit={startPrice}
          />
          <PriceStream
            events={sseEvents}
            error={sseError}
            streaming={streaming}
            aborted={aborted}
            onRetry={startPrice}
          />
        </main>
      </div>
    </div>
  );
}
