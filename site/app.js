"use strict";

const $ = (id) => document.getElementById(id);

const form = $("assessment-form");
const analyseButton = $("analyse-button");
const analyseLabel = $("analyse-label");
const runtimeStatus = $("runtime-status");
const resultStatus = $("result-status");
const emptyState = $("empty-state");
const resultsContent = $("results-content");
const errorBox = $("error-box");

let pyodide = null;
let runtimeReady = false;

const defaults = {
  age: 52, weight: 70, gcs: 15, bun: 28, cr: 1.6, hct: 46, wbc: 16.5,
  temp: 38.4, hr: 104, rr: 24, pao2_fio2: 320, sbp: 115, ph: 7.36,
  of_hours: 0, necrosis: 0, balthazar: "", local_complication: ""
};

const example = {
  age: 68, weight: 76, gcs: 14, bun: 38, cr: 3.4, hct: 48, wbc: 21,
  temp: 38.9, hr: 120, rr: 28, pao2_fio2: 160, sbp: 82, ph: 7.28,
  of_hours: 56, necrosis: 35, balthazar: "D", local_complication: "acute necrotic collection"
};

function setTheme(theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem("ap-theme", theme);
  $("theme-toggle").setAttribute("aria-label", theme === "dark" ? "Switch to light theme" : "Switch to dark theme");
}

function initTheme() {
  const stored = localStorage.getItem("ap-theme");
  setTheme(stored || "light");
}

function setFields(values) {
  Object.entries(values).forEach(([key, value]) => {
    const element = $(key);
    if (element) element.value = String(value);
  });
}

function resetForm() {
  form.reset();
  setFields(defaults);
  $("pleural_effusion").checked = false;
  $("systemic_complication").checked = false;
  $("fluid_responsive").checked = false;
  $("advanced-details").open = false;
  resultsContent.hidden = true;
  emptyState.hidden = false;
  errorBox.hidden = true;
  resultStatus.textContent = "Awaiting input";
}

function loadExample() {
  setFields(example);
  $("pleural_effusion").checked = true;
  $("systemic_complication").checked = false;
  $("fluid_responsive").checked = false;
  $("advanced-details").open = true;
}

function numberValue(id) {
  const element = $(id);
  const value = Number(element.value);
  if (!Number.isFinite(value)) throw new Error(`${element.closest("label")?.firstChild?.textContent?.trim() || id} must be a number.`);
  return value;
}

function payloadFromForm() {
  if (!form.reportValidity()) throw new Error("Check the highlighted input values.");
  return {
    patient_id: "WEB",
    age: numberValue("age"),
    weight: numberValue("weight"),
    gcs: numberValue("gcs"),
    bun: numberValue("bun"),
    cr: numberValue("cr"),
    hct: numberValue("hct"),
    wbc: numberValue("wbc"),
    temp: numberValue("temp"),
    hr: numberValue("hr"),
    rr: numberValue("rr"),
    pao2_fio2: numberValue("pao2_fio2"),
    sbp: numberValue("sbp"),
    ph: numberValue("ph"),
    pleural_effusion: $("pleural_effusion").checked,
    systemic_complication: $("systemic_complication").checked,
    fluid_responsive_hypotension: $("fluid_responsive").checked,
    of_hours: numberValue("of_hours"),
    balthazar: $("balthazar").value || null,
    necrosis: numberValue("necrosis"),
    local_complications: $("local_complication").value.trim() ? [$("local_complication").value.trim()] : []
  };
}

function setText(id, value) {
  $(id).textContent = value;
}

function renderActions(items) {
  const list = $("action-list");
  list.replaceChildren();
  const safeItems = items.length ? items : ["No additional flags from the entered data."];
  safeItems.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    list.appendChild(li);
  });
}

function renderResult(data) {
  const atlanta = data.atlanta_classification;
  const marshall = data.modified_marshall;
  setText("atlanta-category", atlanta.category);
  setText("organ-failure-status", `Organ failure: ${atlanta.organ_failure_status}`);
  setText("bisap-score", `${data.bisap.total_score}/5`);
  setText("bisap-tier", data.bisap.severity_tier);
  setText("marshall-score", `${marshall.max_organ_score}/4`);
  setText("marshall-detail", marshall.has_organ_failure ? "Organ failure present" : "No organ failure by score");
  setText("sirs-score", `${data.sirs_criteria_count}/4`);
  setText("sirs-detail", data.sirs_present ? "SIRS present" : "SIRS not present");
  setText("fluid-rate", `${Number(data.fluid_guidelines.initial_rate_ml_hr).toFixed(1)} mL/h`);
  setText("fluid-bolus", data.fluid_guidelines.bolus_indicated ? "Bolus flag present" : "No bolus flag");
  setText("care-level", atlanta.recommended_level_of_care);
  setText("nutrition-guideline", data.nutrition_guideline);
  setText("antibiotic-guideline", data.antibiotic_guideline);
  renderActions(data.action_items || []);

  const ctsiCard = $("ctsi-card");
  if (data.ctsi) {
    ctsiCard.hidden = false;
    setText("ctsi-score", `${data.ctsi.total_ctsi}/10`);
    setText("ctsi-detail", `Balthazar ${data.ctsi.balthazar_grade}; necrosis ${data.ctsi.necrosis_pct}%`);
  } else {
    ctsiCard.hidden = true;
  }

  emptyState.hidden = true;
  errorBox.hidden = true;
  resultsContent.hidden = false;
  resultStatus.textContent = "Calculated";
}

function showError(error) {
  const message = error instanceof Error ? error.message : String(error);
  errorBox.textContent = message.replace(/^Error:\s*/, "");
  errorBox.hidden = false;
  resultStatus.textContent = "Input error";
}

async function initialiseRuntime() {
  try {
    runtimeStatus.textContent = "Loading Python runtime…";
    pyodide = await loadPyodide({ indexURL: "https://cdn.jsdelivr.net/pyodide/v0.29.5/full/" });
    const response = await fetch("pancreatitis_severity.py", { cache: "no-store" });
    if (!response.ok) throw new Error(`Unable to load calculator module (${response.status}).`);
    const source = await response.text();
    pyodide.FS.writeFile("/home/pyodide/pancreatitis_severity.py", source);
    await pyodide.runPythonAsync("import pancreatitis_severity");
    runtimeReady = true;
    analyseButton.disabled = false;
    analyseLabel.textContent = "Analyse";
    runtimeStatus.textContent = "Calculator ready · runs locally";
  } catch (error) {
    runtimeStatus.textContent = "Calculator failed to load";
    analyseLabel.textContent = "Unavailable";
    showError(error);
  }
}

async function analyse(event) {
  event.preventDefault();
  if (!runtimeReady || !pyodide) return;

  errorBox.hidden = true;
  analyseButton.disabled = true;
  analyseLabel.textContent = "Analysing…";
  resultStatus.textContent = "Calculating";

  try {
    const payload = payloadFromForm();
    pyodide.globals.set("payload_json", JSON.stringify(payload));
    const resultJson = await pyodide.runPythonAsync(`
import json
from dataclasses import asdict
from pancreatitis_severity import PancreatitisLabs, AcutePancreatitisBundleEngine

p = json.loads(payload_json)
labs = PancreatitisLabs(
    bun_mg_dl=p["bun"],
    creatinine_mg_dl=p["cr"],
    hematocrit_pct=p["hct"],
    wbc_k_ul=p["wbc"],
    temp_c=p["temp"],
    heart_rate_bpm=int(p["hr"]),
    resp_rate_bpm=int(p["rr"]),
    pao2_fio2_ratio=p["pao2_fio2"],
    systolic_bp_mmhg=p["sbp"],
    arterial_ph=p["ph"],
    age=int(p["age"]),
    fluid_responsive_hypotension=p["fluid_responsive_hypotension"],
)
result = AcutePancreatitisBundleEngine().evaluate_patient(
    patient_id=p["patient_id"],
    labs=labs,
    gcs_score=int(p["gcs"]),
    pleural_effusion=p["pleural_effusion"],
    organ_failure_duration_hours=p["of_hours"],
    local_complications=p["local_complications"],
    systemic_complications=p["systemic_complication"],
    ct_balthazar_grade=p["balthazar"],
    ct_necrosis_pct=p["necrosis"],
    weight_kg=p["weight"],
)
json.dumps(asdict(result))
`);
    renderResult(JSON.parse(resultJson));
  } catch (error) {
    showError(error);
  } finally {
    analyseButton.disabled = false;
    analyseLabel.textContent = "Analyse";
  }
}

$("theme-toggle").addEventListener("click", () => {
  setTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
});
$("example-button").addEventListener("click", loadExample);
$("reset-button").addEventListener("click", resetForm);
form.addEventListener("submit", analyse);

initTheme();
resetForm();
initialiseRuntime();
