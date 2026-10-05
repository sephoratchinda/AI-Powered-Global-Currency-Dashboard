const $ = id => document.getElementById(id);
const api = async p => { const r = await fetch("/api" + p); const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.detail || r.status); return j; };
const fmt = v => v >= 100 ? v.toFixed(2) : v >= 1 ? v.toFixed(4) : v.toFixed(5);
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
let CUR = [], days = 30, charts = {};
const sel = (id, val, list = CUR) => $(id).innerHTML = list.map(c => `<option ${c === val ? "selected" : ""}>${c}</option>`).join("");
const setStatus = (t, ok) => { $("st").textContent = t; $("st").style.color = ok ? "var(--up)" : "var(--dn)"; };
function toast(m) { const t = $("toast"); t.textContent = "🔔 " + m; t.style.display = "block"; setTimeout(() => t.style.display = "none", 6000); }
function draw(id, cfg) { if (charts[id]) charts[id].destroy(); charts[id] = new Chart($(id), cfg); }
const opts = { responsive: true, maintainAspectRatio: false, interaction: { mode: "index", intersect: false }, plugins: { legend: { labels: { color: css("--tx") } } }, scales: { x: { ticks: { color: css("--mu"), maxTicksLimit: 8 } }, y: { ticks: { color: css("--mu") } } } };

async function cards() {
  const b = $("base").value, d = await api("/latest?base=" + b);
  $("cards").innerHTML = d.rates.map(r => `<div class="rc" data-c="${r.quote}"><b>${b}/${r.quote}</b><div>${fmt(r.rate)}</div><span class="${r.change_pct >= 0 ? "up" : "dn"}">${r.change_pct >= 0 ? "▲" : "▼"} ${Math.abs(r.change_pct).toFixed(2)}%</span></div>`).join("");
  document.querySelectorAll(".rc").forEach(e => e.onclick = () => { $("from").value = b; $("to").value = e.dataset.c; pair(); });
  setStatus("● Live · data as of " + d.rates[0].date, true);
}

async function pair() {
  const a = $("from").value, b = $("to").value;
  if (a === b) { $("ct").textContent = "Pick two different currencies"; return; }
  $("ct").textContent = `${a}/${b} · ${days}D`; $("glp").textContent = `(${a}/${b}, ${days}D)`;
  const h = await api(`/history?base=${a}&quote=${b}&days=${days}`);
  $("vol").textContent = h.volatility.toFixed(1) + "%"; $("vl").textContent = h.volatility_label + " volatility · period change " + h.period_change_pct.toFixed(2) + "%";
  draw("gl", { type: "bar", data: { labels: h.dates.slice(1), datasets: [{ data: h.daily_change_pct, backgroundColor: h.daily_change_pct.map(x => x >= 0 ? css("--up") : css("--dn")) }] }, options: { ...opts, plugins: { legend: { display: false } } } });
  let f = null;
  try { f = await api(`/forecast?base=${a}&quote=${b}&horizon=7`); } catch (e) { $("fm").textContent = "Forecast unavailable: " + e.message; }
  const labels = h.dates.concat(f ? f.dates : []), n = h.dates.length, pad = k => Array(k).fill(null);
  const ds = [{ label: "History", data: h.values, borderColor: css("--ac"), pointRadius: 0, tension: .2 }];
  if (f) {
    ds.push({ label: "AI forecast (" + f.model + ")", data: pad(n - 1).concat([h.values[n - 1]], f.forecast), borderColor: css("--up"), borderDash: [6, 4], pointRadius: 2 });
    ds.push({ label: "95% band", data: pad(n).concat(f.upper), borderColor: "transparent", backgroundColor: "rgba(37,99,235,.12)", fill: "+1", pointRadius: 0 });
    ds.push({ label: "lower", data: pad(n).concat(f.lower), borderColor: "transparent", pointRadius: 0 });
    const last = f.forecast[f.forecast.length - 1], d = (last / f.last_value - 1) * 100;
    $("fc").textContent = fmt(last); $("fd").innerHTML = `<span class="${d >= 0 ? "up" : "dn"}">${d >= 0 ? "▲ Bullish" : "▼ Bearish"} ${Math.abs(d).toFixed(2)}%</span> vs latest`;
    $("mt").innerHTML = "<tr><th>Model</th><th>MAE %</th><th>Direction acc.</th></tr>" + Object.entries(f.metrics).map(([k, m]) => `<tr><td>${k === f.model ? "★ " : ""}${k}</td><td>${m.mae_pct.toFixed(3)}</td><td>${m.direction_acc.toFixed(0)}%</td></tr>`).join("") + `<tr><td>Naive baseline</td><td>${f.naive_mae_pct.toFixed(3)}</td><td>–</td></tr>`;
    $("fm").textContent = `Trained on ${f.train_days} days of history; chronological 80/20 hold-out picks the best model. FX is close to a random walk, so treat forecasts as indicative, not advice.`;
  }
  draw("chart", { type: "line", data: { labels, datasets: ds }, options: { ...opts, plugins: { legend: { labels: { color: css("--tx"), filter: i => i.text !== "lower" } } } } });
  conv();
}

async function conv() {
  try { const r = await api(`/convert?amount=${$("amt").value || 0}&from=${$("cf").value}&to=${$("ctt").value}`);
    $("cout").textContent = r.result.toLocaleString(undefined, { maximumFractionDigits: 4 }) + " " + r.to; $("crate").textContent = `1 ${r.from} = ${fmt(r.rate)} ${r.to} · ECB reference rate, ${r.date}`; } catch (e) { $("cout").textContent = "—"; }
}

async function heat() {
  const d = await api("/heatmap?days=30");
  let h = `<table><tr><th></th>${d.currencies.map(c => `<th>${c}</th>`).join("")}</tr>`;
  d.currencies.forEach(a => { h += `<tr><th>${a}</th>` + d.currencies.map(b => { const v = d.matrix[a][b]; if (v === null) return "<td>–</td>"; const al = Math.min(Math.abs(v) / 4, 1) * .75; return `<td style="background:${v >= 0 ? `rgba(15,157,88,${al})` : `rgba(217,48,37,${al})`}">${v.toFixed(1)}</td>`; }).join("") + "</tr>"; });
  $("hm").innerHTML = h + "</table>";
  $("rank").innerHTML = "Strongest → weakest: " + Object.entries(d.strength).map(([c, v]) => `<b>${c}</b> <span class="${v >= 0 ? "up" : "dn"}">${v.toFixed(1)}%</span>`).join(" · ");
}

async function alerts() {
  const l = await api("/alerts");
  $("al").innerHTML = l.map(a => `<li>${a.pair} ${a.direction} ${a.threshold} <button onclick="delA(${a.id})">✕</button></li>`).join("") || "<li><small>No alerts set</small></li>";
  const c = await api("/alerts/check");
  c.threshold_alerts.forEach(toast);
  $("auto").innerHTML = c.significant_moves.slice(0, 5).map(x => `<li>⚠ ${x}</li>`).join("") || "<li><small>None today</small></li>";
}
window.delA = async id => { await fetch("/api/alerts/" + id, { method: "DELETE" }); alerts(); };

async function news() {
  const s = await api("/sentiment");
  $("src").textContent = s.live ? "(live Google News RSS)" : "(offline — sample headlines)";
  $("sent").innerHTML = `Overall: <span class="${s.overall === "Positive" ? "up" : s.overall === "Negative" ? "dn" : ""}">${s.overall}</span>`;
  $("news").innerHTML = s.items.map(i => `<li>${i.headline} <small class="${i.score > 0 ? "up" : i.score < 0 ? "dn" : ""}">${i.score > 0 ? "Positive" : i.score < 0 ? "Negative" : "Neutral"}</small></li>`).join("");
}

async function boot() {
  for (let i = 0; i < 30; i++) while(true){ try { CUR = await api("/currencies"); await api("/latest?base=USD"); break; } catch (e) { setStatus("Downloading first rates… " + e.message, false); await new Promise(r => setTimeout(r, 2000)); } }
  ["base", "from", "cf"].forEach((id, i) => sel(id, ["USD", "USD", "USD"][i])); sel("to", "INR"); sel("ctt", "INR");
  $("ap").innerHTML = CUR.flatMap(a => CUR.filter(b => a !== b).map(b => `<option>${a}/${b}</option>`)).join(""); $("ap").value = "USD/INR";
  $("tf").innerHTML = [["7D", 7], ["30D", 30], ["90D", 90], ["1Y", 365]].map(([l, d]) => `<button data-d="${d}" class="${d === 30 ? "on" : ""}">${l}</button>`).join(" ");
  document.querySelectorAll("#tf button").forEach(b => b.onclick = () => { days = +b.dataset.d; document.querySelectorAll("#tf button").forEach(x => x.classList.toggle("on", x === b)); pair(); });
  $("base").onchange = cards; $("from").onchange = $("to").onchange = pair;
  ["amt", "cf", "ctt"].forEach(i => $(i).oninput = conv);
  $("sw").onclick = () => { const t = $("cf").value; $("cf").value = $("ctt").value; $("ctt").value = t; conv(); };
  $("aa").onclick = async () => { const v = parseFloat($("av").value); if (!v) return;
    const r = await fetch("/api/alerts", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ pair: $("ap").value, direction: $("ad").value, threshold: v }) });
    if (!r.ok) toast("Could not add alert"); alerts(); };
  try { await Promise.all([cards(), pair(), heat(), alerts(), news()]); } catch (e) { setStatus("Error: " + e.message, false); }
  setInterval(() => { cards().catch(() => {}); alerts().catch(() => {}); }, 60000);
}
boot();
