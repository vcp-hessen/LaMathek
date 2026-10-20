---
status: accepted
---

# API contract: Pydantic models, OpenAPI, generated zod

Every JSON answer of `/api` is described once, as a Pydantic model in `server/lamathek/contract/models.py`. Each route names its model with `@responds(Model)` (or `None` for 204, `bytes` with a mimetype for PDF, photos and ICS). `lamathek openapi` exports an OpenAPI 3.1 document to `server/lamathek/domain/openapi.json`; `npm run generate:api` turns it into `web/src/api/generated/schemas.ts`, the zod schemas the client parses with. The modules in `web/src/schemas/` only re-export them, plus the request schemas that are not part of the contract yet.

Serializers stay plain dict builders. Under test and in the dev server (`TESTING` or `DEBUG`, override with `API_CONTRACT_CHECK`) an `after_request` hook validates every answer strictly: no missing or extra keys, no wrong types, the declared status; errors must match `ErrorResponse`. A mismatch raises instead of reaching the client. Production does not validate. Tests check that every route declares a model, that `openapi.json` matches the models and that the generated zod file matches `openapi.json`, so drift fails `pytest` or `npm test` without CI.

Every key is always present; "not applicable" or "not visible to you" is `null`. That keeps one model per answer instead of optional keys that differ by caller.

Hand-written zod schemas next to hand-written serializers were rejected: they drifted (a draft without Gruppe emptied every Verleih list). Building the API on Pydantic for validation and serialisation (flask-openapi3, spectree, FastAPI) was rejected as a rewrite of every route for little gain; a generator package (openapi-zod-client, orval) as a dependency for the small subset of JSON Schema Pydantic emits. Request bodies and query parameters are not described yet.
