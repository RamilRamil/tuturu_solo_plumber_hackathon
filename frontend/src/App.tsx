import { useEffect, useMemo, useRef, useState } from "react";
import { fetchPlaces, streamPrice } from "./api/client";
import { HttpError } from "./mocks/priceStream";
import { ClusterMap } from "./components/ClusterMap";
import { IngredientMenu } from "./components/IngredientMenu";
import { ModeToggle } from "./components/ModeToggle";
import { OriginForm } from "./components/OriginForm";
import { PlaceList } from "./components/PlaceList";
import { PriceStream } from "./components/PriceStream";
import { RadiusSlider } from "./components/RadiusSlider";
import { DEFAULT_RADIUS, ETALON_INGREDIENTS, ETALON_PAIR_ID } from "./ids";
import type {
  ApiMode,
  BudgetScope,
  PlacesResponse,
  RadiusKm,
  SseEvent,
} from "./types/contract";

type CardState = { grey: boolean; reason: string | null };

function parseAges(raw: string): number[] {
  return raw
    .split(",")
    .map((part) => Number(part.trim()))
    .filter((n) => Number.isFinite(n) && n > 0);
}

function sameBurger(a: string[], b: readonly string[]): boolean {
  if (a.length !== b.length) return false;
  const left = [...a].sort();
  const right = [...b].sort();
  return left.every((id, i) => id === right[i]);
}

export function App() {
  const [mode, setMode] = useState<ApiMode>("mock");
  const [selectedIngredients, setSelectedIngredients] = useState<string[]>([
    "ancient_temple",
    "industrial_museum",
  ]);
  const [radiusKm, setRadiusKm] = useState<RadiusKm>(DEFAULT_RADIUS);
  const [placesRes, setPlacesRes] = useState<PlacesResponse | null>(null);
  const [placesError, setPlacesError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [cardState, setCardState] = useState<Record<string, CardState>>({});
  const [origin, setOrigin] = useState("Москва");
  const [days, setDays] = useState(3);
  const [month, setMonth] = useState("2026-10");
  const [adults, setAdults] = useState(1);
  const [childrenAges, setChildrenAges] = useState("");
  const [budgetScope, setBudgetScope] = useState<BudgetScope>("transport");
  const [sseEvents, setSseEvents] = useState<SseEvent[]>([]);
  const [sseError, setSseError] = useState<string | null>(null);
  const [streaming, setStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const places = placesRes?.places ?? [];
  const selectedPlace = useMemo(
    () => places.find((place) => place.cluster_id === selectedId) ?? null,
    [places, selectedId],
  );
  const etalonCombo = sameBurger(selectedIngredients, ETALON_INGREDIENTS);
  const pairInList = places.some((place) => place.cluster_id === ETALON_PAIR_ID);
  const pairIndex = places.findIndex((place) => place.cluster_id === ETALON_PAIR_ID);

  useEffect(() => {
    if (selectedIngredients.length === 0) {
      setPlacesRes(null);
      setPlacesError(null);
      setSelectedId(null);
      return;
    }
    let cancelled = false;
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
        setSelectedId((prev) =>
          prev && res.places.some((place) => place.cluster_id === prev) ? prev : null,
        );
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setPlacesError(err instanceof Error ? err.message : "places failed");
        setPlacesRes(null);
      });
    return () => {
      cancelled = true;
    };
  }, [mode, selectedIngredients, radiusKm]);

  const toggleIngredient = (id: string) => {
    setSelectedIngredients((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id],
    );
  };

  const startPrice = () => {
    if (!selectedId) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setStreaming(true);
    setSseEvents([]);
    setSseError(null);
    setCardState((prev) => {
      const next: Record<string, CardState> = { ...prev };
      for (const place of places) {
        if (place.cluster_id === selectedId) continue;
        if (place.hubs.some((hub) => hub.probe_status === "not_sellable")) {
          next[place.cluster_id] = { grey: true, reason: "дальше своим ходом" };
        } else if (place.cluster_id !== selectedId && place.hubs.length === 1) {
          next[place.cluster_id] = { grey: true, reason: "no_route от origin" };
        }
      }
      return next;
    });
    streamPrice(
      mode,
      {
        cluster_id: selectedId,
        origin,
        days,
        month,
        adults,
        children_ages: parseAges(childrenAges),
        budget_scope: budgetScope,
      },
      (event) => {
        setSseEvents((prev) => [...prev, event]);
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
        if (!controller.signal.aborted) setStreaming(false);
      });
  };

  return (
    <div className="app">
      <header className="topbar">
        <div>
          <p className="kicker">инверсия: сначала места, потом origin</p>
          <h1>Бургер</h1>
        </div>
        <ModeToggle mode={mode} onChange={setMode} />
      </header>

      <IngredientMenu selected={selectedIngredients} onToggle={toggleIngredient} />
      <RadiusSlider
        value={radiusKm}
        totalFound={placesRes?.total_found ?? null}
        onChange={setRadiusKm}
      />

      {placesError ? <p className="error">{placesError}</p> : null}
      {etalonCombo && pairInList ? (
        <p className="hint">
          SC-D2: список не сортируется. Пара «Ярославль и Ростов Великий» в ответе
          {pairIndex >= 5 ? " ниже пятого" : ` на месте ${pairIndex + 1}`}. Для SSE кликните
          карточку пары, даже если выше одиночный Ярославль.
        </p>
      ) : null}

      <div className="stage">
        <PlaceList
          places={places}
          selectedId={selectedId}
          cardState={cardState}
          onSelect={setSelectedId}
        />
        <ClusterMap place={selectedPlace} />
      </div>

      <OriginForm
        enabled={Boolean(selectedPlace)}
        origin={origin}
        days={days}
        month={month}
        adults={adults}
        childrenAges={childrenAges}
        budgetScope={budgetScope}
        busy={streaming}
        onOrigin={setOrigin}
        onDays={setDays}
        onMonth={setMonth}
        onAdults={setAdults}
        onChildrenAges={setChildrenAges}
        onBudgetScope={setBudgetScope}
        onSubmit={startPrice}
      />
      <PriceStream events={sseEvents} error={sseError} />
    </div>
  );
}
