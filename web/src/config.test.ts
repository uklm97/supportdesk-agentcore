import { describe, expect, it } from "vitest";
import { parseConfig } from "./config";

const good = {
  region: "us-east-1",
  userPoolId: "us-east-1_abc",
  userPoolClientId: "client123",
  apiUrl: "https://x.execute-api.us-east-1.amazonaws.com/",
};

describe("parseConfig", () => {
  it("accepts a full config and trims the trailing slash of the API url", () => {
    expect(parseConfig(good).apiUrl).toBe("https://x.execute-api.us-east-1.amazonaws.com");
  });

  it("names the missing fields", () => {
    expect(() => parseConfig({ region: "us-east-1" })).toThrow(/userPoolId, userPoolClientId, apiUrl/);
  });

  it("rejects empty strings and non-objects", () => {
    expect(() => parseConfig({ ...good, apiUrl: "" })).toThrow(/apiUrl/);
    expect(() => parseConfig(null)).toThrow(/not a JSON object/);
    expect(() => parseConfig("text")).toThrow(/not a JSON object/);
  });
});
