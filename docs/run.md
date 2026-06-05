# Run / Simulate the Workflow

This project is currently demo-ed on Render. The link to the hosted web app is `https://devin-automation.onrender.com`.

## 1. Check that the service is live

```bash
curl https://devin-automation.onrender.com/ | python -m json.tool
```

Expected response includes:

- `status: ok`
- `target_repo`
- `trigger_label`

## 2. Trigger through Github

In the target repository (set by `TARGET_REPO` the environmental variables on Render), a Github issue can be created and labeled with `devin-fix`. Github sends `issues` webhook events to `https://devin-automation.onrender.com/webhook/github` and the service only creates a Devin session if the event matches:

- repository equals `TARGET_REPO`
- event type is `issues`
- action is `labeled`
- label is `devin-fix`

## 3. Check task status

This returns tracked Devin tasks, including issue / session / PR metadata where available.

```bash
curl https://devin-automation.onrender.com/tasks | python -m json.tool
```

## 4. Refresh a task

Use this to refresh task metadata, such as an associated issue or PR status.

```bash
curl -X POST https://devin-automation.onrender.com/tasks/{task_id}/refresh | python -m json.tool
```

## 5. Simulate the workflow

The service also supports a manual simulation endpoint, `POST /simulate` which is useful when testing without relying on a real Github webhook event. This can be utilized when running locally, as there is no public facing URL for the webhook to send events to. An example is provided below (`<url>` should be either `localhost:<PORT>` or the URL where the production service is hosted, i.e. `devin-automation.onrender.com`).

```bash
curl -X POST https://<url>/simulate \
  -H "Content-Type: application/json" \
  -d '{
    "repo": "kyuhur2/superset",
    "issue_url": "https://github.com/kyuhur2/superset/issues/1"
  }' | python -m json.tool
```