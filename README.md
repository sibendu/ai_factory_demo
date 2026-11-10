# A Basic Web App for Demonstration of Autonomous Software Development Factory

A simple Next.js application showcasing

* a UI backend-for-frontend (BFF)
* SSO Login with Azure AD
* a separate Entra OAuth integration boundary
* Simple database connection to PostgreSQL. Though no database is required by this starter, but it is ready
* Allow local login

This is meant to serve as a seed.


## Docker login configuration

Local login uses only runtime environment variables: `ALLOW_LOCAL_PASSWORD_LOGIN=true`,
`AUTH_USER`, `AUTH_PASSWORD`, and `AIFACTORY_SESSION_SECRET` (at least 32 characters).
There is no account file or default account. `config/users.local.json` and
`EINVOICE_USERS_FILE` are not used. Supply the values with Docker's `--env-file`.
Use unquoted `NAME=value` lines for Docker env files.

For local testing of the production Docker image, set these additional values:

```dotenv
NEXTAUTH_URL=http://localhost:3000
AZURE_AD_REDIRECT_URI=http://localhost:3000/api/auth/azure/callback
```

The Microsoft sign-in button is always displayed. Only local password login is
controlled by `ALLOW_LOCAL_PASSWORD_LOGIN`. Completing Azure sign-in requires `AZURE_AD_TENANT_ID`, `AZURE_AD_CLIENT_ID`, and
`AZURE_AD_CLIENT_SECRET`. Register the exact callback URI as a Web redirect URI
in the Azure application. HTTP callbacks and cookies are supported automatically
for localhost, 127.0.0.1, and ::1, including production Docker builds. Other hosts
require HTTPS. No SSO enable flag is needed; `AIFACTORY_ALLOW_LOCAL_HTTP` is no
longer used.
Use the same browser hostname as the redirect URI throughout sign-in.

```bash
docker build --platform linux/amd64 -t sibendu/aifactorydemo:latest .
docker run --rm --name aifactorydemo -p 3000:3000 --env-file .env.local sibendu/aifactorydemo:latest
```

For ECS, use the public HTTPS URL for
`NEXTAUTH_URL`, and use its `/api/auth/azure/callback` URL for the Azure redirect.
Keep the session signing key consistent across ECS tasks. Secrets are supplied
at runtime, not copied into the image.

## CI/CD with GitHub Actions

Pull requests and pushes run lint, tests, a production build, and a production
dependency audit. Successful `main` checks publish the same Docker image as a
unique build tag and `sibendu/aifactorydemo:latest`, then force and verify deployment
of the existing ECS service using its existing task definition. Setup and rollback
instructions are in [the GitHub Actions deployment guide](docs/GITHUB-ACTIONS-ECS.md).
