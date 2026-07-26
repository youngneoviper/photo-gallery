const DATA_URL = "data/photos.json";
const THUMB_DIR = "web/images/thumb/";

const stage = document.getElementById("stage");
const modesNav = document.getElementById("modes");
const filtersNav = document.getElementById("filters");
const readout = document.getElementById("readout");

let photos = [];
let collection = "all";
let mode = "spectrum";

const asJpg = (file) => file.replace(/\.[^.]+$/, ".jpg");

// Below this saturation, hue is essentially noise — a near-grey pixel's
// "hue" is whatever rounding error happened to win.
const GREY_LIMIT = 0.12;

function visible() {
  return collection === "all"
    ? photos
    : photos.filter((p) => p.collection === collection);
}

/* ---------- mode 1: spectrum — pure colour, no photographs ---------- */

function drawSpectrum(list) {
  const chromatic = list
    .filter((p) => p.color.saturation >= GREY_LIMIT)
    .sort((a, b) => a.color.hue - b.color.hue);
  const greys = list
    .filter((p) => p.color.saturation < GREY_LIMIT)
    .sort((a, b) => a.color.value - b.color.value);

  stage.className = "spectrum";
  stage.innerHTML = "";

  for (const photo of [...chromatic, ...greys]) {
    const band = document.createElement("div");
    band.className = "band";
    band.style.background = photo.color.hex;
    // Saturated colours get more room; near-greys stay thin.
    band.style.flexGrow = String(0.4 + photo.color.saturation * 2);
    band.title = `${photo.file} · ${photo.color.hex}`;
    band.addEventListener("mouseenter", () => describe(photo));
    stage.append(band);
  }

  readout.textContent =
    `${chromatic.length} chromatic, ${greys.length} near-grey — hover a band`;
}

/* ---------- mode 2: scatter — hue across, brightness up ---------- */

function drawScatter(list) {
  stage.className = "scatter";
  stage.innerHTML = "";

  for (const photo of list) {
    const dot = document.createElement("img");
    dot.src = THUMB_DIR + asJpg(photo.file);
    dot.loading = "lazy";
    dot.className = "dot";
    // Greys have no meaningful hue, so park them in a lane on the left.
    const grey = photo.color.saturation < GREY_LIMIT;
    dot.style.left = grey ? "1%" : `${2 + (photo.color.hue / 360) * 96}%`;
    dot.style.bottom = `${2 + photo.brightness * 92}%`;
    dot.style.outlineColor = photo.color.hex;
    dot.title = `${photo.file} · ${photo.color.hex}`;
    dot.addEventListener("mouseenter", () => describe(photo));
    stage.append(dot);
  }

  readout.textContent = "hue left→right, brightness bottom→top";
}

/* ---------- mode 3: mosaic — colour blocks in a grid ---------- */

function paletteGradient(entries) {
  // Palette is truncated to 8, so shares don't sum to 1 — renormalise.
  const total = entries.reduce((sum, e) => sum + e.share, 0);
  let pos = 0;
  const stops = [];
  for (const entry of entries) {
    const width = (entry.share / total) * 100;
    // Two stops at the same colour = hard edge instead of a blend.
    stops.push(`${entry.hex} ${pos.toFixed(2)}%`);
    pos += width;
    stops.push(`${entry.hex} ${pos.toFixed(2)}%`);
  }
  return `linear-gradient(to bottom, ${stops.join(", ")})`;
}

function sortKey(photo) {
  if (photo.monochrome) return [2, photo.brightness];
  if (!photo.accent) return [1, photo.brightness];
  return [0, photo.accent.hue];
}

function drawMosaic(list) {
  const sorted = [...list].sort((a, b) => {
    const [ga, va] = sortKey(a);
    const [gb, vb] = sortKey(b);
    return ga - gb || va - vb;
  });

  stage.className = "mosaic";
  stage.innerHTML = "";

  for (const photo of sorted) {
    const cell = document.createElement("div");
    cell.className = "cell";
    cell.style.backgroundImage = paletteGradient(photo.palette);
    cell.title = photo.file;
    cell.addEventListener("mouseenter", () => describe(photo));
    stage.append(cell);
  }

  readout.textContent = `${sorted.length} photographs as palettes`;
}

/* ---------- plumbing ---------- */

const MODES = {
  spectrum: drawSpectrum,
  scatter: drawScatter,
  mosaic: drawMosaic,
};

function describe(photo) {
  const a = photo.accent;
  readout.textContent = photo.monochrome
    ? `${photo.file} — monochrome · brightness ${photo.brightness}`
    : `${photo.file} — accent ${a.hex} · hue ${a.hue}° · sat ${a.saturation}`;
}

function draw() {
  MODES[mode](visible());
}

function buildNav(nav, names, current, onPick) {
  nav.innerHTML = "";
  for (const name of names) {
    const button = document.createElement("button");
    button.textContent = name;
    if (name === current()) button.classList.add("active");
    button.addEventListener("click", () => {
      onPick(name);
      nav.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
      button.classList.add("active");
      draw();
    });
    nav.append(button);
  }
}

async function init() {
  try {
    photos = await (await fetch(DATA_URL)).json();
  } catch {
    stage.textContent = "Could not load photos.json — running a local server?";
    return;
  }

  buildNav(modesNav, Object.keys(MODES), () => mode, (name) => (mode = name));
  buildNav(
    filtersNav,
    ["all", ...new Set(photos.map((p) => p.collection))].sort(),
    () => collection,
    (name) => (collection = name)
  );
  draw();
}

init();