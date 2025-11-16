# Logging System Documentation

## Overview

This project implements a comprehensive logging system that writes logs to the `logs/` directory. The logging behavior is controlled by the `DEBUG` setting in the `.env` file.

## Configuration

### Environment Variable

In your `.env` file:
```
DEBUG=True
```

- When `DEBUG=True`: Detailed debug logs are enabled and written to `debug.log`
- When `DEBUG=False`: Only INFO and higher level logs are written

### Log Files

The logging system creates the following log files in the `logs/` directory:

- **debug.log**: Contains DEBUG and higher level messages (only when DEBUG=True)
- **info.log**: Contains INFO and higher level messages
- **error.log**: Contains ERROR and CRITICAL messages only

All log files are configured with rotation:
- Maximum size: 10 MB per file
- Backup count: 5 files (debug.log.1, debug.log.2, etc.)

## Usage

### In Your Django Application

```python
from apps.common.logger import get_logger

# Get a logger for your module
logger = get_logger(__name__)

# Log at different levels
logger.debug('Detailed diagnostic information')
logger.info('General informational message')
logger.warning('Warning message - something unexpected')
logger.error('Error message - something failed')
logger.critical('Critical error - system unstable')
```

### Example in a View

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.common.logger import get_logger

logger = get_logger(__name__)

class MyView(APIView):
    def get(self, request):
        logger.info(f'User {request.user} accessed MyView')

        try:
            # Your business logic
            data = self.process_data()
            logger.debug(f'Processed data: {data}')
            return Response(data)
        except Exception as e:
            logger.error(f'Error in MyView: {str(e)}', exc_info=True)
            raise
```

### Example in a Service

```python
from apps.common.logger import get_logger

logger = get_logger(__name__)

class UserService:
    def create_user(self, data):
        logger.info(f'Creating user with email: {data.get("email")}')

        try:
            user = User.objects.create(**data)
            logger.info(f'User created successfully: {user.id}')
            return user
        except Exception as e:
            logger.error(f'Failed to create user: {str(e)}', exc_info=True)
            raise
```

## Log Levels

- **DEBUG**: Detailed information for diagnosing problems (only in DEBUG mode)
- **INFO**: Confirmation that things are working as expected
- **WARNING**: Indication that something unexpected happened
- **ERROR**: Serious problem that prevented a function from completing
- **CRITICAL**: Very serious error that may cause the application to abort

## Log Format

### Verbose Format (debug.log, error.log)
```
[LEVEL] YYYY-MM-DD HH:MM:SS module_name module function_name - message
```

Example:
```
[ERROR] 2025-11-16 17:56:23 apps.accounts views create_user - Failed to create user: Duplicate email
```

### Simple Format (info.log)
```
[LEVEL] YYYY-MM-DD HH:MM:SS - message
```

Example:
```
[INFO] 2025-11-16 17:56:23 - User created successfully
```

## Testing

To test the logging system:

```bash
python test_logging.py
```

This will create sample log entries at all levels and verify the logging configuration.

## Loggers Available

The project has several pre-configured loggers:

- **django**: General Django framework logs
- **django.request**: HTTP request/response logs
- **django.db.backends**: Database query logs (DEBUG mode only)
- **apps**: Application-specific logs (your custom code)

## Console Output

When `DEBUG=True`:
- All logs are also output to the console (stdout)
- Console shows DEBUG level and above

When `DEBUG=False`:
- Console shows INFO level and above

## Git Ignore

Log files are automatically ignored by git:
- Individual `.log` files are ignored
- The entire `logs/` directory is ignored

## Best Practices

1. **Use appropriate log levels**: Don't log everything as ERROR
2. **Include context**: Add relevant information to help debugging
3. **Use exc_info=True**: When logging exceptions to get full traceback
4. **Don't log sensitive data**: Passwords, tokens, etc.
5. **Use structured logging**: Include user IDs, request IDs for tracing

## Example: Logging with Context

```python
logger.info(
    f'Payment processed',
    extra={
        'user_id': user.id,
        'amount': amount,
        'transaction_id': transaction.id
    }
)
```

## Configuration Location

The logging configuration is defined in:
- **config/settings.py** (lines 158-240)

## Troubleshooting

If logs are not appearing:
1. Check that the `logs/` directory exists
2. Verify `DEBUG` setting in `.env` file
3. Check file permissions on the `logs/` directory
4. Ensure Django settings are properly loaded
