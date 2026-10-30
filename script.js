const DATA = (typeof BIO !== "undefined") ? BIO : require("./data.js");
const ORDER = ["LC", "NT", "VU", "EN", "CR", "EX"];
const LABEL = {LC: "Least Concern", NT: "Near Threatened", VU: "Vulnerable", EN: "Endangered", CR: "Critically Endangered", EX: "Extinct"};
const COLOR = {LC: "#4c9f50", NT: "#a6c34a", VU: "#f2c230", EN: "#f28c28", CR: "#d64545", EX: "#4a4a4a"};
const TIER = {LC: "Low", NT: "Low", VU: "Medium", EN: "High", CR: "High", EX: "High"};
const GEN_REASONS = ["Habitat loss and degradation (agriculture, logging, urban growth)", "Hunting, poaching and illegal wildlife trade", "Overfishing and fishing bycatch", "Invasive species and disease", "Pollution and chemical contamination", "Climate change and extreme weather", "Small, fragmented populations with low genetic diversity"];
const GEN_MEASURES = ["Protect and restore critical habitat and create wildlife corridors", "Enforce anti-poaching and wildlife-trade laws", "Use wildlife-safe fishing gear and set catch limits", "Control invasive species and manage disease", "Reduce pollution and pesticide use", "Cut emissions and protect climate-resilient habitat", "Monitor populations; use captive breeding and reintroduction where numbers are very small", "Work with local communities through incentives and human-wildlife conflict programmes"];

function predict(group, status) {
  const known = Object.prototype.hasOwnProperty.call(DATA.model, group);
  const table = (known ? DATA.model[group] : DATA.model.__unseen__)[status];
  if (!table) throw new Error("Invalid status: " + status);
  const rows = Object.entries(table).sort((a, b) => b[1] - a[1]);
  const r0 = ORDER.indexOf(status);
  const sum = f => rows.filter(([c]) => f(ORDER.indexOf(c))).reduce((a, [, v]) => a + v, 0);
  return {top: rows[0][0], conf: rows[0][1], rows, known,
          worse: sum(i => i > r0), better: sum(i => i < r0), same: sum(i => i === r0)};
}

if (typeof document !== "undefined") {
  const $ = id => document.getElementById(id);
  const esc = s => String(s).replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
  const pc = x => (x * 100).toFixed(1) + "%";
  const badge = s => `<span class="badge" style="background:${COLOR[s]}">${s}</span> ${LABEL[s]}`;
  const post = (url, data) => fetch(url, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(data || {})});

  fetch("/api/me").then(r => r.ok ? r.json() : (location.href = "/login")).then(u => { if (u) $("who").textContent = u.name; });
  $("logout").onclick = async () => { await post("/api/logout"); location.href = "/login"; };

  if (DATA.demo) $("demo").innerHTML = "⚠️ <b>Demo data:</b> predictions are illustrative only and are not real findings.";
  $("names").innerHTML = DATA.species.map(s => `<option value="${esc(s[1] || s[0])}">${esc(s[0])}</option>`).join("");
  $("status").innerHTML = ORDER.map(s => `<option value="${s}">${s} – ${LABEL[s]}</option>`).join("");
  $("group").innerHTML = DATA.groups.map(g => `<option>${esc(g)}</option>`).join("") + '<option value="__unseen__">Other / not in training data</option>';

  $("form").addEventListener("submit", e => {
    e.preventDefault();
    const q = $("name").value.trim().toLowerCase();
    const sp = DATA.species.find(s => s[0].toLowerCase() === q || (s[1] || "").toLowerCase() === q);
    let status, group, title, plain, extra;
    if (sp) {
      [status, group, plain] = [sp[3], sp[2], sp[1] ? `${sp[1]} (${sp[0]})` : sp[0]];
      title = sp[1] ? `${esc(sp[1])} (<i>${esc(sp[0])}</i>)` : `<i>${esc(sp[0])}</i>`;
      extra = `<p class="meta">Current status: ${badge(status)} · Group: ${esc(group)}${sp[4] ? ` · Recorded next status: <b>${sp[4]}</b>` : ""}</p>`;
    } else {
      if (!$("manual").open) {
        $("manual").open = true;
        $("result").innerHTML = `<p class="err">“${esc($("name").value)}” is not in the species list. Choose its current status and taxonomic group above, then press Predict again.</p>`;
        return;
      }
      [status, group, plain] = [$("status").value, $("group").value, $("name").value.trim()];
      title = esc(plain);
      extra = `<p class="meta">Using your inputs: ${badge(status)} · Group: ${esc(group === "__unseen__" ? "Other" : group)}</p>`;
    }
    if (status === "EX") {
      $("result").innerHTML = `<h2>${title}</h2>${extra}<p>This species is already <b>Extinct</b>; no further prediction applies.</p>`;
      return;
    }
    const r = predict(group, status);
    const bars = r.rows.map(([c, v]) => `<div class="bar"><span>${c}</span><div class="track"><div class="fill" style="width:${v * 100}%;background:${COLOR[c]}"></div></div><span>${pc(v)}</span></div>`).join("");
    let risk = "", report = `Species: ${plain}\nCurrent status: ${status} (${LABEL[status]})\nPredicted next status: ${r.top} (${LABEL[r.top]})\nConfidence: ${pc(r.conf)}\n`;
    if (["EN", "CR"].includes(status) || ["EN", "CR"].includes(r.top)) {
      const own = sp && sp[5] && sp[5].length;
      const reasons = own ? sp[5] : GEN_REASONS, measures = sp && sp[6] && sp[6].length ? sp[6] : GEN_MEASURES;
      const li = a => a.map(t => `<li>${esc(t)}</li>`).join("");
      risk = `<div class="reasons"><h3>Reasons for extinction risk${own ? "" : " (general)"}</h3><ul>${li(reasons)}</ul></div>` +
             `<div class="measures"><h3>Measures to conserve it${sp && sp[6] && sp[6].length ? "" : " (general)"}</h3><ul>${li(measures)}</ul></div>`;
      report += `\nReasons for extinction risk:\n- ${reasons.join("\n- ")}\n\nConservation measures:\n- ${measures.join("\n- ")}\n`;
    }
    $("result").innerHTML = `<h2>${title}</h2>${extra}
      <p>Predicted next IUCN status:</p><p>${badge(r.top)}</p>
      <p>Confidence ${pc(r.conf)} · Risk tier: <b>${TIER[r.top]}</b> · Worsen ${pc(r.worse)} / Improve ${pc(r.better)} / Same ${pc(r.same)}</p>
      ${bars}${risk}${r.known ? "" : '<p class="note">⚠️ Group not in training data; prediction relies mainly on current status.</p>'}
      <p class="note">Probabilities assume the status changes at the next assessment. Reasons and measures are informational and do not affect the prediction.</p>
      <button type="button" id="mailbtn" class="ghost mailbtn">Email me this report</button> <span id="mailmsg" class="note"></span>`;
    $("mailbtn").onclick = async () => {
      const b = $("mailbtn"); b.disabled = true;
      const res = await post("/api/email-report", {text: report});
      if (res.status === 401) { location.href = "/login"; return; }
      const j = await res.json().catch(() => ({}));
      $("mailmsg").textContent = res.ok ? (j.dev ? "Email service not configured: report printed in the server console." : "Report sent to your email.") : (j.error || "Could not send the email.");
      b.disabled = false;
    };
  });
}
if (typeof module !== "undefined") module.exports = {predict};
