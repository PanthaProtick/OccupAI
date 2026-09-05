import { describe, expect, it } from "vitest";
import { env } from "./env";

describe("frontend API origin",()=>{
  it("uses the browser loopback hostname so SameSite auth cookies survive reload",()=>{
    expect(new URL(env.apiBaseUrl).hostname).toBe(window.location.hostname);
  });
});
