# Multi-Tenant SaaS Platform with Dynamic Role-Based Permissions

A production-ready Django 5.x multi-tenant SaaS platform featuring a dynamic role-based permission system, JWT authentication, and comprehensive billing management.

## 🚀 Features

### Core Features
- **Multi-Tenant Architecture**: Isolated tenant data with PostgreSQL database per tenant support
- **Dynamic Role System**: JSON-based permissions with support for multiple roles per user
- **JWT Authentication**: Secure token-based authentication with custom claims and token rotation
- **Permission Scopes**: Flexible permission control (own/team/all) for granular access management
- **Module System**: Enable/disable features per tenant (CRM, WhatsApp, Meetings, Tasks)
- **Subscription & Billing**: Complete subscription management with plans, invoicing, and trial periods
- **Super Admin**: Platform-wide administration capabilities
- **REST API**: Complete RESTful API with Swagger documentation

### Technical Features
- Django 5.x with Django REST Framework
- PostgreSQL database with proper migrations
- JWT authentication with blacklisting and rotation
- Comprehensive API documentation (Swagger UI)
- CORS support for frontend integration
- Customized Django admin interface
- Extensive test coverage

## 📋 Requirements

- Python 3.11+
- PostgreSQL 12+
- pip or pip3

## 🛠️ Installation

### 1. Clone the repository
```bash
git clone <repository-url>
cd <project-directory>
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the project root:
```bash
cp .env.example .env
```

Update the `.env` file with your configuration:
```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
PGDATABASE=your_database_name
PGUSER=your_db_user
PGPASSWORD=your_db_password
PGHOST=localhost
PGPORT=5432

# JWT
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ACCESS_TOKEN_LIFETIME_MINUTES=60
JWT_REFRESH_TOKEN_LIFETIME_DAYS=7

# Email (Optional)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
```

### 4. Run Migrations
```bash
python manage.py migrate
```

### 5. Create Superuser (Optional)
```bash
python manage.py createsuperuser
```

### 6. Run the Server
```bash
python manage.py runserver 0.0.0.0:5000
```

The API will be available at `http://localhost:5000/api/`

## 📚 API Documentation

### Swagger UI
Access interactive API documentation at:
```
http://localhost:5000/api/docs/
```

### Key Endpoints

#### Authentication
- `POST /api/auth/register/` - Register new tenant with admin user
- `POST /api/auth/login/` - Login and receive JWT tokens
- `POST /api/auth/logout/` - Blacklist refresh token
- `POST /api/auth/token/refresh/` - Refresh access token
- `POST /api/auth/token/verify/` - Verify token validity
- `POST /api/auth/password/change/` - Change password

#### Users
- `GET /api/users/me/` - Get current user profile
- `PUT /api/users/me/` - Update current user
- `GET /api/users/` - List tenant users (admin)
- `POST /api/users/` - Create new user (admin)
- `GET /api/users/{id}/` - Get user details
- `PUT /api/users/{id}/` - Update user
- `DELETE /api/users/{id}/` - Delete user

#### Roles
- `GET /api/roles/` - List tenant roles
- `POST /api/roles/` - Create new role
- `GET /api/roles/{id}/` - Get role details
- `PUT /api/roles/{id}/` - Update role
- `DELETE /api/roles/{id}/` - Delete role
- `GET /api/roles/{id}/members/` - Get users with this role
- `GET /api/roles/permissions_schema/` - Get permission schema for UI builder

#### Tenants
- `GET /api/tenants/me/` - Get current tenant
- `PUT /api/tenants/me/` - Update current tenant
- `GET /api/tenants/` - List all tenants (super admin)
- `POST /api/tenants/` - Create tenant (super admin)

#### Billing
- `GET /api/plans/` - List subscription plans
- `GET /api/subscriptions/my_subscription/` - Get current subscription
- `POST /api/subscriptions/subscribe/` - Subscribe to a plan
- `POST /api/subscriptions/cancel/` - Cancel subscription
- `GET /api/invoices/` - List invoices

## 🔑 JWT Token Structure

Access tokens include custom claims for efficient authorization:

```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "tenant_id": "uuid",
  "tenant_slug": "company-slug",
  "is_super_admin": false,
  "permissions": {
    "crm.leads.view": "team",
    "crm.leads.create": true,
    "crm.leads.edit": "own",
    "whatsapp.messages.send": true
  },
  "enabled_modules": ["crm", "whatsapp", "meetings"],
  "exp": 1234567890
}
```

## 🎯 Permission System

### Permission Schema
The system supports modular permissions with scopes:

```python
{
    "crm": {
        "leads": {
            "view": "team",      # Scope: own, team, all
            "create": true,      # Boolean permission
            "edit": "own",
            "delete": false
        }
    },
    "whatsapp": {
        "messages": {
            "send": true,
            "view": true
        }
    }
}
```

### Permission Scopes
- **own**: User can only access their own resources
- **team**: User can access team resources
- **all**: User can access all tenant resources
- **boolean**: Simple yes/no permission

### Multi-Role Support
Users can have multiple roles, with permissions merged using these rules:
- Boolean permissions: `True` wins over `False`
- Scope permissions: `all` > `team` > `own`

## 🏗️ Project Structure

```
├── apps/
│   ├── accounts/          # User authentication and roles
│   ├── tenants/           # Multi-tenant management
│   ├── billing/           # Subscription and billing
│   └── common/            # Shared utilities and permissions
├── config/                # Django settings and URLs
├── .env.example           # Environment variables template
├── manage.py              # Django management script
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## 🧪 Running Tests

```bash
python manage.py test
```

Run specific tests:
```bash
python manage.py test apps.accounts.tests.AuthenticationTests
python manage.py test apps.accounts.tests.RoleTests
```

## 🔧 Django Admin

Access the admin interface at:
```
http://localhost:5000/admin/
```

Features:
- User management with role filtering
- Role management with JSON permission viewer
- Tenant configuration
- Subscription plan management
- Invoice management with "mark as paid" action

## 📝 Usage Examples

### Register a New Tenant
```bash
curl -X POST http://localhost:5000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_name": "Acme Corp",
    "tenant_slug": "acme-corp",
    "admin_email": "admin@acme.com",
    "admin_password": "SecurePass123!",
    "admin_password_confirm": "SecurePass123!",
    "admin_first_name": "John",
    "admin_last_name": "Doe",
    "enabled_modules": ["crm", "whatsapp", "meetings"]
  }'
```

### Login
```bash
curl -X POST http://localhost:5000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@acme.com",
    "password": "SecurePass123!"
  }'
```

### Create a Custom Role
```bash
curl -X POST http://localhost:5000/api/roles/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sales Representative",
    "description": "Can manage own leads and activities",
    "permissions": {
      "crm": {
        "leads": {
          "view": "team",
          "create": true,
          "edit": "own",
          "delete": false
        },
        "activities": {
          "view": "own",
          "create": true,
          "edit": "own"
        }
      }
    },
    "is_active": true
  }'
```

## 🚀 Deployment

For production deployment:

1. Set `DEBUG=False` in `.env`
2. Configure proper `ALLOWED_HOSTS`
3. Set strong `SECRET_KEY` and `JWT_SECRET_KEY`
4. Use environment-specific database credentials
5. Configure static files serving
6. Set up SSL/TLS
7. Configure email backend
8. Run collectstatic:
```bash
python manage.py collectstatic
```

## 📄 License

This project is licensed under the MIT License.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📧 Support

For support, email support@example.com or create an issue in the repository.
