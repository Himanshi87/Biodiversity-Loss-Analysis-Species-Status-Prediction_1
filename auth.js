const $ = id => document.getElementById(id);
function say(t) { const m = $("msg"); m.textContent = t || ""; m.className = "msg" + (t ? " bad" : ""); }
async function api(url, data) {
  try {
    const r = await fetch(url, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(data)});
    const j = await r.json().catch(() => ({}));
    return Object.assign({}, j, {ok: r.ok});
  } catch (e) { return {ok: false, error: "Cannot reach the server."}; }
}
if ($("f-login")) $("f-login").onsubmit = async e => {
  e.preventDefault(); say("");
  const r = await api("/api/login", {email: $("l-email").value.trim(), password: $("l-pass").value});
  if (r.ok) location.href = "/"; else say(r.error);
};
if ($("f-reg")) $("f-reg").onsubmit = async e => {
  e.preventDefault(); say("");
  const r = await api("/api/register", {name: $("r-name").value, email: $("r-email").value.trim(), password: $("r-pass").value});
  if (r.ok) location.href = "/"; else say(r.error);
};
