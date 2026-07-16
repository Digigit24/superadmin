#!/usr/bin/env python3
"""Generate permission artifacts from apps/common/permissions_catalog.yaml.

Run from any directory:
    python superadmin/scripts/generate_permissions.py
    python superadmin/scripts/generate_permissions.py --check
"""
from __future__ import annotations

import argparse
import json
import pprint
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "superadmin" / "apps" / "common" / "permissions_catalog.yaml"
OUTPUTS = (
    ROOT / "superadmin" / "apps" / "common" / "generated_permissions.py",
    ROOT / "dghms" / "common" / "generated_permissions.py",
    ROOT / "celiyohms" / "src" / "constants" / "permissions.ts",
    ROOT / "celiyohms" / "src" / "constants" / "permission-types.ts",
)
REQUIRED_ENTRY_FIELDS = {
    "key", "label", "module", "resource", "action", "allowed_values",
    "scope_model", "status", "enforced_by",
}
VALID_STATUSES = {"active", "ui_only", "deprecated"}


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
                    "enforced_by": (["superadmin.apps.common.permissions.IsTenantAdmin"] if module == "admin" else ["dghms.common.drf_auth.HMSPermission"]),
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
    return f'''# GENERATED — DO NOT EDIT. Source: superadmin/apps/common/permissions_catalog.yaml\n# Catalog version: {catalog["version"]}\n\nPERMISSION_CATALOG = {payload}\n\nACTIVE_PERMISSION_KEYS = tuple({active_keys})\nPERMISSION_BY_KEY = {{entry["key"]: entry for entry in PERMISSION_CATALOG}}\n\ndef get_permission_schema():\n    \"\"\"Build the role-editor schema from active catalog entries.\"\"\"\n    schema = {{}}\n    for entry in PERMISSION_CATALOG:\n        if entry["status"] not in ("active", "ui_only"):\n            continue\n        module = schema.setdefault(entry["module"], {{"label": entry["module"].upper(), "resources": {{}}}})\n        resource = module["resources"].setdefault(entry["resource"], {{"label": entry["resource"].replace("_", " ").title(), "actions": {{}}}})\n        resource["actions"][entry["action"]] = ({{"type": "scope", "options": ["own", "all"]}} if entry["scope_model"] == "own_all" else {{"type": "boolean"}})\n    return schema\n\nPERMISSION_SCHEMA = get_permission_schema()\n'''


def typescript_outputs(catalog: dict) -> tuple[str, str]:
    active = [entry for entry in catalog["entries"] if entry["status"] in {"active", "ui_only"}]
    lines = ["// GENERATED — DO NOT EDIT. Source: superadmin/apps/common/permissions_catalog.yaml", "", "export const PERMISSIONS = {"]
    for entry in active:
        lines.append(f'  "{entry["key"]}": "{entry["key"]}",')
    lines.extend(["} as const;", "", "export type PermissionKey = keyof typeof PERMISSIONS;", "export type PermissionValue = (typeof PERMISSIONS)[PermissionKey];", ""])
    types = """// GENERATED — DO NOT EDIT. Source: superadmin/apps/common/permissions_catalog.yaml\n\nexport type PermissionScope = \"own\" | \"all\";\nexport type PermissionGrant = boolean | PermissionScope;\n"""
    return "\n".join(lines), types


def render(catalog: dict) -> dict[Path, str]:
    py = python_output(catalog)
    ts, types = typescript_outputs(catalog)
    return {OUTPUTS[0]: py, OUTPUTS[1]: py, OUTPUTS[2]: ts, OUTPUTS[3]: types}


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
