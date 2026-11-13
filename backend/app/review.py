"""Rule-based code review (deterministic) + optional LLM explanations of each finding."""
import ast, re
from . import llm

SECRET = re.compile(r"""(?i)(api[_-]?key|secret|token|password)\s*=\s*['"][^'"\s]{6,}['"]""")


def review_python(path: str, src: str) -> list[dict]:
    out = []

    def add(line, sev, rule, msg, why):
        out.append({"path": path, "line": line, "severity": sev, "rule": rule, "message": msg, "why": why})

    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return [{"path": path, "line": e.lineno or 1, "severity": "high", "rule": "syntax-error",
                 "message": "File does not parse.", "why": str(e)}]
    for n in ast.walk(tree):
        if isinstance(n, ast.ExceptHandler):
            if n.type is None:
                add(n.lineno, "medium", "bare-except", "Bare `except:` swallows every error, including KeyboardInterrupt.",
                    "Catch specific exceptions so real bugs are not hidden.")
            elif len(n.body) == 1 and isinstance(n.body[0], ast.Pass):
                add(n.lineno, "medium", "silent-except", "Exception is caught and silently ignored.",
                    "Log or handle the error; silent failures are hard to debug.")
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for d in n.args.defaults + [x for x in n.args.kw_defaults if x]:
                if isinstance(d, (ast.List, ast.Dict, ast.Set)):
                    add(n.lineno, "high", "mutable-default", f"`{n.name}` uses a mutable default argument.",
                        "The default object is shared across calls, so state leaks between them.")
            if (n.end_lineno - n.lineno) > 60:
                add(n.lineno, "low", "long-function", f"`{n.name}` is {n.end_lineno - n.lineno} lines long.",
                    "Long functions are harder to test; consider splitting by responsibility.")
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in ("eval", "exec"):
            add(n.lineno, "high", "eval-exec", f"`{n.func.id}()` executes arbitrary code.",
                "If any input is user-controlled this is a code-injection risk.")
        elif isinstance(n, ast.Call) and any(k.arg == "shell" and getattr(k.value, "value", None) is True for k in n.keywords):
            add(n.lineno, "high", "shell-true", "Subprocess call with `shell=True`.",
                "Shell metacharacters in input can lead to command injection; pass an argument list instead.")
    for i, line in enumerate(src.splitlines(), 1):
        if SECRET.search(line):
            add(i, "high", "hardcoded-secret", "Possible hard-coded credential.", "Move secrets to environment variables.")
        if re.search(r"#\s*(TODO|FIXME|HACK)", line):
            add(i, "low", "todo", "Unresolved TODO/FIXME marker.", "Track it in an issue or resolve it.")
    return out


def review_repo(files: list[dict], explain: bool = False) -> dict:
    findings = [f for file in files if file["language"] == "Python" for f in review_python(file["path"], file["source"])]
    order = {"high": 0, "medium": 1, "low": 2}
    findings.sort(key=lambda f: (order[f["severity"]], f["path"], f["line"]))
    summary = {s: sum(f["severity"] == s for f in findings) for s in order}
    note = None
    if explain and findings and llm.available():
        top = "\n".join(f"{f['path']}:{f['line']} {f['rule']}: {f['message']}" for f in findings[:15])
        note = llm.generate("You are a pragmatic code reviewer. Explain why each issue matters and how to fix it "
                            "in prose. Do not rewrite whole files.", [{"role": "user", "content": top}], 900)
    return {"findings": findings, "summary": summary, "llm_notes": note,
            "scope": "Rule-based checks run on Python files only."}
