# GitHub Actions deployment to the existing ECS service

This follows APR's CI/reusable-deployment workflow pattern, using Docker Hub as
requested. Pull requests and pushes to `main`/`develop` run lint, application tests,
deployment safeguard tests, the production build (including TypeScript validation),
and a production dependency audit. Successful `main` checks call the deployment
workflow. Manual runs use Actions → CI → Run workflow → main, with the same checks.
There are no database migrations or RDS operations in this starter's workflow.

## What gets published and deployed

The root Dockerfile is built once for `linux/amd64`, matching the existing ECS
Linux/X86_64 task. That same image is pushed under two tags:

- `sibendu/aifactorydemo:build-<full-commit-sha>-<run-id>-<attempt>`
- `sibendu/aifactorydemo:latest`

The workflow reads both remote manifest digests and requires them to match. Docker
Hub may show both tags on the same image; these are two references to one build.
Build layers are cached through GitHub Actions. No application secrets are passed
to Docker builds. Existing runtime secrets and environment settings remain in ECS.

Before publishing, the service must be stable, active, use the ECS deployment
controller, have a positive desired count, and have a running container named
`Main` using `sibendu/aifactorydemo:latest`. The selected task-definition ARN is
recorded. A changed revision or wrong container/image fails the workflow.

Deployment calls only:

```bash
aws ecs update-service --cluster "$ECS_CLUSTER" --service "$ECS_SERVICE" --force-new-deployment
aws ecs wait services-stable --cluster "$ECS_CLUSTER" --services "$ECS_SERVICE"
```

It does not register a task definition or pass a task-definition override. After
the wait, it requires the requested deployment ID to be PRIMARY/COMPLETED, the
original task-definition ARN to be unchanged, and every running application
container to use the published digest. A rollback to an old deployment cannot
report success. A failing ECS wait reports failure; check service events before
rerunning. The AWS waiter has an approximately ten-minute limit.

Deployment jobs are serialized without cancelling a running deployment. Superseded
main commits are rejected before building and before publishing. This lock is
repository-local: coordinate other publishers and manual deployments separately.

## GitHub settings

In **sibendu/ai_factory_demo → Settings → Secrets and variables → Actions**, add
these repository **Variables**:

| Variable | Value |
| --- | --- |
| `AWS_ACCOUNT_ID` | `630634485794` |
| `AWS_REGION` | `eu-west-1` |
| `AWS_ROLE_ARN` | `arn:aws:iam::630634485794:role/github-actions-deploy-role` |
| `ECS_CLUSTER` | `aifactory-cluster` |
| `ECS_SERVICE` | `svc_ai_facotry_demo` |
| `ECS_CONTAINER_NAME` | `Main` |
| `DOCKERHUB_USERNAME` | `sibendu` |
| `DOCKERHUB_REPOSITORY` | `sibendu/aifactorydemo` (also the workflow default) |

Add this repository **Secret**:

| Secret | Value |
| --- | --- |
| `DOCKERHUB_TOKEN` | Docker Hub personal access token with read/write access to `sibendu/aifactorydemo` |

Use a Docker Hub token, not an account password. Keep build tags for rollback and
allow the `latest` tag to be overwritten. The initial workflow assumes the working
service already pulls that exact image reference; it never switches registries.

## AWS OIDC access

Reuse APR's `github-actions-deploy-role` and its GitHub OIDC provider. Reconcile the
local shared files in [extensions/deploy](../extensions/deploy/) with the live IAM
policy and trust, preserving any newer application entries. These files do not
modify AWS. No static AWS access-key secrets are needed.

This repository's OIDC settings were read on 2026-11-09. They use an immutable
subject, so its main-branch trust entry is:

```text
repo:sibendu@11136023/ai_factory_demo@1449435525:ref:refs/heads/main
```

The audience is `sts.amazonaws.com`. The workflow deliberately uses no GitHub
Environment, which would change the subject. The deployment permission additions
are ECS service describe/update and task list/describe for this project's exact
service and cluster. No ECR, task-definition registration, `RunTask`, `iam:PassRole`,
secret-value access, or new infrastructure permission is needed for this app.

The complete copied policy retains APR/GALA entries, including APR's existing RDS
placeholder. If applying the complete document, retain the actual live APR DB ARN
instead of overwriting it with the placeholder. Prefer merging the new AI Factory
entries into the existing policy. See the [IAM setup instructions](../extensions/md/AWS-IAM-GITHUB-ACTIONS.md).

## First run

1. Configure the variables, Docker Hub secret, and shared IAM additions above.
2. Confirm the existing service is healthy and uses `sibendu/aifactorydemo:latest`.
3. Push/merge the workflows to `main`, or manually run **CI** on `main`.
4. Check the Actions summary for both tags, the digest, and verified deployment.
5. Confirm the ALB target is healthy and sign-in works. Its health check remains
   HTTP `/login` on traffic port 3000, with success code 200.

No live IAM settings, repository variables/secrets, or ECS resources are updated
merely by adding these files. No workflow is dispatched during local preparation.

## Rollback

Pause competing deployments, pull a retained build tag, retag it as
`sibendu/aifactorydemo:latest`, push it, then force a deployment of the existing
service. Keep the same task definition and verify running image digests. An ECS
automatic rollback does not move Docker Hub's `latest` tag back; resolve the image
or retag it before retrying. Never delete the working task definition for a rollback.

References: [AWS same-tag service deployment](https://docs.aws.amazon.com/cli/latest/reference/ecs/update-service.html),
[Docker Hub authentication](https://docs.docker.com/security/access-tokens/),
[GitHub OIDC with AWS](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws).
