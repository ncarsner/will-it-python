// Trait Venn — renders the page state computed by /api/state.
// All probabilities, odds, percentages, ordering, label placement, and text
// (headline, sources, summary) come from the server; this file only draws
// them and handles interaction.
"use strict";

const DEFAULT_OPEN = "Senses & mind";

const ui = {
  selection: null, // null: let the server apply its default selection

  country: "US",
  open: DEFAULT_OPEN,
  textView: false,
  data: null,
  hover: 0,
};

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
const slotColor = (slot) => `var(--c${slot})`;
// Concrete colors for the SVG. Reader views copy the SVG without the page's
// stylesheet, so CSS variables there would resolve to black.
function palette() {
  const css = getComputedStyle(document.documentElement);
  const get = (name) => css.getPropertyValue(name).trim();
  return { bg: get("--bg"), fg: get("--fg"), muted: get("--muted"), card: get("--card"),
           slots: [0, 1, 2, 3, 4].map((i) => get(`--c${i}`)) };
}
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
// `push`: record the change as a new history entry. Browser reader views
// re-read the page on navigation but not on replaceState, so user changes
// are pushed (which also makes Back undo a selection); the initial load and
// Back/Forward restores replace.
async function load(toggle, { push = false } = {}) {
  const params = new URLSearchParams({ country: ui.country });
  if (ui.selection !== null) params.set("sel", ui.selection.join(","));
  if (toggle) params.set("toggle", toggle);
  const response = await fetch(`/api/state?${params}`);
  const body = await response.json();
  if (!response.ok) {
    if (!ui.data && (ui.selection !== null || ui.country !== "US")) {
      // A stale or hand-edited link (e.g. a renamed trait id): start fresh.
      ui.selection = null;
      ui.country = "US";
      return load(undefined, { push });
    }
    $("hero").textContent = `Error: ${body.error}`;
    return;
  }
  ui.data = body;
  ui.selection = body.selection;
  ui.country = body.country;
  ui.hover = 0;
  updateUrl(push);
  render();
}

function updateUrl(push) {
  const url = new URL(location.href);
  url.searchParams.set("sel", ui.selection.join(","));
  url.searchParams.set("country", ui.country);
  if (ui.textView) url.searchParams.set("view", "text"); else url.searchParams.delete("view");
  if (url.href === location.href) return;
  if (push) history.pushState(null, "", url); else history.replaceState(null, "", url);
}

// Read selection, nation, and view from the URL (initial load, Back/Forward).
function readUrl() {
  const params = new URLSearchParams(location.search);
  ui.selection = params.has("sel") ? params.get("sel").split(",").filter(Boolean) : null;
  ui.country = params.get("country") || "US";
  ui.textView = params.get("view") === "text";
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

  $("hero").innerHTML = d.headline.html;

  // Real spaces between spans: reader views and copy/paste drop the CSS margins.
  $("world-count").innerHTML = any ? `<span class="big" id="world-live"></span> <span class="muted">on Earth</span>` : "";
  $("nation-count").textContent = "";
  $("nation-odds").textContent = any ? ` · ${d.nation.odds}` : "";
  $("nation-name").textContent = d.countryName;
  renderNations();
  $("selected-count").textContent = `${d.selection.length}/${d.max} traits`;
  $("clear").hidden = !any;
  $("text-view").setAttribute("aria-pressed", String(ui.textView));
  $("text-view").textContent = ui.textView ? "Diagram view" : "Text view";
  document.querySelector(".page").classList.toggle("text-view", ui.textView);
  $("conventional-note").dataset.text = `One per row · % shown for ${d.countryName}`;

  $("conventional").innerHTML = d.categories.filter((c) => c.side === "conventional").map(groupHtml).join("");
  $("unconventional").innerHTML = d.categories.filter((c) => c.side === "unconventional").map(accordionHtml).join("");

  renderDiagram();
  renderInspector();
  $("sources").textContent = d.sourcesText;
  $("summary-body").innerHTML = d.summaryHtml;
  document.title = d.title;
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
  const pal = palette();
  const text = (x, y, s, attrs = "", fill = pal.fg) =>
    `<text x="${x}" y="${y}" text-anchor="middle" fill="${fill}" ${attrs}>${esc(s)}</text>`;
  let labels = "";
  for (const l of g.labels) {
    labels += text(l.x, l.y - 4, l.name, `font-size="15" font-weight="700"`, pal.slots[l.slot]);
    if (l.pct) labels += text(l.x, l.y + 14, l.pct, `font-size="13"`);
  }
  const b = g.badge;
  if (b) {
    labels += `<circle cx="${b.x}" cy="${b.y}" r="${b.r}" fill="${pal.card}" stroke="${pal.fg}" stroke-width="1.5"/>`;
    labels += text(b.x, b.y - b.r * 0.34, `ALL ${b.sets}`, `font-size="9" font-weight="700" letter-spacing=".1em"`, pal.muted);
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
    <rect width="${g.size}" height="${g.size}" fill="${pal.bg}"/>
    ${g.ellipses.map((e, i) => `<ellipse ${ellipseAttrs(e)} fill="${pal.slots[i]}" stroke="${pal.slots[i]}" fill-opacity=".16" stroke-width="2.5"/>`).join("")}
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
    let inner = `<rect width="${g.size}" height="${g.size}" fill="${palette().fg}" fill-opacity=".28" mask="url(#hl-mask)"/>`;
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
  if (chip && !chip.disabled) { load(chip.dataset.trait, { push: true }); return; }
  const acc = ev.target.closest("[data-category]");
  if (acc) {
    ui.open = ui.open === acc.dataset.category ? null : acc.dataset.category;
    render();
  }
});
$("clear").addEventListener("click", () => { ui.selection = []; load(undefined, { push: true }); });
// In-app text view: the same summary shown in place of the diagram. Unlike a
// browser reader view (a one-time snapshot), it updates with every change.
$("text-view").addEventListener("click", () => {
  ui.textView = !ui.textView;
  updateUrl(true);
  render();
});
// Re-draw the SVG with the new concrete colors when the OS theme changes.
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => { if (ui.data) renderDiagram(); });
// Nation picker: plain text until opened, so reader views never copy a select.
function setPicker(open, { refocus = true } = {}) {
  $("nation-picker").hidden = !open;
  $("nation-name").hidden = open;
  $("nation-edit").hidden = open;
  $("nation-edit").setAttribute("aria-expanded", String(open));
  if (open) $("nation").focus();
  else if (refocus) $("nation-edit").focus();
}
$("nation-edit").addEventListener("click", () => setPicker(true));
$("nation-name").addEventListener("click", () => setPicker(true));
$("nation").addEventListener("change", (ev) => {
  ui.country = ev.target.value;
  setPicker(false);
  load(undefined, { push: true });
});
$("nation").addEventListener("keydown", (ev) => { if (ev.key === "Escape") setPicker(false); });
// Leaving the picker (Tab, click elsewhere) closes it without pulling focus back.
$("nation").addEventListener("blur", () => { if (!$("nation-picker").hidden) setPicker(false, { refocus: false }); });
addEventListener("popstate", () => { readUrl(); load(); });
setInterval(tick, 1000);

readUrl();
load();
