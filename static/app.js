// NEW: browser behavior for searching part numbers and importing the Excel layout.
const searchForm = document.querySelector("#search-form");
const searchInput = document.querySelector("#part-number");
const searchStatus = document.querySelector("#search-status");
const result = document.querySelector("#result");
const uploadForm = document.querySelector("#upload-form");
const uploadStatus = document.querySelector("#upload-status");

function setStatus(element, message, type = "") {
  element.textContent = message;
  element.className = `status ${type}`;
}

function showResult(data) {
  document.querySelector("#result-part-number").textContent = data.part_number;
  document.querySelector("#result-rack").textContent = data.rack;
  document.querySelector("#result-column").textContent = data.columna;
  document.querySelector("#result-level").textContent = data.nivel;
  document.querySelector("#result-position").textContent = data.posicion;
  document.querySelector("#result-location-id").textContent = data.id_ubicacion;
  result.classList.remove("hidden");
}

searchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const partNumber = searchInput.value.trim();
  result.classList.add("hidden");
  if (!partNumber) {
    setStatus(searchStatus, "Enter a part number to search.", "error");
    return;
  }
  setStatus(searchStatus, "Searching...");
  try {
    const response = await fetch(`/inventario/${encodeURIComponent(partNumber)}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Part number was not found.");
    showResult(data);
    setStatus(searchStatus, "Location found.", "success");
  } catch (error) {
    setStatus(searchStatus, error.message, "error");
  }
});

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const fileInput = document.querySelector("#layout-file");
  const file = fileInput.files[0];
  if (!file) {
    setStatus(uploadStatus, "Select an Excel file first.", "error");
    return;
  }
  const formData = new FormData();
  formData.append("archivo", file);
  setStatus(uploadStatus, "Uploading and replacing inventory...");
  try {
    const response = await fetch("/importar-layout", { method: "POST", body: formData });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "The layout could not be imported.");
    setStatus(uploadStatus, data.mensaje, "success");
    uploadForm.reset();
  } catch (error) {
    setStatus(uploadStatus, error.message, "error");
  }
});
