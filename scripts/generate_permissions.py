#!/usr/bin/env python3
"""Generate permission artifacts from apps/common/permissions_catalog.yaml.

Run from any directory:
    python superadmin/scripts/generate_permissions.py
    python superadmin/scripts/generate_permissions.py --check
"""
from __future__ import annotations

import argparse
import pprint
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "superadmin" / "apps" / "common" / "permissions_catalog.yaml"
SUPERADMIN_OUTPUT = ROOT / "superadmin" / "apps" / "common" / "generated_permissions.py"
DGHMS_OUTPUT = ROOT / "dghms" / "common" / "generated_permissions.py"
DIGICRM_OUTPUT = ROOT / "digicrm" / "common" / "generated_permissions.py"
CELIYOHMS_PERMISSIONS_OUTPUT = ROOT / "celiyohms" / "src" / "constants" / "permissions.ts"
CELIYOHMS_TYPES_OUTPUT = ROOT / "celiyohms" / "src" / "constants" / "permission-types.ts"
SEPRATECRM_OUTPUT = ROOT / "sepratecrm" / "src" / "constants" / "permissions.ts"
OUTPUTS = (
    SUPERADMIN_OUTPUT,
    DGHMS_OUTPUT,
    DIGICRM_OUTPUT,
    CELIYOHMS_PERMISSIONS_OUTPUT,
    CELIYOHMS_TYPES_OUTPUT,
    SEPRATECRM_OUTPUT,
)
REQUIRED_ENTRY_FIELDS = {
    "key", "label", "module", "resource", "action", "allowed_values",
    "scope_model", "status", "enforced_by",
}
VALID_STATUSES = {"active", "ui_only", "deprecated"}
CRM_MODULES = {"crm", "whatsapp", "integrations", "telephony", "meetings", "tasks"}


def _default_enforcer(module: str) -> list[str]:
    """Return the canonical enforcement class for a catalog module."""
    if module == "admin":
        return ["superadmin.apps.common.permissions.IsTenantAdmin"]
    if module in CRM_MODULES:
        return ["digicrm.common.permissions.HasDigiPermission"]
    return ["dghms.common.drf_auth.HMSPermission"]


def load_catalog() -> dict:
    with CATALOG_PATH.open(encoding="utf-8") as catalog_file:
        catalog = yaml.safe_load(catalog_file)
    if not isinstance(catalog, dict) or not catalog.get("version"):
        raise ValueError("catalog must contain a non-empty top-level version")
    entries = list(catalog.get("entries", []))
    # Keep the YAML readable while materializing a complete entry for every
    # schema key.  Generated artifacts always receive only fully populated
    # entries, including all required metadata.
    for module, resources in catalog.get("resource_actions", {}).items():
        for resource, actions in resources.items():
            for action, kind in actions.items():
                if kind not in {"scope", "boolean"}:
                    raise ValueError(f"{module}.{resource}.{action}: unknown action kind {kind}")
                entries.append({
                    "key": f"{module}.{resource}.{action}",
                    "label": f"{resource.replace('_', ' ').title()}: {action.replace('_', ' ').title()}",
                    "module": module,
                    "resource": resource,
                    "action": action,
                    "allowed_values": ["own", "all"] if kind == "scope" else ["boolean"],
                    "scope_model": "own_all" if kind == "scope" else "none",
                    "status": "active",
                    "enforced_by": _default_enforcer(module),
                    "sensitive": action == "delete" or (module == "hms" and resource == "payments" and action in {"refund", "reconcile"}),
                })
    catalog["entries"] = entries
    if not isinstance(entries, list) or not entries:
        raise ValueError("catalog must contain a non-empty entries list")
    seen = set()
    for entry in entries:
        missing = REQUIRED_ENTRY_FIELDS - entry.keys()
        if missing:
            raise ValueError(f"{entry.get('key', '<unknown>')}: missing {sorted(missing)}")
        key = entry["key"]
        if key in seen:
            raise ValueError(f"duplicate permission key: {key}")
        seen.add(key)
        if entry["status"] not in VALID_STATUSES:
            raise ValueError(f"{key}: invalid status {entry['status']}")
        if entry["scope_model"] not in {"none", "own_all"}:
            raise ValueError(f"{key}: scope_model must be none or own_all")
        if entry["scope_model"] == "own_all" and entry["allowed_values"] != ["own", "all"]:
            raise ValueError(f"{key}: scoped entries must allow exactly own/all")
        if entry["scope_model"] == "none" and entry["allowed_values"] != ["boolean"]:
            raise ValueError(f"{key}: boolean entries must allow exactly boolean")
        if entry.get("alias_of") is not None and not isinstance(entry["alias_of"], str):
            raise ValueError(f"{key}: alias_of must be a string or null")
    return catalog


def python_output(catalog: dict) -> str:
    entries = catalog["entries"]
    active = [entry for entry in entries if entry["status"] in {"active", "ui_only"}]
    payload = pprint.pformat(entries, width=100, sort_dicts=True)
    active_keys = pprint.pformat([entry["key"] for entry in active], width=100)
    return f'''# GENERATED — DO NOT EDIT. Source: superadmin/apps/common/permissions_catalog.yaml
# Catalog version: {catalog["version"]}

PERMISSION_CATALOG = {payload}

ACTIVE_PERMISSION_KEYS = tuple({active_keys})
PERMISSION_BY_KEY = {{entry["key"]: entry for entry in PERMISSION_CATALOG}}

def get_permission_schema():
    """Build the role-editor schema from active catalog entries."""
    schema = {{}}
    for entry in PERMISSION_CATALOG:
        if entry["status"] not in ("active", "ui_only"):
            continue
        module = schema.setdefault(entry["module"], {{"label": entry["module"].upper(), "resources": {{}}}})
        resource = module["resources"].setdefault(entry["resource"], {{"label": entry["resource"].replace("_", " ").title(), "actions": {{}}}})
        resource["actions"][entry["action"]] = ({{"type": "scope", "options": ["own", "all"]}} if entry["scope_model"] == "own_all" else {{"type": "boolean"}})
    return schema

PERMISSION_SCHEMA = get_permission_schema()
'''


def _crm_constant_name(entry: dict) -> str:
    """Turn a CRM catalog key into a Python class attribute name."""
    parts = entry["key"].split(".")
    return "_".join(p.upper() for p in parts)


def digicrm_python_output(catalog: dict) -> str:
    """Python artifacts for DigiCRM: catalog + CRMPermissions constants class."""
    base = python_output(catalog)
    active = [entry for entry in catalog["entries"] if entry["status"] in {"active", "ui_only"}]
    crm_entries = [entry for entry in active if entry["module"] in CRM_MODULES]
    constants_lines = [f"    {_crm_constant_name(entry)} = \"{entry['key']}\"" for entry in crm_entries]
    constants_block = "\n".join(constants_lines)
    crm_class = f'''

class CRMPermissions:
    """Canonical CRM permission keys generated from the SuperAdmin catalog."""

{constants_block}
'''
    return base + crm_class


def typescript_outputs(catalog: dict) -> tuple[str, str]:
    active = [entry for entry in catalog["entries"] if entry["status"] in {"active", "ui_only"}]
    lines = ["// GENERATED — DO NOT EDIT. Source: superadmin/apps/common/permissions_catalog.yaml", "", "export const PERMISSIONS = {"]
    for entry in active:
        lines.append(f'  "{entry["key"]}": "{entry["key"]}",')
    lines.extend(["} as const;", "", "export type PermissionKey = keyof typeof PERMISSIONS;", "export type PermissionValue = (typeof PERMISSIONS)[PermissionKey];", ""])
    types = """// GENERATED — DO NOT EDIT. Source: superadmin/apps/common/permissions_catalog.yaml

export type PermissionScope = \"own\" | \"all\";
export type PermissionGrant = boolean | PermissionScope;
"""
    return "\n".join(lines), types


def sepratecrm_typescript_output(catalog: dict) -> str:
    """Single-file TypeScript constants for the separate CRM React frontend."""
    active = [entry for entry in catalog["entries"] if entry["status"] in {"active", "ui_only"}]
    lines = [
        "// GENERATED — DO NOT EDIT. Source: superadmin/apps/common/permissions_catalog.yaml",
        "",
        "export const PERMISSIONS = {",
    ]
    for entry in active:
        lines.append(f'  "{entry["key"]}": "{entry["key"]}",')
    lines.extend([
        "} as const;",
        "",
        "export type PermissionKey = keyof typeof PERMISSIONS;",
        "export type PermissionValue = (typeof PERMISSIONS)[PermissionKey];",
        "",
        'export type PermissionScope = "own" | "all";',
        "export type PermissionGrant = boolean | PermissionScope;",
        "",
    ])
    return "\n".join(lines)


def render(catalog: dict) -> dict[Path, str]:
    py = python_output(catalog)
    ts, types = typescript_outputs(catalog)
    return {
        SUPERADMIN_OUTPUT: py,
        DGHMS_OUTPUT: py,
        DIGICRM_OUTPUT: digicrm_python_output(catalog),
        CELIYOHMS_PERMISSIONS_OUTPUT: ts,
        CELIYOHMS_TYPES_OUTPUT: types,
        SEPRATECRM_OUTPUT: sepratecrm_typescript_output(catalog),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if generated files are stale")
    args = parser.parse_args()
    expected = render(load_catalog())
    stale = [path for path, contents in expected.items() if not path.exists() or path.read_text(encoding="utf-8") != contents]
    if args.check:
        if stale:
            print("Generated permission artifacts are stale:", *[str(path.relative_to(ROOT)) for path in stale], sep="\n  ", file=sys.stderr)
            return 1
        print("Permission artifacts are up to date.")
        return 0
    for path, contents in expected.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
