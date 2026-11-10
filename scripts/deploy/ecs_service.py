"""Deploy a new :latest image without registering or selecting a task definition."""

import json
import os
from pathlib import Path
import re
import subprocess
import sys


def aws(*arguments):
    result = subprocess.run(
        ["aws", "ecs", *arguments, "--output", "json"],
        check=True, capture_output=True, text=True,
    )
    return json.loads(result.stdout) if result.stdout.strip() else None


def image_reference(value):
    for prefix in ("docker.io/", "index.docker.io/", "registry-1.docker.io/"):
        if value.startswith(prefix):
            return value[len(prefix):]
    return value


def service(settings):
    # Project only deployment metadata; never read task environment or secret values.
    result = aws(
        "describe-services", "--cluster", settings["ECS_CLUSTER"],
        "--services", settings["ECS_SERVICE"], "--query",
        "{failures:failures,services:services[].{status:status,taskDefinition:taskDefinition,"
        "desiredCount:desiredCount,runningCount:runningCount,pendingCount:pendingCount,"
        "deploymentController:deploymentController,deployments:deployments[].{id:id,"
        "status:status,rolloutState:rolloutState,taskDefinition:taskDefinition}}}",
    )
    entries = result.get("services", [])
    if result.get("failures") or len(entries) != 1:
        raise ValueError("ECS did not return the selected service.")
    selected = entries[0]
    if selected.get("status") != "ACTIVE" or selected.get("desiredCount", 0) < 1:
        raise ValueError("The selected ECS service must be active with a positive desired count.")
    if selected.get("deploymentController", {}).get("type") != "ECS":
        raise ValueError("This workflow requires the ECS rolling deployment controller.")
    return selected


def verify_tasks(settings, task_definition, expected_digest=None):
    task_arns = aws(
        "list-tasks", "--cluster", settings["ECS_CLUSTER"],
        "--service-name", settings["ECS_SERVICE"], "--desired-status", "RUNNING",
        "--query", "taskArns",
    )
    if not isinstance(task_arns, list) or not task_arns:
        raise ValueError("No running service tasks were found. Check ECS service events.")
    expected_image = settings["DOCKERHUB_REPOSITORY"] + ":latest"
    for offset in range(0, len(task_arns), 100):
        batch = task_arns[offset:offset + 100]
        result = aws(
            "describe-tasks", "--cluster", settings["ECS_CLUSTER"], "--tasks", *batch,
            "--query", "{failures:failures,tasks:tasks[].{lastStatus:lastStatus,"
            "taskDefinitionArn:taskDefinitionArn,containers:containers[].{name:name,"
            "image:image,imageDigest:imageDigest,lastStatus:lastStatus}}}",
        )
        tasks = result.get("tasks", [])
        if result.get("failures") or len(tasks) != len(batch):
            raise ValueError("ECS did not return every requested task.")
        for task in tasks:
            if task.get("lastStatus") != "RUNNING" or task.get("taskDefinitionArn") != task_definition:
                raise ValueError("A service task is not running the existing task definition.")
            containers = [c for c in task.get("containers", []) if c.get("name") == settings["ECS_CONTAINER_NAME"]]
            if len(containers) != 1 or containers[0].get("lastStatus") != "RUNNING":
                raise ValueError("The configured application container is not running in every task.")
            container = containers[0]
            if image_reference(container.get("image", "")) != expected_image:
                raise ValueError("The existing application container must already use " + expected_image + ".")
            if expected_digest and container.get("imageDigest") != expected_digest:
                raise ValueError("A running application container does not use the newly published image digest.")
    return len(task_arns)


def verify_completed(selected, task_definition, deployment_id=None):
    deployments = selected.get("deployments", [])
    if not (
        selected.get("taskDefinition") == task_definition
        and selected.get("runningCount") == selected.get("desiredCount")
        and selected.get("pendingCount") == 0
        and len(deployments) == 1
        and deployments[0].get("status") == "PRIMARY"
        and deployments[0].get("rolloutState") == "COMPLETED"
        and deployments[0].get("taskDefinition") == task_definition
        and (deployment_id is None or deployments[0].get("id") == deployment_id)
    ):
        raise ValueError("The selected deployment has not completed, changed task definition, or rolled back.")


def run(mode, settings):
    state_path = Path(settings["RUNNER_TEMP"]) / "aifactory-ecs-deployment.json"
    if mode == "preflight":
        selected = service(settings)
        task_definition = selected["taskDefinition"]
        verify_completed(selected, task_definition)
        verify_tasks(settings, task_definition)
        state_path.write_text(json.dumps({"task_definition": task_definition}), encoding="utf-8")
        print("Verified the existing service, task definition, and Docker Hub :latest image.")
        return

    if mode not in ("check-target", "deploy"):
        raise ValueError("Use preflight, check-target, or deploy.")
    task_definition = json.loads(state_path.read_text(encoding="utf-8"))["task_definition"]
    selected = service(settings)
    verify_completed(selected, task_definition)
    verify_tasks(settings, task_definition)
    if mode == "check-target":
        return
    digest = settings.get("EXPECTED_IMAGE_DIGEST", "")
    if not re.fullmatch(r"sha256:[a-f0-9]{64}", digest):
        raise ValueError("A valid published image digest is required before deploying.")

    # Deliberately omit --task-definition: retain the service's selected revision.
    deployment_id = aws(
        "update-service", "--cluster", settings["ECS_CLUSTER"],
        "--service", settings["ECS_SERVICE"], "--force-new-deployment",
        "--query", "service.deployments[?status==`PRIMARY`].id | [0]",
    )
    if not isinstance(deployment_id, str) or not deployment_id:
        raise ValueError("ECS did not return the requested primary deployment ID.")
    state_path.write_text(json.dumps({
        "task_definition": task_definition, "deployment_id": deployment_id,
    }), encoding="utf-8")
    aws("wait", "services-stable", "--cluster", settings["ECS_CLUSTER"], "--services", settings["ECS_SERVICE"])
    verify_completed(service(settings), task_definition, deployment_id)
    count = verify_tasks(settings, task_definition, digest)
    print(f"Verified deployment {deployment_id}: {count} running task(s) use {digest}.")
    with Path(settings["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as summary:
        summary.write(f"\nExisting task definition: {task_definition}\n\nVerified deployment: {deployment_id}\n")


if __name__ == "__main__":
    try:
        run(sys.argv[1], os.environ)
    except subprocess.CalledProcessError as error:
        # Do not echo raw AWS responses or credential-provider output.
        match = re.search(r"An error occurred \(([A-Za-z0-9_.-]+)\) when calling the ([A-Za-z0-9]+) operation", error.stderr or "")
        detail = f"{match[2]} ({match[1]})" if match else "command or service stability wait"
        sys.exit(f"::error::AWS ECS {detail} failed. Check service events, permissions, and deployment settings.")
    except (ValueError, KeyError, OSError, IndexError) as error:
        message = str(error) if isinstance(error, ValueError) else "Missing deployment settings or preflight state."
        sys.exit(f"::error::{message}")
