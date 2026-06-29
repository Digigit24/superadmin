"""Management command to seed HMS system roles for the Digitech tenant.

Usage:
    python manage.py setup_hms_tenant
    python manage.py setup_hms_tenant --tenant-slug=myhospital
    python manage.py setup_hms_tenant --force   # overwrite permissions even if role exists

What it does:
  1. Finds (or creates) a tenant with 'hms' in enabled_modules
  2. Seeds 7 system roles with permissions that match the PERMISSION_SCHEMA in
     apps/common/constants.py — the same schema the frontend PermissionMatrix renders
  3. Creates one sample user per role (password: Celiyo@2026)
  4. Prints the tenant_id UUID needed for digihms seed data

Role permission design:
  - hospital_admin : full HMS access + admin.full_access (can manage roles/users)
  - doctor         : own OPD consult + own IPD, team patient view, diagnostics order
  - nurse          : team IPD/clinical, team patient edit
  - receptionist   : all patient registration, all appointments, all OPD triage, basic IPD view
  - cashier        : all payments/billing, opd & ipd bill actions
  - pharmacist     : full pharmacy (sell, stock, statistics), patient view
  - staff          : read-only view across patients/appointments/opd/ipd
"""

from django.core.management.base import BaseCommand
from apps.tenants.models import Tenant
from apps.accounts.models import CustomUser, Role


class Command(BaseCommand):
    help = "Seed HMS system roles and sample users for the Digitech tenant"

    # ─── Role definitions ─────────────────────────────────────────────────────
    # Permission structure MUST match PERMISSION_SCHEMA in apps/common/constants.py.
    # Format: { "<module>": { "<resource>": { "<action>": true | "own" | "team" | "all" } } }
    # Scope hierarchy: "own" < "team" < "all"
    HMS_ROLES = [
        # ── 1. hospital_admin ──────────────────────────────────────────────
        {
            "name": "hospital_admin",
            "description": "Hospital Administrator — full HMS + user/role management access",
            "permissions": {
                # Full admin access (required for IsTenantAdmin permission class)
                "admin": {
                    "full_access": {"enabled": True},
                    "users": {"view": "all", "create": True, "edit": "all", "delete": True},
                    "roles": {"view": "all", "create": True, "edit": "all", "delete": True},
                    "settings": {"view": "all", "edit": "all"},
                },
                "hms": {
                    "clinical": {
                        "view": "all", "create": True, "edit": "all",
                        "delete": True, "export": "all",
                    },
                    "hospital": {
                        "view": "all", "edit_config": "all", "create": True,
                        "edit": "all", "delete": True,
                    },
                    "patients": {
                        "view": "all", "create": True, "edit": "all",
                        "delete": True, "export": "all",
                    },
                    "doctors": {
                        "view": "all", "create": True, "edit": "all",
                        "delete": True, "export": "all", "set_availability": "all",
                    },
                    "appointments": {
                        "view": "all", "create": True, "edit": "all", "delete": True,
                        "cancel": "all", "reschedule": "all",
                    },
                    "opd": {
                        "view": "all", "create": True, "edit": "all", "delete": True,
                        "export": "all", "consult": "all", "bill": "all", "settings": "all",
                    },
                    "ipd": {
                        "view": "all", "create": True, "edit": "all", "delete": True,
                        "export": "all", "admit": True, "discharge": "all",
                        "transfer": "all", "bill": "all",
                    },
                    "diagnostics": {
                        "view": "all", "create": True, "edit": "all", "delete": True,
                        "export": "all", "order": True, "report": "all", "approve": "all",
                    },
                    "pharmacy": {
                        "view": "all", "create": True, "edit": "all", "delete": True,
                        "export": "all", "sell": True, "stock_adjust": "all",
                        "statistics": "all",
                    },
                    "payments": {
                        "view": "all", "create": True, "edit": "all", "delete": True,
                        "export": "all", "refund": "all", "reconcile": "all",
                    },
                    "services": {
                        "view": "all", "create": True, "edit": "all", "delete": True,
                    },
                    "orders": {
                        "view": "all", "create": True, "edit": "all", "delete": True,
                        "pay": "all", "refund": "all",
                    },
                    "panchakarma": {
                        "view": "all", "create": True, "edit": "all", "delete": True,
                    },
                },
            },
        },

        # ── 2. doctor ──────────────────────────────────────────────────────
        {
            "name": "doctor",
            "description": "Doctor — own OPD/IPD consultations, team patient view, diagnostics ordering",
            "permissions": {
                "hms": {
                    "clinical": {
                        "view": "team", "create": True, "edit": "own",
                    },
                    "patients": {
                        "view": "team",   # can see patients in their area
                        "create": True,   # may register walk-ins
                        "edit": "team",
                        "export": "own",
                    },
                    "doctors": {
                        "view": "all",
                        "set_availability": "own",  # only own schedule
                    },
                    "appointments": {
                        "view": "own",    # own appointment queue
                        "create": True,
                        "edit": "own",
                        "cancel": "own",
                        "reschedule": "own",
                    },
                    "opd": {
                        "view": "own",      # own OPD visits
                        "create": True,
                        "edit": "own",
                        "consult": "own",   # clinical consult action
                        "export": "own",
                    },
                    "ipd": {
                        "view": "own",      # own admitted patients
                        "edit": "own",
                        "admit": True,      # can admit patients
                        "discharge": "own", # own patients only
                        "transfer": "own",
                    },
                    "diagnostics": {
                        "view": "team",
                        "order": True,      # can order tests
                        "report": "team",   # can view reports
                    },
                    "pharmacy": {
                        "view": "team",     # view prescriptions
                    },
                },
            },
        },

        # ── 3. nurse ───────────────────────────────────────────────────────
        {
            "name": "nurse",
            "description": "Nurse — team IPD/OPD clinical support, patient vitals and care",
            "permissions": {
                "hms": {
                    "clinical": {
                        "view": "team", "create": True, "edit": "team",
                    },
                    "patients": {
                        "view": "team",
                        "edit": "team",     # update vitals, notes
                    },
                    "doctors": {
                        "view": "all",      # see doctor list for referrals
                    },
                    "appointments": {
                        "view": "team",
                        "edit": "team",     # can update appointment status
                    },
                    "opd": {
                        "view": "team",
                        "edit": "team",     # triage notes, vitals
                    },
                    "ipd": {
                        "view": "team",
                        "edit": "team",     # nursing notes, vitals
                    },
                    "diagnostics": {
                        "view": "team",
                        "report": "team",   # view/upload reports
                    },
                    "pharmacy": {
                        "view": "team",     # view prescriptions for dispensing reference
                    },
                },
            },
        },

        # ── 4. receptionist ────────────────────────────────────────────────
        {
            "name": "receptionist",
            "description": "Receptionist — patient registration, appointments, OPD triage, basic billing",
            "permissions": {
                "hms": {
                    "patients": {
                        "view": "all",
                        "create": True,     # register new patients
                        "edit": "all",      # update demographics
                        "export": "all",
                    },
                    "doctors": {
                        "view": "all",      # see doctor schedules
                    },
                    "appointments": {
                        "view": "all",
                        "create": True,     # book appointments
                        "edit": "all",
                        "cancel": "all",
                        "reschedule": "all",
                    },
                    "opd": {
                        "view": "all",
                        "create": True,     # open OPD visits
                        "bill": "all",      # generate OPD bills
                    },
                    "ipd": {
                        "view": "all",      # view admissions for coordination
                    },
                    "payments": {
                        "view": "all",
                        "create": True,     # collect payments
                    },
                    "services": {
                        "view": "all",      # view service catalogue for billing
                    },
                },
            },
        },

        # ── 5. cashier ─────────────────────────────────────────────────────
        {
            "name": "cashier",
            "description": "Cashier — billing, payments, refunds, reconciliation",
            "permissions": {
                "hms": {
                    "patients": {
                        "view": "all",      # search patient for billing
                    },
                    "opd": {
                        "view": "all",
                        "bill": "all",      # OPD billing
                    },
                    "ipd": {
                        "view": "all",
                        "bill": "all",      # IPD billing
                    },
                    "payments": {
                        "view": "all",
                        "create": True,
                        "edit": "all",
                        "export": "all",
                        "refund": "all",
                        "reconcile": "all",
                    },
                    "orders": {
                        "view": "all",
                        "create": True,     # create payment orders
                        "pay": "all",
                        "refund": "all",
                    },
                    "services": {
                        "view": "all",      # view service catalogue for pricing
                    },
                },
            },
        },

        # ── 6. pharmacist ──────────────────────────────────────────────────
        {
            "name": "pharmacist",
            "description": "Pharmacist — dispensing, stock management, pharmacy billing",
            "permissions": {
                "hms": {
                    "patients": {
                        "view": "all",      # look up patient for prescription
                    },
                    "pharmacy": {
                        "view": "all",
                        "create": True,     # add stock, create entries
                        "edit": "all",
                        "sell": True,       # dispense medications
                        "stock_adjust": "all",
                        "statistics": "all",
                        "export": "all",
                    },
                    "payments": {
                        "view": "all",
                        "create": True,     # pharmacy-counter payments
                    },
                },
            },
        },

        # ── 7. staff ───────────────────────────────────────────────────────
        {
            "name": "staff",
            "description": "General Staff — read-only view across HMS modules",
            "permissions": {
                "hms": {
                    "patients": {"view": "team"},
                    "doctors": {"view": "all"},
                    "appointments": {"view": "team"},
                    "opd": {"view": "team"},
                    "ipd": {"view": "team"},
                    "services": {"view": "all"},
                },
            },
        },
    ]

    # One sample user per role
    HMS_USERS = [
        {
            "email": "admin@digitech.celiyo.com",
            "first_name": "Admin", "last_name": "User",
            "role": "hospital_admin",
        },
        {
            "email": "doctor@digitech.celiyo.com",
            "first_name": "Arjun", "last_name": "Sharma",
            "role": "doctor",
        },
        {
            "email": "nurse@digitech.celiyo.com",
            "first_name": "Priya", "last_name": "Verma",
            "role": "nurse",
        },
        {
            "email": "reception@digitech.celiyo.com",
            "first_name": "Sneha", "last_name": "Patel",
            "role": "receptionist",
        },
        {
            "email": "cashier@digitech.celiyo.com",
            "first_name": "Vikram", "last_name": "Singh",
            "role": "cashier",
        },
        {
            "email": "pharmacist@digitech.celiyo.com",
            "first_name": "Rahul", "last_name": "Gupta",
            "role": "pharmacist",
        },
        {
            "email": "staff@digitech.celiyo.com",
            "first_name": "Meena", "last_name": "Rao",
            "role": "staff",
        },
    ]

    DEFAULT_PASSWORD = "Celiyo@2026"

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant-slug",
            default="digitech",
            help="Slug of the tenant to seed roles into (default: digitech)",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite permissions on existing roles (default: only update if role already exists)",
        )
        parser.add_argument(
            "--no-users",
            action="store_true",
            help="Skip sample user creation",
        )

    def handle(self, *args, **options):
        tenant_slug = options["tenant_slug"]
        force = options["force"]
        skip_users = options["no_users"]

        # ── 1. Find or create the tenant ──────────────────────────────────
        tenant = Tenant.objects.filter(slug=tenant_slug).first()
        if not tenant:
            tenant = Tenant.objects.filter(name__iexact=tenant_slug).first()
        if not tenant:
            tenant = Tenant.objects.create(
                name=tenant_slug.capitalize(),
                slug=tenant_slug,
                enabled_modules=["hms", "admin"],
            )
            self.stdout.write(self.style.SUCCESS(f"✓ Created tenant: {tenant.name} ({tenant.id})"))
        else:
            self.stdout.write(f"→ Found tenant: {tenant.name} ({tenant.id})")

        # ── 2. Ensure 'hms' and 'admin' are in enabled_modules ────────────
        modules = list(tenant.enabled_modules) if tenant.enabled_modules else []
        changed = False
        for required in ("hms", "admin"):
            if required not in modules:
                modules.append(required)
                changed = True
        if changed:
            tenant.enabled_modules = modules
            tenant.save(update_fields=["enabled_modules"])
            self.stdout.write(self.style.SUCCESS(f"✓ enabled_modules updated: {modules}"))
        else:
            self.stdout.write(f"→ enabled_modules OK: {modules}")

        # ── 3. Seed roles ─────────────────────────────────────────────────
        self.stdout.write("\nSeeding HMS roles:")
        role_map: dict[str, Role] = {}

        for role_def in self.HMS_ROLES:
            role, created = Role.objects.get_or_create(
                tenant=tenant,
                name=role_def["name"],
                defaults={
                    "description": role_def["description"],
                    "permissions": role_def["permissions"],
                    "is_active": True,
                },
            )
            if not created and force:
                role.permissions = role_def["permissions"]
                role.description = role_def["description"]
                role.is_active = True
                role.save(update_fields=["permissions", "description", "is_active", "updated_at"])

            role_map[role.name] = role
            marker = "✓ Created" if created else ("✓ Updated" if force else "→ Exists")
            self.stdout.write(f"  {marker}: {role.name}")

        # ── 4. Seed sample users ──────────────────────────────────────────
        if not skip_users:
            self.stdout.write("\nSeeding sample users:")
            for user_def in self.HMS_USERS:
                user = CustomUser.objects.filter(email=user_def["email"]).first()
                if not user:
                    user = CustomUser.objects.create_user(
                        email=user_def["email"],
                        password=self.DEFAULT_PASSWORD,
                        first_name=user_def["first_name"],
                        last_name=user_def["last_name"],
                        tenant=tenant,
                        is_active=True,
                    )
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Created user: {user.email}"))
                else:
                    if user.tenant_id != tenant.id:
                        user.tenant = tenant
                        user.save(update_fields=["tenant"])
                    self.stdout.write(f"  → Existing user: {user.email}")

                role = role_map.get(user_def["role"])
                if role:
                    user.roles.set([role])
                    self.stdout.write(f"      role → {user_def['role']}")

        # ── 5. Summary ────────────────────────────────────────────────────
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS(f"TENANT ID  : {tenant.id}"))
        self.stdout.write(self.style.SUCCESS(f"TENANT SLUG: {tenant.slug}"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(
            "\nRoles seeded: "
            + ", ".join(role_map.keys())
        )
        self.stdout.write(
            "\nDefault password for all sample users: " + self.DEFAULT_PASSWORD
        )
        self.stdout.write(
            "\nAdd to digihms/.env:\n"
            "  DEFAULT_TENANT_ID=" + str(tenant.id)
        )
        if not force:
            self.stdout.write(
                "\nTip: run with --force to overwrite permissions on existing roles."
            )
