import { useEffect, useMemo, useRef, useState } from "react";
import { fetchPlaces, streamPrice } from "./api/client";
import { HttpError } from "./api/price";
import { AlmostFits } from "./components/AlmostFits";
import { ClusterMap } from "./components/ClusterMap";
import { CoverageMap } from "./components/CoverageMap";
import { IngredientMenu } from "./components/IngredientMenu";
import { OriginForm } from "./components/OriginForm";
import { PlaceDetails } from "./components/PlaceDetails";
import { PlaceList } from "./components/PlaceList";
import { PriceStream } from "./components/PriceStream";
import { RadiusSlider } from "./components/RadiusSlider";
import { noRouteRecovered } from "./format";
import { DEFAULT_RADIUS, ETALON_INGREDIENTS } from "./ids";
import { encodeShare, parseShare, shareHref, type ShareState } from "./share";
import type {
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
    fetchPlaces({
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
        if (wanted && ids.has(wanted)) {
          setSelectedId(wanted);
          return;
        }
        const firstFull = res.places.find((place) => place.coverage.missing.length === 0);
        const pick = firstFull ?? res.places[0];
        setSelectedId(pick ? pick.cluster_id : null);
        if (pick) wantedClusterRef.current = pick.cluster_id;
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
  }, [selectedIngredients, radiusKm, placesNonce]);

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
    !places.some((place) => place.cluster_id === shareClusterRef.current);

  return (
    <div className="app">
      <header className="topbar">
        <div>
          <p className="kicker">сначала места, потом город выезда</p>
          <h1>Бургер</h1>
          <p className="lede">
            Конструктор поездки: интересы и радиус → кластеры без цен → один
            кластер → откуда едете и живой поток маршрута.
          </p>
        </div>
        <div className="topbar-actions">
          <button type="button" className="share-btn" onClick={() => void copyShare()}>
            {shareFlash ? "ссылка скопирована" : "Поделиться"}
          </button>
        </div>
      </header>

      <div className="layout">
        <aside className="rail">
          <IngredientMenu
            selected={selectedIngredients}
            onToggle={toggleIngredient}
            radiusKm={radiusKm}
            onParsed={(ingredients, parsedRadius) => {
              setSelectedIngredients(ingredients);
              if (parsedRadius) setRadiusKm(parsedRadius);
            }}
          />
          <RadiusSlider
            value={radiusKm}
            totalFound={placesRes?.total_found ?? null}
            onChange={setRadiusKm}
          />
          <CoverageMap
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
              Пустая выдача. Вне залитых областей это дыра в данных, не отсутствие
              комбинации.
            </p>
          ) : null}
          {unknownFromShare ? (
            <div className="not-found">
              <h3>404</h3>
              <p>Этого места нет в текущей выдаче.</p>
            </div>
          ) : null}

          <div className={selectedPlace ? "stage has-selection" : "stage"}>
            <PlaceList
              places={fullPlaces}
              selectedId={selectedId}
              cardState={cardState}
              loading={placesLoading}
              hasIngredients={selectedIngredients.length > 0}
              onSelect={handleSelect}
            />
            <div className="stage-mid">
              <ClusterMap place={selectedPlace} />
              <PlaceDetails place={selectedPlace} />
            </div>
            {selectedPlace ? (
              <div className="stage-price">
                <OriginForm
                  enabled
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
              </div>
            ) : null}
          </div>

          <AlmostFits
            places={almostPlaces}
            selectedId={selectedId}
            cardState={cardState}
            onSelect={handleSelect}
          />
        </main>
      </div>
    </div>
  );
}
