"""Pure-logic catalog contract tests; no Django database required."""
import unittest

from apps.common.generated_permissions import PERMISSION_CATALOG


class PermissionCatalogContractTests(unittest.TestCase):
    # Modules the catalog is expected to carry. This list used to read
    # `(admin|hms)`, which quietly encoded "this catalog is HMS-only" — and that
    # assumption is why nobody noticed the 84 crm/whatsapp/telephony/meetings/
    # tasks keys living in the GENERATED artifacts but not in their source. They
    # are in the YAML now, so the assertion says so.
    CATALOG_MODULES = (
        "admin", "hms", "crm", "whatsapp", "integrations", "telephony",
        "meetings", "tasks", "real_estate",
    )

    def test_active_keys_are_flat_and_enforced(self):
        # Longest-first so `real_estate` is not shadowed by a shorter prefix.
        alternation = "|".join(sorted(self.CATALOG_MODULES, key=len, reverse=True))
        pattern = r"^(%s)\.[a-z_]+\.[a-z_]+$" % alternation
        for entry in PERMISSION_CATALOG:
            if entry["status"] not in ("active", "ui_only"):
                continue
            self.assertRegex(entry["key"], pattern)
            self.assertNotIn("team", entry["allowed_values"])
            self.assertNotEqual(entry["enforced_by"], ["none"], entry["key"])

    def test_every_catalog_module_declares_who_enforces_it(self):
        """
        A module missing from `enforced_by_by_module` silently falls back to
        HMSPermission, which for a CRM-side key would be wrong and invisible.
        """
        import yaml
        from pathlib import Path

        # parents[3] is the superadmin root, same as the seed-role test below.
        catalog_path = (
            Path(__file__).resolve().parents[3]
            / "apps" / "common" / "permissions_catalog.yaml"
        )
        catalog = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
        declared = set(catalog.get("enforced_by_by_module") or {})

        expanded_modules = set(catalog.get("resource_actions") or {})
        self.assertEqual(
            sorted(expanded_modules - declared),
            [],
            "these modules expand declaratively but do not say who enforces them",
        )

    def test_deprecated_aliases_have_a_migration_target_or_note(self):
        for entry in PERMISSION_CATALOG:
            if entry["status"] == "deprecated":
                self.assertTrue(entry.get("alias_of") or entry.get("note"), entry["key"])

    def test_alias_targets_are_active(self):
        by_key = {entry["key"]: entry for entry in PERMISSION_CATALOG}
        for entry in PERMISSION_CATALOG:
            if entry.get("alias_of"):
                self.assertIn(entry["alias_of"], by_key)
                self.assertIn(by_key[entry["alias_of"]]["status"], ("active", "ui_only"))

    def test_seed_role_names_and_catalog_permissions(self):
        # Source inspection keeps this test DB/Django independent.
        from pathlib import Path
        source = Path(__file__).resolve().parents[3] / "apps" / "tenants" / "management" / "commands" / "setup_hms_tenant.py"
        text = source.read_text(encoding="utf-8")
        for role in ("hospital_admin", "doctor", "nurse", "receptionist", "cashier", "pharmacist", "staff"):
            self.assertIn(f'"name": "{role}"', text)
        self.assertNotIn(': "team"', text)

    def test_migration_aliases_match_canonical_targets(self):
        by_key = {entry["key"]: entry for entry in PERMISSION_CATALOG}
        expected = {
            "inventory.manage": "hms.inventory.edit",
            "billing.view_reports": "hms.patients.view_reports",
            "admin.full_access": "admin.full_access.enabled",
        }
        for legacy, canonical in expected.items():
            self.assertEqual(by_key[legacy]["alias_of"], canonical)

    def test_role_merge_scope_precedence_contract(self):
        rank = {"own": 1, "all": 2}
        grants = ["own", "all", "own"]
        self.assertEqual(max(grants, key=rank.__getitem__), "all")
