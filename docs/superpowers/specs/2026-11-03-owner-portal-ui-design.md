# Owner Portal UI Design

## Intent

Complete the owner-facing screens in the existing React application so a restaurant owner can register, understand their review status, manage their venue and menu, submit proposed venue changes, use the AI description helper, and read review notifications.

## Goals

- Keep the current owner route structure and provide a working screen for each existing navigation item.
- Use the existing React, React Router, Tailwind, axios client, and visual conventions already present in the project.
- Connect forms and views to the owner/admin API paths already implemented on this branch.
- Show clear loading, empty, success, and error states, and prevent actions unavailable to unverified owners.
- Preserve responsive behavior for narrow and desktop screens.

## Non-goals

- Redesign the wider application or introduce a new UI library/design system.
- Change backend contracts unless the frontend reveals a blocking mismatch; report any such mismatch before changing the contract.
- Build admin screens or change public consumer experiences.

## Approaches

1. **Separate pages following the existing navigation (chosen).** Finish registration, dashboard, venue/menu, submissions, registration status, notification list, and notification detail as separate pages. This matches the routes and APIs that already exist and keeps each owner task easy to find.
2. **Tabbed venue management.** Combine venue details, menu, and AI tools into one tabbed workspace. This reduces route changes but alters the existing navigation and makes the current API/page layout less direct.

## Product behavior

- Public registration collects the required contact, venue, identity, password, and storefront fields and posts to `/admin/auth/register-owner`; after success, direct the user to sign in and check their application status.
- The owner shell provides navigation, active route indication, and session-aware sign-out using existing auth conventions.
- The dashboard reads `/owner/dashboard` and presents venue and menu counts, pending submissions, unread notifications, and useful links.
- Venue/menu management reads `/owner/pois/me`; owners can change open/closed availability, create and edit menu items, and delete a menu item. Venue profile changes are sent as proposals through `/owner/submissions`.
- The AI helper reads `/ai/usage`, sends a selected venue and user-provided notes/keywords to `/ai/enhance-description`, displays the generated text, and lets the user copy or insert it into the relevant venue proposal flow.
- Submissions show status, submitted fields, and review feedback from `/owner/submissions`.
- Registration status uses `/owner/registration-status`, with pending/approved/rejected states and the admin note where present.
- Notifications have a real list page and detail page, backed by `/owner/notifications` and `/owner/notifications/{id}`.
- Unverified owners can access application status and notifications; owner-only management actions follow the server's verification gate and show an explanation when blocked.

## Constraints and calls

- The project currently uses Tailwind and its existing orange/amber owner styling; retain that language.
- Keep the user's current edits in `OwnerDashboardPage.jsx`; relocate notification-list behavior into a correctly named notification page without discarding user content or formatting.
- `OwnerLayout.jsx` references `OwnerNotificationsPage.jsx`, which does not currently exist; create that page and correct the route/import wiring.
- No Better Design MCP is used, per the user's explicit instruction.
- No new dependencies are planned.

## Acceptance criteria

- Every owner route renders without a missing import and navigation links identify the current page.
- Every implemented form/view uses the matching API, validates required input, and handles loading, empty, success, and API error states.
- Owners can complete registration and follow its status; verified owners can manage menu entries, submit venue edits, use the AI helper, and inspect notifications.
- Layout remains usable on mobile and desktop widths and matches existing project styles.
- Frontend production build completes; no test suite will be added or run unless requested.
