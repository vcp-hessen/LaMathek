---
status: accepted
---

# Workflow gates shared between server and client

Which line action is allowed in which workflow step, the step of each line status, and the restore targets live in one JSON file, `server/lamathek/domain/workflow_gates.json`. The server reads it as package data; the Vue client imports the same file through the `@shared` alias, and the Docker build copies it into the web stage.

The server remains the authority: it rejects actions the JSON does not allow. The client uses the same file only to show or hide actions, so both sides cannot drift apart. Generating TypeScript from Python was rejected as more tooling for a small table.
