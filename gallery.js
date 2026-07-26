const DATA_URL = "data/photos.json";
const THUMB_DIR = "web/images/thumb/";
const LARGE_DIR = "web/images/large/";

const grid = document.getElementById("grid");
const filters = document.getElementById("filters");
const lightbox = document.getElementById("lightbox");
const lightboxImg = document.getElementById("lightbox-img");
const lightboxCaption = document.getElementById("lightbox-caption");

let photos = [];

// extract.py records the ORIGINAL filename (.tif, .png...) but resize.py
// writes everything as .jpg, so swap the extension when building URLs.
function asJpg(file) {
  return file.replace(/\.[^.]+$/, ".jpg");
}

function caption(photo) {
  const bits = [photo.collection];
  const exif = photo.exif || {};
  if (exif.Model) bits.push(exif.Model);
  if (exif.DateTimeOriginal) bits.push(exif.DateTimeOriginal.slice(0, 10).replace(/:/g, "-"));
  bits.push(`${photo.width}×${photo.height}`);
  return bits.join(" · ");
}

function render(list) {
  grid.innerHTML = "";
  for (const photo of list) {
    const figure = document.createElement("figure");
    const img = document.createElement("img");
    img.src = THUMB_DIR + asJpg(photo.file);
    img.alt = photo.file;
    img.loading = "lazy";
    img.addEventListener("load", () => img.classList.add("loaded"));
    figure.append(img);
    figure.addEventListener("click", () => openLightbox(photo));
    grid.append(figure);
  }
}

function openLightbox(photo) {
  lightboxImg.src = LARGE_DIR + asJpg(photo.file);
  lightboxImg.alt = photo.file;
  lightboxCaption.textContent = caption(photo);
  lightbox.hidden = false;
}

function closeLightbox() {
  lightbox.hidden = true;
  lightboxImg.src = "";
}

lightbox.addEventListener("click", closeLightbox);
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeLightbox();
});

function buildFilters() {
  const names = ["all", ...new Set(photos.map((p) => p.collection))].sort();
  for (const name of names) {
    const button = document.createElement("button");
    button.textContent = name;
    if (name === "all") button.classList.add("active");
    button.addEventListener("click", () => {
      filters.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
      button.classList.add("active");
      render(name === "all" ? photos : photos.filter((p) => p.collection === name));
    });
    filters.append(button);
  }
}

async function init() {
  try {
    const response = await fetch(DATA_URL);
    photos = await response.json();
  } catch (err) {
    grid.textContent = "Could not load photos.json — are you running a local server?";
    return;
  }
  buildFilters();
  render(photos);
}

init();