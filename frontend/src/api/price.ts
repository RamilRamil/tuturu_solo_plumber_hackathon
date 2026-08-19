import { parseSseStream } from "./sse";
import type { PriceRequest, SseEvent } from "../types/contract";

export class HttpError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function streamLivePrice(
  req: PriceRequest,
  onEvent: (event: SseEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  const res = await fetch("/api/price", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify(req),
    signal,
  });
  if (res.status === 404) {
    throw new HttpError(404, "unknown cluster_id");
  }
  if (!res.ok) {
    throw new HttpError(res.status, `price failed: ${res.status}`);
  }
  if (!res.body) {
    throw new Error("empty SSE body");
  }
  await parseSseStream(res.body, onEvent, signal);
}
