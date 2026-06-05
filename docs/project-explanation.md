# Devin Issue Automation

A barebones event-driven automation service that starts Devin sessions. It listens for Github issue/PR activity from a repository provided in the `.env` file, checks whether the event should trigger Devin, creates a Devin session, and stores the resulting task locally.

This project demonstrates how Devin can be used as an autonomous engineering primitive to improve workflows.

## Workflow

1. Github issue in kyuhur2/superset-devin
2. Issue gets label: `devin-fix`
3. Github webhook calls this service
4. This service (hosted on [Render](https://render.com/)) calls Devin API
5. Devin starts a session to fix the issue
6. Devin opens a PR / reports progress
7. This service exposes task status via `/tasks`

## Quick start

### 1. Create `.env`

```bash
DEVIN_API_KEY=cog_xxx
DEVIN_ORG_ID=org_xxx
DEVIN_API_BASE_URL=https://api.devin.ai

TARGET_REPO=owner/repo
TRIGGER_LABEL=devin-fix

TASK_STORE_PATH=.data/tasks.json
```

- `DEVIN_API_KEY`: API key created on the Devin platform
- `DEVIN_ORG_ID`: Org ID registered on the Devin platform
- `TARGET_REPO`: Github repo this app should respond to
- `TRIGGER_LABEL`: label intended to trigger the Devin API
- `TASK_STORE_PATH`: local JSON file used to persist task/session state

### 2. Run the app

- Run only once after doing a fresh clone of this repo
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

- Run with `--build` tag if there are code changes; otherwise run with `docker compose up`
```bash
docker compose up --build
```

The app should now be available at `http://localhost:8000`.

### 3. Open Swagger and Check Tasks

FastAPI exposes interactive API docs at `http://localhost:8000/docs`. Use Swagger to test endpoints without writing curl commands. Check tasks with the following:

```bash
curl http://localhost:8000/tasks | python -m json.tool
```

This returns locally tracked Devin tasks from `TASK_STORE_PATH`.

### 4. Trigger the Webhook Manually

A Github issue raised in the target repo with the `devin-fix` label is done by triggering the `/webhook/github` endpoint. The webhook can also be triggered manually, aka "simulating" the necessary conditions to trigger Devin through this web app. Example issue-label event:

```bash
curl -X POST http://localhost:8000/webhook/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: issues" \
  -d '{
    "action": "labeled",
    "repository": {
      "full_name": "owner/repo"
    },
    "issue": {
      "number": 123,
      "title": "Example bug",
      "body": "Fix this issue",
      "labels": [
        { "name": "devin-fix" }
      ],
      "html_url": "https://github.com/owner/repo/issues/123"
    },
    "label": {
      "name": "devin-fix"
    }
  }'
```

If the event matches the configured repo and trigger label, the app creates a Devin session and saves the task locally.

## Core endpoints

- `POST /simulate`

Simulates a webhook trigger from an issue being created and labeled with `devin-fix` on the target repository. Similar to sending a POST request to `/webhook/github`, but done by simply providing the `issue_url` and `repo`.

- `POST /webhook/github`

Main integration endpoint for Github webhook events. The handler receives a Github event, checks whether it is relevant, and decides whether to invoke Devin. The intended flow is:

`Github issue/PR event -> webhook handler -> trigger validation -> Devin session -> local task record`

- `GET /tasks`

Returns the locally stored task list. Useful for checking whether webhook events successfully created Devin sessions.

- `POST /tasks/{task_id}/refresh`

Refreshes any data associated with the `task_id`. Useful for checking associated issues, pull requests, etc.

## How the app works

The app has four core responsibilities:

1. Receive Github webhook events
2. Filter events by repository, action, and label
3. Create a Devin session for valid tasks
4. Store task/session state locally

The most important guardrail is the trigger logic. The app should not create Devin sessions for every Github event. It should only act when the event matches the configured `TARGET_REPO` and satisfies the intended `TRIGGER_LABEL` behavior. When triggered, the app sends Devin enough context to work on the task, such as the repository name, issue/PR number, title, body, and Github URL.

## Local persistence

Task state is stored in a local JSON file:

`TASK_STORE_PATH=.data/tasks.json`

Each task links a GitHub issue/PR to the Devin session created for it. This is intentionally simple for demo purposes. For production, this would likely move to a real database such as PostgreSQL or DynamoDB.
