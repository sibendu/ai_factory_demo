import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

vi.mock("server-only", () => ({}));
vi.mock("../server/auth/actions", () => ({ login: vi.fn() }));

import Login from "../app/login/page";

beforeEach(() => {
  vi.stubEnv("ALLOW_LOCAL_PASSWORD_LOGIN", "false");
  for (const key of ["AZURE_AD_TENANT_ID", "AZURE_AD_CLIENT_ID", "AZURE_AD_CLIENT_SECRET", "AZURE_AD_REDIRECT_URI", "AIFACTORY_SESSION_SECRET"]) {
    vi.stubEnv(key, "");
  }
});
afterEach(() => vi.unstubAllEnvs());

async function markup() {
  return renderToStaticMarkup(await Login({ params: Promise.resolve({}), searchParams: Promise.resolve({}) }));
}

describe("login page sign-in choices", () => {
  it("always displays Microsoft sign-in even without Azure settings or local login", async () => {
    const html = await markup();
    expect(html).toContain('href="/api/auth/azure/login"');
    expect(html).toContain("Sign in with Microsoft");
    expect(html).not.toContain('name="username"');
    expect(html).not.toContain("or use your local account");
    expect(html).not.toContain("Sign-in is currently unavailable");
  });
  it("shows the local form and divider alongside Microsoft sign-in when local login is enabled", async () => {
    vi.stubEnv("ALLOW_LOCAL_PASSWORD_LOGIN", "true");
    const html = await markup();
    expect(html).toContain('href="/api/auth/azure/login"');
    expect(html).toContain('name="username"');
    expect(html).toContain('name="password"');
    expect(html).toContain("or use your local account");
  });
});
