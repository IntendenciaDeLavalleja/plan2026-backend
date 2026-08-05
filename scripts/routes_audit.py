"""Auditoria de rutas: compara las rutas reales de Flask contra las que invoca la UI.

Uso (desde la raiz del proyecto backend):

    python scripts/routes_audit.py

Escribe Routes-audit.md en la raiz del proyecto. No modifica nada mas.
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ADMIN_JS = ROOT / "app" / "static" / "admin" / "admin.js"
TEMPLATES_DIR = ROOT / "app" / "templates"
STATIC_DIR = ROOT / "app" / "static"
OUTPUT = ROOT / "Routes-audit.md"

HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}

# --------------------------------------------------------------------------
# 1. Rutas declaradas en el servidor
# --------------------------------------------------------------------------

def collect_routes_from_app() -> tuple[list[dict], str]:
    """Fuente autoritativa: el url_map real de Flask."""
    from app import create_app

    app = create_app()
    routes = []
    for rule in app.url_map.iter_rules():
        methods = sorted(m for m in (rule.methods or set()) if m in HTTP_METHODS)
        routes.append({
            "rule": rule.rule,
            "methods": methods,
            "endpoint": rule.endpoint,
            "blueprint": rule.endpoint.rsplit(".", 1)[0] if "." in rule.endpoint else "(app)",
        })
    routes.sort(key=lambda r: r["rule"])
    return routes, "url_map de Flask (autoritativo)"

DECORATOR_RE = re.compile(
    r"@(?P<bp>\w+)\.(?P<verb>get|post|put|patch|delete|route)\(\s*(['\"])(?P<path>[^'\"]*)\3"
    r"(?P<rest>[^)]*)\)",
)
REGISTER_RE = re.compile(
    r"register_blueprint\(\s*(?P<bp>\w+)\s*(?:,\s*url_prefix\s*=\s*(['\"])(?P<prefix>[^'\"]*)\2)?",
)
METHODS_KW_RE = re.compile(r"methods\s*=\s*\[([^\]]*)\]")

def collect_routes_static() -> tuple[list[dict], str]:
    """Respaldo: parseo estatico si la app no se puede importar."""
    init_src = (ROOT / "app" / "__init__.py").read_text(encoding="utf-8", errors="replace")
    prefixes = {}
    for m in REGISTER_RE.finditer(init_src):
        prefixes[m.group("bp")] = m.group("prefix") or ""

    routes = []
    for py in sorted((ROOT / "app" / "blueprints").rglob("*.py")):
        src = py.read_text(encoding="utf-8", errors="replace")
        for m in DECORATOR_RE.finditer(src):
            bp = m.group("bp")
            if bp not in prefixes:
                continue
            verb = m.group("verb").upper()
            if verb == "ROUTE":
                kw = METHODS_KW_RE.search(m.group("rest") or "")
                methods = (
                    sorted({v.strip().strip("'\"").upper() for v in kw.group(1).split(",") if v.strip()})
                    if kw else ["GET"]
                )
            else:
                methods = [verb]
            rule = (prefixes[bp] + m.group("path")) or "/"
            routes.append({
                "rule": rule,
                "methods": methods,
                "endpoint": f"{bp}.{'?'}",
                "blueprint": bp,
            })
    routes.sort(key=lambda r: r["rule"])
    return routes, "parseo estatico de decoradores (la app no se pudo importar)"

# --------------------------------------------------------------------------
# 2. Llamadas que hace la interfaz
# --------------------------------------------------------------------------

CALL_RE = re.compile(r"(?:AdminUI|ui)\.request\(\s*(['\"])(?P<path>[^'\"]*)\1")
HREF_RE = re.compile(r"data-api-href\s*=\s*(['\"])(?P<path>[^'\"]*)\1")
METHOD_RE = re.compile(r"\bmethod\s*:\s*(['\"])(?P<verb>[A-Za-z]+)\1")
CONST_RE = re.compile(r"const\s+(?P<name>\w*API_BASE_URL)\s*=\s*(['\"])(?P<value>[^'\"]*)\2")

def read_base_urls() -> dict[str, str]:
    """Lee las constantes de admin.js para no duplicar su valor aca."""
    bases = {}
    if ADMIN_JS.exists():
        src = ADMIN_JS.read_text(encoding="utf-8", errors="replace")
        for m in CONST_RE.finditer(src):
            bases[m.group("name")] = m.group("value")
    bases["_public_declarado"] = "PUBLIC_API_BASE_URL" in bases
    bases.setdefault("API_BASE_URL", "/admin/api")
    bases.setdefault("PUBLIC_API_BASE_URL", "/api/v1/public")
    return bases

def build_api_url(path: str, bases: dict[str, str]) -> str:
    """Replica de buildApiUrl() de admin.js."""
    p = path.strip().lstrip("/")
    if not p:
        return ""
    if re.match(r"^https?://", p, re.I):
        return p
    if p == "public" or p.startswith("public/") or p.startswith("public?"):
        return bases["PUBLIC_API_BASE_URL"] + "/" + re.sub(r"^public/?", "", p)
    if p.startswith("api/"):
        return "/" + p
    return bases["API_BASE_URL"] + "/" + re.sub(r"^admin/", "", p)

def line_of(src: str, index: int) -> int:
    return src.count("\n", 0, index) + 1

def collect_ui_calls(bases: dict[str, str]) -> list[dict]:
    files = sorted(TEMPLATES_DIR.rglob("*.html")) + sorted(STATIC_DIR.rglob("*.js"))
    calls = []
    for f in files:
        src = f.read_text(encoding="utf-8", errors="replace")
        for regex, kind in ((CALL_RE, "request"), (HREF_RE, "data-api-href")):
            for m in regex.finditer(src):
                raw = m.group("path")
                tail = src[m.end():m.end() + 240]
                # Concatenacion tipo:  'admin/appointments/' + item.id + '/cancel'
                dynamic = raw.endswith("/")
                if dynamic:
                    suffix = re.match(r"\s*\+\s*[^+]+\+\s*(['\"])([^'\"]*)\1", tail)
                    raw = raw + "<id>" + (suffix.group(2) if suffix else "")
                verb = "GET"
                if kind == "request":
                    mm = METHOD_RE.search(tail)
                    if mm:
                        verb = mm.group("verb").upper()
                calls.append({
                    "file": str(f.relative_to(ROOT)).replace("\\", "/"),
                    "line": line_of(src, m.start()),
                    "source": raw,
                    "method": verb,
                    "url": build_api_url(raw, bases),
                    "dynamic": dynamic,
                })
    calls.sort(key=lambda c: (c["file"], c["line"]))
    return calls

# --------------------------------------------------------------------------
# 3. Comparacion
# --------------------------------------------------------------------------

CONVERTERS = {"int": r"\d+", "float": r"[\d.]+", "path": r".+", "uuid": r"[0-9a-fA-F-]+"}

def rule_to_regex(rule: str) -> re.Pattern[str]:
    """Respeta el convertidor: <int:id> no debe matchear 'bulk-generate'."""
    parts = re.split(r"(<[^>]+>)", rule)
    out = []
    for part in parts:
        if part.startswith("<"):
            inner = part[1:-1]
            conv = inner.split(":", 1)[0] if ":" in inner else "string"
            out.append(CONVERTERS.get(conv, "[^/]+"))
        else:
            out.append(re.escape(part))
    return re.compile("^" + "".join(out) + "$")

def audit(routes: list[dict], calls: list[dict]) -> list[dict]:
    compiled = [(r, rule_to_regex(r["rule"])) for r in routes]
    results = []
    for call in calls:
        path = call["url"].split("?", 1)[0].split("#", 1)[0]
        candidates = [re.sub(r"<id>", "1", path)]
        if "<id>" in path:
            candidates.append(re.sub(r"<id>", "x", path))
        path_matches = [r for r, rx in compiled if any(rx.match(c) for c in candidates)]
        if not path_matches:
            status, detail = "SIN RUTA", "ninguna ruta del servidor coincide con este path"
        elif any(call["method"] in r["methods"] for r in path_matches):
            status, detail = "OK", ""
        else:
            allowed = sorted({m for r in path_matches for m in r["methods"]})
            status = "METODO"
            detail = f"la ruta existe pero acepta {', '.join(allowed)}, no {call['method']}"
        results.append({**call, "status": status, "detail": detail,
                        "matched": path_matches[0]["rule"] if path_matches else ""})
    return results

def render(routes: list[dict], results: list[dict], source_label: str, bases: dict[str, str]) -> str:
    problems = [r for r in results if r["status"] != "OK"]
    used_rules = {r["matched"] for r in results if r["matched"]}

    lines = [
        "# Auditoría de rutas",
        "",
        f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Fuente de las rutas: {source_label}",
        f"Constantes leídas de `admin.js`: "
        + ", ".join(f"`{k} = '{v}'`" for k, v in sorted(bases.items()) if not k.startswith("_")),
        "",
        "## Resumen",
        "",
        f"- Rutas declaradas en el servidor: **{len(routes)}**",
        f"- Llamadas encontradas en la interfaz: **{len(results)}**",
        f"- Llamadas con problema: **{len(problems)}**",
        "",
    ]
    if not bases.get("_public_declarado"):
        lines += [
            "> **Atencion:** `admin.js` no declara `PUBLIC_API_BASE_URL`. Esta auditoria asumio "
            "que las rutas `public/...` van a `/api/v1/public`, pero el `buildApiUrl()` real las "
            "manda a `/admin/api/public/...`, que no existe. Revisar ese archivo.",
            "",
        ]

    lines += ["## Llamadas de la interfaz con problema", ""]
    if problems:
        lines += ["| Archivo:línea | Llamada | Método | URL resuelta | Problema |",
                  "|---|---|---|---|---|"]
        for r in problems:
            lines.append(
                f"| `{r['file']}:{r['line']}` | `{r['source']}` | {r['method']} | "
                f"`{r['url']}` | **{r['status']}** — {r['detail']} |"
            )
    else:
        lines.append("Ninguno. Todas las llamadas de la interfaz coinciden con una ruta real.")
    lines.append("")

    lines += ["## Todas las llamadas de la interfaz", "",
              "| Archivo:línea | Llamada | Método | URL resuelta | Ruta que matchea | Estado |",
              "|---|---|---|---|---|---|"]
    for r in results:
        lines.append(
            f"| `{r['file']}:{r['line']}` | `{r['source']}` | {r['method']} | "
            f"`{r['url']}` | `{r['matched'] or '—'}` | {r['status']} |"
        )
    lines.append("")

    lines += ["## Rutas del servidor que la interfaz nunca llama", "",
              "No es necesariamente un error: puede ser API para el visualizer, el portal "
              "público o uso externo.", ""]
    orphans = [r for r in routes if r["rule"] not in used_rules]
    lines += ["| Ruta | Métodos | Blueprint |", "|---|---|---|"]
    for r in orphans:
        lines.append(f"| `{r['rule']}` | {', '.join(r['methods'])} | `{r['blueprint']}` |")
    lines.append("")

    lines += ["## Todas las rutas declaradas", ""]
    by_bp: dict[str, list[dict]] = defaultdict(list)
    for r in routes:
        by_bp[r["blueprint"]].append(r)
    for bp in sorted(by_bp):
        lines += [f"### `{bp}`", "", "| Ruta | Métodos |", "|---|---|"]
        for r in by_bp[bp]:
            lines.append(f"| `{r['rule']}` | {', '.join(r['methods'])} |")
        lines.append("")

    return "\n".join(lines)

def main() -> int:
    try:
        routes, source_label = collect_routes_from_app()
    except Exception as err:  # noqa: BLE001
        print(f"[aviso] no se pudo importar la app ({err.__class__.__name__}: {err})")
        print("[aviso] usando parseo estatico como respaldo")
        routes, source_label = collect_routes_static()

    bases = read_base_urls()
    calls = collect_ui_calls(bases)
    results = audit(routes, calls)
    OUTPUT.write_text(render(routes, results, source_label, bases), encoding="utf-8")

    problems = sum(1 for r in results if r["status"] != "OK")
    print(f"Rutas declaradas : {len(routes)}")
    print(f"Llamadas de la UI: {len(calls)}")
    print(f"Con problema     : {problems}")
    print(f"Escrito          : {OUTPUT}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())