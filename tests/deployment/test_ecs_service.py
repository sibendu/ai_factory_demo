"""Regression checks for deployment identity, image matching, and rollback rejection."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "ecs_service", Path(__file__).resolve().parents[2] / "scripts/deploy/ecs_service.py",
)
ecs = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ecs)
DIGEST = "sha256:" + "a" * 64
TASKDEF = "arn:aws:ecs:eu-west-1:630634485794:task-definition/taskdef_ai_facotry_demo:1"


def healthy_service(deployment="ecs-svc/new"):
    return {
        "status": "ACTIVE", "taskDefinition": TASKDEF, "desiredCount": 1,
        "runningCount": 1, "pendingCount": 0, "deploymentController": {"type": "ECS"},
        "deployments": [{"id": deployment, "status": "PRIMARY", "rolloutState": "COMPLETED", "taskDefinition": TASKDEF}],
    }


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.settings = {"ECS_CLUSTER": "aifactory-cluster", "ECS_SERVICE": "svc_ai_facotry_demo",
                         "ECS_CONTAINER_NAME": "Main", "DOCKERHUB_REPOSITORY": "sibendu/aifactorydemo"}

    def test_successful_aws_wait_has_no_json_output(self):
        with patch.object(ecs.subprocess, "run", return_value=ecs.subprocess.CompletedProcess([], 0, stdout="", stderr="")):
            self.assertIsNone(ecs.aws("wait", "services-stable"))

    def test_rejects_rollback_even_when_service_is_stable(self):
        with self.assertRaises(ValueError):
            ecs.verify_completed(healthy_service("ecs-svc/old"), TASKDEF, "ecs-svc/new")

    def test_rejects_task_definition_change(self):
        selected = healthy_service()
        selected["taskDefinition"] = TASKDEF[:-1] + "2"
        with self.assertRaises(ValueError):
            ecs.verify_completed(selected, TASKDEF)

    def test_rejects_failed_or_incomplete_rollout(self):
        for state in ("FAILED", "IN_PROGRESS"):
            selected = healthy_service()
            selected["deployments"][0]["rolloutState"] = state
            with self.subTest(state=state), self.assertRaises(ValueError):
                ecs.verify_completed(selected, TASKDEF)

    def test_checks_named_application_and_published_digest(self):
        container = {"name": "Main", "lastStatus": "RUNNING", "image": "docker.io/sibendu/aifactorydemo:latest", "imageDigest": DIGEST}
        response = {"tasks": [{"lastStatus": "RUNNING", "taskDefinitionArn": TASKDEF, "containers": [container]}]}
        with patch.object(ecs, "aws", side_effect=[["task-1"], response]):
            self.assertEqual(ecs.verify_tasks(self.settings, TASKDEF, DIGEST), 1)
        for field, value in (("imageDigest", "sha256:" + "b" * 64), ("image", "other/app:latest"), ("name", "sidecar")):
            changed = dict(container, **{field: value})
            bad = {"tasks": [{"lastStatus": "RUNNING", "taskDefinitionArn": TASKDEF, "containers": [changed]}]}
            with self.subTest(field=field), patch.object(ecs, "aws", side_effect=[["task-1"], bad]), self.assertRaises(ValueError):
                ecs.verify_tasks(self.settings, TASKDEF, DIGEST)

    def test_deploy_only_forces_existing_service_and_checks_result(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = dict(self.settings, RUNNER_TEMP=directory, EXPECTED_IMAGE_DIGEST=DIGEST,
                            GITHUB_STEP_SUMMARY=str(Path(directory) / "summary.md"))
            (Path(directory) / "aifactory-ecs-deployment.json").write_text(json.dumps({"task_definition": TASKDEF}))
            with patch.object(ecs, "service", return_value=healthy_service()), patch.object(ecs, "verify_tasks", return_value=1) as tasks, patch.object(ecs, "aws", side_effect=["ecs-svc/new", None]) as commands:
                ecs.run("deploy", settings)
                self.assertEqual(commands.call_args_list[0].args, (
                    "update-service", "--cluster", "aifactory-cluster", "--service", "svc_ai_facotry_demo",
                    "--force-new-deployment", "--query", "service.deployments[?status==`PRIMARY`].id | [0]",
                ))
                tasks.assert_called_with(settings, TASKDEF, DIGEST)

    def test_target_change_blocks_update_service(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "aifactory-ecs-deployment.json").write_text(json.dumps({"task_definition": "previous-revision"}))
            with patch.object(ecs, "service", return_value=healthy_service()), patch.object(ecs, "aws") as commands, self.assertRaises(ValueError):
                ecs.run("deploy", dict(self.settings, RUNNER_TEMP=directory))
            commands.assert_not_called()


if __name__ == "__main__":
    unittest.main()
