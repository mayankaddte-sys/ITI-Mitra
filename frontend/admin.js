const API_URL = window.ITI_MITRA_API_URL || "";
const $ = (id) => document.getElementById(id);
let adminKey = sessionStorage.getItem("iti_admin_key") || "";

function setStatus(el, text, color) {
  el.textContent = text;
  el.style.color = color || "";
}

async function api(path, options = {}) {
  const headers = Object.assign({ "X-API-Key": adminKey }, options.headers || {});
  const res = await fetch(`${API_URL}${path}`, Object.assign({}, options, { headers }));
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : `Request failed (${res.status})`);
  return data;
}

function showPanels(unlocked) {
  $("loginPanel").hidden = unlocked;
  $("adminPanels").hidden = !unlocked;
}

async function refresh() {
  const data = await api("/admin/files");
  $("kbStats").textContent = `Files: ${data.stats.files_indexed} • Chunks: ${data.stats.total_chunks}`;
  const list = $("filesList");
  list.replaceChildren();
  if (!data.files.length) {
    const p = document.createElement("p");
    p.className = "hint";
    p.textContent = "No documents indexed yet.";
    list.appendChild(p);
    return;
  }
  data.files.forEach((f) => {
    const item = document.createElement("div");
    item.className = "file-item";
    const name = document.createElement("span");
    const meta = [f.category, f.issue_date].filter(Boolean).join(" • ");
    name.textContent = `📄 ${f.filename}${meta ? "  (" + meta + ")" : ""}`; // textContent: filenames are untrusted
    const del = document.createElement("button");
    del.className = "btn-mini";
    del.textContent = "Delete";
    del.addEventListener("click", async () => {
      if (!confirm(`Delete "${f.filename}" from the knowledge base?`)) return;
      try {
        await api(`/admin/files/${encodeURIComponent(f.filename)}`, { method: "DELETE" });
        await refresh();
      } catch (e) {
        setStatus($("uploadStatus"), `✗ ${e.message}`, "#ef4444");
      }
    });
    item.append(name, del);
    list.appendChild(item);
  });
}

function fillList(el, rows, render) {
  el.replaceChildren();
  if (!rows.length) {
    const p = document.createElement("p");
    p.className = "hint";
    p.textContent = "Nothing yet.";
    el.appendChild(p);
    return;
  }
  rows.forEach((r) => {
    const d = document.createElement("div");
    d.className = "file-item";
    d.textContent = render(r); // textContent: trainee-typed text is untrusted
    el.appendChild(d);
  });
}

async function refreshInsights() {
  const data = await api("/admin/insights");
  $("insightTotals").textContent = `👍 ${data.totals.up}  •  👎 ${data.totals.down}`;
  fillList($("unansweredList"), data.unanswered, (r) => `${r.count}× ${r.question}`);
  fillList($("downList"), data.thumbs_down, (r) => `Q: ${r.question}${r.comment ? " — " + r.comment : ""}`);
}

async function unlock(key) {
  adminKey = key;
  try {
    await api("/admin/check");
    sessionStorage.setItem("iti_admin_key", key); // cleared when the tab closes
    showPanels(true);
    await refresh();
    await refreshInsights();
  } catch (e) {
    adminKey = "";
    sessionStorage.removeItem("iti_admin_key");
    showPanels(false);
    setStatus($("loginStatus"), `✗ ${e.message}`, "#ef4444");
  }
}

async function uploadFiles(files) {
  for (const file of files) {
    setStatus($("uploadStatus"), `Uploading and indexing ${file.name}…`, "#cbd5e1");
    const fd = new FormData();
    fd.append("file", file);
    fd.append("category", $("category").value);
    fd.append("issue_date", $("issueDate").value);
    try {
      const r = await api("/admin/upload", { method: "POST", body: fd });
      setStatus($("uploadStatus"), `✓ ${r.filename}: ${r.chunks} chunks indexed`, "#4ade80");
    } catch (e) {
      setStatus($("uploadStatus"), `✗ ${file.name}: ${e.message}`, "#ef4444");
    }
  }
  await refresh();
}

$("loginBtn").addEventListener("click", () => unlock($("keyInput").value.trim()));
$("keyInput").addEventListener("keydown", (e) => e.key === "Enter" && unlock($("keyInput").value.trim()));
$("logoutBtn").addEventListener("click", () => {
  adminKey = "";
  sessionStorage.removeItem("iti_admin_key");
  $("keyInput").value = "";
  showPanels(false);
});
$("dropZone").addEventListener("click", () => $("fileInput").click());
$("dropZone").addEventListener("dragover", (e) => { e.preventDefault(); $("dropZone").classList.add("dragover"); });
$("dropZone").addEventListener("dragleave", () => $("dropZone").classList.remove("dragover"));
$("dropZone").addEventListener("drop", (e) => {
  e.preventDefault();
  $("dropZone").classList.remove("dragover");
  uploadFiles(e.dataTransfer.files);
});
$("fileInput").addEventListener("change", async () => {
  await uploadFiles($("fileInput").files);
  $("fileInput").value = "";
});
$("clearInsightsBtn").addEventListener("click", async () => {
  if (!confirm("Clear the unanswered-question and feedback log?")) return;
  try {
    await api("/admin/insights", { method: "DELETE" });
    await refreshInsights();
  } catch (e) {
    setStatus($("uploadStatus"), `✗ ${e.message}`, "#ef4444");
  }
});
$("clearKBBtn").addEventListener("click", async () => {
  if (!confirm("This deletes ALL indexed documents. Continue?")) return;
  try {
    await api("/admin/knowledge-base", { method: "DELETE" });
    await refresh();
  } catch (e) {
    setStatus($("uploadStatus"), `✗ ${e.message}`, "#ef4444");
  }
});

if (adminKey) unlock(adminKey);
