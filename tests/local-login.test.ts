import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const state = vi.hoisted(() => ({ cookie: undefined as string | undefined, set: vi.fn() }));
vi.mock("server-only", () => ({}));
vi.mock("next/headers", () => ({ cookies: async () => ({
  get: () => state.cookie ? { value: state.cookie } : undefined,
  set: (name: string, value: string, options: unknown) => { state.cookie = value; state.set(name, value, options); },
}) }));
vi.mock("next/navigation", () => ({ redirect: (url: string) => { throw new Error("REDIRECT:" + url); } }));

import { login } from "../server/auth/actions";
import { hasSession } from "../server/auth/session";
import { authenticateLocalUser } from "../server/auth/local-users";

beforeEach(() => {
  vi.stubEnv("NODE_ENV", "production");
  vi.stubEnv("ALLOW_LOCAL_PASSWORD_LOGIN", "true");
  vi.stubEnv("AUTH_USER", "admin");
  vi.stubEnv("AUTH_PASSWORD", "admin");
  vi.stubEnv("AIFACTORY_SESSION_SECRET", "test-session-secret-at-least-32-characters");
  vi.stubEnv("NEXTAUTH_URL", "http://localhost:3000");
  state.cookie = undefined;
  state.set.mockClear();
});
afterEach(() => vi.unstubAllEnvs());

function credentials(username = "admin", password = "admin") {
  const form = new FormData();
  form.set("username", username); form.set("password", password);
  return form;
}

describe("environment-only local login", () => {
  it("signs in with AUTH_USER/AUTH_PASSWORD and maintains a session in the local Docker configuration", async () => {
    await expect(login(credentials())).rejects.toThrow("REDIRECT:/");
    expect(await hasSession()).toBe(true);
    expect(state.set).toHaveBeenCalledWith("einvoice_demo_session", expect.any(String),
      expect.objectContaining({ httpOnly: true, secure: false, sameSite: "lax" }));
    vi.stubEnv("AUTH_USER", "replacement");
    expect(await hasSession()).toBe(false);
  });
  it.each([["admin", "wrong"], ["wrong", "admin"], ["admin", ""], ["", "admin"]])("rejects invalid credentials %s", async (username, password) => {
    await expect(login(credentials(username, password))).rejects.toThrow("REDIRECT:/login?error=invalid");
    expect(state.set).not.toHaveBeenCalled();
  });
  it.each(["AUTH_USER", "AUTH_PASSWORD"])("has no default account when %s is missing", name => {
    vi.stubEnv(name, "");
    expect(authenticateLocalUser("admin", "admin")).toBeNull();
  });
  it("disables login and existing sessions when local login is disabled", async () => {
    await expect(login(credentials())).rejects.toThrow("REDIRECT:/");
    vi.stubEnv("ALLOW_LOCAL_PASSWORD_LOGIN", "false");
    expect(await hasSession()).toBe(false);
    await expect(login(credentials())).rejects.toThrow("REDIRECT:/login?error=local_disabled");
  });
  it("keeps cookies secure for a deployed HTTPS URL", async () => {
    vi.stubEnv("NEXTAUTH_URL", "https://app.example.com");
    await expect(login(credentials())).rejects.toThrow("REDIRECT:/");
    expect(state.set).toHaveBeenCalledWith("einvoice_demo_session", expect.any(String), expect.objectContaining({ secure: true }));
  });
});
