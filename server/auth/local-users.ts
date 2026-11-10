import "server-only";
import { createHash, timingSafeEqual } from "node:crypto";
import { localPasswordLoginAllowed } from "./settings";

export function configuredLocalUser() {
  const email = process.env.AUTH_USER?.trim().toLowerCase();
  if (!localPasswordLoginAllowed() || !email || !process.env.AUTH_PASSWORD) return null;
  return { email, displayName: process.env.AUTH_USER!.trim() };
}

export function authenticateLocalUser(username: string, password: string) {
  const user = configuredLocalUser();
  if (!user) return null;
  const digest = (value: string) => createHash("sha256").update(value).digest();
  const validPassword = timingSafeEqual(digest(password), digest(process.env.AUTH_PASSWORD!));
  return username.trim().toLowerCase() === user.email && validPassword ? user : null;
}

