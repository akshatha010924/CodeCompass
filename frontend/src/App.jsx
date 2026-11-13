// import { useEffect, useRef, useState } from "react";
// import { api } from "./api.js";

// const NAV = ["Repository", "Chat", "Code review", "Insights"];
// const COLORS = ["#7c6cff", "#f5b942", "#2fb3ff", "#34d399", "#f472b6", "#94a3b8"];

// export default function App() {
//   const [repos, setRepos] = useState([]);
//   const [rid, setRid] = useState(null);
//   const [overview, setOverview] = useState(null);
//   const [view, setView] = useState("Repository");
//   const [health, setHealth] = useState({});
//   const [busy, setBusy] = useState(false);
//   const [error, setError] = useState("");
//   const [url, setUrl] = useState("");

//   const load = async (id) => { setRid(id); setOverview(await api.overview(id)); };
//   const refresh = async () => setRepos(await api.repos());
//   useEffect(() => { api.health().then(setHealth).catch(() => setError("Backend is not reachable. Start it with: uvicorn app.main:app --port 8000")); refresh().catch(() => {}); }, []);

//   const ingest = async (fn) => {
//     setBusy(true); setError("");
//     try { const r = await fn(); await refresh(); await load(r.id); setView("Repository"); }
//     catch (e) { setError(e.message); } finally { setBusy(false); }
//   };

//   return (
//     <div className="shell">
//       <aside className="side">
//         <div className="brand"><span className="mark">⌖</span> CodeCompass</div>
//         <nav>{NAV.map((n) => <button key={n} className={view === n ? "on" : ""} onClick={() => setView(n)} disabled={!rid}>{n}</button>)}</nav>
//         <div className="mode">{health.llm ? "Answers: LLM + sources" : "Answers: sources only (no API key)"}</div>
//       </aside>
//       <main>
//         <header className="top">
//           <select value={rid || ""} onChange={(e) => e.target.value && ingest(async () => ({ id: e.target.value }))}>
//             <option value="">{repos.length ? "Choose a repository" : "No repositories yet"}</option>
//             {repos.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
//           </select>
//           <label className="btn">Upload ZIP<input type="file" accept=".zip" hidden onChange={(e) => e.target.files[0] && ingest(() => api.upload(e.target.files[0]))} /></label>
//           <form onSubmit={(e) => { e.preventDefault(); url && ingest(() => api.github(url)); }}>
//             <input placeholder="https://github.com/owner/repo" value={url} onChange={(e) => setUrl(e.target.value)} />
//             <button className="btn">Analyze</button>
//           </form>
//         </header>
//         {busy && <div className="note">Indexing repository…</div>}
//         {error && <div className="note err">{error}</div>}
//         {!rid && !busy && <div className="empty"><h1>Understand any codebase.</h1><p>Upload a ZIP or paste a public GitHub URL to get an overview, ask questions with source citations, and review code.</p></div>}
//         {rid && overview && view === "Repository" && <Explorer rid={rid} overview={overview} />}
//         {rid && view === "Chat" && <Chat rid={rid} />}
//         {rid && view === "Code review" && <Review rid={rid} llm={health.llm} />}
//         {rid && overview && view === "Insights" && <Insights rid={rid} overview={overview} />}
//       </main>
//     </div>
//   );
// }

// function Explorer({ rid, overview }) {
//   const [file, setFile] = useState(null);
//   const [exp, setExp] = useState("");
//   const open = async (p) => { setExp(""); setFile(await api.file(rid, p)); };
//   const explain = async (symbol) => { setExp("Explaining…"); try { setExp((await api.explain(rid, file.path, symbol)).explanation); } catch (e) { setExp(e.message); } };
//   return (
//     <div className="grid3">
//       <section className="panel tree"><h3>Files</h3>{overview.tree.map((p) => <button key={p} className={file?.path === p ? "on" : ""} onClick={() => open(p)}>{p}</button>)}</section>
//       <section className="panel code"><h3>{file ? file.path : "Select a file"}</h3>
//         {file && <pre>{file.source.split("\n").map((l, i) => <div key={i}><i>{i + 1}</i>{l}</div>)}</pre>}</section>
//       <section className="panel"><h3>Explain</h3>
//         {file ? <>
//           <button className="chip" onClick={() => explain(null)}>Whole file</button>
//           {file.symbols.map((s) => <button key={s.name + s.start} className="chip" onClick={() => explain(s.name)}>{s.kind} {s.name}</button>)}
//           <p className="prose">{exp}</p></> : <p className="muted">Pick a file, then a function or class.</p>}
//       </section>
//     </div>
//   );
// }

// function Chat({ rid }) {
//   const [msgs, setMsgs] = useState([]);
//   const [q, setQ] = useState("");
//   const [busy, setBusy] = useState(false);
//   const end = useRef();
//   useEffect(() => { setMsgs([]); }, [rid]);
//   useEffect(() => end.current?.scrollIntoView({ behavior: "smooth" }), [msgs]);
//   const send = async (e) => {
//     e.preventDefault(); if (!q.trim() || busy) return;
//     const question = q; setQ(""); setBusy(true); setMsgs((m) => [...m, { role: "user", text: question }]);
//     try { const r = await api.chat(rid, question); setMsgs((m) => [...m, { role: "ai", text: r.answer, cites: r.citations, id: r.retrieval_id }]); }
//     catch (err) { setMsgs((m) => [...m, { role: "ai", text: err.message, cites: [] }]); } finally { setBusy(false); }
//   };
//   return (
//     <div className="chat">
//       <div className="log">
//         {!msgs.length && <p className="muted">Try: “Where are records saved?” or “What does process_data do?”</p>}
//         {msgs.map((m, i) => <div key={i} className={"msg " + m.role}><p className="prose">{m.text}</p>
//           {m.cites?.map((c, j) => <details key={j}><summary>{c.path}:{c.start}-{c.end}{c.symbol && ` · ${c.symbol}`} <small>score {c.score}</small></summary><pre>{c.snippet}</pre></details>)}
//           {m.id && <div className="fb">Were these sources useful? <button onClick={() => api.feedback(rid, m.id, 1)}>Yes</button><button onClick={() => api.feedback(rid, m.id, -1)}>No</button></div>}
//         </div>)}
//         <div ref={end} />
//       </div>
//       <form onSubmit={send}><input placeholder="Ask anything about this repo…" value={q} onChange={(e) => setQ(e.target.value)} /><button className="btn" disabled={busy}>Ask</button></form>
//     </div>
//   );
// }

// function Review({ rid, llm }) {
//   const [data, setData] = useState(null);
//   const run = (ex) => { setData(null); api.review(rid, ex).then(setData); };
//   useEffect(() => run(false), [rid]);
//   if (!data) return <div className="note">Reviewing…</div>;
//   return (
//     <div className="panel">
//       <div className="row"><h3>{data.findings.length} findings</h3>
//         <span className="sev high">{data.summary.high} high</span><span className="sev medium">{data.summary.medium} medium</span><span className="sev low">{data.summary.low} low</span>
//         {llm && <button className="btn" onClick={() => run(true)}>Explain with AI</button>}</div>
//       <p className="muted">{data.scope}</p>
//       {data.llm_notes && <p className="prose">{data.llm_notes}</p>}
//       {data.findings.map((f, i) => <div key={i} className="finding"><span className={"sev " + f.severity}>{f.severity}</span>
//         <div><b>{f.path}:{f.line}</b> — {f.message}<p className="muted">{f.why}</p></div></div>)}
//     </div>
//   );
// }

// function Insights({ rid, overview: o }) {
//   const [m, setM] = useState(null);
//   useEffect(() => { api.metrics(rid).then(setM); }, [rid]);
//   let acc = 0;
//   const stops = o.languages.map((l, i) => { const s = `${COLORS[i % 6]} ${acc}% ${acc + l.percent}%`; acc += l.percent; return s; }).join(",");
//   const deps = [...(o.dependencies.python || []), ...(o.dependencies.node || [])];
//   return (
//     <div className="grid2">
//       <section className="panel"><h3>Languages (by lines)</h3>
//         <div className="donut" style={{ background: `conic-gradient(${stops})` }} />
//         {o.languages.map((l, i) => <div key={l.name} className="legend"><i style={{ background: COLORS[i % 6] }} />{l.name}<b>{l.percent}%</b></div>)}</section>
//       <section className="panel"><h3>Totals</h3>
//         <div className="stats"><div><b>{o.file_count}</b>files</div><div><b>{o.function_count}</b>functions</div><div><b>{o.class_count}</b>classes</div><div><b>{o.total_lines}</b>lines</div></div>
//         <p className="muted">Index: {o.index.chunks} chunks · {o.index.embedder} · {o.index.vector_store}</p>
//         {m && <p className="muted">Chat: {m.queries} questions · {m.helpful} marked useful · {m.not_helpful} not useful{m.avg_top_score != null && ` · avg top similarity ${m.avg_top_score.toFixed(2)}`}</p>}</section>
//       <section className="panel"><h3>File relationships</h3>{o.relationships.length ? o.relationships.map((r, i) => <p key={i} className="mono">{r.from} → {r.to}</p>) : <p className="muted">No internal Python imports found.</p>}</section>
//       <section className="panel"><h3>Dependencies</h3>{deps.length ? deps.map((d) => <span key={d} className="chip">{d}</span>) : <p className="muted">No requirements.txt or package.json found.</p>}</section>
//     </div>
//   );
// }



import { useEffect, useRef, useState } from "react";
import { api } from "./api.js";

const NAV = ["Repository", "Chat", "Code review", "Insights"];

const COLORS = [
  "#7c6cff",
  "#f5b942",
  "#2fb3ff",
  "#34d399",
  "#f472b6",
  "#94a3b8",
];

export default function App() {
  const [repos, setRepos] = useState([]);
  const [rid, setRid] = useState(null);
  const [overview, setOverview] = useState(null);
  const [view, setView] = useState("Repository");
  const [health, setHealth] = useState({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [url, setUrl] = useState("");

  const load = async (id) => {
    setRid(id);
    setOverview(await api.overview(id));
  };

  const refresh = async () => {
    const data = await api.repos();
    setRepos(data);
  };

  useEffect(() => {
    api.health()
      .then(setHealth)
      .catch(() => {
        setError(
          "Backend is not reachable. Start it with: uvicorn app.main:app --port 8000"
        );
      });

    refresh().catch(() => {});
  }, []);

  const ingest = async (fn) => {
    setBusy(true);
    setError("");

    try {
      const result = await fn();

      await refresh();
      await load(result.id);

      setView("Repository");
    } catch (e) {
      setError(e.message || "Something went wrong.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="shell">
      <aside className="side">
        <div className="brand">
          <span className="mark">⌖</span> CodeCompass
        </div>

        <nav>
          {NAV.map((n) => (
            <button
              key={n}
              className={view === n ? "on" : ""}
              onClick={() => setView(n)}
              disabled={!rid}
            >
              {n}
            </button>
          ))}
        </nav>

        <div className="mode">
          {health.llm
            ? "Answers: LLM + sources"
            : "Answers: sources only (no API key)"}
        </div>
      </aside>

      <main>
        <header className="top">
          <select
            value={rid || ""}
            onChange={(e) => {
              const id = e.target.value;
              if (id) {
                ingest(async () => ({ id }));
              }
            }}
          >
            <option value="">
              {repos.length ? "Choose a repository" : "No repositories yet"}
            </option>

            {repos.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </select>

          <label className="btn">
            Upload ZIP
            <input
              type="file"
              accept=".zip"
              hidden
              onChange={(e) => {
                const file = e.target.files?.[0];

                if (file) {
                  ingest(() => api.upload(file));
                  e.target.value = "";
                }
              }}
            />
          </label>

          <form
            onSubmit={(e) => {
              e.preventDefault();

              if (url.trim()) {
                ingest(() => api.github(url.trim()));
              }
            }}
          >
            <input
              placeholder="https://github.com/owner/repo"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />

            <button className="btn" disabled={busy}>
              Analyze
            </button>
          </form>
        </header>

        {busy && <div className="note">Indexing repository…</div>}

        {error && <div className="note err">{error}</div>}

        {!rid && !busy && (
          <div className="empty">
            <h1>Understand any codebase.</h1>
            <p>
              Upload a ZIP or paste a public GitHub URL to get an overview,
              ask questions with source citations, and review code.
            </p>
          </div>
        )}

        {rid && overview && view === "Repository" && (
          <Explorer rid={rid} overview={overview} />
        )}

        {rid && view === "Chat" && <Chat rid={rid} />}

        {rid && view === "Code review" && (
          <Review rid={rid} llm={health.llm} />
        )}

        {rid && overview && view === "Insights" && (
          <Insights rid={rid} overview={overview} />
        )}
      </main>
    </div>
  );
}

// --------------------------------------------------
// REPOSITORY EXPLORER
// --------------------------------------------------

function Explorer({ rid, overview }) {
  const [file, setFile] = useState(null);
  const [exp, setExp] = useState("");

  const open = async (path) => {
    setExp("");

    try {
      const result = await api.file(rid, path);
      setFile(result);
    } catch (e) {
      setExp(e.message || "Unable to open this file.");
    }
  };

  const explain = async (symbol) => {
    setExp("Explaining…");

    try {
      const result = await api.explain(rid, file.path, symbol);
      setExp(result.explanation);
    } catch (e) {
      setExp(e.message || "Unable to explain this code.");
    }
  };

  return (
    <div className="grid3">
      <section className="panel tree">
        <h3>Files</h3>

        {overview.tree.map((path) => (
          <button
            key={path}
            className={file?.path === path ? "on" : ""}
            onClick={() => open(path)}
          >
            {path}
          </button>
        ))}
      </section>

      <section className="panel code">
        <h3>{file ? file.path : "Select a file"}</h3>

        {file && (
          <pre>
            {file.source.split("\n").map((line, index) => (
              <div key={index}>
                <i>{index + 1}</i>
                {line}
              </div>
            ))}
          </pre>
        )}
      </section>

      <section className="panel">
        <h3>Explain</h3>

        {file ? (
          <>
            <button className="chip" onClick={() => explain(null)}>
              Whole file
            </button>

            {file.symbols.map((symbol) => (
              <button
                key={symbol.name + symbol.start}
                className="chip"
                onClick={() => explain(symbol.name)}
              >
                {symbol.kind} {symbol.name}
              </button>
            ))}

            <p className="prose">{exp}</p>
          </>
        ) : (
          <p className="muted">
            Pick a file, then a function or class.
          </p>
        )}
      </section>
    </div>
  );
}

// --------------------------------------------------
// CHAT
// --------------------------------------------------

function Chat({ rid }) {
  const [msgs, setMsgs] = useState([]);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState({});
  const [feedbackError, setFeedbackError] = useState("");

  const end = useRef(null);

  useEffect(() => {
    setMsgs([]);
    setQ("");
    setFeedback({});
    setFeedbackError("");
  }, [rid]);

  useEffect(() => {
    if (end.current) {
      end.current.scrollIntoView({
        behavior: "smooth",
        block: "end",
      });
    }
  }, [msgs]);

  const submitFeedback = async (retrievalId, value) => {
    if (feedback[retrievalId]) return;

    setFeedbackError("");
    setFeedback((previous) => ({
      ...previous,
      [retrievalId]: "saving",
    }));

    try {
      await api.feedback(rid, retrievalId, value);
      setFeedback((previous) => ({
        ...previous,
        [retrievalId]: value,
      }));
    } catch (error) {
      setFeedback((previous) => {
        const next = { ...previous };
        delete next[retrievalId];
        return next;
      });
      setFeedbackError(
        error.message || "Could not save your feedback. Please try again."
      );
    }
  };

  const send = async (e) => {
    e.preventDefault();

    if (!q.trim() || busy) return;

    const question = q.trim();

    setQ("");
    setBusy(true);

    setMsgs((previous) => [
      ...previous,
      { role: "user", text: question },
    ]);

    try {
      const result = await api.chat(rid, question);

      setMsgs((previous) => [
        ...previous,
        {
          role: "ai",
          text: result.answer,
          cites: result.citations,
          id: result.retrieval_id,
        },
      ]);
    } catch (err) {
      setMsgs((previous) => [
        ...previous,
        {
          role: "ai",
          text: err.message || "Unable to get an answer.",
          cites: [],
        },
      ]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="chat">
      <div className="log">
        {!msgs.length && (
          <p className="muted">
            Try: "Where are records saved?" or
            "What does process_data do?"
          </p>
        )}

        {msgs.map((message, index) => (
          <div
            key={index}
            className={"msg " + message.role}
          >
            <p className="prose">{message.text}</p>

            {message.cites?.map((citation, citationIndex) => (
              <details key={citationIndex}>
                <summary>
                  {citation.path}:{citation.start}-{citation.end}
                  {citation.symbol && ` · ${citation.symbol}`}
                  <small> score {citation.score}</small>
                </summary>

                <pre>{citation.snippet}</pre>
              </details>
            ))}

            {message.id && (
              <div className="fb">
                {feedback[message.id] === 1 ? (
                  <span>Thanks! You marked these sources useful.</span>
                ) : feedback[message.id] === -1 ? (
                  <span>Thanks! You marked these sources not useful.</span>
                ) : (
                  <>
                    <span>Were these sources useful?</span>

                    <button
                      type="button"
                      disabled={feedback[message.id] === "saving"}
                      aria-pressed={false}
                      onClick={() => submitFeedback(message.id, 1)}
                    >
                      {feedback[message.id] === "saving" ? "Saving…" : "Yes"}
                    </button>

                    <button
                      type="button"
                      disabled={feedback[message.id] === "saving"}
                      aria-pressed={false}
                      onClick={() => submitFeedback(message.id, -1)}
                    >
                      {feedback[message.id] === "saving" ? "Saving…" : "No"}
                    </button>
                  </>
                )}
              </div>
            )}

            {feedbackError && message.id && (
              <p className="muted" role="alert">{feedbackError}</p>
            )}
          </div>
        ))}

        {busy && (
          <div className="msg ai">
            <p className="muted">Searching your repository…</p>
          </div>
        )}

        <div ref={end} />
      </div>

      <form onSubmit={send}>
        <input
          placeholder="Ask anything about this repo…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          disabled={busy}
        />

        <button
          className="btn"
          disabled={busy || !q.trim()}
        >
          {busy ? "Thinking…" : "Ask"}
        </button>
      </form>
    </div>
  );
}

// --------------------------------------------------
// CODE REVIEW
// --------------------------------------------------

function Review({ rid, llm }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const run = async (explainWithAI) => {
    setData(null);
    setError("");
    setBusy(true);

    try {
      const result = await api.review(rid, explainWithAI);
      setData(result);
    } catch (e) {
      setError(e.message || "Unable to review this repository.");
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    run(false);
  }, [rid]);

  if (error) {
    return <div className="note err">{error}</div>;
  }

  if (busy || !data) {
    return <div className="note">Reviewing…</div>;
  }

  return (
    <div className="panel">
      <div className="row">
        <h3>{data.findings.length} findings</h3>

        <span className="sev high">
          {data.summary.high} high
        </span>

        <span className="sev medium">
          {data.summary.medium} medium
        </span>

        <span className="sev low">
          {data.summary.low} low
        </span>

        {llm && (
          <button
            className="btn"
            onClick={() => run(true)}
            disabled={busy}
          >
            Explain with AI
          </button>
        )}
      </div>

      <p className="muted">{data.scope}</p>

      {data.llm_notes && (
        <p className="prose">{data.llm_notes}</p>
      )}

      {data.findings.map((finding, index) => (
        <div key={index} className="finding">
          <span className={"sev " + finding.severity}>
            {finding.severity}
          </span>

          <div>
            <b>
              {finding.path}:{finding.line}
            </b>{" "}
            — {finding.message}

            <p className="muted">{finding.why}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

// --------------------------------------------------
// INSIGHTS
// --------------------------------------------------

function Insights({ rid, overview }) {
  const [metrics, setMetrics] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    api.metrics(rid)
      .then((result) => {
        if (active) setMetrics(result);
      })
      .catch((e) => {
        if (active) setError(e.message);
      });

    return () => {
      active = false;
    };
  }, [rid]);

  let accumulated = 0;

  const stops = overview.languages
    .map((language, index) => {
      const stop = `${COLORS[index % 6]} ${accumulated}% ${
        accumulated + language.percent
      }%`;

      accumulated += language.percent;
      return stop;
    })
    .join(",");

  const dependencies = [
    ...(overview.dependencies.python || []),
    ...(overview.dependencies.node || []),
  ];

  return (
    <div className="grid2">
      <section className="panel">
        <h3>Languages (by lines)</h3>

        <div
          className="donut"
          style={{
            background: `conic-gradient(${stops})`,
          }}
        />

        {overview.languages.map((language, index) => (
          <div key={language.name} className="legend">
            <i
              style={{
                background: COLORS[index % 6],
              }}
            />

            {language.name}

            <b>{language.percent}%</b>
          </div>
        ))}
      </section>

      <section className="panel">
        <h3>Totals</h3>

        <div className="stats">
          <div>
            <b>{overview.file_count}</b> files
          </div>

          <div>
            <b>{overview.function_count}</b> functions
          </div>

          <div>
            <b>{overview.class_count}</b> classes
          </div>

          <div>
            <b>{overview.total_lines}</b> lines
          </div>
        </div>

        <p className="muted">
          Index: {overview.index.chunks} chunks ·
          {overview.index.embedder} ·
          {overview.index.vector_store}
        </p>

        {error && <p className="note err">{error}</p>}

        {metrics && (
          <p className="muted">
            Chat: {metrics.queries} questions ·
            {metrics.helpful} marked useful ·
            {metrics.not_helpful} not useful
            {metrics.avg_top_score != null &&
              ` · avg top similarity ${metrics.avg_top_score.toFixed(2)}`}
          </p>
        )}
      </section>

      <section className="panel">
        <h3>File relationships</h3>

        {overview.relationships.length ? (
          overview.relationships.map((relationship, index) => (
            <p key={index} className="mono">
              {relationship.from} → {relationship.to}
            </p>
          ))
        ) : (
          <p className="muted">
            No internal Python imports found.
          </p>
        )}
      </section>

      <section className="panel">
        <h3>Dependencies</h3>

        {dependencies.length ? (
          dependencies.map((dependency) => (
            <span key={dependency} className="chip">
              {dependency}
            </span>
          ))
        ) : (
          <p className="muted">
            No requirements.txt or package.json found.
          </p>
        )}
      </section>
    </div>
  );
}



