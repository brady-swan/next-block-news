"use strict";
// Visible-tab polling only; the server supplies escaped read-only fragments.
(() => {
  const content = document.getElementById("content");
  const connection = document.getElementById("connection");
  const pause = document.getElementById("pause");
  const refresh = document.getElementById("refresh");
  if (!content || !connection || !pause || !refresh) return;
  let paused = false, busy = false, timer;
  let lastSuccess = Number(content.dataset.observed) * 1000;
  const timestamp = value => new Date(value).toLocaleTimeString("en-US", {timeZone: "America/Chicago", hour: "numeric", minute: "2-digit", second: "2-digit"}) + " CT";
  const schedule = () => {
    clearTimeout(timer);
    if (!paused && !document.hidden) timer = setTimeout(() => update(false), 15000);
  };
  async function update(manual) {
    if (busy || (!manual && (paused || document.hidden))) return;
    // Do not replace focused controls or copy someone is selecting.
    if (!manual && (content.contains(document.activeElement) || String(window.getSelection()).length)) {
      connection.textContent = `Updates waiting while reading · snapshot ${timestamp(lastSuccess)}`;
      schedule(); return;
    }
    busy = true; refresh.disabled = true;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
    try {
      const url = new URL("/desk/api/snapshot", window.location.origin);
      url.search = window.location.search;
      url.searchParams.set("view", document.body.dataset.view);
      // Keep the loaded Central date fixed, including across midnight.
      url.searchParams.set("d", document.querySelector('input[name="d"]').defaultValue);
      const response = await fetch(url, {cache: "no-store", signal: controller.signal, referrerPolicy: "no-referrer"});
      if (!response.ok) throw new Error(String(response.status));
      const data = await response.json();
      if (typeof data.html !== "string" || !Number.isFinite(data.generated_at)) throw new Error("shape");
      const openIds = [...content.querySelectorAll("details[open][id]")].map(el => el.id);
      content.innerHTML = data.html;
      for (const id of openIds) { const el = document.getElementById(id); if (el) el.open = true; }
      lastSuccess = data.generated_at * 1000;
      connection.textContent = `${paused ? "Paused · " : "Updated "}${timestamp(lastSuccess)}`;
      connection.classList.remove("failed");
    } catch (_) {
      connection.textContent = `Updates unavailable · last success ${timestamp(lastSuccess)}. Display may be stale.`;
      connection.classList.add("failed");
    } finally {
      clearTimeout(timeout); busy = false; refresh.disabled = false; schedule();
    }
  }
  pause.addEventListener("click", () => {
    paused = !paused; pause.textContent = paused ? "Resume updates" : "Pause updates";
    pause.setAttribute("aria-pressed", String(paused));
    connection.textContent = `${paused ? "Paused · snapshot " : "Snapshot "}${timestamp(lastSuccess)}`;
    if (!paused) update(true); else schedule();
  });
  refresh.addEventListener("click", () => update(true));
  document.addEventListener("visibilitychange", () => {
    clearTimeout(timer); if (!document.hidden && !paused) update(false);
  });
  schedule();
})();
