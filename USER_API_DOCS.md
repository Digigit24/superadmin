# Users API - Documentation for Frontend and Service Callers

SuperAdmin is the sole owner of users, roles and permissions. Every other service
(digicrm, the SPA) reads the user directory from here.

## Endpoints

| Method | Path | Who may call it |
|---|---|---|
| GET | `/api/users/` | **any authenticated user** (payload depends on role, see below) |
| POST | `/api/users/` | any authenticated user (tenant-restricted, see below) |
| GET | `/api/users/me/` | any authenticated user |
| PUT/PATCH | `/api/users/update_me/` | any authenticated user |
| GET | `/api/users/{id}/` | tenant admin / super admin |
| PUT/PATCH/DELETE | `/api/users/{id}/` | tenant admin / super admin |
| POST | `/api/users/{id}/assign_roles/`, `reset_password/`, `activate/`, `deactivate/` | tenant admin / super admin |
| GET | `/api/users/export/`, POST `/api/users/import_users/` | tenant admin / super admin |

"Tenant admin" means `is_super_admin` **or** the flat permission key
`admin.full_access.enabled` (see `apps/common/permissions.py`).

## Authentication

```
Authorization: Bearer <your-jwt-token>
```

---

## GET /api/users/ - List users

### Query parameters

| Param | Type | Default | Notes |
|---|---|---|---|
| `page` | int | 1 | Page-number pagination. |
| `page_size` | int | 20 | **Honoured**, hard maximum **500**. Values above the maximum are clamped, not rejected. |
| `search` | string | - | Case-insensitive `icontains` match against `email`, `first_name`, `last_name`. Always applied *after* tenant scoping, so it can never reach another tenant's users. |
| `ordering` | string | `-date_joined` | Standard DRF `OrderingFilter`. |

### Tenant scoping (server-enforced)

The tenant scope is derived from the **authenticated principal**, never from a
client-supplied parameter. Precedence, in order:

1. **Trusted principal** - a platform super-admin, or a service/integration
   token. It may target a specific tenant with the `x-tenant-id` header. With no
   header, it sees **all users across all tenants**.
2. **Everyone else** - scoped to the tenant on their own user record. A
   client-supplied `x-tenant-id` header is **ignored entirely**; it can neither
   widen nor narrow the scope. A user with no tenant gets an empty list.

A malformed (non-UUID) `x-tenant-id` from a trusted principal returns an empty
result set rather than an error.

#### `x-tenant-id` - service-to-service header

```http
GET /api/users/?page=1&page_size=200&search=asha
Authorization: Bearer <SERVICE JWT>
x-tenant-id: d2bcd1ee-e5c5-4c9f-bff2-aaf901d40440
```

This is the supported path for digicrm, which proxies this endpoint for its CRM
user directory. **The service JWT must belong to a super-admin or
service/integration principal** - if the token is an ordinary tenant user's
token, the header is ignored and the response is scoped to that user's own
tenant instead.

`x-tenant-slug` and `tenanttoken` are allowed through CORS but are **not** used
for scoping on this endpoint.

### Response shape

Pagination envelope is always the same:

```json
{
  "count": 42,
  "next": null,
  "previous": null,
  "results": [ /* ... */ ]
}
```

These keys are present on **every** result row regardless of the caller's role -
this is the pinned contract other services code against:

| Field | Type | Notes |
|---|---|---|
| `id` | string (UUID) | |
| `email` | string | |
| `first_name` | string | may be `""` |
| `last_name` | string | may be `""` |
| `full_name` | string | `"First Last"`, **falls back to the email** - never empty |
| `is_active` | bool | |
| `avatar` | string (URL) or `null` | alias of `profile_picture` |

**Non-admin caller** (regular tenant member) - gets exactly the fields above and
nothing else. Roles, permissions, `preferences`, `tenant`, `phone`, `timezone`
and `is_super_admin` are deliberately withheld:

```json
{
  "count": 42, "next": null, "previous": null,
  "results": [
    {
      "id": "8b393428-fee3-458d-8329-e6f1d36ffc8d",
      "email": "asha@example.com",
      "first_name": "Asha",
      "last_name": "Rao",
      "full_name": "Asha Rao",
      "is_active": true,
      "avatar": null
    }
  ]
}
```

**Tenant admin / super admin** - gets the richer `UserSerializer`, which is the
contract fields plus:

```json
{
  "id": "8b393428-fee3-458d-8329-e6f1d36ffc8d",
  "email": "gore@gmail.com",
  "phone": null,
  "first_name": "Admin",
  "last_name": "User",
  "full_name": "Admin User",
  "tenant": "d2bcd1ee-e5c5-4c9f-bff2-aaf901d40440",
  "tenant_name": "gore",
  "roles": [ /* full role objects, including their permissions JSON */ ],
  "is_super_admin": false,
  "profile_picture": null,
  "avatar": null,
  "timezone": "Asia/Kolkata",
  "preferences": {},
  "is_active": true,
  "date_joined": "2025-11-23T22:07:27.464478+05:30"
}
```

Note `preferences` (the user's settings blob) and the full nested role
permissions are in the admin payload. Do not forward that payload to
non-admin clients.

---

## POST /api/users/ - Create user

The tenant may be supplied in the request body or via the `x-tenant-id` header
(body wins if both are present). Non-super-admins may only create users inside
their own tenant; anything else returns 403.

```http
POST /api/users/
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
x-tenant-id: d2bcd1ee-e5c5-4c9f-bff2-aaf901d40440
Content-Type: application/json

{
  "email": "newuser@example.com",
  "password": "SecurePass123!",
  "password_confirm": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+1234567890",
  "timezone": "America/New_York",
  "role_ids": ["role-uuid-1", "role-uuid-2"]
}
```

### Request fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| email | string | Yes | User's email address (unique) |
| password | string | Yes | Must pass Django's password validators |
| password_confirm | string | Yes | Must match `password` |
| first_name | string | Yes | |
| last_name | string | Yes | |
| phone | string | No | Unique when set |
| timezone | string | No | Defaults to `Asia/Kolkata` |
| tenant | UUID | No | Auto-populated from `x-tenant-id` when absent |
| role_ids | array[UUID] | No | Roles to assign (must belong to the same tenant) |
| preferences | object | No | |

The 201 response body is the full `UserSerializer` shape shown above.

---

## Error responses

### 400 Bad Request
```json
{ "error": "Your account is not associated with a tenant" }
```

### 403 Forbidden
```json
{ "error": "You can only create users in your own tenant" }
```
Also returned when a non-admin calls a detail/write action (`retrieve`,
`update`, `destroy`, `assign_roles`, `export`, ...).

### 500 Internal Server Error
```json
{ "error": "Failed to create user: <error details>" }
```

---

## Security notes

- `GET /api/users/` is tenant-scoped server-side. A normal user token cannot
  read another tenant's users under any combination of headers or query
  parameters.
- `x-tenant-id` is a **trusted-principal-only** control on this endpoint. For an
  ordinary user token it is ignored, not honoured and not an error.
- Non-admin list responses are served by `UserDirectorySerializer`, which cannot
  leak credentials, tokens, roles, permissions, preferences or `is_super_admin`.
- Non-super-admins may only create users inside their own tenant.
- `page_size` is clamped at 500 so the endpoint cannot be used to dump an
  unbounded page.
- All user IDs are UUIDs returned as strings.

## CORS

These custom headers are accepted:
- `x-tenant-id` - tenant UUID (scoping for trusted principals; tenant assignment on create)
- `x-tenant-slug` - tenant slug identifier (informational)
- `tenanttoken` - alternative tenant token header (informational)
