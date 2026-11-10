import "server-only";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { configuredLocalUser } from "./local-users";
import { entraTenant, isGuid, localPasswordLoginAllowed, secureAuthCookie } from "./settings";
import { cookieOptions, readCookie, signCookie } from "./signed-cookie";

export const SESSION_COOKIE = "einvoice_demo_session";
const SESSION_LIFETIME_MS = 8 * 60 * 60 * 1000;

export function createSession(email: string) {
  return signCookie("ui-session", { provider: "local", email }, SESSION_LIFETIME_MS);
}

export function createAzureSession(tenant: string, objectId: string) {
  return signCookie("ui-session", { provider: "azure", tenant, objectId }, SESSION_LIFETIME_MS);
}

export async function setSession(value: string, publicUrl = process.env.NEXTAUTH_URL) {
  (await cookies()).set(SESSION_COOKIE, value, {
    ...cookieOptions,
    secure: secureAuthCookie(publicUrl),
    maxAge: SESSION_LIFETIME_MS / 1000,
  });
}

async function currentUser(): Promise<string | null> {
  const session = readCookie("ui-session", (await cookies()).get(SESSION_COOKIE)?.value);
  if (!session) return null;
  if (session.provider === "azure") {
    const tenant = entraTenant(process.env.AZURE_AD_TENANT_ID);
    return tenant && session.tenant === tenant && isGuid(session.objectId) ? `${tenant}:${session.objectId}` : null;
  }
  if (session.provider !== "local" || !localPasswordLoginAllowed() || typeof session.email !== "string") return null;
  try {
    const email = session.email.toLowerCase();
    const user = configuredLocalUser();
    return user?.email === email ? user.email : null;
  } catch { return null; }
}

export async function requireSession() {
  const user = await currentUser();
  if (!user) redirect("/login");
  return user;
}

export async function hasSession() {
  return Boolean(await currentUser());
}
