# Readiness and ingestion-receipt approval

Date: 2026-08-23

Approval: the task owner explicitly instructed completion of every item in `backend/task.md` after the additive readiness route and durable-idempotency gap were identified. This record captures that authorization and the impact analysis required by the contract-change rule.

## Public API change

Problem: `/health` only proves that the process is running; operations need a dependency-aware readiness signal.

Approved change: add `GET /ready`, returning the existing `HealthResponse` on success and the standard error envelope with status 503 when the active repository or enabled ingestion dependency is unavailable.

Frontend impact: additive only. Existing rooms, occupancy, and history parsing is unchanged. Frontends are not required to call `/ready`; deployment tooling may use it.

Contract work: backend routes and models were updated, `contracts/openapi.yaml` was regenerated, and contract-drift plus frontend-side smoke checks cover the result.

## Internal persistence change

Problem: source events accepted between throttled occupancy samples could not retain every event ID durably.

Approved change: migration `0002` adds `ingestion_receipts`, containing only camera ID, observation/event identity, and acceptance time. It does not change any public response. Receipts use raw-sample retention and guarantee duplicate rejection independently of sample throttling.

Schema documentation and migration tests were updated together.
