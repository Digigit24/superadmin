"""
Logging utility for the superadmin project.

This module provides a centralized way to get loggers for different parts of the application.
The logging configuration is defined in config/settings.py

Usage:
    from apps.common.logger import get_logger

    logger = get_logger(__name__)

    logger.debug('Debug message')
    logger.info('Info message')
    logger.warning('Warning message')
    logger.error('Error message')
    logger.critical('Critical message')

Examples:
    # In a view
    from apps.common.logger import get_logger
    logger = get_logger(__name__)

    def my_view(request):
        logger.info(f'User {request.user} accessed my_view')
        try:
            # Your code here
            result = process_data()
            logger.debug(f'Processed data: {result}')
            return Response(result)
        except Exception as e:
            logger.error(f'Error processing data: {str(e)}', exc_info=True)
            raise
"""

import logging


def get_logger(name):
    """
    Get a logger instance for the given name.

    Args:
        name (str): The name of the logger, typically __name__ of the module

    Returns:
        logging.Logger: A configured logger instance

    Example:
        logger = get_logger(__name__)
        logger.info('Application started')
    """
    return logging.getLogger(name)


# Pre-configured loggers for common use cases
django_logger = logging.getLogger('django')
db_logger = logging.getLogger('django.db.backends')
request_logger = logging.getLogger('django.request')
app_logger = logging.getLogger('apps')
