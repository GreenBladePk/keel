const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

function restore() {
  $("url").value = localStorage.getItem("keel_url") || "http://localhost:8000";
  $("token").value = localStorage.getItem("keel_token") || "";
}

function base() { return ($("url").value || "").replace(/\/$/, ""); }

async function api(path) {
  const r = await fetch(base() + path, {
    headers: { "Authorization": "Bearer " + $("token").value, "X-Keel-Session": "dashboard" },
  });
  if (!r.ok) throw new Error(r.status === 401 ? "unauthorized (check token)" : "HTTP " + r.status);
  return r.json();
}

function rows(el, items, fn) {
  el.innerHTML = items.length ? items.map((x) => `<div class="row">${fn(x)}</div>`).join("")
                             : `<div class="row mut">none</div>`;
}

async function refresh() {
  try {
    localStorage.setItem("keel_url", $("url").value);
    localStorage.setItem("keel_token", $("token").value);
    const state = await api("/api/state");
    const ev = await api("/api/events?limit=100");
    rows($("decisions"), state.active_decisions, (d) =>
      `${esc(d.statement)} <span class="tag">[${esc((d.scope_tags || []).join(", "))}]</span>`);
    rows($("conflicts"), state.open_conflicts, (c) =>
      `<span class="pill">${esc(c.severity)}/${esc(c.relation)}</span> ${esc(c.explanation)}`);
    rows($("alerts"), state.pending_alerts, (a) =>
      `<span class="pill">${esc(a.kind)}</span> ${esc(a.ref_id)}`);
    rows($("handoffs"), state.pending_handoffs, (h) =>
      `→ ${esc(h.note || "")} <span class="tag">[${esc((h.scope_tags || []).join(", "))}]</span>`);
    rows($("events"), ev.events, (e) =>
      `<span class="mut">${esc(e.created_at || "")}</span> <code>${esc(e.action)}</code> `
      + `<span class="mut">by ${esc(e.actor)}</span>`);
    $("msg").textContent = "updated " + new Date().toLocaleTimeString();
  } catch (err) {
    $("msg").textContent = "error: " + err.message;
  }
}

let timer = null;
$("go").onclick = refresh;
$("auto").onchange = (e) => {
  clearInterval(timer);
  if (e.target.checked) timer = setInterval(refresh, 5000);
};
restore();
if ($("token").value) refresh();
