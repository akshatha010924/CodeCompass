async function req(url, opts) {
  const r = await fetch(url, opts);
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(body.detail || `Request failed (${r.status})`);
  return body;
}
const post = (url, data) => req(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
export const api = {
  health: () => req("/api/health"),
  repos: () => req("/api/repos"),
  upload: (file) => { const f = new FormData(); f.append("file", file); return req("/api/repos/upload", { method: "POST", body: f }); },
  github: (url) => post("/api/repos/github", { url }),
  overview: (id) => req(`/api/repos/${id}/overview`),
  file: (id, path) => req(`/api/repos/${id}/file?path=${encodeURIComponent(path)}`),
  chat: (id, question) => post(`/api/repos/${id}/chat`, { question }),
  explain: (id, path, symbol) => post(`/api/repos/${id}/explain`, { path, symbol }),
  review: (id, explain) => req(`/api/repos/${id}/review?explain=${explain}`),
  feedback: (id, retrieval_id, value) => post(`/api/repos/${id}/feedback`, { retrieval_id, value }),
  metrics: (id) => req(`/api/repos/${id}/metrics`),
};
