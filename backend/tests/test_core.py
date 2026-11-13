import io, os, shutil, tempfile, zipfile
from pathlib import Path

os.environ["CODECOMPASS_DATA"] = tempfile.mkdtemp()
os.environ["EMBED_BACKEND"] = os.environ.get("EMBED_BACKEND", "hashing")
os.environ.pop("ANTHROPIC_API_KEY", None)

import pytest
from fastapi.testclient import TestClient
from app import parser, chunker, review, repo
from app.main import app

DEMO = Path(__file__).resolve().parents[2] / "samples" / "demo_repo"
client = TestClient(app)


def demo_zip(extra=None):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for p in DEMO.rglob("*"):
            if p.is_file():
                z.write(p, "demo/" + p.relative_to(DEMO).as_posix())
        for k, v in (extra or {}).items():
            z.writestr(k, v)
    return buf.getvalue()


def test_python_symbols_and_lines():
    syms, imports = parser.py_symbols("import os\n\ndef a():\n    return 1\n\nclass B:\n    def m(self): pass\n")
    assert [(s["name"], s["start"]) for s in syms] == [("a", 3), ("B", 6), ("m", 7)]
    assert imports == ["os"]


def test_redaction():
    assert "[REDACTED]" in parser.redact('API_KEY = "sk-abcdef123456"')


def test_chunks_have_line_ranges():
    f = {"path": "x.py", "language": "Python", "source": "def a():\n    return 1\n\nX = 2\n",
         "symbols": [{"name": "a", "kind": "function", "start": 1, "end": 2}]}
    ch = chunker.chunk_file(f)
    assert ch[0]["id"] == "x.py:1-2" and ch[0]["symbol"] == "a"


def test_review_rules():
    src = ('def f(x, cache={}):\n    try:\n        eval(x)\n    except:\n        pass\n'
           'PASSWORD = "hunter2hunter2"\n')
    rules = {f["rule"] for f in review.review_python("f.py", src)}
    assert {"mutable-default", "eval-exec", "bare-except", "hardcoded-secret"} <= rules


def test_zip_slip_rejected(tmp_path):
    p = tmp_path / "evil.zip"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("../../evil.txt", "x")
    with pytest.raises(repo.IngestError):
        repo.safe_extract(p, tmp_path / "out")


def test_rejects_non_zip_and_bad_github():
    assert client.post("/api/repos/upload", files={"file": ("a.txt", b"hi")}).status_code == 400
    assert client.post("/api/repos/github", json={"url": "file:///etc/passwd"}).status_code == 400


def test_end_to_end_retrieval_and_review():
    r = client.post("/api/repos/upload", files={"file": ("demo.zip", demo_zip(), "application/zip")})
    assert r.status_code == 200, r.text
    rid = r.json()["id"]
    ov = client.get(f"/api/repos/{rid}/overview").json()
    assert ov["file_count"] >= 4 and ov["function_count"] >= 4
    assert any(e["from"] == "app.py" and e["to"] == "database.py" for e in ov["relationships"])

    chat = client.post(f"/api/repos/{rid}/chat", json={"question": "where are records saved to sqlite?"}).json()
    assert chat["mode"] == "retrieval-only"
    assert chat["citations"][0]["path"] == "database.py"

    findings = client.get(f"/api/repos/{rid}/review").json()["findings"]
    rules = {f["rule"] for f in findings}
    assert {"bare-except", "mutable-default", "hardcoded-secret"} <= rules

    src = client.get(f"/api/repos/{rid}/file", params={"path": "app.py"}).json()["source"]
    assert "sk-demo-1234567890abcdef" not in src      # secrets never served

    assert client.post(f"/api/repos/{rid}/feedback", json={"retrieval_id": chat["retrieval_id"], "value": 1}).status_code == 200
    assert client.get(f"/api/repos/{rid}/metrics").json()["queries"] == 1
    assert client.get("/api/repos/nope/overview").status_code == 404


def test_env_files_are_not_indexed():
    z = demo_zip({"demo/.env": "SECRET=abc", "demo/key.pem": "x"})
    rid = client.post("/api/repos/upload", files={"file": ("d.zip", z)}).json()["id"]
    assert not any(p.endswith((".env", ".pem")) for p in client.get(f"/api/repos/{rid}/overview").json()["tree"])
