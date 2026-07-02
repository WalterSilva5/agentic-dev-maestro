> 🇧🇷 [Versão em português](04-rbac-e-multitenant.ptbr.md)

# 04 — RBAC and multi-tenant

## Multi-tenancy

- **Tenant = Company.** A user can belong to several companies (one
  `Membership` per company), potentially with a different role in each.
- **Row-level isolation:** every domain entity carries `companyId`. A global
  guard resolves the company from the context (from the JWT/Membership or the API key) and **every
  query is filtered by `companyId`**. No exceptions — this is the defense against leakage
  between tenants.
- The `companyId` **never** comes from the trusted request body: it comes from the token/key.

### Per-request context resolution

```
Human (JWT)    → token identifies the User → picks the active company
                 (X-Company-Id header or /companies/:id/... route) →
                 loads the Membership → role + permissions
Agent (key)    → x-api-key → ApiKey → Membership → companyId + role
                 (role defines the permission; key scopes: planned refinement)
```

## Roles and permission matrix

| Action | OWNER | MANAGER | TECH_LEAD | DEV | VIEWER |
|---|:--:|:--:|:--:|:--:|:--:|
| View projects/boards/tasks | ✅ | ✅ | ✅ | ✅ | ✅ |
| Create/edit tasks | ✅ | ✅ | ✅ | ✅ | ❌ |
| Move tasks on the board | ✅ | ✅ | ✅ | ✅ | ❌ |
| Delete tasks | ✅ | ✅ | ✅ | ⚠️ own | ❌ |
| Write docs | ✅ | ✅ | ✅ | ✅ | ❌ |
| Create/configure projects and boards | ✅ | ✅ | ✅ | ❌ | ❌ |
| Manage members (invite / change role) | ✅ | ✅ | ❌ | ❌ | ❌ |
| Manage API keys | ✅ | ✅ | ⚠️ own | ⚠️ own | ❌ |
| Configure/delete the company, transfer ownership | ✅ | ❌ | ❌ | ❌ | ❌ |

⚠️ = restricted to own resources.

### Notes

- **OWNER** is responsible for the company (whoever created it or received ownership). Can
  demote/remove anyone except another OWNER (explicit ownership transfer).
- **MANAGER** handles day-to-day operations: members, projects, boards, tasks — but does not
  destroy the company or touch OWNERs.
- **TECH_LEAD** runs the technical side (projects, boards, tasks, docs, review), but does not
  manage people.
- **DEV** is the executor: creates/edits/moves tasks and writes docs.
- **VIEWER** is read-only — ideal for stakeholders/managers who only consume the
  view (generates the same markdown reports as today, without being able to edit).

## Agents and permissions

> **Current state:** the effective authorization of an API key is given by the **Membership
> role** (`@RequireRole` on the guard). The `scopes` are already **stored** on the key
> and exposed in the context, but granular per-scope enforcement is a **planned
> refinement**. The description below is the target design (role ∩ scopes).

The effective permission of an API key is **the intersection** of the Membership role with the
key's `scopes`. Examples:

- A key on a **DEV** member with scope `tasks:write tasks:move docs:write` → can
  run the loop, but never manage members (the role already blocks it).
- A key on a **MANAGER** member but with scope only `tasks:read` → despite the high
  role, the key only reads (least-privilege principle for agents).

Recommendation: **executor agents** use a dedicated Membership with role `DEV`
(or a future `AGENT` role) with minimal scopes, to keep auditing clean
(every agent action is attributed to that identity).

## Auditing

Every write records into `ActivityLog`: `actorUserId` + `viaApiKeyId` (if agent) +
`action` + `changes` (diff). This answers "who changed the status / created the task /
edited the doc — human or agent, and which key".
