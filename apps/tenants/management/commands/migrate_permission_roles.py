"""Dry-run canonical permission migration.  Writes require explicit --apply."""
import json
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.accounts.models import Role
from apps.common.generated_permissions import PERMISSION_BY_KEY
from apps.common.permissions import flatten_permissions


ROOT = Path(__file__).resolve().parents[5]
FIXTURES = (ROOT / "dghms" / "fixtures" / "roles.json", ROOT / "dghms" / "fixtures" / "permissions.json")


def map_key(key, value):
    """Return (canonical_key, value, disposition), without mutating input."""
    if value == "team":
        value, disposition = "all", "normalized team->all"
    else:
        disposition = None
    entry = PERMISSION_BY_KEY.get(key)
    if entry and entry["status"] in ("active", "ui_only"):
        return key, value, disposition or "kept"
    if entry and entry.get("alias_of"):
        return entry["alias_of"], value, disposition or "renamed"
    return None, value, "dropped — no equivalent" if entry else "failed-to-map"


class Command(BaseCommand):
    help = "Map role permissions to canonical catalog keys (dry-run by default)."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="persist mapped DB roles (never fixtures)")

    def _report(self, name, permissions):
        flat = flatten_permissions(permissions) if isinstance(permissions, dict) else {key: True for key in permissions}
        result, changes, team_count = {}, [], 0
        for key, value in flat.items():
            if value == "team": team_count += 1
            mapped, normalized, disposition = map_key(key, value)
            if mapped: result[mapped] = normalized
            if mapped != key or disposition != "kept": changes.append(f"{key} -> {mapped or 'DROP'} ({disposition})")
        self.stdout.write(f"ROLE {name}: team_grants={team_count}")
        for change in changes: self.stdout.write(f"  {change}")
        return result, team_count

    def handle(self, *args, **options):
        mode = "APPLY" if options["apply"] else "DRY-RUN (NO WRITES)"
        self.stdout.write(f"Permission migration report: {mode}")
        total_team = 0
        for role in Role.objects.all().iterator():
            mapped, teams = self._report(f"db:{role.name}", role.permissions)
            total_team += teams
            if options["apply"]:
                role.permissions = mapped
                role.save(update_fields=["permissions"])
        for path in FIXTURES:
            if not path.exists(): continue
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                for item in data:
                    if "permissions" in item:
                        _, teams = self._report(f"fixture:{path.name}:{item.get('name', item.get('code'))}", item["permissions"])
                        total_team += teams
                    elif "code" in item:
                        _, teams = self._report(f"fixture:{path.name}:{item['code']}", [item["code"]])
                        total_team += teams
        self.stdout.write(f"TOTAL team grants: {total_team}")
        if not options["apply"]:
            self.stdout.write("No database or fixture data was written. Re-run with --apply only after review.")
