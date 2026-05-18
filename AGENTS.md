# AGENTS.md - CollectPay Tracker

## Purpose
Local operating guide for coding agents working in this repository.
The goal is to keep implementation consistent, secure, testable, and production-minded.

## Scope
- Applies to the entire repository.
- Priority order: user request > this file > general defaults.

## Project Context
- Product: payment tracking platform (phase 1: manual payment recording).
- Backend stack: Python + Django + Django REST Framework.
- Critical domains: organizations, customers, catalog/services, payment requests, transactions, receipts, audit.

## Mandatory Workflow (Skill-First)
Before implementing any substantial task (feature, refactor, bugfix, migration, test/security update):
1. Understand task scope and acceptance criteria.
2. Check whether a relevant Codex skill exists.
3. Use the matching skill workflow when available.
4. If no skill is relevant, proceed with standard implementation.
5. In final output, mention briefly which skill was used (or why none was used).

## Branch Roadmap (One Section = One Branch)
The project must be developed branch-by-branch. Each branch below is one implementation section.
When all branches are completed and merged, the full product scope is covered.

1. `codex/01-foundation-core`
- Setup settings, environment, DRF, JWT, CORS, OpenAPI, base URL routing.
- Register all domain apps and prepare project-wide conventions.

2. `codex/02-auth-roles-permissions`
- User auth endpoints (login/logout/profile), role model, permission rules.
- Secure write endpoints and role-based access boundaries.

3. `codex/03-organizations-multi-tenant`
- Organization model and user-to-organization linking.
- Tenant isolation rules and organization-scoped query filtering.

4. `codex/04-customers-management`
- Customer model CRUD, search, pagination, soft deactivation.
- Customer payment history endpoint.

5. `codex/05-catalog-services`
- Service/motif model CRUD, active/inactive lifecycle, expected amount/currency.
- Link services to organization and payment requests.

6. `codex/06-payment-requests-core`
- PaymentRequest model, reference generation, due-date, status lifecycle.
- Pending/overdue/partial views and core status transitions.

7. `codex/07-transactions-idempotence`
- Manual transaction recording API.
- Idempotence and duplicate transaction reference protection.
- Auto-update request status (`PARTIAL`, `PAID`) and reject on `CANCELLED`.

8. `codex/08-receipts-verification`
- Receipt generation and retrieval.
- Public verification endpoint with secure reference/UUID/hash strategy.

9. `codex/09-audit-trail`
- Sensitive action logging (who, when, before/after, amount/ref changes).
- Structured audit querying for admin controls.

10. `codex/10-dashboard-reporting`
- Aggregated metrics endpoints (today/month totals, pending/paid/partial, remaining gap).
- ORM performance-minded queries with annotations and filters.

11. `codex/11-exports`
- CSV/Excel/PDF exports with filters (period, status, customer, service).
- Export reliability checks for large result sets.

12. `codex/12-frontend-backoffice`
- HTMX + Alpine.js + Tailwind admin flows for core operations.
- Integrate API flows for requests, transactions, receipts, dashboard, exports.

13. `codex/13-quality-hardening`
- Test expansion (unit/integration), validation hardening, error handling.
- Security review, performance pass, operational readiness checklist.

14. `codex/14-mobile-money-phase-2`
- MTN/Orange integration layer and webhook flows.
- Reconciliation safeguards and production-grade callback security.

## Branch Execution Rules
- Work on one branch section at a time in roadmap order unless user reprioritizes.
- Each branch must include code, tests, and migration updates when needed.
- A branch is only complete when its section deliverables are verifiably implemented.
- Mention the current branch section explicitly in task updates and final summaries.

## Coding Rules
- Keep business rules in domain/service layer, not in views.
- Use `Decimal` for money; never float.
- Enforce idempotence for transaction ingestion.
- Keep models and API explicit (no hidden side effects).
- Write/adjust tests with each business change.
- Prefer small, reviewable commits.

## Django/API Conventions
- App paths stay under `apps/<domain>/`.
- Add apps explicitly in `INSTALLED_APPS`.
- Use serializers/validators for input contracts.
- Filter all tenant data by organization.
- Prefer explicit status enums/constants for payment lifecycle.

## Security & Reliability Guardrails
- Reject duplicate confirmed transaction references.
- Cancelled payment requests must reject new transactions.
- Update payment status deterministically (`PENDING`, `PARTIAL`, `PAID`, etc.).
- Log sensitive state changes (who, when, before, after).
- Validate auth/permissions on all write endpoints.

## Commands (Typical)
- Run checks: `python manage.py check`
- Migrations: `python manage.py makemigrations && python manage.py migrate`
- Tests: `python manage.py test`
- Dev server: `python manage.py runserver`

## Definition of Done
A task is done only if:
1. Functional behavior matches request.
2. Security/business rules are preserved.
3. Tests are added/updated and pass locally.
4. Any schema changes include migrations.
5. Final summary explains what changed and why.
