import { useEffect, useRef, useState, type FormEvent } from "react";
import { ApiError, sendChat } from "./api";
import type { Session } from "./auth";
import type { AppConfig } from "./config";

interface Message {
  role: "user" | "assistant";
  text: string;
}

interface Props {
  config: AppConfig;
  session: Session;
  onSignOut: () => void;
  onSessionExpired: () => void;
}

export default function Chat({ config, session, onSignOut, onSessionExpired }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottom.current?.scrollIntoView?.({ behavior: "smooth" });
  }, [messages, busy]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const prompt = draft.trim();
    if (!prompt || busy) return;
    setDraft("");
    setError(null);
    setBusy(true);
    setMessages((previous) => [...previous, { role: "user", text: prompt }]);
    try {
      const reply = await sendChat(config.apiUrl, session.accessToken, prompt, sessionId);
      setSessionId(reply.sessionId);
      setMessages((previous) => [...previous, { role: "assistant", text: reply.response }]);
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 401) {
        onSessionExpired();
        return;
      }
      setError(failure instanceof Error ? failure.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="card chat">
      <header>
        <h1>SupportDesk</h1>
        <span className="muted">{session.email}</span>
        <button type="button" className="link" onClick={onSignOut}>
          Sign out
        </button>
      </header>
      <section className="messages" aria-live="polite">
        {messages.length === 0 && <p className="muted">Ask about your orders, for example: “Where is my latest order?”</p>}
        {messages.map((message, index) => (
          <p key={index} className={`bubble ${message.role}`}>
            {message.text}
          </p>
        ))}
        {busy && <p className="bubble assistant muted">Thinking…</p>}
        <div ref={bottom} />
      </section>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <form onSubmit={submit} className="composer">
        <input
          aria-label="Message"
          value={draft}
          maxLength={2000}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Type your question"
        />
        <button type="submit" disabled={busy || draft.trim() === ""}>
          Send
        </button>
      </form>
    </main>
  );
}
