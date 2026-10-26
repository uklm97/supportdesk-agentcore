// Settings are read at run time from /config.json, so the same build works locally and on CloudFront.
// The file is written by scripts/write_web_config.py from the deployed stack outputs (it is git-ignored).

export interface AppConfig {
  region: string;
  userPoolId: string;
  userPoolClientId: string;
  apiUrl: string; // base URL of the HTTP API, for example https://abc123.execute-api.us-east-1.amazonaws.com
}

const REQUIRED: (keyof AppConfig)[] = ["region", "userPoolId", "userPoolClientId", "apiUrl"];

export function parseConfig(raw: unknown): AppConfig {
  if (typeof raw !== "object" || raw === null) {
    throw new Error("config.json is not a JSON object");
  }
  const record = raw as Record<string, unknown>;
  const missing = REQUIRED.filter((key) => typeof record[key] !== "string" || record[key] === "");
  if (missing.length > 0) {
    throw new Error(`config.json is missing: ${missing.join(", ")}`);
  }
  const apiUrl = (record.apiUrl as string).replace(/\/+$/, "");
  return {
    region: record.region as string,
    userPoolId: record.userPoolId as string,
    userPoolClientId: record.userPoolClientId as string,
    apiUrl,
  };
}

export async function loadConfig(): Promise<AppConfig> {
  const response = await fetch("/config.json", { cache: "no-store" });
  if (!response.ok) {
    throw new Error("config.json was not found. Run scripts/write_web_config.py after the deploy.");
  }
  return parseConfig(await response.json());
}
