# PBI-051 – League Description Field

## Overview
PBI-051 introduces a rich-text description field that league owners and admins can manage. Descriptions are stored in the database, exposed through the API, and rendered safely in the web app using a Markdown subset. The feature allows leagues to publish key information such as rules, schedules, or onboarding steps without risking cross-site scripting (XSS) issues.

## Backend Changes
- **Database** – A new nullable `description` `TEXT` column has been added to the `leagues` table via Alembic migration `20251020_0006_add_league_description`.
- **Models** – `League` ORM model now includes the `description` attribute so it can be persisted and queried alongside other league fields.
- **Routes & Schemas** – The `POST /leagues` and `PATCH /leagues/{id}` endpoints accept an optional `description`. Incoming text is sanitized on the server with `sanitize_league_description` to enforce the Markdown subset and strip disallowed HTML. API response schemas return the sanitized description to clients.
- **Validation & Tests** – Regression tests in `api/tests/test_leagues.py` cover length limits (up to 1000 characters) and sanitization rules, ensuring scripts and unsafe attributes are removed consistently.

## Frontend Changes
- **Types & API Layer** – Client-side TypeScript interfaces, hooks, and API helpers now include the optional `description` field so React pages receive the sanitized value.
- **League Settings** – Owners can edit the description within the League Settings page. The form validates the 1000-character limit and persists the sanitized text through the API update call.
- **League Overview** – The Overview page renders the league description beneath the league header. Markdown is parsed with `marked`, sanitized with `DOMPurify`, and displayed as HTML so users see bold text, emphasis, lists, and safe links.
- **Shared Utilities** – A new `renderSafeMarkdown` helper in `frontend/src/utils/markdown.ts` centralizes Markdown parsing and sanitization. Unit tests in `frontend/src/utils/__tests__/markdown.test.ts` assert that unsupported tags are stripped while allowed formatting remains.
- **UI Tests** – React Testing Library coverage in `frontend/src/pages/__tests__/LeagueOverviewPage.test.tsx` ensures descriptions appear on the overview screen and that rendered links remain safe.

## User Experience
1. **Editing** – League owners visit *League Settings → General* and enter up to 1000 characters of Markdown-supported text (bold, italic, lists, and links).
2. **Saving** – On save, the client trims the text and sends it to the API. Both client and server sanitize the content to remove unsupported tags or unsafe URLs.
3. **Viewing** – The sanitized Markdown renders on the League Overview page for all viewers, providing rich formatting while guaranteeing scripts and inline event handlers are removed.
4. **Exports & API Consumers** – Any API responses, exports, or downstream consumers receive the sanitized `description` field, ensuring consistent presentation across surfaces.

## Safety Considerations
- Only a limited subset of Markdown is honored (links, bold, italics, unordered/ordered lists, paragraphs, and line breaks).
- Sanitization runs on both the client and server to defend against malicious payloads introduced through external clients.
- Descriptions longer than 1000 characters are rejected with a validation error, preventing oversized content.

## Rollout Notes
- Run database migrations before deploying the updated services so the new column exists.
- After deployment, existing leagues will show an empty description until owners populate the field.
- No additional configuration is required beyond including the new frontend dependencies (`marked`, `dompurify`).
