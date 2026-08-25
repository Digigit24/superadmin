#!/usr/bin/env python3
"""Generate permission artifacts from apps/common/permissions_catalog.yaml.

Run from any directory:
    python superadmin/scripts/generate_permissions.py
    python superadmin/scripts/generate_permissions.py --check
    python superadmin/scripts/generate_permissions.py --allow-shrink

Writing REFUSES by default if it would remove permission keys from any output.
See `keys_that_would_be_lost`.
"""
from __future__ import annotations

import argparse
import json
import pprint
import re
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
    # digicrm was hand-maintained for as long as this catalog could not express
    # its keys. Now that it can, this file is generated like the rest — it just
    # carries one extra artifact, the CRMPermissions constants class.
    ROOT / "digicrm" / "common" / "generated_permissions.py",
)

# Modules whose keys digicrm's CRMPermissions class does NOT carry: it is the
# CRM-side constant set, and digicrm has no use for hospital or tenant-admin
# keys even though it holds the whole catalog.
CRM_PERMISSIONS_EXCLUDED_MODULES = {"hms", "admin"}
REQUIRED_ENTRY_FIELDS = {
    "key", "label", "module", "resource", "action", "allowed_values",
    "scope_model", "status", "enforced_by",
}
VALID_STATUSES = {"active", "ui_only", "deprecated"}

# A dotted permission key as it appears in each artifact:
#   Python  ->  'key': 'whatsapp.contacts.view',
#   TS      ->  "whatsapp.contacts.view": "whatsapp.contacts.view",
_PY_KEY = re.compile(r"'key': '([^']+)'")
_TS_KEY = re.compile(r'"([a-z_]+(?:\.[a-z_]+)+)":')


# Fallback for a catalog that predates `enforced_by_by_module`. Every module
# should be named there; this only keeps an older YAML working.
_LEGACY_ENFORCED_BY = {"admin": ["superadmin.apps.common.permissions.IsTenantAdmin"]}
_LEGACY_DEFAULT = ["dghms.common.drf_auth.HMSPermission"]


def enforced_by_for(catalog: dict, module: str) -> list[str]:
    """
    Who checks this module's keys at runtime.

    Was hardcoded to "IsTenantAdmin for admin, HMSPermission for everything
    else", which is why the 84 crm/whatsapp/telephony/meetings/tasks keys could
    not live in this catalog: they are enforced by digicrm's HasDigiPermission
    and the declarative path had no way to say so. Moving the mapping into the
    YAML is what makes those modules expressible here at all.
    """
    declared = (catalog.get("enforced_by_by_module") or {}).get(module)
    if declared:
        return list(declared)
    return list(_LEGACY_ENFORCED_BY.get(module, _LEGACY_DEFAULT))


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
                    "enforced_by": enforced_by_for(catalog, module),
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


def crm_permissions_class(catalog: dict) -> str:
    """
    digicrm's `CRMPermissions`, the one artifact the other Python outputs do not
    carry. Purely derived: the constant name is the key upper-cased with dots as
    underscores, over the active non-HMS/admin keys in catalog order. Verified
    to reproduce the hand-written class exactly — same set, same order, same
    names — before this file was ever generated.
    """
    keys = [
        entry["key"]
        for entry in catalog["entries"]
        if entry["status"] in {"active", "ui_only"}
        and entry["module"] not in CRM_PERMISSIONS_EXCLUDED_MODULES
    ]
    lines = [
        "",
        "",
        "class CRMPermissions:",
        '    """Canonical CRM permission keys generated from the SuperAdmin catalog."""',
        "",
    ]
    lines += [f'    {key.upper().replace(".", "_")} = "{key}"' for key in keys]
    return "\n".join(lines) + "\n"


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


def extract_keys(path: Path, text: str) -> set[str]:
    """Every permission key present in one artifact's text."""
    pattern = _TS_KEY if path.suffix == ".ts" else _PY_KEY
    return set(pattern.findall(text))


def keys_that_would_be_lost(expected: dict[Path, str]) -> dict[Path, list[str]]:
    """
    Per output: which keys exist on disk now and would NOT survive a write.

    This exists because the catalog is not, in practice, the only source of the
    keys in these files. dghms/common/generated_permissions.py and
    celiyohms/src/constants/permissions.ts each carry 84 crm/whatsapp/telephony/
    meetings/tasks keys that this YAML has never contained and cannot produce —
    they were added by hand. Regenerating would therefore DELETE those 84 keys
    and add nothing, silently, from a command that reads as routine.

    Per file rather than in aggregate: one output gaining keys must never mask
    another losing them.
    """
    losses: dict[Path, list[str]] = {}
    for path, contents in expected.items():
        if not path.exists():
            continue
        current = extract_keys(path, path.read_text(encoding="utf-8"))
        lost = current - extract_keys(path, contents)
        if lost:
            losses[path] = sorted(lost)
    return losses


def render(catalog: dict) -> dict[Path, str]:
    py = python_output(catalog)
    ts, types = typescript_outputs(catalog)
    return {
        OUTPUTS[0]: py,
        OUTPUTS[1]: py,
        OUTPUTS[2]: ts,
        OUTPUTS[3]: types,
        # Same catalog, plus the constants class only digicrm consumes. Kept out
        # of the shared `py` so superadmin and dghms do not silently grow a class
        # they have no use for.
        OUTPUTS[4]: py + crm_permissions_class(catalog),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if generated files are stale")
    parser.add_argument(
        "--allow-shrink",
        action="store_true",
        help="write even if it removes permission keys from an output (destructive)",
    )
    args = parser.parse_args()
    expected = render(load_catalog())
    stale = [path for path, contents in expected.items() if not path.exists() or path.read_text(encoding="utf-8") != contents]
    if args.check:
        if stale:
            print("Generated permission artifacts are stale:", *[str(path.relative_to(ROOT)) for path in stale], sep="\n  ", file=sys.stderr)
            return 1
        print("Permission artifacts are up to date.")
        return 0

    # Deliberately AFTER the --check early return: --check is a read-only
    # staleness diagnostic and must keep answering that question truthfully
    # whether or not a write would be refused. The two are independent.
    losses = keys_that_would_be_lost(expected)
    if losses and not args.allow_shrink:
        print("Refusing to write: this would REMOVE permission keys.", file=sys.stderr)
        for path, lost in losses.items():
            modules = sorted({key.split(".")[0] for key in lost})
            print(f"  {path.relative_to(ROOT)}: {len(lost)} keys ({', '.join(modules)})", file=sys.stderr)
            for key in lost[:10]:
                print(f"      {key}", file=sys.stderr)
            if len(lost) > 10:
                print(f"      ... and {len(lost) - 10} more", file=sys.stderr)
        print(
            "\nThose keys are not in the catalog, so regenerating cannot reproduce them.\n"
            "Add them to permissions_catalog.yaml first, or pass --allow-shrink if you\n"
            "genuinely mean to delete them.",
            file=sys.stderr,
        )
        return 1

    for path, contents in expected.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
