# Owner Portal Implementation Plan

> **For agentic workers:** Use this plan task-by-task. Keep the owner feature on `feature/owner-portal` and preserve shared API/auth contracts from `feature/admin-core`.

**Goal:** Implement the owner registration, verified-owner workflows, menu, submissions, notifications, dashboard data, and AI advisor using the current FastAPI and React stack.

**Architecture:** Extend the existing FastAPI owner and AI modules, sharing authentication, RBAC, MongoDB transactions, and POI validation with admin-core. Owner-originated core POI edits remain review submissions; menu records are scoped to POIs owned by the authenticated user. The UI follows the repository design system and remains gated on Better Design MCP availability or explicit local-fallback authorization.

**Tech Stack:** FastAPI, Pydantic v2, Motor/MongoDB, React 19, React Router, Axios, Zustand.

**Spec:** `docs/UI_UX_SPECIFICATION.md` (on `main`); FR-06, FR-07, FR-08 from `PRD - Hệ Thống Du Lịch Ẩm Thực Quận 4.pdf`.

## Global Constraints

- Preserve current routes, cookie JWT authentication, dynamic RBAC, owner verification gate, and admin review/Activation Gate behavior.
- Encrypt CCCD with configured Fernet key before storing; never expose it in owner responses, notifications, or logs.
- Do not make owner core POI changes public until admin review approves them.
- Apply the configured owner AI daily limit and do not invent facts in generated content.
- Keep data belonging to another owner inaccessible; return real empty states when records do not exist.
- Use the existing design tokens and shared UI components for frontend work; no fake product data.
- Do not run or add tests unless requested by the user. Record checks actually run and any unverified behavior.

## Review Focus

- Duplicate/invalid registration and unavailable encryption key must fail without partial account creation.
- Unverified owners must not read or mutate business data even if they have an owner role.
- POI and menu IDs supplied by a caller must always be checked against the authenticated owner's assignments.
- Review submissions must reject forbidden fields and conflicting/stale changes.
- Concurrent AI requests must never exceed the daily quota; failed provider requests must not consume a completed-use quota.
- UI must preserve unfinished form content, show server state accurately, and expose errors/loading/empty states accessibly.

---

### Task 1: Owner registration and status API

Implement validated registration, Fernet PII encryption, password hashing, duplicate-email handling, transaction-safe user/registration creation, and authenticated status retrieval.

### Task 2: Verified owner data and menu API

Implement owner-scoped POI listing, a clearly modeled quick availability update, and menu item list/create/update/delete. Enforce `owner:access`, `owner:manage_own_poi`, and verification requirements.

### Task 3: POI submissions and history API

Implement owner-scoped submission creation and history, allowing only fields accepted by admin review. Keep submissions pending until admin acts.

### Task 4: AI Advisor API

Implement authenticated usage reporting, atomic per-user/day quota accounting, Gemini generation, and safe provider/configuration error handling.

### Task 5: Owner portal UI

Repair owner routes and build registration, status, dashboard, POI/menu, submission history, notifications, and AI Advisor screens using shared components. This task is blocked until Better Design MCP is available or the user explicitly authorizes the repository's local fallback for this session.

### Task 6: Final integration and handoff

Run only user-authorized checks, inspect changed routes and data boundaries, document checks and remaining limitations, and leave the work on `feature/owner-portal` without pushing or merging remotely.
