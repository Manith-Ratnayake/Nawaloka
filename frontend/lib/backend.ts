export type BackendChatResponse = {
  message: string;
};

export async function callBackend(
  message: string,
  model: string
): Promise<BackendChatResponse> {
  const backendUrl = process.env.BACKEND_URL;

  if (!backendUrl) {
    throw new Error("BACKEND_URL is not configured");
  }

  const response = await fetch(`${backendUrl}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, model }),
    cache: "no-store",
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      `Backend request failed: ${response.status} ${errorText}`
    );
  }

  return response.json();
}
