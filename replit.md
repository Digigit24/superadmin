# Multi-Tenant SaaS Platform with Dynamic Role-Based Permissions

## Overview

This is a production-ready Django 5.x multi-tenant SaaS platform with a sophisticated role-based permission system. The platform enables multiple organizations (tenants) to use the same application instance while maintaining complete data isolation. Each tenant can have custom roles with granular permissions, subscription plans, and modular features (CRM, WhatsApp, Meetings, Tasks).

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Multi-Tenant Architecture

**Problem:** Multiple organizations need to use the platform while keeping their data completely separate and allowing per-tenant customization.

**Solution:** Soft multi-tenancy with tenant isolation at the application layer. Each tenant has:
- A unique identifier (UUID) and slug
- Isolated user base (users belong to one tenant)
- Configurable enabled modules (stored as JSON array)
- Optional separate PostgreSQL database support (via Neon database URLs)
- Custom settings stored as JSON

**Rationale:** Soft multi-tenancy provides a good balance between data isolation and operational simplicity. The architecture supports future migration to separate databases per tenant without requiring major code changes.

### Authentication & Authorization

**Problem:** Need secure, stateless authentication with rich user context including permissions and tenant information.

**Solution:** JWT-based authentication using `djangorestframework-simplejwt` with custom token claims:
- Tokens include: email, tenant_id, tenant_slug, is_super_admin, permissions, enabled_modules
- Token blacklisting for logout functionality
- Email-based authentication (no username field)
- Separate super admin role for platform-wide access

**Pros:**
- Stateless authentication scales well
- Rich token payload reduces database queries
- Built-in token rotation and refresh

**Cons:**
- Tokens cannot be invalidated until expiry (mitigated by blacklisting)
- Larger token payload size

### Dynamic Role-Based Permission System

**Problem:** Different tenants need different role structures, and users often need multiple roles with combined permissions.

**Solution:** JSON-based permission system with:
- Users can have multiple roles (ManyToMany relationship)
- Permissions stored as nested JSON: `{"crm": {"leads": {"view": "team", "create": true}}}`
- Scope-based permissions: "own" (user's data), "team" (team data), "all" (tenant-wide)
- Boolean permissions for simple yes/no actions
- Permission merging algorithm combines multiple roles (higher scopes and true values win)
- Flattened permission format in JWT tokens for easy frontend consumption

**Rationale:** JSON-based permissions provide maximum flexibility without database schema changes. The flattened format in tokens enables efficient client-side permission checks.

### Module System

**Problem:** Different subscription tiers need different features, and tenants should be able to enable/disable modules.

**Solution:** Module-based feature flags stored in tenant configuration:
- Available modules: CRM, WhatsApp, Meetings, Tasks
- Stored as JSON array in tenant model
- Included in JWT tokens for client-side feature detection
- Subscription plans define included modules

**Alternatives considered:** Database-based feature flags per user - rejected due to complexity and subscription plan requirements.

### Data Models

**Core entities:**

1. **Tenant** - Organization/company using the platform
   - UUID primary key for security
   - Slug for user-friendly URLs
   - Optional custom domain support
   - Database connection details for future separate DB support

2. **CustomUser** - Extended Django AbstractUser
   - Email-based authentication (no username)
   - Belongs to one tenant
   - Can have multiple roles
   - Includes super admin flag for platform administration

3. **Role** - Dynamic permission container
   - Belongs to one tenant
   - JSON permission structure
   - Can be active/inactive
   - Tracks creator for audit

4. **SubscriptionPlan** - Billing tier definition
   - Monthly/yearly pricing
   - Resource limits (users, leads, storage)
   - Included modules list
   - Trial period configuration

5. **Subscription** - Active tenant subscription
   - One-to-one with tenant
   - Status tracking (trial, active, past_due, cancelled, expired)
   - Billing cycle and period management

6. **Invoice** - Billing records
   - Auto-generated invoice numbers
   - Status tracking
   - Payment date recording

### API Design

**Pattern:** RESTful API using Django REST Framework with ViewSets

**Structure:**
- `/api/auth/` - Authentication endpoints (register, login, logout, token refresh)
- `/api/users/` - User management
- `/api/roles/` - Role management
- `/api/tenants/` - Tenant management with `/me` endpoint
- `/api/plans/` - Subscription plans (read-only for non-admins)
- `/api/subscriptions/` - Subscription management with `/my_subscription` endpoint
- `/api/invoices/` - Invoice records

**Documentation:** Swagger UI via drf-spectacular at `/api/docs/`

### Permission Classes

**Custom permission hierarchy:**

1. **IsSuperAdmin** - Platform administrators only
2. **IsTenantAdmin** - Tenant administrators (users with admin role)
3. **IsTenantMember** - Any authenticated user belonging to a tenant

**Rationale:** Three-tier permission system provides clear separation between platform administration, tenant administration, and regular users.

### Registration & Onboarding

**Flow:**
1. User registers with tenant information
2. System creates tenant and admin user atomically
3. Default admin role created with full permissions
4. Trial subscription automatically created
5. JWT tokens returned immediately

**Rationale:** Single-step registration reduces friction while ensuring data consistency through atomic transactions.

## External Dependencies

### Core Framework
- **Django 5.0** - Web framework providing ORM, admin interface, and core functionality
- **Django REST Framework** - RESTful API framework with serializers and viewsets
- **djangorestframework-simplejwt** - JWT authentication with token blacklisting

### Database
- **PostgreSQL 12+** - Primary database (via psycopg2-binary driver)
- **Neon PostgreSQL** - Optional separate databases per tenant (connection URLs stored in tenant model)

### API Documentation
- **drf-spectacular** - OpenAPI 3 schema generation and Swagger UI

### Configuration & CORS
- **python-decouple** - Environment variable management
- **django-cors-headers** - CORS support for frontend integration
- **django-filter** - Query parameter filtering for API endpoints

### Third-Party Integrations (Planned)
Based on the module system and permission schema, the platform is designed to integrate:
- WhatsApp Business API (for messaging module)
- Payment gateways (for subscription billing)
- Calendar services (for meetings module)
- Email services (for notifications)

Note: Integration specifics are not yet implemented but are architecturally supported through the module system and permission structure.