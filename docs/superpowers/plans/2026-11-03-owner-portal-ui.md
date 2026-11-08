# Owner Portal UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the existing owner portal screens and wire them to the owner APIs already present on `feature/owner-portal`.

**Architecture:** Keep the current route-per-page structure, React 19, React Router, Tailwind, Zustand auth store, and shared axios client. Implement focused page components for registration, status, dashboard, venue/menu, AI, submissions, and notifications; use server verification as the authority while explaining restricted actions in the UI.

**Tech Stack:** React 19, JSX, React Router 7, Tailwind CSS 4, Zustand 5, Axios.

**Spec:** `docs/superpowers/specs/2026-11-03-owner-portal-ui-design.md`

## Global Constraints

- Keep the current owner route structure and provide a working screen for each existing navigation item.
- Use the existing React, React Router, Tailwind, axios client, and visual conventions already present in the project.
- Connect forms and views to the owner/admin API paths already implemented on this branch.
- Show clear loading, empty, success, and error states, and prevent actions unavailable to unverified owners.
- Preserve responsive behavior for narrow and desktop screens.
- No new UI library or dependencies.
- Keep the user's current edits in `OwnerDashboardPage.jsx`; relocate notification-list behavior into a correctly named notification page without discarding user content or formatting.
- No Better Design MCP is used, per the user's explicit instruction.
- Per workspace instruction, do not add or run tests unless the user asks; use manual route/API checks and a frontend production build instead.

## Review Focus

- Expired or missing session: shell redirects to `/admin/login` and preserves the requested owner path.
- Owner is unverified: status and notifications stay accessible while protected write actions explain the verification requirement; the API remains authoritative.
- API returns validation details, authorization errors, or network failure: the active page retains input and shows a readable error.
- Owner has no venue/menu/submissions/notifications: show explicit empty states and safe next steps.
- Narrow viewport: navigation and forms remain reachable without horizontal overflow.

## File Map

- `frontend/src/features/owner-portal/OwnerLayout.jsx`: session gate, owner shell, nav, sign-out, route wiring.
- `frontend/src/features/owner-portal/pages/OwnerDashboardPage.jsx`: summary cards, venue overview, shortcuts.
- `frontend/src/features/owner-portal/pages/OwnerNotificationsPage.jsx`: notification list extracted from the current `OwnerDashboardPage.jsx` content.
- `frontend/src/features/owner-portal/pages/PublicOwnerRegisterPage.jsx`: public owner registration form.
- `frontend/src/features/owner-portal/pages/RegistrationStatusPage.jsx`: application status and admin feedback.
- `frontend/src/features/owner-portal/pages/OwnerPOIPage.jsx`: venue availability, venue change proposal form, menu CRUD, AI entry point.
- `frontend/src/features/owner-portal/components/AIAdvisorModal.jsx`: AI quota, generation, copy/insert flow.
- `frontend/src/features/owner-portal/pages/OwnerSubmissionsPage.jsx`: proposal history and review outcomes.
- `frontend/src/features/owner-portal/pages/OwnerNotificationDetailPage.jsx`: notification detail and loading/error polish.

## Tasks

### Task 1: Owner shell, session behavior, dashboard, and notifications

**Files:**
- Modify: `frontend/src/features/owner-portal/OwnerLayout.jsx`
- Modify: `frontend/src/features/owner-portal/pages/OwnerDashboardPage.jsx`
- Create: `frontend/src/features/owner-portal/pages/OwnerNotificationsPage.jsx`

**Interfaces:**
- Consume `useAdminSession()` from `features/admin-dashboard/hooks/useAdminSession.js` and `useAuthStore()` for sign-out.
- Consume `GET /owner/dashboard` response `{ pois, summary: { poi_count, menu_item_count, pending_submission_count, unread_notification_count } }`.
- Consume `GET /owner/notifications` response `{ items, unread_count, total }` and preserve the current list content/behavior.

- [x] Implement the shell loading/auth/owner-role gate, route-aware navigation, and logout using `POST /admin/auth/logout`; keep application-status and notifications available to unverified owners.
- [x] Move the current dashboard file's notification-list component into `OwnerNotificationsPage.jsx` without dropping its existing functionality, then make `OwnerDashboardPage.jsx` load and display actual summary data plus shortcuts.
- [x] Wire every existing route to an existing page component and add sensible not-found behavior inside `/owner/*`.
- [ ] Manually inspect `/owner`, `/owner/notifications`, and an unauthenticated `/owner` visit; verify active nav, loading/error/empty states, logout destination, and narrow viewport navigation.

### Task 2: Public owner registration and application status

**Files:**
- Modify: `frontend/src/features/owner-portal/pages/PublicOwnerRegisterPage.jsx`
- Modify: `frontend/src/features/owner-portal/pages/RegistrationStatusPage.jsx`

**Interfaces:**
- Registration request fields: `full_name`, `phone`, `email`, `password`, `poi_name`, `poi_address`, `cccd_number`, optional `storefront_image_url`.
- Registration endpoint: `POST /admin/auth/register-owner`; successful response contains `{ id, email, status, is_poi_owner_verified }`.
- Status endpoint: `GET /owner/registration-status`; response includes `status`, `is_poi_owner_verified`, `poi_name`, `admin_note`, `created_at`, `reviewed_at`.

- [x] Build the registration form with required and max-length constraints matching `OwnerRegisterRequest`, password confirmation, inline field errors, submit progress, success state, and API error handling.
- [x] Build the status page with distinct not-submitted, pending, approved, and rejected states; display the venue name, dates, and admin note when present.
- [ ] Manually submit valid/invalid form values against the API and inspect each status state with representative API responses.

### Task 3: Venue availability, venue edit submissions, and menu CRUD

**Files:**
- Modify: `frontend/src/features/owner-portal/pages/OwnerPOIPage.jsx`

**Interfaces:**
- Venue list: `GET /owner/pois/me` returns `{ items: [{ id, name, address, is_open, ... }], total }`.
- Availability: `PUT /owner/pois/{poi_id}` body `{ is_open }`.
- Menu list/create/update/delete: `GET /owner/menu-items?poi_id=...`, `POST /owner/menu-items` with `{ poi_id, name, price_vnd, image_url?, tags? }`, `PATCH /owner/menu-items/{id}`, `DELETE /owner/menu-items/{id}`.
- Venue proposal: `POST /owner/submissions` with `{ poi_id, proposed_changes }`; only admin-reviewable POI fields are allowed by the backend.

- [x] Load the owner's venues and menu items, expose open/closed updates, and show loading, empty, error, and success states.
- [x] Implement an accessible create/edit menu form with VND price, optional image URL/tags, validation, and confirmed delete.
- [x] Implement a venue profile proposal form for schema-supported owner profile fields (name, address, ward, description, category, image list, and map coordinates; leave activation and internal audio settings to admins); submit proposals rather than writing directly to POI profile fields.
- [ ] Manually verify CRUD and proposal flows, including server validation errors, no venues, and an unverified account.

### Task 4: AI description assistant

**Files:**
- Modify: `frontend/src/features/owner-portal/components/AIAdvisorModal.jsx`
- Modify: `frontend/src/features/owner-portal/pages/OwnerPOIPage.jsx`

**Interfaces:**
- Usage: `GET /ai/usage` returns `{ used_today, daily_limit, remaining }`.
- Generation: `POST /ai/enhance-description` body `{ poi_id, poi_name, keywords: string[], raw_notes }`; response `{ enhanced_description, usage }`.

- [x] Implement modal open/close, focusable inputs for bounded keywords and raw notes, quota display, pending/error/rate-limit states, and generate action.
- [x] Show generated text with copy and insert-into-proposal actions; refresh displayed quota from the response and disable generation at zero remaining uses.
- [ ] Manually verify generate success, quota exhausted, missing API configuration, modal keyboard close, and insert behavior.

### Task 5: Submission history and notification detail

**Files:**
- Modify: `frontend/src/features/owner-portal/pages/OwnerSubmissionsPage.jsx`
- Modify: `frontend/src/features/owner-portal/pages/OwnerNotificationDetailPage.jsx`

**Interfaces:**
- Submissions: `GET /owner/submissions?limit=50&skip=0` returns `{ items, counts, total, limit, skip }`; each item contains proposal, status, admin note, and timestamps.
- Notification detail: `GET /owner/notifications/{id}`; response includes title/message/read state/admin note as available.

- [x] Render proposal status counts, proposed field diffs, review note, and timestamps with readable status labels and empty/loading/error states.
- [x] Complete notification detail presentation, safe back navigation, and not-found/error handling.
- [ ] Manually inspect pending/approved/rejected proposal states and notification detail for both success and API error.

### Task 6: Frontend integration verification

**Files:**
- Modify only the files above if integration fixes are needed.

- [x] Run `npm run build` from `frontend/`; expected result is a successful Vite production build with no unresolved imports.
- [ ] Manually navigate every route and exercise one representative success and error path per form/API page; verify mobile and desktop widths and that unverified users cannot perform owner-only writes.
- [x] Review `git diff --check` and confirm existing unrelated/untracked user files remain untouched.

