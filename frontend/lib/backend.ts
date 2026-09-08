export type BackendChatResult = {
  message: string;
  debug?: unknown;
};

export type BackendProgressEvent = {
  phase: "router" | "vector" | "sql" | "answer";
  message: string;
  modelId?: string;
  modelName?: string;
};

type BackendDoneEvent = {
  phase: "done";
  message: string;
  debug?: unknown;
};

type BackendErrorEvent = {
  phase: "error";
  error: string;
  status?: number;
};

type BackendStreamEvent =
  | BackendProgressEvent
  | BackendDoneEvent
  | BackendErrorEvent;

export type HistoryMessage = {
  role: "user" | "assistant";
  content: string;
};

export async function callBackend(
  message: string,
  model: string,
  onProgress?: (event: BackendProgressEvent) => void,
  history: HistoryMessage[] = [],
  sessionId?: string,
): Promise<BackendChatResult> {
  const backendUrl = process.env.BACKEND_URL;

  if (!backendUrl) {
    throw new Error("BACKEND_URL is not configured");
  }

  const response = await fetch(`${backendUrl}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      model,
      history,
      session_id: sessionId ?? null,
    }),
    cache: "no-store",
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => "");
    throw new Error(
      `Backend request failed: ${response.status} ${errorText}`
    );
  }

  if (!response.body) {
    throw new Error("Backend response had no body to stream");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalResult: BackendChatResult | null = null;

  const handleLine = (line: string) => {
    const trimmed = line.trim();
    if (!trimmed) {
      return;
    }

    const event = JSON.parse(trimmed) as BackendStreamEvent;

    if (event.phase === "error") {
      throw new Error(event.error);
    }

    if (event.phase === "done") {
      finalResult = { debug: event.debug, message: event.message };
      return;
    }

    onProgress?.(event);
  };

  try {
    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        handleLine(line);
      }
    }

    buffer += decoder.decode();
    if (buffer.trim()) {
      handleLine(buffer);
    }
  } finally {
    reader.releaseLock();
  }

  if (!finalResult) {
    throw new Error("Backend stream ended without a final response");
  }

  return finalResult;
}