import os
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Request

from app.devin_client import DevinClient
from app.models import SimulateRequest, Task
from app.store import TaskStore


app = FastAPI(
    title="Devin Issue Automation",
    description="Event-driven automation that starts Devin sessions for GitHub issues.",
    version="0.1.0",
)

TARGET_REPO = os.environ.get("TARGET_REPO", "kyuhur2/superset-devin")
TRIGGER_LABEL = os.environ.get("TRIGGER_LABEL", "devin-fix")
TASK_STORE_PATH = os.environ.get("TASK_STORE_PATH", ".data/tasks.json")

store = TaskStore(TASK_STORE_PATH)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_devin_prompt(issue_url: str, repo: str) -> str:
    return f"""
    You are working on a Cognition take-home demo.

    Target repository:
    {repo}

    GitHub issue to remediate:
    {issue_url}

    Please:
    1. Inspect the issue and relevant code.
    2. Make the smallest safe change that resolves the issue.
    3. Run relevant tests or checks if practical.
    4. Open a pull request back to {repo}.
    5. In the PR description, include:
    - Summary of the change
    - Validation performed
    - Any follow-up recommendations

    Keep the change focused and production-quality.
    """.strip()


def extract_devin_status(response: dict[str, Any]) -> str | None:
    return response.get("status")


def extract_devin_status_detail(response: dict[str, Any]) -> str | None:
    return response.get("status_detail")


def extract_pull_requests(response: dict[str, Any]) -> list[dict[str, Any]]:
    pull_requests = response.get("pull_requests")
    if not isinstance(pull_requests, list):
        return []

    return pull_requests


def extract_session_id(response: dict[str, Any]) -> str | None:
    """
    Devin API response shapes can vary by API version.
    This tries the common names.
    """
    return (
        response.get("devin_id")
        or response.get("session_id")
        or response.get("id")
    )


def extract_session_url(response: dict[str, Any]) -> str | None:
    return (
        response.get("url")
        or response.get("session_url")
        or response.get("web_url")
    )


def update_task_from_devin_response(task: Task, response: dict[str, Any]) -> Task:
    task.devin_session_id = extract_session_id(response) or task.devin_session_id
    task.devin_session_url = extract_session_url(response) or task.devin_session_url
    task.devin_status = extract_devin_status(response)
    task.devin_status_detail = extract_devin_status_detail(response)
    task.pull_requests = extract_pull_requests(response)
    task.raw_devin_response = response
    task.updated_at = now_iso()
    return task


async def start_devin_for_issue(issue_url: str, repo: str) -> Task:
    task = Task(
        task_id=f"task_{uuid.uuid4().hex[:12]}",
        issue_url=issue_url,
        repo=repo,
        status="received",
    )
    store.upsert_task(task)

    try:
        client = DevinClient()
        prompt = build_devin_prompt(issue_url=issue_url, repo=repo)
        response = await client.create_session(prompt=prompt)

        task.status = "session_started"
        task = update_task_from_devin_response(task, response)
        store.upsert_task(task)
        return task

    except Exception as exc:
        task.status = "failed"
        task.updated_at = now_iso()
        task.error = str(exc)
        store.upsert_task(task)
        return task


@app.get("/")
def health() -> dict[str, str]:
    return {
        "service": "devin-issue-automation",
        "status": "ok",
        "target_repo": TARGET_REPO,
        "trigger_label": TRIGGER_LABEL,
    }


@app.post("/simulate")
async def simulate(request: SimulateRequest) -> Task:
    """
    Simulation trigger.

    Example:
    curl -X POST http://localhost:8000/simulate \\
      -H 'Content-Type: application/json' \\
      -d '{"issue_url":"https://github.com/kyuhur2/superset-devin/issues/1"}'
    """
    repo = request.repo or TARGET_REPO

    if "/" not in repo:
        raise HTTPException(
            status_code=400,
            detail="repo must be a full GitHub repo name, e.g. kyuhur2/superset-devin",
        )

    return await start_devin_for_issue(issue_url=request.issue_url, repo=repo)


@app.post("/webhook/github")
async def github_webhook(request: Request) -> dict[str, Any]:
    """
    GitHub issue webhook trigger.

    For the take-home, this handles issue events and triggers Devin when:
    - action is opened or labeled
    - issue has the configured trigger label, e.g. devin-fix
    """
    payload = await request.json()

    action = payload.get("action")
    issue = payload.get("issue")
    repository = payload.get("repository", {})

    if not issue:
        return {"ignored": True, "reason": "not an issue event"}

    repo_full_name = repository.get("full_name")
    if repo_full_name != TARGET_REPO:
        return {
            "ignored": True,
            "reason": f"repo {repo_full_name} does not match target repo {TARGET_REPO}",
        }

    if action not in {"opened", "labeled", "reopened"}:
        return {"ignored": True, "reason": f"action {action} is not a trigger action"}

    labels = {label.get("name") for label in issue.get("labels", [])}
    if TRIGGER_LABEL not in labels:
        return {
            "ignored": True,
            "reason": f"issue does not have label {TRIGGER_LABEL}",
        }

    issue_url = issue.get("html_url")
    if not issue_url:
        raise HTTPException(status_code=400, detail="issue.html_url missing")

    task = await start_devin_for_issue(issue_url=issue_url, repo=TARGET_REPO)
    return {"ignored": False, "task": task}


@app.get("/tasks")
def list_tasks() -> list[Task]:
    return store.list_tasks()


@app.get("/tasks/{task_id}")
def get_task(task_id: str) -> Task:
    task = store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    return task


@app.post("/tasks/{task_id}/refresh")
async def refresh_task(task_id: str) -> Task:
    task = store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")

    if not task.devin_session_id:
        raise HTTPException(status_code=400, detail="task has no Devin session ID")

    try:
        client = DevinClient()
        response = await client.get_session(task.devin_session_id)

        task.status = "refreshed"
        task = update_task_from_devin_response(task, response)
        store.upsert_task(task)
        return task

    except Exception as exc:
        task.status = "failed"
        task.updated_at = now_iso()
        task.error = str(exc)
        store.upsert_task(task)
        return task
