// Trait Venn — renders the page state computed by /api/state.
// All probabilities, odds, percentages, ordering and label placement come
// from the server; this file only draws them and handles interaction.
"use strict";

const SVG_NS = "http://www.w3.org/2000/svg";
const DEFAULT_SELECTION = ["female", "left", "green"];
const DEFAULT_OPEN = "Senses & mind";

const ui = {
  selection: [],
  country: "US",
  open: DEFAULT_OPEN,
  data: null,
  hover: 0,
};

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
const slotColor = (slot) => `var(--c${slot})`;
const dots = (slots) => slots.map((s) => `<span class="dot" style="background:${slotColor(s)}"></span>`).join("");

// ---------------------------------------------------------------------------
// Population clock (mirrors population.Clock and calc.expected_count)
// ---------------------------------------------------------------------------
const popNow = (clock) => Math.floor(clock.base + clock.perSecond * (Date.now() / 1000 - clock.at));
function countLabel(population, p) {
  const expected = population * p;
  if (expected >= 1) {
    const n = Math.floor(expected);
    return `≈ ${n.toLocaleString("en-US")} ${n === 1 ? "person" : "people"}`;
  }
  return `statistically nobody (expected ${Number(expected.toPrecision(2))})`;
}
const worldPop = () => popNow(ui.data.population.world);
const nationPop = () => popNow(ui.data.population.nation);

// ---------------------------------------------------------------------------
// Data loading
// ---------------------------------------------------------------------------
async function load(toggle) {
  const params = new URLSearchParams({ sel: ui.selection.join(","), country: ui.country });
  if (toggle) params.set("toggle", toggle);
  const response = await fetch(`/api/state?${params}`);
  const body = await response.json();
  if (!response.ok) {
    $("hero").textContent = `Error: ${body.error}`;
    return;
  }
  ui.data = body;
  ui.selection = body.selection;
  ui.country = body.country;
  ui.hover = 0;
  const url = new URL(location.href);
  url.searchParams.set("sel", ui.selection.join(","));
  url.searchParams.set("country", ui.country);
  history.replaceState(null, "", url);
  render();
}

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------
function render() {
  const d = ui.data;
  const any = d.selection.length > 0;
  // Re-rendering replaces the chips; remember which control had focus.
  const focused = document.activeElement;
  const refocus = focused && (focused.dataset.trait ? `[data-trait="${focused.dataset.trait}"]`
    : focused.dataset.category ? `[data-category="${focused.dataset.category}"]` : null);

  const who = [d.headline.is && `is <strong>${esc(d.headline.is)}</strong>`,
               d.headline.has && `has <strong>${esc(d.headline.has)}</strong>`].filter(Boolean).join(", and ");
  $("hero").innerHTML = any
    ? `Someone who ${who} is <span class="odds">${esc(d.headline.odds)}</span> worldwide.`
    : "Pick traits on either side to see how rare that person is.";

  $("world-count").innerHTML = any ? `<span class="big" id="world-live"></span><span class="muted">on Earth</span>` : "";
  $("nation-count").textContent = "";
  $("nation-odds").textContent = any ? `· ${d.nation.odds}` : "";
  renderNations();
  $("selected-count").textContent = `${d.selection.length}/${d.max} traits`;
  $("clear").hidden = !any;
  $("conventional-note").textContent = `One per row · % shown for ${d.countryName}`;

  $("conventional").innerHTML = d.categories.filter((c) => c.side === "conventional").map(groupHtml).join("");
  $("unconventional").innerHTML = d.categories.filter((c) => c.side === "unconventional").map(accordionHtml).join("");

  renderDiagram();
  renderInspector();
  renderSources();
  tick();
  if (refocus) document.querySelector(refocus)?.focus();
}

function renderNations() {
  const d = ui.data;
  const option = (c) => `<option value="${esc(c.code)}"${c.code === d.country ? " selected" : ""}>${esc(c.name)}</option>`;
  const [first, ...rest] = d.countries;
  $("nation").innerHTML = `${option(first)}<option disabled>──────────</option>${rest.map(option).join("")}`;
}

function chipHtml(t) {
  const on = t.slot !== null;
  const style = on ? ` style="background:${slotColor(t.slot)}"` : "";
  const pct = t.pct ? `<small>${esc(t.pct)}</small>` : "";
  return `<button type="button" class="chip" data-trait="${esc(t.id)}" aria-pressed="${on}" title="${esc(t.name)}"${style}${t.enabled ? "" : " disabled"}>${esc(t.short)}${pct}</button>`;
}

const groupHtml = (c) => `<div class="grp"><h3 class="label">${esc(c.name)}</h3><div class="chips">${c.traits.map(chipHtml).join("")}</div></div>`;

function accordionHtml(c, i) {
  const open = ui.open === c.name;
  const badge = c.selectedCount ? `<span class="badge">${c.selectedCount}</span>` : "";
  return `<div class="grp">
    <h3 class="label"><button type="button" class="acc" data-category="${esc(c.name)}" aria-expanded="${open}" aria-controls="acc-${i}">
      <span>${esc(c.name)}${badge}</span><span class="caret" aria-hidden="true">▸</span></button></h3>
    <div class="chips" id="acc-${i}"${open ? "" : " hidden"}>${c.traits.map(chipHtml).join("")}</div></div>`;
}

function renderSources() {
  const d = ui.data;
  const pops = d.country === "US"
    ? `US & world population: ${d.population.source}`
    : `${d.countryName} population: ${d.population.source} · world: ${d.population.worldSource}`;
  $("sources").textContent =
    `Hover the diagram, or focus it and use ← → to explore regions · diagram & chips use ${d.countryName} shares, headline is worldwide · ${pops}`;
}

// ---------------------------------------------------------------------------
// Diagram
// ---------------------------------------------------------------------------
function ellipseAttrs(e) {
  return `cx="${e.cx}" cy="${e.cy}" rx="${e.rx}" ry="${e.ry}" transform="rotate(${e.rotation} ${e.cx} ${e.cy})"`;
}

function contains(e, x, y) {
  const a = -e.rotation * Math.PI / 180, dx = x - e.cx, dy = y - e.cy;
  const u = dx * Math.cos(a) - dy * Math.sin(a), v = dx * Math.sin(a) + dy * Math.cos(a);
  return (u / e.rx) ** 2 + (v / e.ry) ** 2 <= 1;
}

function renderDiagram() {
  const d = ui.data, g = d.diagram, host = $("venn");
  if (!g) {
    host.innerHTML = `<div class="empty">Pick at least one trait.</div>`;
    return;
  }
  const text = (x, y, s, attrs = "") => `<text x="${x}" y="${y}" text-anchor="middle" ${attrs}>${esc(s)}</text>`;
  let labels = "";
  for (const l of g.labels) {
    labels += text(l.x, l.y - 4, l.name, `font-size="15" font-weight="700" style="fill:${slotColor(l.slot)}"`);
    if (l.pct) labels += text(l.x, l.y + 14, l.pct, `font-size="13"`);
  }
  const b = g.badge;
  if (b) {
    labels += `<circle cx="${b.x}" cy="${b.y}" r="${b.r}" fill="var(--card)" stroke="var(--fg)" stroke-width="1.5"/>`;
    labels += text(b.x, b.y - b.r * 0.34, `ALL ${b.sets}`, `font-size="9" font-weight="700" letter-spacing=".1em" style="fill:var(--muted)"`);
    if (b.bottom) {
      labels += text(b.x, b.y + 1, b.top, `font-size="12"`);
      const size = Math.min(18, (2 * b.r - 12) / (b.bottom.length * 0.58));
      labels += text(b.x, b.y + b.r * 0.4, b.bottom, `font-size="${size.toFixed(1)}" font-weight="800"`);
    } else {
      labels += text(b.x, b.y + 8, b.top, `font-size="11" font-weight="700"`);
    }
  }
  const center = d.regions.find((r) => r.isCenter);
  host.innerHTML = `<svg viewBox="0 0 ${g.size} ${g.size}" role="img" tabindex="0"
      aria-label="Venn diagram of ${esc(d.selection.length)} traits; everyone in the center is ${esc(center.nation.odds)} in ${esc(d.countryName)}">
    <defs>${g.ellipses.map((e, i) => `<clipPath id="clip${i}"><ellipse ${ellipseAttrs(e)}/></clipPath>`).join("")}<mask id="hl-mask"></mask></defs>
    ${g.ellipses.map((e, i) => `<ellipse ${ellipseAttrs(e)} style="fill:${slotColor(i)};stroke:${slotColor(i)}" fill-opacity=".16" stroke-width="2.5"/>`).join("")}
    <g id="hl"></g>${labels}</svg>`;

  const svg = host.querySelector("svg");
  svg.addEventListener("mousemove", (ev) => {
    const pt = svg.createSVGPoint();
    pt.x = ev.clientX; pt.y = ev.clientY;
    const q = pt.matrixTransform(svg.getScreenCTM().inverse());
    let mask = 0;
    g.ellipses.forEach((e, i) => { if (contains(e, q.x, q.y)) mask |= 1 << i; });
    setHover(mask);
  });
  svg.addEventListener("mouseleave", () => setHover(0));
  svg.addEventListener("blur", () => setHover(0));
  svg.addEventListener("keydown", (ev) => {
    const order = [...d.regions].sort((a, b) => b.slots.length - a.slots.length || a.mask - b.mask).map((r) => r.mask);
    const i = order.indexOf(ui.hover);
    if (ev.key === "ArrowRight" || ev.key === "ArrowDown") setHover(order[(i + 1) % order.length]);
    else if (ev.key === "ArrowLeft" || ev.key === "ArrowUp") setHover(order[(i - 1 + order.length) % order.length]);
    else if (ev.key === "Escape") setHover(0);
    else return;
    ev.preventDefault();
  });
}

function setHover(mask) {
  if (mask === ui.hover) return;
  ui.hover = mask;
  const g = ui.data.diagram, hl = $("hl"), mk = $("hl-mask");
  if (!mask) {
    hl.innerHTML = "";
  } else {
    mk.innerHTML = `<rect width="${g.size}" height="${g.size}" fill="#fff"/>` +
      g.ellipses.map((e, i) => (mask >> i & 1) ? "" : `<ellipse ${ellipseAttrs(e)} fill="#000"/>`).join("");
    let inner = `<rect width="${g.size}" height="${g.size}" fill="var(--fg)" fill-opacity=".28" mask="url(#hl-mask)"/>`;
    g.ellipses.forEach((_, i) => { if (mask >> i & 1) inner = `<g clip-path="url(#clip${i})">${inner}</g>`; });
    hl.innerHTML = inner;
  }
  renderInspector();
}

// ---------------------------------------------------------------------------
// Inspector (lower right): hovered region, or the center by default
// ---------------------------------------------------------------------------
function renderInspector() {
  const d = ui.data, box = $("inspector");
  if (!d.selection.length) {
    box.innerHTML = `<span class="muted">Pick a trait to begin.</span>`;
    return;
  }
  const r = d.regions.find((x) => x.mask === ui.hover) || d.regions.find((x) => x.isCenter);
  const n = d.selection.length;
  const lead = !r.isCenter ? "Hovered region" : n > 1 ? `Center — all ${n} traits` : "Your trait";
  const detail = [r.nation.pct && `${r.nation.pct} have ${r.slots.length > 1 ? "all of these" : "this"}`,
                  !r.isCenter && `${r.nation.onlyOdds} have <i>only</i> these`].filter(Boolean).join(" · ");
  box.innerHTML = `<div class="muted">${lead}</div>
    <div>${dots(r.slots)}<b>${r.names.map(esc).join(" + ")}</b></div>
    <div class="odds">${esc(r.nation.odds)}</div>
    <div>${detail} <span class="muted">in ${esc(d.countryName)}</span></div>
    <div class="counts"><span>${esc(d.countryName)}: ${countLabel(nationPop(), r.nation.p)}</span>
      <span>World: ${countLabel(worldPop(), r.world.p)} · ${esc(r.world.odds)}</span></div>`;
}

function tick() {
  const d = ui.data;
  if (!d || !d.selection.length) return;
  const world = $("world-live");
  if (world) world.textContent = countLabel(worldPop(), d.world.p);
  $("nation-count").textContent = countLabel(nationPop(), d.nation.p);
  renderInspector();
}

// ---------------------------------------------------------------------------
// Events
// ---------------------------------------------------------------------------
document.addEventListener("click", (ev) => {
  const chip = ev.target.closest("[data-trait]");
  if (chip && !chip.disabled) { load(chip.dataset.trait); return; }
  const acc = ev.target.closest("[data-category]");
  if (acc) {
    ui.open = ui.open === acc.dataset.category ? null : acc.dataset.category;
    render();
  }
});
$("clear").addEventListener("click", () => { ui.selection = []; load(); });
$("nation").addEventListener("change", (ev) => { ui.country = ev.target.value; load(); });
setInterval(tick, 1000);

const params = new URLSearchParams(location.search);
ui.selection = params.has("sel") ? params.get("sel").split(",").filter(Boolean) : DEFAULT_SELECTION;
ui.country = params.get("country") || "US";
load();
