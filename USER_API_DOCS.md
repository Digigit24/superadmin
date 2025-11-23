# User Creation API - Documentation for Frontend

## Endpoint
`POST /api/users/`

## Authentication
Requires JWT authentication token in the `Authorization` header:
```
Authorization: Bearer <your-jwt-token>
```

## Tenant ID Support

The API now supports **automatic tenant ID extraction** from request headers. You can pass the tenant ID in two ways:

### Option 1: Request Headers (Recommended for Tenant Apps)
Include the tenant ID in the request headers. All of these headers are supported:
```http
x-tenant-id: 8cf51f60-39ff-4094-ac0c-91fec5f36565
x-tenant-slug: jeevisha
tenanttoken: 8cf51f60-39ff-4094-ac0c-91fec5f36565
```

The backend will automatically populate the `tenant` field from the `x-tenant-id` header if not provided in the request body. The `x-tenant-slug` and `tenanttoken` headers are also allowed through CORS for your convenience.

### Option 2: Request Body
Include the tenant ID directly in the JSON payload:
```json
{
  "tenant": "8cf51f60-39ff-4094-ac0c-91fec5f36565",
  ...
}
```

**Note:** If both are provided, the request body value takes precedence.

## Request Example

```http
POST /api/users/
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
x-tenant-id: d2bcd1ee-e5c5-4c9f-bff2-aaf901d40440
x-tenant-slug: gore
tenanttoken: d2bcd1ee-e5c5-4c9f-bff2-aaf901d40440
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

## Request Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| email | string | Yes | User's email address (unique) |
| password | string | Yes | User password (must meet validation requirements) |
| password_confirm | string | Yes | Password confirmation (must match password) |
| first_name | string | Yes | User's first name |
| last_name | string | Yes | User's last name |
| phone | string | No | User's phone number |
| timezone | string | No | User's timezone (defaults to 'Asia/Kolkata') |
| tenant | UUID | No | Tenant ID (auto-populated from x-tenant-id header if not provided) |
| role_ids | array[UUID] | No | Array of role IDs to assign to the user |

## Response Example (201 Created)

```json
{
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "email": "newuser@example.com",
  "phone": "+1234567890",
  "first_name": "John",
  "last_name": "Doe",
  "tenant": "8cf51f60-39ff-4094-ac0c-91fec5f36565",
  "tenant_name": "Jeevisha",
  "roles": [
    {
      "id": "role-uuid-1",
      "name": "Admin",
      "description": "Administrator role",
      "permissions": {...},
      "is_active": true
    }
  ],
  "is_super_admin": false,
  "profile_picture": null,
  "timezone": "America/New_York",
  "is_active": true,
  "date_joined": "2025-11-23T10:30:00Z"
}
```

## Error Responses

### 400 Bad Request
```json
{
  "error": "Your account is not associated with a tenant"
}
```

### 403 Forbidden
```json
{
  "error": "You can only create users in your own tenant"
}
```

### 500 Internal Server Error
```json
{
  "error": "Failed to create user: <error details>"
}
```

## Security Notes

- Non-super-admin users can **only** create users within their own tenant
- The `x-tenant-id` header is validated against the authenticated user's tenant
- Password must meet Django's password validation requirements
- All user IDs are UUIDs returned as strings

## CORS Configuration

The backend has been configured to accept the following custom headers:
- `x-tenant-id` - Tenant UUID (used for automatic tenant assignment)
- `x-tenant-slug` - Tenant slug identifier
- `tenanttoken` - Alternative tenant token header

These headers will not cause CORS errors when sent from your frontend application.
