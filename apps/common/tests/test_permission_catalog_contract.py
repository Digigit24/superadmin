"""Pure-logic catalog contract tests; no Django database required."""
import unittest

from apps.common.generated_permissions import PERMISSION_CATALOG


class PermissionCatalogContractTests(unittest.TestCase):
    def test_active_keys_are_flat_and_enforced(self):
        for entry in PERMISSION_CATALOG:
            if entry["status"] not in ("active", "ui_only"):
                continue
            self.assertRegex(entry["key"], r"^(admin|hms)\.[a-z_]+\.[a-z_]+$")
            self.assertNotIn("team", entry["allowed_values"])
            self.assertNotEqual(entry["enforced_by"], ["none"], entry["key"])

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
