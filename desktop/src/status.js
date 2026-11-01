const logEl = document.getElementById("log");
const add = (line) => {
  const atEnd = logEl.scrollTop + logEl.clientHeight >= logEl.scrollHeight - 20;
  logEl.append(line + "\n");
  if (atEnd) logEl.scrollTop = logEl.scrollHeight;
};
const when = (iso) => (iso ? new Date(iso).toLocaleString() : "never");
window.x25.init().then((s) => {
  s.lines.forEach(add);
  logEl.scrollTop = logEl.scrollHeight;
  document.getElementById("facts").textContent =
    `Last data update: ${when(s.lastUpdateAt)}. Last full load: ${when(s.lastFullAt)}. ` +
    (s.running ? `Running now: ${s.running === "full" ? "full load" : "update"}. ` : "") +
    `Data folder: ${s.dataDir}`;
});
window.x25.onLog(add);
window.x25.onStatus((t) => (document.getElementById("status").textContent = t));
document.getElementById("open").addEventListener("click", () => window.x25.openApp());
