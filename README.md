# Devin Issue Automation

A barebones event-driven automation service that starts Devin sessions for GitHub issues.

This project is part of a Cognition take-home demo. It shows how Devin can be used as an autonomous engineering primitive in a remediation workflow.

## Workflow

```text
GitHub issue in kyuhur2/superset-devin
        ↓
Issue gets label: devin-fix
        ↓
GitHub webhook calls this service
        ↓
This service calls Devin API
        ↓
Devin starts a session to fix the issue
        ↓
Devin opens a PR / reports progress
        ↓
This service exposes task status via /tasks
```

