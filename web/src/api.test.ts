import { describe, expect, it } from "vitest";
import { ApiError, sendChat } from "./api";

function fakeFetch(status: number, body: unknown, seen: { url?: string; init?: RequestInit } = {}) {
  return (async (url: string, init?: RequestInit) => {
    seen.url = url;
    seen.init = init;
    return new Response(typeof body === "string" ? body : JSON.stringify(body), { status });
  }) as unknown as typeof fetch;
}

describe("sendChat", () => {
  it("sends the bearer token and the prompt, and never a customer id", async () => {
    const seen: { url?: string; init?: RequestInit } = {};
    const reply = await sendChat(
      "https://api.test",
      "tok",
      "hello",
      null,
      fakeFetch(200, { response: "Hi!", session_id: "session-abc" }, seen),
    );
    expect(reply).toEqual({ response: "Hi!", sessionId: "session-abc" });
    expect(seen.url).toBe("https://api.test/chat");
    const headers = seen.init?.headers as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer tok");
    expect(JSON.parse(seen.init?.body as string)).toEqual({ prompt: "hello" });
  });

  it("sends the session id on later turns", async () => {
    const seen: { url?: string; init?: RequestInit } = {};
    await sendChat("https://api.test", "tok", "again", "session-abc", fakeFetch(200, { response: "ok", session_id: "session-abc" }, seen));
    expect(JSON.parse(seen.init?.body as string)).toEqual({ prompt: "again", session_id: "session-abc" });
  });

  it("turns a 401 into a sign-in-again error", async () => {
    const promise = sendChat("https://api.test", "tok", "x", null, fakeFetch(401, { message: "Unauthorized" }));
    await expect(promise).rejects.toMatchObject({ status: 401, message: /sign in again/i });
  });

  it("shows the server's message on other errors, and a generic one for non-JSON", async () => {
    await expect(sendChat("u", "t", "x", null, fakeFetch(502, { message: "The assistant is not available right now" }))).rejects.toBeInstanceOf(ApiError);
    await expect(sendChat("u", "t", "x", null, fakeFetch(500, "<html>oops</html>"))).rejects.toThrow(/not available/);
  });

  it("rejects an answer without the expected fields", async () => {
    await expect(sendChat("u", "t", "x", null, fakeFetch(200, { nope: 1 }))).rejects.toThrow(/unexpected/);
  });
});
