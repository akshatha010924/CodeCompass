"""FastAPI application."""
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from . import config, db, llm, rag, repo
from .parser import analyze_file, iter_files
from .review import review_repo

app = FastAPI(title="CodeCompass")
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])


class GithubIn(BaseModel):
    url: str = Field(max_length=200)


class ChatIn(BaseModel):
    question: str = Field(min_length=2, max_length=3000)


class ExplainIn(BaseModel):
    path: str
    symbol: str | None = None


class FeedbackIn(BaseModel):
    retrieval_id: int
    value: int = Field(ge=-1, le=1)


def _guard(fn, *a):
    try:
        return fn(*a)
    except repo.IngestError as e:
        raise HTTPException(400, str(e))


def _repo_or_404(rid):
    r = db.get_repo(rid)
    if not r:
        raise HTTPException(404, "Repository not found.")
    return r


def _files(rid):
    root = _guard(repo.repo_root, rid)
    return [analyze_file(root, p) for p in iter_files(root, config.MAX_FILES, config.MAX_FILE_KB)]


@app.get("/api/health")
def health():
    return {"ok": True, "llm": llm.available()}


@app.post("/api/repos/upload")
async def upload(file: UploadFile = File(...)):
    data = await file.read()
    return _guard(repo.ingest_zip, file.filename or "", data)


@app.post("/api/repos/github")
def github(body: GithubIn):
    return _guard(repo.ingest_github, body.url)


@app.get("/api/repos")
def repos():
    return db.list_repos()


@app.get("/api/repos/{rid}/overview")
def overview(rid: str):
    return _repo_or_404(rid)["overview"]


@app.get("/api/repos/{rid}/file")
def file(rid: str, path: str):
    _repo_or_404(rid)
    f = next((f for f in _files(rid) if f["path"] == path), None)  # only indexed, redacted files are served
    if not f:
        raise HTTPException(404, "File not found.")
    return {"path": f["path"], "language": f["language"], "source": f["source"], "symbols": f["symbols"]}


@app.post("/api/repos/{rid}/chat")
def chat(rid: str, body: ChatIn):
    _repo_or_404(rid)
    return rag.answer(rid, body.question)


@app.post("/api/repos/{rid}/explain")
def explain(rid: str, body: ExplainIn):
    _repo_or_404(rid)
    f = next((f for f in _files(rid) if f["path"] == body.path), None)
    if not f:
        raise HTTPException(404, "File not found.")
    src, lines = f["source"], f["source"].splitlines()
    if body.symbol:
        s = next((s for s in f["symbols"] if s["name"] == body.symbol), None)
        if not s:
            raise HTTPException(404, "Symbol not found.")
        src = "\n".join(lines[s["start"] - 1:s["end"]])
    return rag.explain(rid, body.path, body.symbol, src)


@app.get("/api/repos/{rid}/review")
def review(rid: str, explain: bool = False):
    _repo_or_404(rid)
    return review_repo(_files(rid), explain)


@app.post("/api/repos/{rid}/feedback")
def feedback(rid: str, body: FeedbackIn):
    db.set_feedback(body.retrieval_id, body.value)
    return {"ok": True}


@app.get("/api/repos/{rid}/metrics")
def metrics(rid: str):
    _repo_or_404(rid)
    return db.metrics(rid)
