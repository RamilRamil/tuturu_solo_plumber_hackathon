import type { SseEvent, SseEventName } from "../types/contract";

const EVENT_NAMES: SseEventName[] = [
  "resolved",
  "leg",
  "hotel",
  "breakdown",
  "checkout",
  "warning",
  "done",
];

function isEventName(value: string): value is SseEventName {
  return (EVENT_NAMES as string[]).includes(value);
}

export async function parseSseStream(
  body: ReadableStream<Uint8Array>,
  onEvent: (event: SseEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const parseBlock = (block: string) => {
    let name: SseEventName = "done";
    const dataLines: string[] = [];
    for (const line of block.split("\n")) {
      if (line.startsWith("event:")) {
        const raw = line.slice(6).trim();
        if (isEventName(raw)) name = raw;
      } else if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).trim());
      }
    }
    if (dataLines.length === 0) return;
    const data = JSON.parse(dataLines.join("\n")) as SseEvent["data"];
    onEvent({ event: name, data } as SseEvent);
  };

  try {
    while (true) {
      if (signal.aborted) break;
      const { done, value } = await reader.read();
      if (done) {
        buffer += decoder.decode();
        break;
      }
      buffer += decoder.decode(value, { stream: true });
      let sep = buffer.indexOf("\n\n");
      while (sep >= 0) {
        const block = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        if (block.trim()) parseBlock(block);
        sep = buffer.indexOf("\n\n");
      }
    }
    if (buffer.trim()) parseBlock(buffer);
  } finally {
    reader.releaseLock();
  }
}
