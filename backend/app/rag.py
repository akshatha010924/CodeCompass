
"""Index -> retrieve -> answer with citations."""
from . import config, db, llm
from .chunker import chunk_file
from .embeddings import get_embedder
from .vectorstore import get_store


SYSTEM = (
    "You are CodeCompass, a senior software engineer helping a developer "
    "understand a codebase. "
    "Answer only from supplied repository snippets and conversation context. "
    "Never invent files, functions, behavior, or line numbers. "
    "Cite claims using the supplied [path:start-end] references. "
    "If information is missing, state exactly what is missing. "
    "Distinguish confirmed behavior from assumptions. "

    "For Python code, trace execution statement by statement in source order. "
    "Follow actual indentation to determine block scope. "
    "Identify exactly which statements belong inside each try/except block. "
    "An except block catches exceptions raised inside its associated try block "
    "only, not exceptions raised by later statements. "
    "After an exception is caught, execution continues after the complete "
    "try/except structure. "

    "For assignments, evaluate the right-hand side before assigning the value. "
    "If the right-hand side raises an exception, the assignment does not "
    "complete successfully. "
    "Never assume an unassigned local variable is None. "
    "If a local variable is accessed before assignment, identify "
    "UnboundLocalError. "
    "The pass statement does not assign a value or re-raise an exception. "

    "Identify the exact exception when supported by the source. "
    "Distinguish the original exception from subsequent exceptions. "
    "Explain whether exceptions are caught, suppressed, logged, "
    "re-raised, or propagated. "
    "Stop tracing a path at its first uncaught exception. "
    "Do not claim that later statements execute after that exception. "

    "Distinguish between functions that are called, functions whose "
    "definitions are supplied, and functions whose implementations "
    "are missing. "
    "Never invent the internal behavior of a missing implementation. "

    "For execution-flow questions, explain the execution order, "
    "function calls, exception path, and final outcome. "
    "Avoid repetition. "
    "Use precise citations and concise explanations. "
    "Prefer correctness over unnecessary detail."
)


ANSWER_MAX_TOKENS = 800
HISTORY_MESSAGES = 2

# Maximum context sizes sent to the language model.
MAX_CONTEXT_CHARS = 12000
MAX_HISTORY_CHARS = 1200

# Keep at least this much code context for long questions.
MIN_CONTEXT_CHARS = 4000


def index_repo(rid: str, files: list[dict]) -> dict:
    chunks = [c for f in files for c in chunk_file(f)]
    emb, store = get_embedder(), get_store()
    vectors = emb.encode([c["text"] for c in chunks])
    store.index(rid, chunks, vectors)

    return {
        "chunks": len(chunks),
        "embedder": emb.name,
        "vector_store": store.backend,
    }


def retrieve(rid: str, question: str, k: int = config.TOP_K) -> list[dict]:
    vec = get_embedder().encode([question])[0]
    return get_store().query(rid, vec, k)


def get_context_budget(question: str) -> int:
    """Reduce code context when the developer question is very long."""
    reduction = min(len(question), MAX_CONTEXT_CHARS - MIN_CONTEXT_CHARS)

    return max(
        MIN_CONTEXT_CHARS,
        MAX_CONTEXT_CHARS - reduction,
    )


def format_context(hits, max_chars: int = MAX_CONTEXT_CHARS):
    """Build context in retrieval order without exceeding its character budget."""
    parts = []
    used = 0

    for hit in hits:
        part = (
            f"[{hit['path']}:{hit['start']}-{hit['end']}]\n"
            f"{hit['text']}"
        )

        separator = "\n\n" if parts else ""
        remaining = max_chars - used - len(separator)

        if remaining <= 0:
            break

        if len(part) > remaining:
            if not parts:
                parts.append(
                    part[:remaining]
                    + "\n[Code snippet truncated to fit context budget.]"
                )
            break

        parts.append(part)
        used += len(separator) + len(part)

    return "\n\n".join(parts)


def prepare_history(history):
    """Keep recent conversation context within a fixed character budget."""
    selected = history[-HISTORY_MESSAGES:]
    messages = []
    used = 0

    for message in selected:
        if not isinstance(message, dict):
            continue

        content = message.get("content", "")

        if not isinstance(content, str) or not content.strip():
            continue

        remaining = MAX_HISTORY_CHARS - used

        if remaining <= 0:
            break

        content = content[-remaining:]

        messages.append({
            "role": message.get("role", "user"),
            "content": content,
        })

        used += len(content)

    return messages


def citations(hits):
    return [
        {
            "path": h["path"],
            "start": h["start"],
            "end": h["end"],
            "symbol": h["symbol"],
            "score": round(h["score"], 3),
            "snippet": h["text"].split("\n", 1)[-1][:1200],
        }
        for h in hits
    ]


def answer(rid: str, question: str) -> dict:
    hits = retrieve(rid, question)
    cites = citations(hits)

    rid_log = db.log_retrieval(
        rid,
        question,
        hits[0]["score"] if hits else 0.0,
        [h["path"] for h in hits],
    )

    if not hits:
        text = "No relevant code was found for that question."
        mode = "retrieval-only"

    elif llm.available():
        history = prepare_history(db.history(rid))

        context = format_context(
            hits,
            max_chars=get_context_budget(question),
        )

        messages = history + [
            {
                "role": "user",
                "content": (
                    f"Repository code snippets:\n{context}\n\n"
                    f"Developer question: {question}\n\n"
                    "Analyze the supplied source carefully. "
                    "Follow actual statement order and indentation. "
                    "Stop at the first uncaught exception. "
                    "Use only the supplied citation ranges. "
                    "Be accurate and concise. "
                    "Do not invent missing details."
                ),
            }
        ]

        try:
            text = llm.generate(
                SYSTEM,
                messages,
                max_tokens=ANSWER_MAX_TOKENS,
            )
            mode = "llm"

        except Exception as exc:
            if isinstance(exc, TimeoutError):
                text = (
                    "The language model took too long to process this question. "
                    "The relevant code was retrieved successfully. "
                    "Try asking about one function or execution stage at a time."
                )
            else:
                text = (
                    f"The language model could not generate an answer "
                    f"({type(exc).__name__}: {exc}). "
                    "Here are the most relevant code locations instead."
                )

            mode = "retrieval-only"

    else:
        text = (
            "No LLM provider is configured. Set LLM_PROVIDER=ollama and "
            "ensure Ollama is running, or configure an Anthropic API key. "
            "Here are the most relevant code locations."
        )
        mode = "retrieval-only"

    db.add_message(rid, "user", question)
    db.add_message(rid, "assistant", text, cites)

    return {
        "answer": text,
        "citations": cites,
        "mode": mode,
        "retrieval_id": rid_log,
    }


def explain(rid: str, path: str, symbol: str | None, source: str) -> dict:
    target = (
        f"function/class `{symbol}` in {path}"
        if symbol
        else f"the file {path}"
    )

    if not llm.available():
        return {
            "explanation": (
                "Configure an LLM provider (Ollama or Anthropic) "
                "to get written explanations."
            ),
            "mode": "retrieval-only",
        }

    text = llm.generate(
        SYSTEM,
        [
            {
                "role": "user",
                "content": (
                    f"Explain {target}: purpose, inputs/outputs, execution flow, "
                    "error handling, and relationships to other code. "
                    "Follow actual Python indentation and statement order. "
                    "Distinguish confirmed behavior from missing information. "
                    "Cite only the supplied file and line references.\n\n"
                    f"{source[:MAX_CONTEXT_CHARS]}"
                ),
            }
        ],
        max_tokens=ANSWER_MAX_TOKENS,
    )

    return {"explanation": text, "mode": "llm"}
