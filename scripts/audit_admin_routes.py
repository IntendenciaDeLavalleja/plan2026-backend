"""Fail when an embedded-admin API consumer does not match Flask's route map."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import create_app  # noqa: E402


API_BASE = "/api/v1"
CALL_RE = re.compile(r"(?:AdminUI|ui)\.request\(\s*(['\"])([^'\"]+)\1", re.MULTILINE)
API_HREF_RE = re.compile(r"data-api-href=\"([^\"]+)\"")


def _route_pattern(rule: str) -> re.Pattern[str]:
    escaped = re.escape(rule)
    escaped = re.sub(r"<[^>]+>", r"[^/]+", escaped)
    return re.compile(r"^" + escaped + r"$")


def _method_after(source: str, end: int) -> str:
    fragment = source[end:end + 180]
    match = re.search(r"\bmethod\s*:\s*['\"]([A-Z]+)['\"]", fragment)
    return match.group(1) if match else "GET"


def _path_with_dynamic_suffix(source: str, match: re.Match[str]) -> str:
    path = match.group(2)
    if not path.endswith("/"):
        return path
    fragment = source[match.end():match.end() + 220]
    suffix = re.search(r"\+\s*[A-Za-z_$][\w$\.]*\s*\+\s*['\"]([^'\"]+)['\"]", fragment)
    return path + "route-id" + (suffix.group(1) if suffix else "")


def _matches_dynamic_prefix(path: str, rule: str) -> bool:
    static_prefix = re.sub(r"<[^>]+>", "", rule)
    return path.endswith("/") and path.startswith(static_prefix)


def main() -> int:
    app = create_app()
    routes = [
        (rule.rule, {method for method in rule.methods if method not in {"HEAD", "OPTIONS"}})
        for rule in app.url_map.iter_rules()
        if rule.rule.startswith(API_BASE + "/")
    ]
    consumed: list[tuple[Path, int, str, str]] = []
    failures: list[str] = []

    for template in sorted((ROOT / "app" / "templates" / "admin").glob("*.html")):
        source = template.read_text(encoding="utf-8")
        for match in CALL_RE.finditer(source):
            path = _path_with_dynamic_suffix(source, match)
            line = source.count("\n", 0, match.start()) + 1
            consumed.append((template, line, path, _method_after(source, match.end())))
        for match in API_HREF_RE.finditer(source):
            line = source.count("\n", 0, match.start()) + 1
            consumed.append((template, line, match.group(1), "GET"))

    for template, line, path, method in consumed:
        normalized = path.split("?", 1)[0].lstrip("/")
        if path.startswith("/api/") or normalized.startswith("api/"):
            failures.append(f"{template.relative_to(ROOT)}:{line}: prefijo API distribuido u obsoleto: {path}")
            continue
        if not normalized or normalized.startswith("/"):
            failures.append(f"{template.relative_to(ROOT)}:{line}: path inválido: {path}")
            continue
        full_path = f"{API_BASE}/{normalized}"
        matches = [(rule, methods) for rule, methods in routes if _route_pattern(rule).match(full_path) or _matches_dynamic_prefix(full_path, rule)]
        if not matches:
            failures.append(f"{template.relative_to(ROOT)}:{line}: ruta no registrada: {method} {full_path}")
        elif not any(method in methods for _, methods in matches):
            allowed = ", ".join(sorted({item for _, methods in matches for item in methods}))
            failures.append(f"{template.relative_to(ROOT)}:{line}: método inválido: {method} {full_path} (permitidos: {allowed})")

    consumed_routes = {f"{API_BASE}/{path.split('?', 1)[0].lstrip('/')}" for _, _, path, _ in consumed}
    unused = [rule for rule, _ in routes if not any(_route_pattern(rule).match(path) or _matches_dynamic_prefix(path, rule) for path in consumed_routes)]
    print(f"Rutas API registradas: {len(routes)}")
    print(f"Consumidores administrativos: {len(consumed)}")
    print(f"Rutas API sin consumidor HTML directo: {len(unused)}")
    for rule in unused:
        print(f"INFO ruta sin consumidor HTML directo: {rule}")
    if failures:
        for failure in failures:
            print(f"ERROR {failure}", file=sys.stderr)
        return 1
    print("OK: todos los consumidores administrativos coinciden con rutas registradas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
