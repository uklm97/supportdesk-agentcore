import {
  AuthenticationDetails,
  CognitoUser,
  CognitoUserPool,
  type CognitoUserSession,
} from "amazon-cognito-identity-js";
import type { AppConfig } from "./config";

// The Cognito library keeps the tokens in the browser's localStorage and refreshes them
// with the refresh token. We send the ACCESS token to the API (the runtime checks its client_id claim).

export class NewPasswordRequiredError extends Error {
  constructor() {
    super("This account must set a new password first. Ask an admin to reset it.");
  }
}

export interface Session {
  email: string;
  accessToken: string;
}

let pool: CognitoUserPool | null = null;

export function initAuth(config: AppConfig): void {
  pool = new CognitoUserPool({ UserPoolId: config.userPoolId, ClientId: config.userPoolClientId });
}

function requirePool(): CognitoUserPool {
  if (!pool) throw new Error("Auth is not initialised");
  return pool;
}

function toSession(email: string, session: CognitoUserSession): Session {
  return { email, accessToken: session.getAccessToken().getJwtToken() };
}

export function signIn(email: string, password: string): Promise<Session> {
  const user = new CognitoUser({ Username: email, Pool: requirePool() });
  const details = new AuthenticationDetails({ Username: email, Password: password });
  return new Promise((resolve, reject) => {
    user.authenticateUser(details, {
      onSuccess: (session) => resolve(toSession(email, session)),
      onFailure: (error: { message?: string }) => reject(new Error(error.message ?? "Sign in failed")),
      newPasswordRequired: () => reject(new NewPasswordRequiredError()),
    });
  });
}

/** The signed-in user from a previous visit, or null. getSession refreshes an expired access token. */
export function currentSession(): Promise<Session | null> {
  const user = requirePool().getCurrentUser();
  if (!user) return Promise.resolve(null);
  return new Promise((resolve) => {
    user.getSession((error: Error | null, session: CognitoUserSession | null) => {
      if (error || !session || !session.isValid()) {
        resolve(null);
        return;
      }
      resolve(toSession(user.getUsername(), session));
    });
  });
}

export function signOut(): void {
  requirePool().getCurrentUser()?.signOut();
}
