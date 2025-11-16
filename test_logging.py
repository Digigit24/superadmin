"""
Test script for the logging system.

This script demonstrates and tests the logging configuration.
Run this script with: python test_logging.py
"""

import os
import django

# Setup Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.common.logger import get_logger

# Get logger for this module
logger = get_logger(__name__)

def test_logging():
    """Test all logging levels."""
    print("\n" + "="*60)
    print("Testing Logging System")
    print("="*60 + "\n")

    print("Testing different log levels...")
    print("-" * 60)

    logger.debug("This is a DEBUG message - detailed diagnostic information")
    print("✓ DEBUG message logged")

    logger.info("This is an INFO message - general informational message")
    print("✓ INFO message logged")

    logger.warning("This is a WARNING message - something unexpected happened")
    print("✓ WARNING message logged")

    logger.error("This is an ERROR message - a serious problem occurred")
    print("✓ ERROR message logged")

    logger.critical("This is a CRITICAL message - a very serious error")
    print("✓ CRITICAL message logged")

    print("\n" + "-" * 60)
    print("Testing exception logging...")
    print("-" * 60)

    try:
        # Intentionally cause an error
        result = 1 / 0
    except Exception as e:
        logger.error("Caught an exception", exc_info=True)
        print("✓ Exception logged with traceback")

    print("\n" + "="*60)
    print("Logging Test Complete!")
    print("="*60)
    print("\nCheck the following log files in the 'logs/' directory:")
    print("  - debug.log  : Contains all DEBUG and higher messages (when DEBUG=True)")
    print("  - info.log   : Contains INFO and higher messages")
    print("  - error.log  : Contains only ERROR and CRITICAL messages")
    print("\nLog files are configured with rotation:")
    print("  - Max size: 10 MB per file")
    print("  - Backup count: 5 files")
    print("\n")

if __name__ == '__main__':
    test_logging()
