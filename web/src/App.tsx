import { useEffect, useState } from "react";
import { currentSession, initAuth, signOut, type Session } from "./auth";
import { loadConfig, type AppConfig } from "./config";
import Chat from "./Chat";
import Login from "./Login";

type State =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; config: AppConfig; session: Session | null };

export default function App() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const config = await loadConfig();
        initAuth(config);
        const session = await currentSession();
        if (!cancelled) setState({ kind: "ready", config, session });
      } catch (error) {
        if (!cancelled) setState({ kind: "error", message: error instanceof Error ? error.message : "Could not start" });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (state.kind === "loading") return <main className="card">Loading…</main>;
  if (state.kind === "error") {
    return (
      <main className="card">
        <h1>SupportDesk</h1>
        <p className="error" role="alert">
          {state.message}
        </p>
      </main>
    );
  }

  const { config, session } = state;
  const setSession = (next: Session | null) => setState({ kind: "ready", config, session: next });

  if (!session) return <Login onSignedIn={setSession} />;
  return (
    <Chat
      config={config}
      session={session}
      onSignOut={() => {
        signOut();
        setSession(null);
      }}
      onSessionExpired={() => {
        signOut();
        setSession(null);
      }}
    />
  );
}
