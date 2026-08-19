"""Pure-logic catalog contract tests; no Django database required."""
import unittest

from apps.common.generated_permissions import PERMISSION_CATALOG


class PermissionCatalogContractTests(unittest.TestCase):
    def test_active_keys_are_flat_and_enforced(self):
        for entry in PERMISSION_CATALOG:
            if entry["status"] not in ("active", "ui_only"):
                continue
            self.assertRegex(entry["key"], r"^(admin|hms|crm|whatsapp|integrations|telephony|meetings|tasks)\.[a-z_]+\.[a-z_]+$")
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

    def test_crm_permission_keys_used_in_digicrm_are_catalogued(self):
        """Every full CRM permission-key string used in the digicrm backend must exist in the catalog."""
        import ast
        import re
        from pathlib import Path
        by_key = {entry["key"]: entry for entry in PERMISSION_CATALOG}
        digicrm_root = Path(__file__).resolve().parents[3] / ".." / "digicrm"
        self.assertTrue(digicrm_root.exists(), f"digicrm root not found: {digicrm_root}")
        crm_key_pattern = re.compile(
            r"^(?:crm|whatsapp|integrations|telephony|meetings|tasks)\.[a-z_]+\.[a-z_]+$"
        )

        def _iter_string_literals(tree):
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    yield node.value
                elif isinstance(node, ast.Str):  # Python < 3.8 compatibility
                    yield node.s

        used_keys = set()
        # Restrict to view/permission files where CRM permission-key strings are actually used.
        for source_file in digicrm_root.rglob("*.py"):
            if "/venv/" in str(source_file):
                continue
            if source_file.name not in {"views.py", "permissions.py", "mixins.py"}:
                continue
            tree = ast.parse(source_file.read_text(encoding="utf-8"), filename=str(source_file))
            for value in _iter_string_literals(tree):
                if crm_key_pattern.match(value):
                    used_keys.add(value)
        for key in used_keys:
            self.assertIn(key, by_key, f"Permission key {key} used in digicrm but missing from catalog")

    def test_crm_action_permission_map_keys_are_catalogued(self):
        """Every action_permission_map entry in digicrm must resolve to a catalog key."""
        import ast
        from pathlib import Path
        by_key = {entry["key"]: entry for entry in PERMISSION_CATALOG}
        digicrm_root = Path(__file__).resolve().parents[3] / ".." / "digicrm"
        self.assertTrue(digicrm_root.exists(), f"digicrm root not found: {digicrm_root}")

        def _literal_value(node):
            if isinstance(node, ast.Constant):
                return node.value
            if isinstance(node, ast.Str):  # Python < 3.8 compatibility
                return node.s
            return None

        for source_file in digicrm_root.rglob("*.py"):
            if "/venv/" in str(source_file):
                continue
            tree = ast.parse(source_file.read_text(encoding="utf-8"), filename=str(source_file))
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                module = resource = None
                action_map = {}
                for item in node.body:
                    if not isinstance(item, ast.Assign):
                        continue
                    target = item.targets[0]
                    if not isinstance(target, ast.Name):
                        continue
                    if target.id == "permission_module":
                        module = _literal_value(item.value)
                    elif target.id == "permission_resource":
                        resource = _literal_value(item.value)
                    elif target.id == "action_permission_map" and isinstance(item.value, ast.Dict):
                        action_map = {
                            _literal_value(k): _literal_value(v)
                            for k, v in zip(item.value.keys, item.value.values)
                            if _literal_value(k) is not None and _literal_value(v) is not None
                        }
                if module and resource and action_map:
                    for action_name in action_map.values():
                        key = f"{module}.{resource}.{action_name}"
                        self.assertIn(
                            key, by_key,
                            f"{node.name}.action_permission_map maps to {key} which is not in the catalog"
                        )
