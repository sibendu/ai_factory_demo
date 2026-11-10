# Reuse the shared GitHub Actions deployment role

Use the existing role `arn:aws:iam::630634485794:role/github-actions-deploy-role`
and policy `GitHubActionsEcsDeployment` from APR. The workflow authenticates with
GitHub OIDC; it does not need static AWS keys.

## Permissions additions

In **IAM → Policies → GitHubActionsEcsDeployment → Edit → JSON**, merge these
AI Factory additions from [the complete local policy](../deploy/github-actions-deployment-policy.json):

| Existing statement | Addition |
| --- | --- |
| `ReadAndDeploySelectedEcsServices` | `arn:aws:ecs:eu-west-1:630634485794:service/aifactory-cluster/svc_ai_facotry_demo` |
| `ListTasksInSelectedClusters`, `ecs:cluster` condition | `arn:aws:ecs:eu-west-1:630634485794:cluster/aifactory-cluster` |
| `ReadTasksInSelectedClusters` | `arn:aws:ecs:eu-west-1:630634485794:task/aifactory-cluster/*` |

Keep existing resources and save the updated policy as the default version. No
additional image-publishing permissions are needed in AWS for Docker Hub.
Do not replace APR's live DB instance ARN with the placeholder retained in this
source copy. Merge additions rather than replacing newer live policy entries.

## Trust addition

In **IAM → Roles → github-actions-deploy-role → Trust relationships → Edit trust
policy**, retain the existing OIDC provider, audience `sts.amazonaws.com`, and all
existing APR/GALA main-branch subjects. Replace AI Factory's previous main-branch
entry with the subject for the selected GitHub environment `dev`:

```text
repo:sibendu@11136023/ai_factory_demo@1449435525:environment:dev
```

The [complete trust copy](../deploy/github-actions-trust-policy.json) includes
the existing GALA/APR subjects. This repository's GitHub OIDC customization API
was read on 2026-11-09 and reports `use_default: true`, `use_immutable_subject: true`.
Use this immutable subject rather than `repo:sibendu/ai_factory_demo:...`.
The deployment job now declares `environment: dev`; the OIDC subject therefore
ends in `environment:dev`, without the branch. Under **GitHub → Settings →
Environments → dev → Deployment branches and tags**, allow only `main`.

Every trusted repository can exercise the shared role's complete permissions. Use
a separate role if application isolation is needed. The local copies authorize no
automatic IAM changes; apply and review them in AWS separately.

## GitHub settings and first deployment

Set `AWS_ROLE_ARN` and the other variables in the GitHub environment **dev**, plus
the `DOCKERHUB_TOKEN` environment secret, using
[the workflow setup table](../../docs/GITHUB-ACTIONS-ECS.md#github-settings).
An existing repository-level Docker Hub secret can also be used; a secret set in
`dev` takes precedence. Keep the caller's explicit secret mapping in `ci.yml`.
The Docker Hub token must have read/write image access; do not paste it into code,
workflow YAML, or chat. Then push/merge to `main` or manually run **CI** on `main`.

The role needs ECS service describe/update and task list/describe. It does not need
task-definition registration, task execution, `iam:PassRole`, or secret-value reads.
The existing ECS task execution role continues to handle startup and logging.
