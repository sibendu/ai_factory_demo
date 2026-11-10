import { login } from "@/server/auth/actions";
import { localPasswordLoginAllowed } from "@/server/auth/settings";
import { loginErrorMessage } from "@/lib/login-errors";

export const dynamic = "force-dynamic";

export default async function Login({ searchParams }: PageProps<"/login">) {
  const error = (await searchParams).error;
  const allowLocal = localPasswordLoginAllowed();
  const errorMessage = loginErrorMessage(error);

  return <main className="login-page">
    <section className="login-story" aria-labelledby="login-product-name">
      <div className="login-story-content">
        <div className="login-brand" id="login-product-name">
          <span className="login-mark" aria-hidden="true"><i /><i /><i /></span>
        </div>
        <h1>Welcome to AI Factory Demo App</h1>
      </div>
    </section>

    <section className="login-access" aria-labelledby="sign-in-title">
      <div className="login-card">
        <div className="login-card-heading">
        </div>
        {errorMessage && <p className="login-error" role="alert">{errorMessage}</p>}
        <a className="login-submit login-sso" href="/api/auth/azure/login">Sign in with Microsoft <span aria-hidden="true">→</span></a>
        {allowLocal && <p className="login-divider">or use your local account</p>}
        {allowLocal && <form action={login} className="login-form">
          <label htmlFor="username">User ID
            <input id="username" name="username" autoComplete="username" required />
          </label>
          <label htmlFor="password">Password
            <input id="password" name="password" type="password" autoComplete="current-password" required />
          </label>
          <button className="login-submit" type="submit">Sign in <span aria-hidden="true">→</span></button>
        </form>}
        <p className="login-support">Need access? Contact AI Factory <a href="mailto:sibendu.das@philips.com">administrator</a>.</p>
      </div>
    </section>
  </main>;
}
