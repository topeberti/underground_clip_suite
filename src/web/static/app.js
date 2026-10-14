"use strict";

// ---------------------------------------------------------------- helpers
const $ = (id) => document.getElementById(id);

function el(tag, props = {}, ...children) {
  const node = Object.assign(document.createElement(tag), props);
  for (const c of children) node.append(c);
  return node;
}

async function api(url, { method = "GET", body } = {}) {
  const res = await fetch(url, {
    method,
    headers: body !== undefined ? { "Content-Type": "application/json" } : (method !== "GET" ? { "Content-Type": "application/json" } : {}),
    body: body !== undefined ? JSON.stringify(body) : (method !== "GET" ? "{}" : undefined),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
  return data;
}

let toastTimer;
function toast(msg, isError = false) {
  const t = $("toast");
  t.textContent = msg;
  t.className = isError ? "error" : "";
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (t.hidden = true), isError ? 8000 : 3500);
}

// Run fn, toasting any error. Disables `btn` while running.
async function guarded(btn, fn) {
  if (btn) btn.disabled = true;
  try { return await fn(); }
  catch (e) { toast(e.message, true); }
  finally { if (btn) btn.disabled = false; }
}

const fmtMs = (ms) => {
  const s = Math.floor(ms / 1000), m = Math.floor(s / 60);
  return `${String(m).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}.${String(Math.floor(ms % 1000)).padStart(3, "0")}`;
};

// Start a job and stream it into box ({log pre, progress}). Resolves with the final job summary.
function runJob(url, body, box) {
  return new Promise(async (resolve, reject) => {
    let started;
    try { started = await api(url, { method: "POST", body }); }
    catch (e) { return reject(e); }

    const log = box.querySelector(".log");
    const bar = box.querySelector("progress");
    box.hidden = false;
    log.textContent = "";
    if (bar) { bar.value = 0; bar.max = 1; }

    const es = new EventSource(`/api/jobs/${started.job_id}/events`);
    es.addEventListener("log", (ev) => {
      const stick = log.scrollTop + log.clientHeight >= log.scrollHeight - 20;
      log.textContent += JSON.parse(ev.data) + "\n";
      if (stick) log.scrollTop = log.scrollHeight;
    });
    es.addEventListener("progress", (ev) => {
      const p = JSON.parse(ev.data);
      if (bar && p.total) { bar.max = p.total; bar.value = p.done; }
    });
    es.addEventListener("end", (ev) => {
      es.close();
      const job = JSON.parse(ev.data);
      if (job.status === "failed") toast(job.error || "Job failed", true);
      resolve(job);
    });
    es.onerror = () => { es.close(); reject(new Error("Lost connection to the server.")); };
  });
}

// ---------------------------------------------------------------- tabs
const loaders = { dashboard: loadStats, library: () => loadClips(), upload: loadUploadInfo };
function showTab(name) {
  document.querySelectorAll("#tabs button").forEach((b) => b.classList.toggle("active", b.dataset.tab === name));
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.id === `tab-${name}`));
  location.hash = name;
  loaders[name]?.();
}
$("tabs").addEventListener("click", (e) => e.target.dataset.tab && showTab(e.target.dataset.tab));

// ---------------------------------------------------------------- file picker
const picker = { cur: "", mode: "file", ext: "", target: null };

async function pickerLoad(path) {
  try {
    const q = new URLSearchParams({ path, ext: picker.mode === "file" ? picker.ext : "" });
    const data = await api(`/api/fs/list?${q}`);
    picker.cur = data.path;
    picker.parent = data.parent;
    $("pk-path").value = data.path;
    $("pk-up").disabled = data.parent === null;
    const list = $("pk-list");
    list.replaceChildren();
    for (const e of data.entries) {
      if (!e.is_dir && picker.mode === "dir") continue;
      const li = el("li", { textContent: (e.is_dir ? "📁 " : "🎵 ") + e.name });
      li.onclick = () => {
        if (e.is_dir) pickerLoad(e.path);
        else { $(picker.target).value = e.path; $(picker.target).dispatchEvent(new Event("change")); $("picker").close(); }
      };
      list.append(li);
    }
  } catch (err) { toast(err.message, true); }
}

document.addEventListener("click", (e) => {
  const b = e.target.closest("[data-pick]");
  if (!b) return;
  picker.mode = b.dataset.pick;
  picker.ext = b.dataset.ext || "";
  picker.target = b.dataset.target;
  $("pk-choose").hidden = picker.mode !== "dir";
  const cur = $(picker.target).value;
  const start = picker.mode === "dir" ? cur : cur.replace(/[\\/][^\\/]*$/, "");
  $("picker").showModal();
  pickerLoad(start);
});
$("pk-up").onclick = () => pickerLoad(picker.parent ?? "");
$("pk-go").onclick = () => pickerLoad($("pk-path").value);
$("pk-path").onkeydown = (e) => e.key === "Enter" && pickerLoad($("pk-path").value);
$("pk-cancel").onclick = () => $("picker").close();
$("pk-choose").onclick = () => { $(picker.target).value = picker.cur; $("picker").close(); };

// ---------------------------------------------------------------- dashboard
async function loadStats() {
  const s = await api("/api/stats").catch((e) => toast(e.message, true));
  if (!s) return;
  $("stats-empty").hidden = s.initialized;
  const box = $("stats");
  box.replaceChildren();
  if (!s.initialized) return;
  const stat = (label, value) => el("div", { className: "stat" }, el("b", { textContent: value }), el("span", { textContent: label }));
  box.append(stat("Total clips", s.total), stat("Total hours", s.total_hours.toFixed(2)));
  for (const [v, n] of Object.entries(s.by_vibe)) box.append(stat(`vibe: ${v}`, n));
  box.append(
    stat("Energy low (≤0.4)", s.energy_histogram.low),
    stat("Energy mid", s.energy_histogram.mid),
    stat("Energy high (≥0.6)", s.energy_histogram.high),
  );
}
$("btn-init-db").onclick = (e) => guarded(e.target, async () => { await api("/api/db/init", { method: "POST" }); toast("Database initialized."); loadStats(); });
$("btn-refresh-stats").onclick = loadStats;

// ---------------------------------------------------------------- library
let clipOffset = 0;
const PAGE = 50;

async function loadClips(offset = clipOffset) {
  clipOffset = Math.max(0, offset);
  const q = new URLSearchParams({ search: $("clip-search").value, vibe: $("clip-vibe").value, offset: clipOffset, limit: PAGE });
  let data;
  try { data = await api(`/api/clips?${q}`); }
  catch (e) { $("clip-count").textContent = e.message; $("clip-table").querySelector("tbody").replaceChildren(); return; }

  $("clip-count").textContent = `${data.total} clip(s)`;
  $("clip-prev").disabled = clipOffset === 0;
  $("clip-next").disabled = clipOffset + PAGE >= data.total;
  const body = $("clip-table").querySelector("tbody");
  body.replaceChildren(...data.clips.map((c) => {
    const retag = el("button", { className: "secondary", textContent: "Re-tag" });
    retag.onclick = () => guarded(retag, async () => {
      const box = $("tag-job");
      const job = await runJob("/api/jobs/retag", { path: c.path }, box);
      if (job.status === "done") { toast("Re-tagged."); loadClips(); }
    });
    const rm = el("button", { className: "danger", textContent: "Remove" });
    rm.onclick = () => guarded(rm, async () => {
      if (!confirm(`Remove from database?\n${c.path}\n(The file on disk is kept.)`)) return;
      await api("/api/clips", { method: "DELETE", body: { path: c.path } });
      loadClips();
    });
    return el("tr", {},
      el("td", { className: "path", textContent: c.path }),
      el("td", { className: `vibe-${c.vibe_label}`, textContent: c.vibe_label }),
      el("td", { textContent: c.energy_score?.toFixed(2) ?? "" }),
      el("td", { textContent: c.duration_sec ? `${c.duration_sec.toFixed(1)}s` : "" }),
      el("td", {}, ...c.tags.slice(0, 6).map((t) => el("span", { className: "tag", textContent: t }))),
      el("td", {}, retag, " ", rm),
    );
  }));
}
let searchTimer;
$("clip-search").oninput = () => { clearTimeout(searchTimer); searchTimer = setTimeout(() => loadClips(0), 300); };
$("clip-vibe").onchange = () => loadClips(0);
$("clip-prev").onclick = () => loadClips(clipOffset - PAGE);
$("clip-next").onclick = () => loadClips(clipOffset + PAGE);

$("btn-tag").onclick = (e) => guarded(e.target, async () => {
  const job = await runJob("/api/jobs/tag", { folder: $("tag-folder").value.trim(), force: $("tag-force").checked }, $("tag-job"));
  if (job.status === "done") { toast("Tagging finished."); loadClips(0); }
});

$("btn-anime-preview").onclick = (e) => guarded(e.target, async () => {
  const name = $("anime-name").value.trim();
  const data = await api(`/api/anime/preview?name=${encodeURIComponent(name)}`);
  $("anime-preview").hidden = false;
  $("anime-summary").textContent = data.count ? `${data.count} clip(s) match "${name}"${data.count > data.paths.length ? ` (showing ${data.paths.length})` : ""}:` : `No clips match "${name}".`;
  $("anime-paths").textContent = data.paths.join("\n");
  $("btn-anime-remove").hidden = !data.count;
  $("anime-delete-files").parentElement.hidden = !data.count;
});
$("btn-anime-remove").onclick = (e) => guarded(e.target, async () => {
  const name = $("anime-name").value.trim();
  const delFiles = $("anime-delete-files").checked;
  const msg = delFiles
    ? `PERMANENTLY delete all clips matching "${name}" from the database AND from disk?`
    : `Remove all clips matching "${name}" from the database?`;
  if (!confirm(msg)) return;
  const r = await api("/api/anime/remove", { method: "POST", body: { name, delete_files: delFiles } });
  toast(`Removed ${r.deleted_from_db} from DB` + (delFiles ? `, deleted ${r.files_deleted} file(s)` + (r.files_missing ? ` (${r.files_missing} already missing)` : "") : "."));
  $("anime-preview").hidden = true;
  loadClips(0);
});

// ---------------------------------------------------------------- lyric sync
const ly = { taps: [], durationMs: 0, phase: "idle", t0: 0, raf: 0, segStop: null, saved: null };
const player = $("ly-player");

$("ly-load").onclick = () => {
  const path = $("ly-audio").value.trim();
  if (!path) return toast("Pick an audio file first.", true);
  player.src = `/api/media?path=${encodeURIComponent(path)}`;
  player.hidden = false;
  player.onloadedmetadata = () => {
    ly.durationMs = Math.round(player.duration * 1000);
    $("ly-tap").hidden = false;
    $("ly-assign").hidden = true;
    $("ly-out").value = path.replace(/\.[^.\\/]+$/, "") + ".srt";
    resetTaps();
  };
  player.onerror = () => toast("Could not load that audio file.", true);
};

function resetTaps() {
  ly.taps = [];
  ly.phase = "idle";
  cancelAnimationFrame(ly.raf);
  $("ly-big").textContent = "—";
  $("ly-start").hidden = false;
  $("ly-stop").hidden = true;
  renderTaps();
}

function renderTaps() {
  $("ly-taps").replaceChildren(...ly.taps.map((t) => el("li", { textContent: fmtMs(t) })));
  $("ly-taps").scrollTop = 1e9;
}

function tick() {
  if (ly.phase !== "tapping") return;
  $("ly-big").textContent = fmtMs(player.currentTime * 1000);
  ly.raf = requestAnimationFrame(tick);
}

$("ly-start").onclick = async () => {
  ly.taps = [];
  renderTaps();
  player.pause();
  ly.phase = "countdown";
  $("ly-start").hidden = true;
  $("ly-stop").hidden = false;
  for (let i = Math.max(0, +$("ly-countdown").value || 0); i > 0; i--) {
    $("ly-big").textContent = i;
    await new Promise((r) => setTimeout(r, 1000));
    if (ly.phase !== "countdown") return;   // cancelled
  }
  player.currentTime = 0;
  ly.phase = "tapping";
  await player.play().catch((e) => { toast(e.message, true); resetTaps(); });
  tick();
};
$("ly-stop").onclick = () => finishTaps();
player.addEventListener("ended", () => ly.phase === "tapping" && finishTaps());

function finishTaps() {
  if (ly.phase === "idle") return;
  const wasTapping = ly.phase === "tapping";
  player.pause();
  cancelAnimationFrame(ly.raf);
  if (!wasTapping || !ly.taps.length) { resetTaps(); return; }
  ly.phase = "assign";
  buildSegments();
}

document.addEventListener("keydown", (e) => {
  if (ly.phase !== "tapping" || !$("tab-lyrics").classList.contains("active")) return;
  if (e.code === "Space") {
    e.preventDefault();
    if (e.repeat) return;
    ly.taps.push(Math.round(player.currentTime * 1000));   // media clock, not wall clock
    renderTaps();
  } else if (e.code === "Backspace") {
    e.preventDefault();
    ly.taps.pop();
    renderTaps();
  } else if (e.key === "r" || e.key === "R") {
    ly.phase = "countdown"; player.pause(); cancelAnimationFrame(ly.raf);
    $("ly-start").click();
  } else if (e.key === "q" || e.key === "Q") {
    finishTaps();
  }
});

function buildSegments() {
  // Auto tap at 0, like the CLI; drop taps that don't advance time.
  const starts = [0];
  for (const t of ly.taps) if (t > starts[starts.length - 1]) starts.push(t);
  const ends = [...starts.slice(1), ly.durationMs];
  ly.segs = starts.map((s, i) => ({ start_ms: s, end_ms: ends[i], text: "" }));
  renderSegments();

  $("ly-assign").hidden = false;
  $("ly-use-build").hidden = true;
  $("ly-assign").scrollIntoView({ behavior: "smooth" });
  const rows = $("ly-rows");
  rows.querySelector("input")?.focus();
  rows.querySelector("button")?.click();
}

// Remove segment i: the previous one grows to cover the gap
// (the first segment has no previous one, so the next one is pulled back to its start).
function deleteSegment(i) {
  if (ly.segs.length <= 1) return;
  const [gone] = ly.segs.splice(i, 1);
  if (i > 0) ly.segs[i - 1].end_ms = gone.end_ms;
  else ly.segs[0].start_ms = gone.start_ms;
  player.pause();
  $("ly-use-build").hidden = true;   // the saved .srt no longer matches
  renderSegments(Math.max(i - 1, 0));
}

function renderSegments(focusIdx = null) {
  const rows = $("ly-rows");
  rows.replaceChildren();
  ly.segs.forEach((seg, i) => {
    const input = el("input", { placeholder: "(empty = skip)", value: seg.text || "" });
    input.oninput = () => (row.classList.toggle("skipped", !input.value.trim()), seg.text = input.value);
    input.onkeydown = (e) => {
      if (e.key !== "Enter") return;
      e.preventDefault();
      const next = rows.children[i + 1]?.querySelector("input");
      if (next) { next.focus(); next.parentElement.querySelector("button").click(); }
    };
    const play = el("button", { className: "secondary", textContent: "▶", title: "Play this segment" });
    play.onclick = () => playSegment(seg);
    const del = el("button", { className: "secondary", textContent: "🗑", title: "Delete this line (previous line extends to fill the gap)", disabled: ly.segs.length <= 1 });
    del.onclick = () => deleteSegment(i);
    const row = el("div", { className: `seg${seg.text?.trim() ? "" : " skipped"}` },
      el("span", { className: "time", textContent: `${i + 1}. ${fmtMs(seg.start_ms)} → ${fmtMs(seg.end_ms)}` }),
      play, input, del);
    rows.append(row);
  });
  if (focusIdx !== null) {
    const row = rows.children[focusIdx];
    row?.querySelector("input").focus();
    row?.querySelector("button").click();   // replay the segment that was extended
  }
}

function playSegment(seg) {
  if (ly.segStop) player.removeEventListener("timeupdate", ly.segStop);
  player.currentTime = seg.start_ms / 1000;
  ly.segStop = () => { if (player.currentTime * 1000 >= seg.end_ms) { player.pause(); player.removeEventListener("timeupdate", ly.segStop); } };
  player.addEventListener("timeupdate", ly.segStop);
  player.play();
}

$("ly-redo").onclick = () => { player.pause(); $("ly-assign").hidden = true; resetTaps(); $("ly-tap").scrollIntoView(); };

$("ly-save").onclick = (e) => guarded(e.target, async () => {
  const entries = ly.segs.filter((s) => (s.text || "").trim());
  const r = await api("/api/lyrics/save", { method: "POST", body: { output_path: $("ly-out").value.trim(), entries } });
  ly.saved = r.path;
  toast(`Saved ${r.count} line(s) → ${r.path}`);
  $("ly-use-build").hidden = false;
});
$("ly-use-build").onclick = () => {
  $("b-song").value = $("ly-audio").value;
  syncBuildOut();
  $("b-lyrics").value = ly.saved;
  $("b-name").value = $("ly-audio").value.replace(/^.*[\\/]/, "").replace(/\.[^.]+$/, "") || "video_project";
  showTab("build");
};

// ---------------------------------------------------------------- build
// Default output folder: <song folder>/timelines. Only overwritten while the field is
// empty or still holds the value we filled in, so a manual choice is never clobbered.
let autoOut = "";
function syncBuildOut() {
  const song = $("b-song").value.trim();
  const m = song.match(/^(.*)([\\/])[^\\/]*$/);
  if (!m) return;
  const out = $("b-out");
  if (out.value.trim() === "" || out.value === autoOut) {
    autoOut = `${m[1]}${m[2]}timelines`;
    out.value = autoOut;
  }
}
$("b-song").addEventListener("change", syncBuildOut);

$("btn-build").onclick = (e) => guarded(e.target, async () => {
  $("build-result").hidden = true;
  const job = await runJob("/api/jobs/build", {
    song: $("b-song").value.trim(),
    lyrics: $("b-lyrics").value.trim(),
    vibe: $("b-vibe").value || null,
    fps: parseFloat($("b-fps").value) || 30,
    name: $("b-name").value.trim(),
    count: parseInt($("b-count").value, 10) || 1,
    output_dir: $("b-out").value.trim() || null,
    same_anime: $("b-same").checked,
  }, $("build-job"));
  if (job.status !== "done") return;
  $("build-files").replaceChildren(...job.result.files.map((f) => {
    const name = f.replace(/^.*[\\/]/, "");
    return el("li", {}, el("code", { textContent: f }), " ", el("a", { href: `/api/download?path=${encodeURIComponent(f)}`, textContent: "download", download: name }));
  }));
  $("build-song").textContent = job.result.song;
  $("build-srt").textContent = job.result.lyrics;
  $("build-result").hidden = false;
});

// ---------------------------------------------------------------- upload
async function loadUploadInfo() {
  const [st, log] = await Promise.all([api("/api/upload/status"), api("/api/upload/log?last=30")]).catch((e) => (toast(e.message, true), []));
  if (!st) return;
  $("auth-status").replaceChildren(...["tiktok", "instagram"].map((p) => {
    const s = st[p];
    const text = !st.config_exists ? "no config file" : s?.authenticated ? `authenticated${s.expires_at ? " · expires " + s.expires_at.slice(0, 10) : ""}` : "not authenticated";
    return el("span", { className: `pill ${s?.authenticated ? "ok" : "bad"}`, textContent: `${p}: ${text}` });
  }));
  $("upload-log").querySelector("tbody").replaceChildren(...log.reverse().map((x) => el("tr", {},
    el("td", { textContent: (x.timestamp || "").slice(0, 19).replace("T", " ") }),
    el("td", { textContent: x.file }),
    el("td", { textContent: x.platform }),
    el("td", { className: x.status === "success" ? "ok-text" : "err-text", textContent: x.status }),
    el("td", { className: "muted", textContent: x.publish_id || `${x.error_code || ""} ${x.error_message || ""}`.trim() }),
  )));
}

document.querySelectorAll("[data-auth]").forEach((b) => (b.onclick = () => guarded(b, async () => {
  const job = await runJob("/api/jobs/setup-upload", { platform: b.dataset.auth }, $("auth-job"));
  if (job.status === "done") toast("Authentication saved.");
  loadUploadInfo();
})));

$("btn-upload").onclick = (e) => guarded(e.target, async () => {
  const platforms = ["tiktok", "instagram"].filter((p) => $(`u-${p}`).checked);
  if (!platforms.length) throw new Error("Select at least one platform.");
  const dry = $("u-dry").checked;
  if (!dry && !confirm("Upload these videos for real?")) return;
  await runJob("/api/jobs/upload", {
    folder: $("u-folder").value.trim(),
    caption: $("u-caption").value,
    platforms,
    delay: parseInt($("u-delay").value, 10) || 0,
    privacy: $("u-privacy").value,
    skip_normalize: $("u-skipnorm").checked,
    dry_run: dry,
  }, $("upload-job"));
  loadUploadInfo();
});

// ---------------------------------------------------------------- boot
showTab(["dashboard", "library", "lyrics", "build", "upload"].includes(location.hash.slice(1)) ? location.hash.slice(1) : "dashboard");
