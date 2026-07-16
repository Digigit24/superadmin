"""Canonical, catalog-validated HMS role seed source."""
from apps.common.generated_permissions import PERMISSION_BY_KEY

def _flat(data, prefix=""):
    out = {}
    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict): out.update(_flat(value, path))
        else: out[path] = value
    return out

def validate_role_seeds(role_seeds):
    for role in role_seeds:
        for key, value in _flat(role["permissions"]).items():
            entry = PERMISSION_BY_KEY.get(key)
            if not entry or entry["status"] not in ("active", "ui_only"):
                raise ValueError(f"{role['name']}: unknown/deprecated permission {key}")
            if entry["scope_model"] == "own_all":
                valid = value in ("own", "all")
            else:
                valid = value is True
            if not valid:
                raise ValueError(f"{role['name']}: invalid value {value!r} for {key}")
    return role_seeds
