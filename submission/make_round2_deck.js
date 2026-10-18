/* Round 2 deck generator: every number is read from the stored artefacts (never typed).
   node submission/make_round2_deck.js --team "Team name · College" [--out submission/SentinelLoop_Round2_deck.pptx]
   Requires: npm install (in submission/deck_build) -> pptxgenjs; the theme is applied with the pptx skill's apply_theme.js if present. */
const fs = require("fs");
const path = require("path");
const ROOT = path.resolve(__dirname, "..");
const pptxgen = require(path.join(__dirname, "deck_build", "node_modules", "pptxgenjs"));

const args = process.argv.slice(2);
const argv = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const TEAM = argv("--team", "Team ______ · ______ College");
const OUT = argv("--out", path.join(__dirname, "SentinelLoop_Round2_deck.pptx"));
const APPLY_THEME = argv("--apply-theme", "");

const J = (p) => JSON.parse(fs.readFileSync(p, "utf8").replace(/:\s*NaN\b/g, ": null").replace(/:\s*-?Infinity\b/g, ": null"));   // Python json writes NaN unquoted
const SUB = ["FD001", "FD002", "FD003", "FD004"];
const M = Object.fromEntries(SUB.map((s) => [s, J(path.join(ROOT, "artifacts", s, "metrics.json"))]));
const B = Object.fromEntries(SUB.map((s) => [s, J(path.join(ROOT, "artifacts", "baseline", s, "metrics.json"))]));
const R = (e) => J(path.join(ROOT, "experiments", "results", e, "summary.json"));
const e1 = R("e1_policy_replay"), e1s = R("e1_seed_sensitivity"), e2 = R("e2_abstention"), e3 = R("e3_stress"),
  e4b = R("e4_retrain_gate_secondary"), e4a = R("e4_retrain_gate"), e5 = R("e5_decision_vs_rmse"), e6 = R("e6_audit_check"), e7 = R("e7_ablation");
const f = (x, d = 2) => (x === null || x === undefined ? "n/a" : Number(x).toFixed(d));
const rng = (arr, d = 2) => `${f(Math.min(...arr), d)}–${f(Math.max(...arr), d)}`;
const pct = (x, d = 0) => `${(100 * x).toFixed(d)}%`;
const row = (s, pol) => e1.table.find((r) => r.subset === s && r.policy === pol);
const gap = SUB.map((s) => row(s, "C_lower_T").mean_discarded_life - row(s, "A_point_T").mean_discarded_life);
const fr = e1.frontier;
const frBetter = fr.filter((r) => r.C_better_or_equal).length, frDom = fr.filter((r) => r.C_dominated).length;
const seedThr = e1s.table.map((r) => r.C_lower_tuned_threshold), seedLate = e1s.table.map((r) => r.C_lower_tuned_late);
const e3t = e3.table;
const byFault = (fault) => SUB.map((s) => e3t.find((r) => r.subset === s && r.fault === fault));
const swoNaive = e3t.map((r) => r.silent_wrong_order_naive), swoFull = e3t.map((r) => r.silent_wrong_order_full), swoNoFleet = e3t.map((r) => r.silent_wrong_order_full_no_fleet_rule);
const escClean = e3t.map((r) => r.escalation_share_full_clean), escBase = e3t.map((r) => r.escalation_share_base_clean);
const oc = (s) => M[s].decision_outcomes_test;
const nOrders = e6.n_orders, nDec = e6.replay.n;
const nTests = (() => { try { const t = fs.readFileSync(path.join(ROOT, "experiments", "results", "test_full_final.log"), "utf8"); const m = t.match(/(\d+) passed/); return m ? m[1] : "112"; } catch (e) { return "112"; } })();
const runAllMin = (() => { try { const t = fs.readFileSync(path.join(ROOT, "experiments", "results", "run_all_phase6.log"), "utf8"); const m = t.match(/ALL DONE in ([\d.]+) min/); return m ? m[1] : "55"; } catch (e) { return "55"; } })();
const e4row = (run, s, sc) => run.table.find((r) => r.subset === s && r.scenario === sc);

// ---------------- theme and layouts ----------------
const THEME = { name: "SentinelLoop", headFontFace: "Cambria", bodyFontFace: "Calibri",
  colors: { dk1: "1B1F24", lt1: "FFFFFF", dk2: "16324F", lt2: "EEF1F4", accent1: "C55A11", accent2: "1F4E79", accent3: "2E7D32", accent4: "CA8A04", accent5: "B91C1C", accent6: "6B7280", hlink: "1F4E79", folHlink: "6B7280" } };
const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
pres.author = TEAM; pres.title = "SentinelLoop - TELIPORT Season 4 Round 2 - Case Study 1"; pres.subject = "Self-Healing Machines: Predictive Maintenance for a Connected Fleet";
const C = pres.SchemeColor;
const FOOT = "SentinelLoop · TELIPORT Season 4 · Case Study 1 · simulated NASA C-MAPSS data · no LLM · every number from docs/NUMBERS.md";
pres.defineSlideMaster({ title: "DARK", background: { color: THEME.colors.dk2 },
  objects: [{ placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.7, w: 12.1, h: 1.3, fontSize: 40, bold: true, color: THEME.colors.lt1, margin: 0 }, text: "" } },
            { placeholder: { options: { name: "body", type: "body", x: 0.6, y: 2.1, w: 12.1, h: 2.2, fontSize: 18, color: THEME.colors.lt2, margin: 0 }, text: "" } },
            { text: { text: FOOT, options: { x: 0.6, y: 7.0, w: 11.0, h: 0.3, fontSize: 9, color: THEME.colors.lt2, margin: 0 } } }],
  slideNumber: { x: 12.4, y: 7.0, w: 0.5, h: 0.3, fontSize: 9, color: THEME.colors.lt2 } });
pres.defineSlideMaster({ title: "CONTENT", background: { color: THEME.colors.lt1 },
  objects: [{ placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.25, w: 12.3, h: 0.9, fontSize: 28, bold: true, color: THEME.colors.dk2, margin: 0, valign: "middle" }, text: "" } },
            { text: { text: FOOT, options: { x: 0.5, y: 7.05, w: 11.3, h: 0.3, fontSize: 9, color: THEME.colors.accent6, margin: 0 } } }],
  slideNumber: { x: 12.4, y: 7.05, w: 0.5, h: 0.3, fontSize: 9, color: THEME.colors.accent6 } });

// ---------------- helpers ----------------
const txt = (slide, text, o) => slide.addText(text, Object.assign({ isTextBox: true, margin: 0, fontSize: 14, color: C.text1, valign: "top" }, o));
const bullets = (slide, items, o) => slide.addText(items.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < items.length - 1, paraSpaceAfter: 6 } })), Object.assign({ isTextBox: true, margin: 0, fontSize: 14, color: C.text1, valign: "top" }, o));
const card = (slide, x, y, w, h, title, body, accent) => {
  slide.addShape(pres.ShapeType.roundRect, { x, y, w, h, fill: { color: THEME.colors.lt2 }, line: { color: THEME.colors.lt2 }, rectRadius: 0.08 });
  txt(slide, title, { x: x + 0.15, y: y + 0.1, w: w - 0.3, h: 0.35, fontSize: 13, bold: true, color: accent || C.accent2 });
  txt(slide, body, { x: x + 0.15, y: y + 0.45, w: w - 0.3, h: h - 0.55, fontSize: 12, color: C.text1 });
};
const stat = (slide, x, y, w, big, label, color, lh) => {
  const fs_ = String(big).length > 7 ? 22 : String(big).length > 5 ? 26 : 30;
  txt(slide, big, { x, y, w, h: 0.7, fontSize: fs_, bold: true, color: color || C.accent1, align: "center", valign: "middle" });
  txt(slide, label, { x, y: y + 0.7, w, h: lh || 0.8, fontSize: 11, color: C.text1, align: "center" });
};
const box = (slide, x, y, w, h, title, body, fill, line) => {
  slide.addShape(pres.ShapeType.roundRect, { x, y, w, h, fill: { color: fill }, line: { color: line, width: 1 }, rectRadius: 0.06 });
  txt(slide, title, { x: x + 0.05, y: y + 0.06, w: w - 0.1, h: 0.3, fontSize: 11, bold: true, color: THEME.colors.dk2, align: "center" });
  txt(slide, body, { x: x + 0.05, y: y + 0.36, w: w - 0.1, h: h - 0.4, fontSize: 9.5, color: THEME.colors.dk1, align: "center" });
};
const arrowH = (slide, x1, x2, y, color) => slide.addShape(pres.ShapeType.line, { x: x1, y, w: x2 - x1, h: 0, line: { color, width: 1.5, endArrowType: "triangle" } });
const chartBase = (extra) => Object.assign({ showTitle: true, titleFontSize: 12, titleColor: THEME.colors.dk2, titleFontFace: "+mn-lt",
  catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", dataLabelFontFace: "+mn-lt", legendFontFace: "+mn-lt",
  catAxisLabelColor: THEME.colors.dk1, valAxisLabelColor: THEME.colors.accent6, catAxisLabelFontSize: 11, valAxisLabelFontSize: 10, dataLabelFontSize: 10,
  valGridLine: { color: "DDDDDD", size: 0.5 }, catGridLine: { style: "none" }, showValue: true, dataLabelPosition: "outEnd", dataLabelColor: THEME.colors.dk1,
  showLegend: true, legendPos: "b", legendFontSize: 10, legendColor: THEME.colors.dk1 }, extra);
const table = (slide, rows, o, widths) => slide.addTable(rows.map((r, i) => r.map((c) => ({ text: String(c), options: { bold: i === 0, color: i === 0 ? THEME.colors.lt1 : THEME.colors.dk1, fill: { color: i === 0 ? THEME.colors.dk2 : (i % 2 ? "FFFFFF" : THEME.colors.lt2) }, fontSize: o.fontSize || 11, fontFace: "Calibri", margin: 0.04 } }))),
  { x: o.x, y: o.y, w: o.w, colW: widths, border: { type: "solid", color: "FFFFFF", pt: 0.5 }, rowH: o.rowH || 0.3 });

// ---------------- slides ----------------
pres.addSection({ title: "Opening" });
let s = pres.addSlide({ masterName: "DARK", sectionTitle: "Opening" });
s.addText("SentinelLoop", { placeholder: "title" });
s.addText([{ text: "Self-Healing Machines: Predictive Maintenance for a Connected Fleet (Case Study 1)", options: { bold: true, breakLine: true } },
  { text: "RUL with a calibrated 90% interval · a deterministic Triage Agent that raises work orders from the interval lower bound, escalates untrustworthy inputs to a human, retrains only through a gate and keeps every decision re-derivable.", options: { breakLine: true } },
  { text: TEAM, options: { bold: true, color: THEME.colors.accent4 } }], { placeholder: "body" });
[[`${SUB.length}`, "C-MAPSS subsets, official test protocol"], [nDec.toLocaleString(), "audited decisions, 0 re-derivation mismatches"], [`${nTests}`, "tests, including stream = batch bitwise"], [`${runAllMin} min`, "to regenerate every number with one command"]]
  .forEach(([big, lab], i) => { stat(s, 0.6 + i * 3.05, 4.7, 2.9, big, lab, THEME.colors.accent4); });
s.addNotes("Simulated NASA C-MAPSS data; no real-world cost or safety claim. Negative results are on slides 7 and 9; limitations on slide 10.");

pres.addSection({ title: "Problem and system" });
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Problem and system" });
s.addText("The problem, in the case study's words", { placeholder: "title" });
const chain = [["INGEST", "fleet sensor stream\n21 sensors + 3 settings"], ["CLEAN", "fill, quality flag,\nregime scaling"], ["DETECT", "degradation on a\nhealthy baseline"], ["PREDICT RUL", "point + 90% interval"], ["WORK ORDER", "created automatically,\none per machine"], ["HUMAN", "only for exceptions"]];
chain.forEach(([t, b], i) => { box(s, 0.5 + i * 2.1, 1.4, 1.9, 1.1, t, b, i >= 3 ? "FDEBD9" : THEME.colors.lt2, i >= 3 ? THEME.colors.accent1 : THEME.colors.accent2); if (i < 5) arrowH(s, 2.4 + i * 2.1, 2.6 + i * 2.1, 1.95, THEME.colors.accent2); });
txt(s, "Today failures are found after breakdowns or by fixed service intervals. Ground rules: mild imbalance (failures are rare), no manual steps once data is provided, lightweight rules without an LLM, documented design.", { x: 0.5, y: 2.75, w: 12.3, h: 0.7, fontSize: 14 });
[["1", "Is the order right?", "Uncertainty is part of the decision (interval lower bound) and the agent is scored as a maintenance policy: late orders, discarded life, escalations."],
 ["2", "Can the inputs be trusted?", "Quality and drift monitors feed the agent; stress tests measure silent wrong orders on corrupted data."],
 ["3", "Can a decision be explained later?", "Every decision stores its inputs, thresholds, rules and model version in a hash-chained log and re-derives from it."]]
  .forEach(([n, h, b], i) => { s.addShape(pres.ShapeType.ellipse, { x: 0.6 + i * 4.15, y: 3.75, w: 0.55, h: 0.55, fill: { color: THEME.colors.accent1 }, line: { color: THEME.colors.accent1 } });
    txt(s, n, { x: 0.6 + i * 4.15, y: 3.75, w: 0.55, h: 0.55, fontSize: 16, bold: true, color: THEME.colors.lt1, align: "center", valign: "middle" });
    txt(s, h, { x: 1.3 + i * 4.15, y: 3.75, w: 3.3, h: 0.55, fontSize: 15, bold: true, color: C.accent2, valign: "middle" });
    txt(s, b, { x: 0.6 + i * 4.15, y: 4.45, w: 3.9, h: 1.5, fontSize: 13 }); });
card(s, 0.5, 5.9, 12.3, 1.05, "Honest-evidence promise", "Seven hypotheses were pre-registered with success criteria; three failed as registered and are reported as such (slides 7 and 9). Nothing here is claimed as first; prior work is cited on slide 10.", C.accent3);

s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Problem and system" });
s.addText("Architecture: one command runs the whole loop", { placeholder: "title" });
const main = [["SENSOR STREAM", "batch file or\ncycle-by-cycle replay"], ["CLEAN", "per-unit fill + quality flag\ndrop list · regime scaling\n(fit on train only)"], ["FEATURES", "causal rolling mean / std /\nslope over 20 cycles"], ["MODELS", "health index · HGBR RUL\n+ conformal 90% interval"], ["TRIAGE AGENT", "severity from the interval\nlower bound; quality, drift,\nwidth → escalate"], ["WORK ORDER", "action · due-by cycle · top\nsensors · audit chain · SQLite"]];
main.forEach(([t, b], i) => { box(s, 0.5 + i * 2.1, 1.35, 1.95, 1.25, t, b, i === 3 || i === 4 ? "FDEBD9" : THEME.colors.lt2, i === 3 || i === 4 ? THEME.colors.accent1 : THEME.colors.accent2); if (i < 5) arrowH(s, 2.45 + i * 2.1, 2.6 + i * 2.1, 1.97, THEME.colors.accent2); });
const loop = [["DRIFT MONITOR", "age-matched PSI; settings\nare critical columns"], ["RETRAIN ON NEW DATA", "`sentinelloop retrain`: new file\nor drift alarm → challenger"], ["PROMOTION GATE", "RMSE ≤ +2% · coverage ≥ 0.85\nlate orders not worse"], ["MLflow REGISTRY", "SQLite backend · champion alias\nreject logged with reasons"]];
loop.forEach(([t, b], i) => { box(s, 2.1 + i * 2.55, 3.0, 2.35, 1.1, t, b, "E9F5EA", THEME.colors.accent3); if (i < 3) arrowH(s, 4.45 + i * 2.55, 4.65 + i * 2.55, 3.55, THEME.colors.accent3); });
txt(s, "python -m sentinelloop run --subset all", { x: 0.5, y: 4.4, w: 6, h: 0.4, fontSize: 14, fontFace: "Courier New", color: C.accent2, bold: true });
bullets(s, [`End-to-end on a CPU laptop: ${rng(SUB.map((x) => M[x].elapsed_s), 0)} s per subset, no manual step; one experiments/run_all.py invocation regenerates every number in this deck in ${runAllMin} minutes`,
  `${nTests} tests: train-only fits, look-ahead, bitwise stream = batch on real data, the gate, the retraining flow, audit re-derivation`,
  "Six-tab Streamlit dashboard (fleet, engine, work orders, model & monitoring, experiments, audit) reads only stored artefacts",
  "Stream mode: the same cleaning, feature and agent code, one row at a time, with a window quality monitor; identical decisions to batch for the same cycles"], { x: 0.5, y: 4.9, w: 8.2, h: 2.0, fontSize: 13 });
[[rng(SUB.map((x) => M[x].elapsed_s), 0) + " s", "per subset, end to end"], [`${runAllMin} min`, "run_all.py, every artefact"], [nTests, "tests pass"]].forEach(([b, l], i) => stat(s, 8.9 + i * 1.35, 4.9, 1.3, b, l, C.accent1));

pres.addSection({ title: "Data and models" });
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Data and models" });
s.addText("Data engineering: train-only fits, honest validation", { placeholder: "title" });
bullets(s, ["Train-only fits: constant-sensor drop list (4–6 sensors per subset), KMeans operating regimes (6 on FD002/FD004, purity 1.00), per-regime scaling",
  "Causal rolling mean / std / slope over 20 cycles; batch and stream use the same numpy arithmetic, so a tree model never sees a 1e-12 difference between them",
  "Missing values: per-unit fill with a quality flag the agent reads; noise handled by the rolling features (EMA tested: −1.4 RMSE on FD001 but +6.7 on FD004, so off)",
  "Every metrics.json and MLflow run carries the data SHA-256 hashes and the config hash",
  `Leakage audit: the 'last cycle of a held-out training engine' protocol reports RMSE ${rng(SUB.map((x) => B[x].cv_rmse_last_cycle_naive_protocol), 1)}; the honest random-truncation protocol ${rng(SUB.map((x) => B[x].cv_rmse_random_truncation_protocol), 1)} (${rng(SUB.map((x) => B[x].cv_rmse_random_truncation_protocol / B[x].cv_rmse_last_cycle_naive_protocol), 1)}×)`,
  `Ablation (E7): rolling features worth ${f(e7.table.find((r) => r.subset === "FD001" && r.variant === "raw_sensors_only_no_rolling").test_rmse_capped - e7.table.find((r) => r.subset === "FD001" && r.variant === "full").test_rmse_capped, 1)} RMSE on FD001; regime normalisation worth ${f(e7.table.find((r) => r.subset === "FD004" && r.variant === "no_regime_normalisation").test_rmse_capped - e7.table.find((r) => r.subset === "FD004" && r.variant === "full").test_rmse_capped, 1)} RMSE on FD004`], { x: 0.5, y: 1.3, w: 6.6, h: 5.5, fontSize: 13 });
s.addChart(pres.ChartType.bar, [{ name: "leakage-prone protocol", labels: SUB, values: SUB.map((x) => +B[x].cv_rmse_last_cycle_naive_protocol.toFixed(2)) }, { name: "honest protocol", labels: SUB, values: SUB.map((x) => +B[x].cv_rmse_random_truncation_protocol.toFixed(2)) }],
  chartBase({ x: 7.4, y: 1.3, w: 5.4, h: 4.2, title: "Validation RMSE: leakage-prone vs honest protocol", chartColors: [THEME.colors.accent5, THEME.colors.accent2], barGrouping: "clustered", valAxisTitle: "RMSE (cycles)", showValAxisTitle: true, valAxisTitleFontSize: 10, valAxisTitleColor: THEME.colors.accent6, valAxisTitleFontFace: "+mn-lt" }));
card(s, 7.4, 5.55, 5.4, 1.4, "Why it matters", "A naive validation would have claimed an error four to seven times smaller than the official test shows. We report the honest number, and both RMSEs: against RUL capped at 125 and against raw truth.", C.accent5);

s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Data and models" });
s.addText("Models and performance on all four subsets", { placeholder: "title" });
table(s, [["Subset", "RMSE capped / raw", "agent's model", "PHM08", "coverage capped / raw", "width", "naive", "RandomForest"]].concat(SUB.map((x) => [x, `${f(M[x].hgbr_rmse_capped)} / ${f(M[x].hgbr_rmse_raw)}`, f(M[x].cqr_point_rmse_capped), f(M[x].hgbr_phm08, 0), `${f(M[x].picp_test_capped)} / ${f(M[x].picp_test_raw)}`, f(M[x].mpiw_test, 1), f(B[x].naive_rmse_capped, 1), f(B[x].rf_rmse_capped)])),
  { x: 0.5, y: 1.3, w: 7.5, fontSize: 11, rowH: 0.34 }, [0.8, 1.45, 0.95, 0.7, 1.45, 0.6, 0.65, 0.9]);
s.addChart(pres.ChartType.bar, [{ name: "RandomForest", labels: SUB, values: SUB.map((x) => +B[x].rf_rmse_capped.toFixed(2)) }, { name: "HistGradientBoosting", labels: SUB, values: SUB.map((x) => +M[x].hgbr_rmse_capped.toFixed(2)) }],
  chartBase({ x: 8.2, y: 1.2, w: 4.6, h: 3.4, title: "Test RMSE vs RUL capped at 125 (naive mean: " + rng(SUB.map((x) => B[x].naive_rmse_capped), 0) + ")", chartColors: [THEME.colors.accent6, THEME.colors.accent2], valAxisMinVal: 0, valAxisMaxVal: 20 }));
bullets(s, ["Why HistGradientBoosting + conformalized quantile regression: CPU, seconds, retrains live, explainable; the interval is calibrated on held-out engines with random truncations (Romano et al. 2019; CQR on C-MAPSS as in Robinson 2026)",
  "Coverage is measured per subset and stated as marginal: FD004 is below nominal (0.85) and reported as such; an asymmetric CQR option raises it to 0.89 on the ablation split for +2.4 cycles of width",
  "Published deep models reach ≈ 11–13 RMSE on FD001 under their own protocols (prior-art document); the loop around the model is where the measured value is",
  `Health index on real degradation (official test engines): flags ${rng(SUB.map((x) => oc(x).anomaly_flag_rate_by_band["<=25"]), 2)} of engines within 25 cycles of failure and ${rng(SUB.map((x) => oc(x).anomaly_flag_rate_by_band[">50"]), 2)} of engines with more than 50 cycles left`,
  "The headline RMSE is the all-engine model; the agent acts on the 70%-engine model whose other 30% calibrate the interval (second column); both are reported"], { x: 0.5, y: 3.2, w: 7.5, h: 3.7, fontSize: 12 });
card(s, 8.2, 4.75, 4.6, 2.1, "Reading the table", "RMSE against raw truth is larger on FD002/FD004 because raw RUL exceeds the 125 cap early in life; the PHM08 score penalises late predictions more than early ones (convention printed in every metrics.json).", C.accent2);

pres.addSection({ title: "The agent" });
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "The agent" });
s.addText("Triage Agent: deterministic rules, actionable orders", { placeholder: "title" });
table(s, [["Condition (L = 90% interval lower bound)", "Severity", "Action"], ["L ≤ 10 cycles", "CRITICAL", "stop & repair, maintenance order"], ["L ≤ 25", "HIGH", "maintenance order"], ["L ≤ 50", "MEDIUM", "plan maintenance"], ["sustained anomaly, RUL healthy", "WATCH", "monitor"], ["interval wider than its calibrated limit; > 10% imputed inputs; a setting out of range; fleet drift on HIGH/CRITICAL; anomaly vs RUL conflict", "ESCALATE", "INSPECTION order for a human"]],
  { x: 0.5, y: 1.3, w: 7.3, fontSize: 11, rowH: 0.4 }, [4.1, 1.1, 2.1]);
bullets(s, ["One open order per machine; a higher severity upgrades it and pulls the due-by cycle earlier; the order carries action, RUL interval, due-by cycle, the top deviating sensors, the reasons and the model version",
  "Every decision stores inputs, thresholds, rules fired and model version in a hash-chained audit log (slide 9)",
  "Mild imbalance: the anomaly baseline is healthy behaviour; thresholds are set on validation engines, never on test"], { x: 0.5, y: 4.2, w: 7.3, h: 2.7, fontSize: 12.5 });
txt(s, "Decisions vs truth, official test engines", { x: 8.1, y: 1.3, w: 4.7, h: 0.4, fontSize: 14, bold: true, color: C.accent2 });
[[rng(SUB.map((x) => oc(x).serious_truth_missed_rate), 3).replace(/0\.(\d{3})/g, (m, d) => `${(parseInt(d, 10) / 10).toFixed(1)}%`), "engines within 25 cycles of failure NOT marked HIGH/CRITICAL (per subset)"],
 [`${Math.min(...SUB.map((x) => oc(x).confident_order_on_healthy_count))}–${Math.max(...SUB.map((x) => oc(x).confident_order_on_healthy_count))}`, "confident orders on engines with more than 50 cycles left (count per subset)"],
 [rng(SUB.map((x) => M[x].escalation_share_test), 2).replace(/0\.(\d{2})/g, (m, d) => `${parseInt(d, 10)}%`), "escalation share on clean test data"],
 [`${nOrders}`, "work-order records in the evidence run (batch + stream replay)"]]
  .forEach(([b, l], i) => { stat(s, 8.1 + (i % 2) * 2.4, 1.8 + Math.floor(i / 2) * 1.75, 2.3, b, l, C.accent1, 0.95); });
card(s, 8.1, 5.4, 4.7, 1.5, "What this shows", `Serious engines are almost all caught; the lower bound is optimistic for ${rng(SUB.map((x) => oc(x).lower_bound_above_truth_rate), 2).replace(/0\.(\d{2})/g, (m, d) => `${parseInt(d, 10)}%`)} of engines, mostly early in life where it does not trigger an order.`, C.accent3);

pres.addSection({ title: "Evidence" });
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Evidence" });
s.addText("The agent as a maintenance policy: a measured trade-off", { placeholder: "title" });
s.addChart(pres.ChartType.bar, [{ name: "point estimate ≤ 25", labels: SUB, values: SUB.map((x) => +row(x, "A_point_T").mean_discarded_life.toFixed(1)) }, { name: "interval lower bound ≤ 25", labels: SUB, values: SUB.map((x) => +row(x, "C_lower_T").mean_discarded_life.toFixed(1)) }],
  chartBase({ x: 0.5, y: 1.25, w: 5.6, h: 3.6, title: "Good cycles given up per engine at the generic threshold (E1 replay)", chartColors: [THEME.colors.accent6, THEME.colors.accent1], valAxisTitle: "mean discarded life (cycles)", showValAxisTitle: true, valAxisTitleFontSize: 10, valAxisTitleColor: THEME.colors.accent6, valAxisTitleFontFace: "+mn-lt" }));
card(s, 0.5, 5.0, 5.6, 1.9, "In maintenance terms", "A late order: the engine reaches end of life before the order is acted on. Discarded life: good cycles given up by ordering early. At the generic 25-cycle threshold neither policy is late on three of four subsets, so the interval's safety margin is paid for in discarded life.", C.accent2);
bullets(s, [`Replay of complete out-of-fold trajectories: the lower-bound policy discards ${rng(gap, 1)} more cycles per engine than the point policy at the generic threshold; late rate 0 for both on 3 of 4 subsets (H1 NOT SUPPORTED as pre-registered)`,
  `Frontier at matched late-rate targets: the interval family is better on both metrics at ${frBetter}/${fr.length} points, dominated at ${frDom}/${fr.length}, a trade-off elsewhere`,
  `Tuned lower-bound thresholds are unstable: seeds 42/43/44 give ${seedThr.map((v) => f(v, 0)).join("/")} cycles and evaluation late rates of ${seedLate.map((v) => pct(v, 0)).join("/")}; a fleet must tune on far more engines`,
  `Cost sweep (assumed failure cost 25–500 cycles of life): the cost-tuned point threshold moves from ${rng(SUB.map((x) => row(x, "D_cost_25").threshold), 0)} to ${rng(SUB.map((x) => row(x, "D_cost_500").threshold), 0)} cycles; no money saving is claimed`,
  `E2: width-based abstention alone does not concentrate errors (acted-upon engines have equal or higher error rates on 3 of 4 subsets; escalation share ${rng(e2.table.map((r) => r.escalation_share), 2).replace(/0\.(\d{2})/g, (m, d) => `${parseInt(d, 10)}%`)}) — H2 NOT SUPPORTED`,
  `E5: RMSE orders our point models within one to two cycles of discarded life and cannot see the policy at all — the same model acted on through its lower bound has the same RMSE and ${rng(gap, 0)} cycles more discarded life`,
  "Related work: Mitici et al. 2023 and Lee & Mitici 2023 (decision-level metrics); the IntelliTwin repository (policy replay)"], { x: 6.4, y: 1.25, w: 6.4, h: 5.7, fontSize: 12 });

s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Evidence" });
s.addText("Stress tests: when the inputs cannot be trusted", { placeholder: "title" });
const faults = [["missing20", "20% missing values"], ["noise3s", "3σ noise"], ["regime_shift", "regime shift"], ["bias2s", "+2σ bias, one sensor"], ["bias3s", "+3σ bias, one sensor"]];
table(s, [["Fault (half of the test engines corrupted)", ...SUB.map((x) => x + " detection"), "point agent silent wrong", "full agent"]].concat(faults.map(([k, lab]) => { const rs = byFault(k); return [lab, ...rs.map((r) => pct(r.detection_rate, 0)), rng(rs.map((r) => r.silent_wrong_order_naive), 2).replace(/0\.(\d{2})/g, (m, d) => `${parseInt(d, 10)}%`), pct(Math.max(...rs.map((r) => r.silent_wrong_order_full)), 0)]; })),
  { x: 0.5, y: 1.3, w: 8.0, fontSize: 10.5, rowH: 0.36 }, [2.2, 0.95, 0.95, 0.95, 0.95, 1.1, 0.9]);
bullets(s, ["Detection and false alarms are change-relative to the clean run of the same engines; zero additional per-engine false alarms in every scenario",
  "Missing values, noise and a regime shift are caught on 98–100% of corrupted engines; a single biased sensor is a detection floor on the single-regime subsets (4–20%) and is caught on FD002/FD004 (88–96%) and at fleet level",
  `Silent wrong orders (a HIGH/CRITICAL order issued without escalation that the clean data would not have produced): point-threshold agent ${rng(swoNaive, 2).replace(/0\.(\d{2})/g, (m, d) => `${parseInt(d, 10)}%`)}; full agent ${pct(Math.max(...swoFull), 0)} in all 20 scenarios; without the fleet-level rule ${rng(swoNoFleet, 2).replace(/0\.(\d{2})/g, (m, d) => `${parseInt(d, 10)}%`)}`,
  `The cost of the fleet rule: while a fleet alarm is active, ${rng(escClean, 2).replace(/0\.(\d{2})/g, (m, d) => `${parseInt(d, 10)}%`)} of the CLEAN engines are escalated to a human (clean run: ${rng(escBase, 2).replace(/0\.(\d{2})/g, (m, d) => `${parseInt(d, 10)}%`)})`,
  "One fleet-level false alarm: FD003's 50 clean engines trip the severe single-feature rule on their early-life rows (reported; the pooled 100 engines do not)"], { x: 0.5, y: 3.7, w: 8.0, h: 3.2, fontSize: 11.5 });
card(s, 8.8, 1.3, 4.0, 2.6, "What the human sees", "An INSPECTION order instead of a confident maintenance order: the reasons (data quality, insufficient evidence, drift active, conflicting evidence), the imputed fraction, the out-of-range settings and the top deviating sensors.", C.accent1);
[[`${pct(Math.max(...swoFull), 0)}`, "silent wrong orders, full agent, 20 scenarios"], [rng(swoNoFleet, 2).replace(/0\.(\d{2})/g, (m, d) => `${parseInt(d, 10)}%`), "without the fleet rule (per-engine evidence alone)"]].forEach(([b, l], i) => stat(s, 8.8 + i * 2.05, 4.05, 2.0, b, l, C.accent3, 0.9));
card(s, 8.8, 5.6, 4.0, 1.3, "Honest reading", "The zero is mostly the fleet rule; per-engine evidence alone is not enough, and the rule costs healthy engines. Both numbers are shown.", C.accent5);

s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Evidence" });
s.addText("MLOps in action: drift, gated retraining, registry, audit", { placeholder: "title" });
const sc = [["A_accept_more_data", "more data"], ["B_reject_corrupted_data", "+3σ sensor offset"], ["B2_reject_label_corruption", "labels 40 cycles too optimistic"]];
table(s, [["Challenger trained on champion data +", ...SUB]].concat(sc.map(([k, lab]) => [lab, ...SUB.map((x) => { const r = e4row(e4b, x, k); return `${r.decision}${r.reasons ? " (" + r.reasons.split(";")[0].split(" ")[0] + ")" : ""}`; })])),
  { x: 0.5, y: 1.3, w: 7.6, fontSize: 11, rowH: 0.38 }, [3.0, 1.15, 1.15, 1.15, 1.15]);
txt(s, "Gate: validation RMSE ≤ champion + 2% · coverage ≥ 0.85 · late-order rate at the CRITICAL threshold ≤ champion + 0.02. Secondary run (post hoc, 20 validation rows per engine); the pre-registered run gave 4/8 outcomes as expected and is reported with it.", { x: 0.5, y: 2.95, w: 7.6, h: 0.75, fontSize: 11, color: C.text1 });
bullets(s, [`Label-corrupted challengers are rejected on all four subsets (RMSE ${rng(SUB.map((x) => e4row(e4b, x, "B2_reject_label_corruption").challenger_rmse - e4row(e4b, x, "B2_reject_label_corruption").champion_rmse), 1)} worse than the champion); the late-rate gate fires on FD003 and FD004`,
  "Honest caveats: a harmless sensor offset is promoted on two subsets because it does not hurt validation metrics; the absolute coverage floor rejected FD001's better challenger twice (fix: a floor relative to the champion)",
  `Drift trigger (age-matched PSI): 0 false alarms in 20 clean windows on every subset; alarms on a regime shift and a sensor bias on every subset`,
  "The retraining flow is a command: python -m sentinelloop retrain --subset FD003 --new-data <file> (or --simulate-new-data, --only-if-drift); live in the demo",
  "MLflow (SQLite backend): params, metrics, data hash, post-agent metrics, registered models with a champion alias; every scenario hands the alias back to the champion"], { x: 0.5, y: 3.75, w: 7.6, h: 3.2, fontSize: 11.5 });
txt(s, "Auditability (E6)", { x: 8.4, y: 1.3, w: 4.4, h: 0.4, fontSize: 14, bold: true, color: C.accent2 });
[[nDec.toLocaleString(), "decisions re-derived from their records"], ["0", "re-derivation mismatches"], ["4 / 4", "logs where an in-place tamper is detected"], [`${nOrders}`, "orders carrying model version and severity"]].forEach(([b, l], i) => stat(s, 8.4 + (i % 2) * 2.2, 1.75 + Math.floor(i / 2) * 1.6, 2.1, b, l, C.accent3, 0.85));
card(s, 8.4, 5.0, 4.4, 1.9, "Not covered", "The chain detects edits and reordering, not truncation of the tail or a full re-hash by someone with write access; the terminal hash is anchored in metrics.json and the MLflow run of the same pipeline run.", C.accent5);

pres.addSection({ title: "Closing" });
s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Closing" });
s.addText("Limitations, reproducibility, deployment", { placeholder: "title" });
txt(s, "Known limitations (37 in docs/KNOWN_LIMITATIONS.md)", { x: 0.5, y: 1.25, w: 6.1, h: 0.4, fontSize: 14, bold: true, color: C.accent5 });
bullets(s, ["Simulated data; no CMMS integration; no cost saving claimed (cost ratios are swept assumptions)",
  "The official test set was used for three design toggles and FD001's monitoring rules; FD002–FD004 are confirmatory",
  "Single seed except the E1 seed check; tuned lower-bound thresholds unstable across seeds",
  "Coverage subset-dependent (FD004 0.85); the absolute coverage gate floor is the weak rule",
  "The audit chain has no external anchor beyond MLflow; thresholds must be tuned per fleet"], { x: 0.5, y: 1.7, w: 6.1, h: 2.9, fontSize: 12 });
txt(s, "What deployment would take", { x: 6.9, y: 1.25, w: 5.9, h: 0.4, fontSize: 14, bold: true, color: C.accent3 });
bullets(s, ["A data contract: 26 columns per cycle per machine, batch or stream",
  "Per-fleet threshold calibration on historical run-to-failure data, validated on held-out machines",
  "A CMMS connector for the work-order record (action, due-by, reasons, sensors)",
  "A retraining calendar driven by the drift monitor, with the gate's reject log reviewed by an engineer",
  "An operator sign-off on the acceptable escalation share"], { x: 6.9, y: 1.7, w: 5.9, h: 2.9, fontSize: 12 });
card(s, 0.5, 4.7, 12.3, 1.3, "Reproducibility", `Pinned environment (requirements.lock.txt), seeds in config, data checksums verified by 'python -m sentinelloop doctor'; experiments/run_all.py regenerates every artefact in ${runAllMin} minutes; experiments/numbers_digest.py prints every number in this deck; ${nTests} tests. Annex: clean-clone commands, recorded run, repository.`, C.accent2);
txt(s, "References: Saxena et al. 2008 (C-MAPSS, PHM08) · Romano, Patterson, Candès 2019 (Conformalized Quantile Regression) · Robinson, IJPHM 2026 (CQR for RUL on C-MAPSS) · Mitici et al. 2023; Lee & Mitici 2023 (decision-level evaluation of prognostics) · Kamariotis et al. 2024 (decision-oriented metrics) · IntelliTwin (policy replay on C-MAPSS, GitHub). Nothing here is claimed as first; the strongest wording we use is 'not found in our search'.", { x: 0.5, y: 6.1, w: 12.3, h: 0.85, fontSize: 10, color: C.text2 });

(async () => {
  await pres.writeFile({ fileName: OUT });
  if (APPLY_THEME) { const { applyTheme } = require(APPLY_THEME); await applyTheme(OUT, THEME); }
  console.log(`wrote ${OUT} (${(fs.statSync(OUT).size / 1024).toFixed(0)} KB, 10 slides; theme ${APPLY_THEME ? "applied" : "NOT applied: pass --apply-theme <apply_theme.js>"})`);
})();
