# Merge marker for independent accounts 0002 branches; intentionally no operations.
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_customuser_preferences"),
        ("accounts", "0002_integrationtoken"),
    ]

    operations = []
