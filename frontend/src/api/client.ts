import { fetchMockPlaces } from "./places";
import { streamLivePrice } from "./price";
import { emitMockPriceStream } from "../mocks/priceStream";
import type {
  ApiMode,
  PlacesRequest,
  PlacesResponse,
  PriceRequest,
  SseEvent,
} from "../types/contract";

export async function fetchPlaces(
  mode: ApiMode,
  req: PlacesRequest,
): Promise<PlacesResponse> {
  if (mode === "mock") {
    return fetchMockPlaces(req);
  }
  const res = await fetch("/api/places", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    throw new Error(`places failed: ${res.status}`);
  }
  return (await res.json()) as PlacesResponse;
}

export async function streamPrice(
  mode: ApiMode,
  req: PriceRequest,
  onEvent: (event: SseEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  if (mode === "mock") {
    await emitMockPriceStream(req, onEvent, signal);
    return;
  }
  await streamLivePrice(req, onEvent, signal);
}
