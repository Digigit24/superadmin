"""Seed the DigiCRM Sales Executive role for a tenant.

Usage:
    python manage.py setup_crm_sales_role
    python manage.py setup_crm_sales_role --tenant-slug=digitechtenant --force
"""

from django.core.management.base import BaseCommand

from apps.accounts.models import Role
from apps.tenants.models import Tenant


SALES_EXECUTIVE_PERMISSIONS = {
    "crm": {
        "leads": {
            "view": "own",
            "create": True,
            "edit": "own",
            "delete": False,
            "export": "own",
        },
        "activities": {
            "view": "own",
            "create": True,
            "edit": "own",
            "delete": False,
        },
        "tasks": {
            "view": "own",
            "create": True,
            "edit": "own",
            "delete": False,
            "assign": False,
        },
        "meetings": {
            "view": "own",
            "create": True,
            "edit": "own",
            "delete": False,
            "cancel": "own",
        },
        "statuses": {
            "view": "all",
            "create": False,
            "edit": "own",
            "delete": False,
        },
        "payments": {
            "view": "own",
            "create": True,
            "edit": "own",
            "delete": False,
        },
        "settings": {
            "view": False,
            "edit": False,
        },
    },
    "whatsapp": {
        "messages": {
            "view": True,
            "send": True,
            "create": True,
            "edit": False,
            "delete": False,
        },
        "templates": {
            "view": True,
            "create": False,
            "edit": False,
            "delete": False,
        },
        "campaigns": {
            "view": False,
            "create": False,
            "edit": False,
            "delete": False,
        },
        "sequences": {
            "view": True,
            "create": False,
            "edit": False,
            "delete": False,
        },
        "settings": {
            "view": False,
            "create": False,
            "edit": False,
            "delete": False,
        },
    },
    "telephony": {
        "calls": {
            "view": "own",
            "create": True,
            "edit": "own",
            "delete": False,
        },
        "sms": {
            "view": "own",
            "create": True,
        },
        "agents": {
            "view": "own",
            "create": False,
            "edit": "own",
            "delete": False,
        },
        "callbacks": {
            "view": "own",
        },
        "settings": {
            "view": False,
            "create": False,
            "edit": False,
            "delete": False,
        },
    },
}


class Command(BaseCommand):
    help = "Seed the Sales Executive role for DigiCRM."

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant-slug",
            default="digitechtenant",
            help="Tenant slug or exact name. Default: digitechtenant",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite permissions if the role already exists.",
        )

    def handle(self, *args, **options):
        tenant_slug = options["tenant_slug"]
        force = options["force"]

        tenant = (
            Tenant.objects.filter(slug=tenant_slug).first()
            or Tenant.objects.filter(name__iexact=tenant_slug).first()
        )

        if tenant is None:
            self.stderr.write(self.style.ERROR(f"Tenant not found: {tenant_slug}"))
            return

        required_modules = ["crm", "whatsapp", "telephony"]
        modules = list(tenant.enabled_modules or [])
        changed_modules = False
        for module in required_modules:
            if module not in modules:
                modules.append(module)
                changed_modules = True
        if changed_modules:
            tenant.enabled_modules = modules
            tenant.save(update_fields=["enabled_modules"])
            self.stdout.write(self.style.SUCCESS(f"Updated enabled_modules: {modules}"))

        role, created = Role.objects.get_or_create(
            tenant=tenant,
            name="Sales Executive",
            defaults={
                "description": "Sales user with own-lead CRM access and no configuration panels.",
                "permissions": SALES_EXECUTIVE_PERMISSIONS,
                "is_active": True,
            },
        )

        if created:
            self.stdout.write(self.style.SUCCESS("Created role: Sales Executive"))
        elif force:
            role.description = "Sales user with own-lead CRM access and no configuration panels."
            role.permissions = SALES_EXECUTIVE_PERMISSIONS
            role.is_active = True
            role.save(update_fields=["description", "permissions", "is_active", "updated_at"])
            self.stdout.write(self.style.SUCCESS("Updated role: Sales Executive"))
        else:
            self.stdout.write("Role already exists. Use --force to overwrite permissions.")

        self.stdout.write(self.style.SUCCESS(f"Tenant: {tenant.name} ({tenant.slug})"))
        self.stdout.write(self.style.SUCCESS(f"Tenant ID: {tenant.id}"))
