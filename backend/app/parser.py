"""File discovery, language detection and symbol extraction."""
import ast, json, re
from collections import Counter
from pathlib import Path

LANGS = {".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript", ".ts": "TypeScript",
         ".tsx": "TypeScript", ".java": "Java", ".go": "Go", ".rs": "Rust", ".rb": "Ruby",
         ".c": "C", ".h": "C", ".cpp": "C++", ".cs": "C#", ".php": "PHP", ".sh": "Shell",
         ".html": "HTML", ".css": "CSS", ".sql": "SQL", ".md": "Markdown", ".json": "JSON",
         ".yml": "YAML", ".yaml": "YAML", ".toml": "TOML"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".idea", ".next"}
SKIP_NAMES = {".env", "id_rsa", "id_ed25519"}
SKIP_SUFFIX = {".pem", ".key", ".p12", ".pfx", ".lock"}
SECRET_RE = re.compile(r"""(?i)(api[_-]?key|secret|token|passwd|password)(\s*[:=]\s*)(['"])[^'"\s]{8,}\3""")

SYMBOL_RES = {
    "js": [(re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)"), "function"),
           (re.compile(r"^\s*(?:export\s+)?class\s+(\w+)"), "class"),
           (re.compile(r"^\s*(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>"), "function")],
    "go": [(re.compile(r"^func\s+(?:\([^)]*\)\s*)?(\w+)"), "function"), (re.compile(r"^type\s+(\w+)\s+struct"), "class")],
    "java": [(re.compile(r"^\s*(?:public|private|protected)?\s*(?:static\s+)?class\s+(\w+)"), "class"),
             (re.compile(r"^\s*(?:public|private|protected)\s+(?:static\s+)?[\w<>\[\]]+\s+(\w+)\s*\([^;]*$"), "function")],
}
EXT_GROUP = {"JavaScript": "js", "TypeScript": "js", "Go": "go", "Java": "java"}


def redact(text: str) -> str:
    return SECRET_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)}[REDACTED]{m.group(3)}", text)


def iter_files(root: Path, max_files: int, max_kb: int):
    n = 0
    for p in sorted(root.rglob("*")):
        if not p.is_file() or any(part in SKIP_DIRS for part in p.relative_to(root).parts):
            continue
        if p.name in SKIP_NAMES or p.name.startswith(".env") or p.suffix in SKIP_SUFFIX:
            continue
        if p.suffix.lower() not in LANGS or p.stat().st_size > max_kb * 1024:
            continue
        n += 1
        if n > max_files:
            break
        yield p


def py_symbols(src: str):
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return [], []
    syms, imports = [], set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            syms.append({"name": node.name, "kind": "function", "start": node.lineno, "end": node.end_lineno})
        elif isinstance(node, ast.ClassDef):
            syms.append({"name": node.name, "kind": "class", "start": node.lineno, "end": node.end_lineno})
        elif isinstance(node, ast.Import):
            imports.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            imports.add(node.module.split(".")[0])
    return sorted(syms, key=lambda s: s["start"]), sorted(imports)


def regex_symbols(src: str, group: str):
    lines, out, imports = src.splitlines(), [], set()
    for i, line in enumerate(lines, 1):
        for rx, kind in SYMBOL_RES.get(group, []):
            m = rx.match(line)
            if m:
                out.append({"name": m.group(1), "kind": kind, "start": i, "end": i})
        m = re.match(r"""^\s*import .*?from\s+['"]([^'"./][^'"]*)['"]""", line)
        if m:
            imports.add(m.group(1).split("/")[0])
    for a, s in zip(out, out[1:] + [None]):   # approximate end = line before next symbol
        a["end"] = (s["start"] - 1) if s else len(lines)
    return out, sorted(imports)


def analyze_file(root: Path, path: Path) -> dict:
    rel = path.relative_to(root).as_posix()
    lang = LANGS[path.suffix.lower()]
    try:
        src = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        src = path.read_text(encoding="latin-1")
    syms, imports = [], []
    if lang == "Python":
        syms, imports = py_symbols(src)
    elif lang in EXT_GROUP:
        syms, imports = regex_symbols(src, EXT_GROUP[lang])
    return {"path": rel, "language": lang, "lines": src.count("\n") + 1, "symbols": syms,
            "imports": imports, "source": redact(src)}


def find_dependencies(root: Path) -> dict:
    deps = {}
    req = root / "requirements.txt"
    if req.exists():
        deps["python"] = [re.split(r"[=<>~! ]", l.strip())[0] for l in req.read_text().splitlines()
                          if l.strip() and not l.startswith("#")]
    pkg = root / "package.json"
    if pkg.exists():
        try:
            j = json.loads(pkg.read_text())
            deps["node"] = sorted({**j.get("dependencies", {}), **j.get("devDependencies", {})})
        except json.JSONDecodeError:
            pass
    return deps


def relationships(files: list[dict]) -> list[dict]:
    """Python-only internal import graph: file A imports a module matching file B."""
    stems = {Path(f["path"]).stem: f["path"] for f in files if f["language"] == "Python"}
    return [{"from": f["path"], "to": stems[i]} for f in files for i in f["imports"]
            if i in stems and stems[i] != f["path"]]


def build_overview(files: list[dict], root: Path) -> dict:
    langs = Counter()
    for f in files:
        langs[f["language"]] += f["lines"]
    total = sum(langs.values()) or 1
    return {
        "file_count": len(files),
        "function_count": sum(s["kind"] == "function" for f in files for s in f["symbols"]),
        "class_count": sum(s["kind"] == "class" for f in files for s in f["symbols"]),
        "total_lines": total,
        "languages": [{"name": k, "lines": v, "percent": round(100 * v / total, 1)} for k, v in langs.most_common()],
        "dependencies": find_dependencies(root),
        "relationships": relationships(files),
        "tree": sorted(f["path"] for f in files),
    }
