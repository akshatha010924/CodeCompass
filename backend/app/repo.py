"""Repository ingestion (ZIP upload / GitHub URL) with basic safety checks."""
import re, shutil, subprocess, time, uuid, zipfile
from pathlib import Path
from . import config, db, rag
from .parser import analyze_file, build_overview, iter_files

GITHUB_RE = re.compile(r"^https://github\.com/[\w.-]+/[\w.-]+?(?:\.git)?/?$")


class IngestError(ValueError):
    pass


def safe_extract(zip_path: Path, dest: Path):
    total = 0
    with zipfile.ZipFile(zip_path) as z:
        infos = z.infolist()
        if len(infos) > config.MAX_FILES * 3:
            raise IngestError("Archive contains too many entries.")
        for i in infos:
            target = (dest / i.filename).resolve()
            if not str(target).startswith(str(dest.resolve())):   # zip-slip guard
                raise IngestError("Archive contains unsafe paths.")
            total += i.file_size
            if total > config.MAX_UPLOAD_MB * 1024 * 1024 * 4:    # zip-bomb guard
                raise IngestError("Archive expands to too much data.")
        z.extractall(dest)


def _finish(rid: str, name: str, source: str, root: Path) -> dict:
    files = [analyze_file(root, p) for p in iter_files(root, config.MAX_FILES, config.MAX_FILE_KB)]
    if not files:
        shutil.rmtree(root.parent, ignore_errors=True)
        raise IngestError("No supported source files found in this repository.")
    overview = build_overview(files, root)
    overview["index"] = rag.index_repo(rid, files)
    db.save_repo(rid, name, source, overview, time.time())
    return {"id": rid, "name": name, "overview": overview}


def _new(name: str):
    rid = uuid.uuid4().hex[:10]
    root = config.REPOS_DIR / rid / "src"
    root.mkdir(parents=True)
    return rid, root


def _single_root(root: Path) -> Path:
    kids = [k for k in root.iterdir() if not k.name.startswith("__MACOSX")]
    return kids[0] if len(kids) == 1 and kids[0].is_dir() else root


def ingest_zip(filename: str, data: bytes) -> dict:
    if not filename.lower().endswith(".zip"):
        raise IngestError("Please upload a .zip file.")
    if len(data) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise IngestError(f"File exceeds {config.MAX_UPLOAD_MB} MB limit.")
    rid, root = _new(filename)
    tmp = root.parent / "upload.zip"
    tmp.write_bytes(data)
    try:
        safe_extract(tmp, root)
    except zipfile.BadZipFile:
        shutil.rmtree(root.parent, ignore_errors=True)
        raise IngestError("That file is not a valid ZIP archive.")
    except IngestError:
        shutil.rmtree(root.parent, ignore_errors=True)
        raise
    return _finish(rid, Path(filename).stem, "zip", _single_root(root))


def ingest_github(url: str) -> dict:
    url = url.strip()
    if not GITHUB_RE.match(url):
        raise IngestError("Enter a public URL like https://github.com/owner/repo.")
    rid, root = _new(url)
    try:
        subprocess.run(["git", "clone", "--depth", "1", url, str(root / "repo")], check=True,
                       capture_output=True, timeout=120)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        shutil.rmtree(root.parent, ignore_errors=True)
        raise IngestError("Could not clone that repository. Check the URL is public and git is installed.")
    return _finish(rid, url.rstrip("/").split("/")[-1].removesuffix(".git"), url, root / "repo")


def repo_root(rid: str) -> Path:
    base = config.REPOS_DIR / rid / "src"
    if not base.exists():
        raise IngestError("Repository not found.")
    return _single_root(base / "repo") if (base / "repo").exists() else _single_root(base)
