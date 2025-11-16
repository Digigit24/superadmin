# Production Debugging Guide - 500 Internal Server Error

## Summary of Changes Made

### 1. Enhanced Logging in Authentication Flow

**Files Modified:**
- `apps/accounts/services.py` - Added comprehensive logging to token generation
- `apps/accounts/views.py` - Added detailed logging to login and registration views
- `config/settings.py` - Fixed SPECTACULAR_SETTINGS to enable API docs

### 2. Key Improvements

#### Token Generation (`apps/accounts/services.py`)
- ✅ Added safe tenant access with proper error handling
- ✅ Handles cases where `user.tenant` is None
- ✅ Handles cases where `user.tenant.enabled_modules` is None or not accessible
- ✅ Comprehensive logging at each step (INFO, DEBUG, ERROR levels)
- ✅ Exception handling with stack traces

#### Login View (`apps/accounts/views.py`)
- ✅ Logs every login attempt with IP address
- ✅ Logs authentication success/failure
- ✅ Logs token generation process
- ✅ Separate error handling for inactive accounts
- ✅ Detailed error messages in development, generic in production

#### API Documentation
- ✅ Fixed `SERVE_INCLUDE_SCHEMA: True` to enable /api/docs/
- ✅ Added JWT authentication scheme to Swagger UI

---

## Production Debugging Steps

### Step 1: Check Error Logs

The application logs to three files in `/home/user/superadmin/logs/`:

```bash
# Check error logs (most important)
tail -n 100 /home/user/superadmin/logs/error.log

# Check info logs for auth flow
tail -n 100 /home/user/superadmin/logs/info.log

# Check debug logs (only available in DEBUG=True)
tail -n 100 /home/user/superadmin/logs/debug.log
```

**What to look for:**
- Lines containing `CRITICAL:` - These are fatal errors
- Lines containing `apps.accounts.services` - Token generation errors
- Lines containing `apps.accounts.views` - Login/registration errors
- Stack traces showing the exact line that failed

### Step 2: Verify Environment Variables

Check your production `.env` file contains:

```bash
# Required settings
DEBUG=False
SECRET_KEY=your-production-secret-key
JWT_SECRET_KEY=your-jwt-secret-key  # Should be different from SECRET_KEY
DATABASE_URL=postgresql://user:password@host:port/database

# Domain settings
ALLOWED_HOSTS=your-domain.com,www.your-domain.com,admin.celiyo.com

# CORS settings
CORS_ALLOWED_ORIGINS=https://your-frontend.com,https://admin.celiyo.com

# Email settings (if required)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

**Verify on production server:**
```bash
python manage.py shell
>>> from django.conf import settings
>>> print(f"DEBUG: {settings.DEBUG}")
>>> print(f"ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
>>> print(f"DATABASE: {settings.DATABASES['default']['NAME']}")
```

### Step 3: Database Connection Check

```bash
# Test database connectivity
python manage.py dbshell
# If this works, your database connection is fine
\q  # to quit

# Check if tenant table has proper data
python manage.py shell
>>> from apps.tenants.models import Tenant
>>> from apps.accounts.models import CustomUser
>>>
>>> # Check if tenants have enabled_modules field properly set
>>> tenants = Tenant.objects.all()
>>> for t in tenants:
...     print(f"Tenant: {t.name}, enabled_modules: {t.enabled_modules}")
>>>
>>> # Check users and their tenant relationships
>>> users = CustomUser.objects.select_related('tenant').all()
>>> for u in users:
...     print(f"User: {u.email}, Tenant: {u.tenant.slug if u.tenant else 'None'}")
```

### Step 4: Check for Missing Migrations

```bash
# Check if there are unapplied migrations
python manage.py showmigrations

# Apply any pending migrations
python manage.py migrate
```

### Step 5: Collect Static Files

```bash
# Required for production if using static files
python manage.py collectstatic --noinput
```

### Step 6: Test Authentication Manually

```python
# Open Django shell
python manage.py shell

# Test authentication flow
from django.contrib.auth import authenticate
from apps.accounts.models import CustomUser

# Get a test user
user = CustomUser.objects.filter(is_active=True).first()
print(f"Test user: {user.email}")
print(f"Has tenant: {user.tenant is not None}")
if user.tenant:
    print(f"Tenant slug: {user.tenant.slug}")
    print(f"Tenant enabled_modules: {user.tenant.enabled_modules}")

# Test token generation
from apps.accounts.services import get_tokens_for_user
try:
    tokens = get_tokens_for_user(user)
    print("✅ Token generation successful!")
    print(f"Access token length: {len(tokens['access'])}")
except Exception as e:
    print(f"❌ Token generation failed: {e}")
    import traceback
    traceback.print_exc()
```

### Step 7: Check Web Server Logs

If using **Gunicorn**:
```bash
# Check gunicorn logs
journalctl -u gunicorn -n 100

# Or if using systemd
systemctl status gunicorn
```

If using **uWSGI**:
```bash
# Check uwsgi logs
tail -n 100 /var/log/uwsgi/uwsgi.log
```

If using **Nginx** (as reverse proxy):
```bash
# Check nginx error logs
tail -n 100 /var/log/nginx/error.log

# Check nginx access logs for 500 errors
tail -n 100 /var/log/nginx/access.log | grep " 500 "
```

### Step 8: Enable Detailed Error Responses (Temporarily)

**⚠️ WARNING: Only do this temporarily for debugging!**

Add to your production settings temporarily:
```python
# In config/settings.py or via environment variable
DEBUG_ERRORS = config('DEBUG_ERRORS', default=False, cast=bool)
```

Then in views, you can return detailed errors when `DEBUG_ERRORS=True`:
```python
'details': str(error) if settings.DEBUG_ERRORS else 'Internal server error'
```

---

## Common Root Causes

### 1. **Tenant `enabled_modules` is NULL in database**

**Symptom:** 500 error when accessing `user.tenant.enabled_modules`

**Fix:**
```sql
-- Connect to your database
UPDATE tenants SET enabled_modules = '[]' WHERE enabled_modules IS NULL;
```

Or in Django shell:
```python
from apps.tenants.models import Tenant
Tenant.objects.filter(enabled_modules__isnull=True).update(enabled_modules=[])
```

### 2. **Database Connection Issues**

**Symptom:** Logs show database connection errors

**Checks:**
- Verify DATABASE_URL is correct
- Check if database server is running
- Verify firewall rules allow connection
- Check connection pooling settings

### 3. **Missing JWT Secret Key**

**Symptom:** Errors about signing keys or token generation

**Fix:**
```bash
# Generate a new secret key
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Add to .env
JWT_SECRET_KEY=<generated-key>
```

### 4. **ALLOWED_HOSTS Mismatch**

**Symptom:** 400 Bad Request or 500 errors

**Fix:**
```bash
# In .env, ensure your domain is listed
ALLOWED_HOSTS=admin.celiyo.com,api.celiyo.com
```

### 5. **CORS Issues**

**Symptom:** Browser shows CORS errors, API returns 500

**Fix:**
```bash
# In .env
CORS_ALLOWED_ORIGINS=https://admin.celiyo.com,https://app.celiyo.com
```

---

## Monitoring Commands

### Real-time Log Monitoring
```bash
# Watch error log in real-time
tail -f /home/user/superadmin/logs/error.log

# Watch info log for auth attempts
tail -f /home/user/superadmin/logs/info.log | grep -i "login\|register\|token"

# Watch all logs simultaneously
tail -f /home/user/superadmin/logs/*.log
```

### Health Check Endpoint

Consider adding a health check endpoint:

```python
# In apps/accounts/views.py
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def health_check(request):
    """Health check endpoint for monitoring."""
    from django.db import connection

    health_status = {
        'status': 'healthy',
        'database': 'unknown',
        'timestamp': timezone.now().isoformat()
    }

    try:
        # Check database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health_status['database'] = 'connected'
    except Exception as e:
        health_status['status'] = 'unhealthy'
        health_status['database'] = f'error: {str(e)}'
        return Response(health_status, status=500)

    return Response(health_status)
```

---

## Log Output Examples

### Successful Login
```
[INFO] 2025-11-16 10:30:45 apps.accounts.views login_view - Login attempt received - Data: {'email': 'user@example.com'}, IP: 192.168.1.100
[DEBUG] 2025-11-16 10:30:45 apps.accounts.views login_view - Attempting authentication for email: user@example.com
[INFO] 2025-11-16 10:30:45 apps.accounts.views login_view - User authenticated successfully: user@example.com (ID: 123e4567-e89b-12d3-a456-426614174000), tenant: acme-corp
[DEBUG] 2025-11-16 10:30:45 apps.accounts.views login_view - Generating JWT tokens for user: user@example.com
[INFO] 2025-11-16 10:30:45 apps.accounts.services get_tokens_for_user - Starting token generation for user: user@example.com (ID: 123e4567-e89b-12d3-a456-426614174000)
[DEBUG] 2025-11-16 10:30:45 apps.accounts.services get_tokens_for_user - Tenant info retrieved - ID: 456e4567-e89b-12d3-a456-426614174000, slug: acme-corp, modules: ['crm', 'whatsapp']
[INFO] 2025-11-16 10:30:45 apps.accounts.services get_tokens_for_user - Tokens successfully generated for user: user@example.com
[INFO] 2025-11-16 10:30:45 apps.accounts.views login_view - Login successful for user: user@example.com
```

### Failed Login (500 Error)
```
[INFO] 2025-11-16 10:35:22 apps.accounts.views login_view - Login attempt received - Data: {'email': 'user@example.com'}, IP: 192.168.1.100
[DEBUG] 2025-11-16 10:35:22 apps.accounts.views login_view - Attempting authentication for email: user@example.com
[INFO] 2025-11-16 10:35:22 apps.accounts.views login_view - User authenticated successfully: user@example.com (ID: 123e4567-e89b-12d3-a456-426614174000), tenant: acme-corp
[DEBUG] 2025-11-16 10:35:22 apps.accounts.views login_view - Generating JWT tokens for user: user@example.com
[INFO] 2025-11-16 10:35:22 apps.accounts.services get_tokens_for_user - Starting token generation for user: user@example.com (ID: 123e4567-e89b-12d3-a456-426614174000)
[ERROR] 2025-11-16 10:35:22 apps.accounts.services get_tokens_for_user - AttributeError accessing tenant data for user user@example.com: 'NoneType' object has no attribute 'enabled_modules'
Traceback (most recent call last):
  File "/home/user/superadmin/apps/accounts/services.py", line 43, in get_tokens_for_user
    enabled_modules = user.tenant.enabled_modules if user.tenant.enabled_modules is not None else []
AttributeError: 'NoneType' object has no attribute 'enabled_modules'
[ERROR] 2025-11-16 10:35:22 apps.accounts.views login_view - CRITICAL: Token generation failed for user user@example.com (ID: 123e4567-e89b-12d3-a456-426614174000): ...
```

This log tells you EXACTLY where the error occurred!

---

## Next Steps After Deployment

1. **Push these changes** to your production server
2. **Restart your web server**:
   ```bash
   sudo systemctl restart gunicorn
   # or
   sudo systemctl restart uwsgi
   ```
3. **Monitor the logs** while attempting login
4. **Check the exact error** in error.log
5. **Report back** with the specific error message

The enhanced logging will now show you exactly where the 500 error is occurring!
