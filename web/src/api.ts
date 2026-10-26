// Calls POST /chat on the HTTP API. The body never carries a customer id: the server reads it from the token.

export interface ChatReply {
  response: string;
  sessionId: string;
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

type Fetch = typeof fetch;

export async function sendChat(
  apiUrl: string,
  accessToken: string,
  prompt: string,
  sessionId: string | null,
  fetchImpl: Fetch = fetch,
): Promise<ChatReply> {
  const body: Record<string, string> = { prompt };
  if (sessionId) body.session_id = sessionId;

  const response = await fetchImpl(`${apiUrl}/chat`, {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}`, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  let data: { response?: unknown; session_id?: unknown; message?: unknown } = {};
  try {
    data = await response.json();
  } catch {
    // Not JSON (for example a gateway error page). Fall through to the generic messages below.
  }

  if (!response.ok) {
    const message =
      response.status === 401
        ? "Your session has expired. Please sign in again."
        : typeof data.message === "string"
          ? data.message
          : "The assistant is not available right now.";
    throw new ApiError(message, response.status);
  }
  if (typeof data.response !== "string" || typeof data.session_id !== "string") {
    throw new ApiError("The assistant sent an unexpected answer.", response.status);
  }
  return { response: data.response, sessionId: data.session_id };
}
