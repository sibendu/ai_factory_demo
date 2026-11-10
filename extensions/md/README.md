# Shared AWS deployment package

This project follows APR's convention of carrying complete local copies of the
shared AWS deployment policy and GitHub OIDC trust under `extensions/deploy/`.

The copies preserve APR/GALA entries and add:

- ECS service `aifactory-cluster/svc_ai_facotry_demo`.
- Task listing and description for `aifactory-cluster`.
- The OIDC subject for `sibendu/ai_factory_demo` using GitHub environment `dev`.

This application publishes to Docker Hub, so it adds no ECR or RDS permissions.
The existing shared AWS role is `github-actions-deploy-role`, and the permissions
policy is `GitHubActionsEcsDeployment`. Local files do not update AWS.

Reconcile new entries with the live policy/trust before use. Preserve any newer
application entries and APR's real RDS instance ARN in place of the inherited
placeholder. APR's source folder was used read-only; its copies were not changed.
Reconcile copies back into other projects when updating their deployment package.

See [manual IAM setup](AWS-IAM-GITHUB-ACTIONS.md) and
[workflow settings](../../docs/GITHUB-ACTIONS-ECS.md).
