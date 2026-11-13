"""Split files into retrievable chunks that keep line numbers for citations."""
WINDOW, OVERLAP = 40, 8


def chunk_file(f: dict) -> list[dict]:
    lines, chunks, covered = f["source"].splitlines(), [], set()
    for s in f["symbols"]:
        end = min(s["start"] + 9, s["end"]) if s["kind"] == "class" and s["end"] - s["start"] > WINDOW else s["end"]
        end = min(end, s["start"] + 120)
        chunks.append(_mk(f, lines, s["start"], end, s["name"]))
        covered.update(range(s["start"], end + 1))
    i = 1  # remaining lines (module-level code, docs, config) -> sliding windows
    while i <= len(lines):
        j = min(i + WINDOW - 1, len(lines))
        if any(n not in covered for n in range(i, j + 1)) and "".join(lines[i - 1:j]).strip():
            chunks.append(_mk(f, lines, i, j, None))
        if j == len(lines):
            break
        i = j - OVERLAP + 1
    return chunks


def _mk(f, lines, start, end, symbol):
    body = "\n".join(lines[start - 1:end])
    header = f"# {f['path']} ({f['language']})" + (f" :: {symbol}" if symbol else "")
    return {"id": f"{f['path']}:{start}-{end}", "path": f["path"], "start": start, "end": end,
            "symbol": symbol or "", "language": f["language"], "text": f"{header}\n{body}"}
