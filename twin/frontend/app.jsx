const { useState, useEffect, useRef } = React;
const post = (p, body) => fetch("/api/" + p, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then(r => r.json());
const get = p => fetch("/api/" + p).then(r => r.json());
const pct = v => (v * 100).toFixed(1) + "%";
const nice = k => k.replace(/_/g, " ");

function Plot({ type, data, options }) {
  const ref = useRef();
  useEffect(() => {
    const c = new window.Chart(ref.current, { type, data, options: { responsive: true, maintainAspectRatio: false,
      plugins: { legend: { labels: { color: "#e2e8f0" } } },
      scales: type === "doughnut" ? {} : { x: { ticks: { color: "#94a3b8" } }, y: { ticks: { color: "#94a3b8" } } }, ...options } });
    return () => c.destroy();
  }, [JSON.stringify(data), type]);
  return <div className="chart"><canvas ref={ref} /></div>;
}
const Probs = ({ p }) => Object.entries(p).map(([k, v]) =>
  <div className="bar" key={k}><span>{k}</span><div><i style={{ width: pct(v) }} /></div><span>{pct(v)}</span></div>);

/* ---------- Digital twin: profile, current state, prediction ---------- */
function Twin({ emps, selected, setSelected, model, goWhatIf }) {
  const [d, setD] = useState(null);
  useEffect(() => { if (selected) get(`employees/${selected}/?model=${encodeURIComponent(model)}`).then(setD); }, [selected, model]);
  if (!d || d.error) return <div className="card">Select an employee…</div>;
  const f = d.features, nums = Object.keys(f).filter(k => typeof f[k] === "number");
  const rel = nums.map(k => d.team_means[k] ? Math.round(100 * f[k] / d.team_means[k]) : 0);
  return <>
    <div className="grid">
      <div className="card"><h2>Employee profile</h2>
        <div className="tiles">
          <div className="tile"><small>Employee ID</small><b>{d.id}</b></div>
          {Object.entries(f).filter(([k]) => ["Age", "Experience_Years", "Project_Count"].includes(k) || typeof f[k] === "string")
            .map(([k, v]) => <div className="tile" key={k}><small>{nice(k)}</small><b>{v}</b></div>)}
          <div className="tile"><small>Recorded level</small><b>{d.actual}</b></div>
        </div></div>
      <div className="card"><h2>Predicted productivity ({d.prediction.model})</h2>
        <span className={"badge " + d.prediction.prediction}>{d.prediction.prediction}</span>
        <p className="mut">Confidence {pct(d.prediction.confidence)}</p>
        <Probs p={d.prediction.probabilities} />
        <button className="btn" onClick={goWhatIf}>Run what-if scenario →</button></div>
    </div>
    <div className="card" style={{ marginTop: 16 }}><h2>Current state</h2>
      <div className="tiles">{Object.entries(f).filter(([k, v]) => typeof v === "number" && !["Age", "Experience_Years", "Project_Count"].includes(k))
        .map(([k, v]) => <div className="tile" key={k}><small>{nice(k)}</small><b>{v}</b></div>)}
        {Object.entries(d.engineered).map(([k, v]) => <div className="tile" key={k}><small>{nice(k)} (derived)</small><b>{v}</b></div>)}</div></div>
    <div className="grid">
      <div className="card"><h2>Employee vs team average (team = 100%)</h2>
        <Plot type="bar" data={{ labels: nums.map(nice), datasets: [{ label: "% of team average", data: rel, backgroundColor: "#38bdf8" }] }} /></div>
      <div className="card"><h2>History for this employee</h2>
        {d.history.length === 0 ? <p className="mut">No simulations yet. Run a what-if to build history.</p> :
          <table><thead><tr><th>Type</th><th>Result</th><th>Conf.</th><th>When</th></tr></thead><tbody>
            {d.history.map((h, i) => <tr key={i}><td>{h.kind}</td><td>{h.label}</td><td>{pct(h.confidence)}</td><td>{new Date(h.created_at).toLocaleString()}</td></tr>)}</tbody></table>}</div>
    </div></>;
}

/* ---------- What-if simulation ---------- */
function WhatIf({ schema, selected, model }) {
  const [base, setBase] = useState(null), [scen, setScen] = useState(null), [out, setOut] = useState(null), [err, setErr] = useState("");
  useEffect(() => {
    if (!selected) return;
    get(`employees/${selected}/`).then(d => { setBase(d.features); setScen(d.features); setOut(null); });
  }, [selected]);
  if (!base) return <div className="card">Select an employee first (top right).</div>;
  const run = () => { setErr(""); post("whatif/", { base, scenario: scen, model, employee_id: selected }).then(r => r.error ? setErr(r.error) : setOut(r)); };
  const set = (k, v) => setScen({ ...scen, [k]: v });
  return <div className="grid">
    <div className="card"><h2>Change inputs for employee {selected}</h2>
      {schema.features.map(f => f.type === "number" ?
        <div className="slider" key={f.name}><span>{nice(f.name)}</span>
          <input type="range" min={f.min} max={f.max * 1.2} step={f.step} value={scen[f.name] ?? f.median} onChange={e => set(f.name, +e.target.value)} />
          <span className={scen[f.name] !== base[f.name] ? "chg" : ""}>{scen[f.name]}</span></div> :
        <div className="slider" key={f.name}><span>{nice(f.name)}</span>
          <select value={scen[f.name] ?? ""} onChange={e => set(f.name, e.target.value)}>{f.categories.map(c => <option key={c}>{c}</option>)}</select><span /></div>)}
      <div className="row"><button className="btn" onClick={run}>Recalculate prediction</button>
        <button className="btn alt" onClick={() => { setScen(base); setOut(null); }}>Reset</button></div>
      {err && <p className="err">{err}</p>}</div>
    <div className="card"><h2>Result</h2>
      {!out ? <p className="mut">Move the sliders, then press Recalculate.</p> : <>
        <div className="row"><div><small className="mut">Baseline</small><br /><span className={"badge " + out.baseline.prediction}>{out.baseline.prediction}</span></div>
          <span className="delta">→</span>
          <div><small className="mut">Scenario</small><br /><span className={"badge " + out.scenario.prediction}>{out.scenario.prediction}</span></div></div>
        <Plot type="bar" data={{ labels: Object.keys(out.baseline.probabilities), datasets: [
          { label: "Baseline", data: Object.values(out.baseline.probabilities).map(v => v * 100), backgroundColor: "#64748b" },
          { label: "Scenario", data: Object.values(out.scenario.probabilities).map(v => v * 100), backgroundColor: "#38bdf8" }] }} options={{ scales: { y: { max: 100, ticks: { color: "#94a3b8" } }, x: { ticks: { color: "#94a3b8" } } } }} />
        <h2 style={{ marginTop: 14 }}>Changes applied</h2>
        {Object.keys(out.changed).length === 0 ? <p className="mut">None</p> :
          <table><tbody>{Object.entries(out.changed).map(([k, c]) => <tr key={k}><td>{nice(k)}</td><td>{c.from} → <b>{c.to}</b></td></tr>)}</tbody></table>}</>}</div>
  </div>;
}

/* ---------- Dataset + model summary ---------- */
function Summary({ s }) {
  const [cmModel, setCmModel] = useState(s.best_model), [hf, setHf] = useState(Object.keys(s.eda.hist)[0]);
  const e = s.eda, nums = Object.keys(e.hist), cm = s.confusion[cmModel], mx = Math.max(...cm.flat());
  return <>
    <div className="grid">
      <div className="card"><h2>Dataset analysis</h2><div className="tiles">
        <div className="tile"><small>Rows</small><b>{e.rows}</b></div><div className="tile"><small>Columns</small><b>{e.columns}</b></div>
        <div className="tile"><small>Duplicates</small><b>{e.duplicates}</b></div>
        <div className="tile"><small>Missing cells</small><b>{Object.values(e.missing).reduce((a, b) => a + b, 0)}</b></div>
        <div className="tile"><small>Invalid fixed</small><b>{e.invalid_values_fixed}</b></div></div>
        <p className="mut">Missing → median/mode imputation inside the model pipeline. Outliers (IQR) are reported, not removed.</p></div>
      <div className="card"><h2>Class distribution</h2>
        <Plot type="doughnut" data={{ labels: Object.keys(e.class_distribution), datasets: [{ data: Object.values(e.class_distribution), backgroundColor: ["#4ade80", "#facc15", "#f87171", "#38bdf8"] }] }} /></div>
    </div>
    <div className="card" style={{ marginTop: 16 }}><h2>Model comparison (best: {s.best_model})</h2>
      <table><thead><tr><th>Model</th><th>Accuracy</th><th>Macro Precision</th><th>Macro Recall</th><th>Macro F1</th><th>Weighted F1</th></tr></thead><tbody>
        {s.metrics.map(m => <tr key={m.Model}><td>{m.Model}</td>{["Accuracy", "Macro Precision", "Macro Recall", "Macro F1", "Weighted F1"].map(k => <td key={k}>{m[k].toFixed(3)}</td>)}</tr>)}</tbody></table></div>
    <div className="grid">
      <div className="card"><h2>Confusion matrix</h2>
        <select value={cmModel} onChange={x => setCmModel(x.target.value)}>{Object.keys(s.confusion).map(m => <option key={m}>{m}</option>)}</select>
        <table style={{ marginTop: 10 }}><thead><tr><th>Actual ↓ / Pred →</th>{s.classes.map(c => <th key={c}>{c}</th>)}</tr></thead><tbody>
          {cm.map((r, i) => <tr key={i}><td>{s.classes[i]}</td>{r.map((v, j) => <td key={j} style={{ background: `rgba(56,189,248,${v / mx * .7})` }}>{v}</td>)}</tr>)}</tbody></table></div>
      <div className="card"><h2>Feature importance (Random Forest)</h2>
        <Plot type="bar" data={{ labels: s.importance.map(i => nice(i.feature)), datasets: [{ label: "Importance", data: s.importance.map(i => i.importance), backgroundColor: "#38bdf8" }] }} options={{ indexAxis: "y" }} /></div>
    </div>
    <div className="grid" style={{ marginTop: 16 }}>
      <div className="card"><h2>Distribution</h2>
        <select value={hf} onChange={x => setHf(x.target.value)}>{nums.map(n => <option key={n} value={n}>{nice(n)}</option>)}</select>
        <Plot type="bar" data={{ labels: e.hist[hf].labels, datasets: [{ label: nice(hf), data: e.hist[hf].counts, backgroundColor: "#818cf8" }] }} /></div>
      <div className="card" style={{ overflowX: "auto" }}><h2>Correlation</h2>
        <table><thead><tr><th></th>{nums.map(n => <th key={n} title={n}>{n.slice(0, 5)}</th>)}</tr></thead><tbody>
          {nums.map(a => <tr key={a}><td>{nice(a)}</td>{nums.map(b => { const v = e.correlation[a][b] ?? 0; return <td key={b} style={{ background: `rgba(${v > 0 ? "56,189,248" : "248,113,113"},${Math.abs(v) * .8})` }}>{v}</td>; })}</tr>)}</tbody></table></div>
    </div></>;
}

function Log() {
  const [h, setH] = useState([]);
  useEffect(() => { get("history/").then(r => setH(r.history)); }, []);
  return <div className="card"><h2>Prediction & what-if history (last 50)</h2>
    <table><thead><tr><th>Employee</th><th>Type</th><th>Model</th><th>Result</th><th>Confidence</th><th>Time</th></tr></thead><tbody>
      {h.map((x, i) => <tr key={i}><td>{x.employee_id || "—"}</td><td>{x.kind}</td><td>{x.model_name}</td><td>{x.label}</td><td>{pct(x.confidence)}</td><td>{new Date(x.created_at).toLocaleString()}</td></tr>)}</tbody></table></div>;
}

function App() {
  const [tab, setTab] = useState("twin"), [schema, setSchema] = useState(null), [sum, setSum] = useState(null),
    [emps, setEmps] = useState([]), [sel, setSel] = useState(""), [model, setModel] = useState(""), [q, setQ] = useState("");
  useEffect(() => {
    get("schema/").then(s => { setSchema(s); setModel(s.best_model); });
    get("summary/").then(setSum);
    get("employees/").then(r => { setEmps(r.employees); if (r.employees[0]) setSel(String(r.employees[0].id)); });
  }, []);
  if (!schema || !sum) return <main><div className="card">Loading… (is the Django server running and the model trained?)</div></main>;
  const list = emps.filter(e => String(e.id).toLowerCase().includes(q.toLowerCase())).slice(0, 300);
  return <>
    <header><h1>🧑‍💼 Employee Productivity Digital Twin</h1>
      <div className="row"><input type="text" placeholder="Search ID…" value={q} onChange={e => setQ(e.target.value)} style={{ width: 110 }} />
        <select value={sel} onChange={e => setSel(e.target.value)}>{list.map(e => <option key={e.id} value={e.id}>{e.id} — {e.actual}</option>)}</select>
        <select value={model} onChange={e => setModel(e.target.value)}>{schema.models.map(m => <option key={m} value={m}>{m}{m === schema.best_model ? " ★" : ""}</option>)}</select></div></header>
    <nav style={{ padding: "0 24px", borderBottom: "1px solid var(--line)" }}>
      {[["twin", "Digital Twin"], ["whatif", "What-If"], ["summary", "Dataset & Models"], ["log", "History"]].map(([k, l]) =>
        <button key={k} className={tab === k ? "on" : ""} onClick={() => setTab(k)}>{l}</button>)}</nav>
    <main>
      {tab === "twin" && <Twin emps={emps} selected={sel} setSelected={setSel} model={model} goWhatIf={() => setTab("whatif")} />}
      {tab === "whatif" && <WhatIf schema={schema} selected={sel} model={model} />}
      {tab === "summary" && <Summary s={sum} />}
      {tab === "log" && <Log />}
    </main></>;
}
ReactDOM.createRoot(document.getElementById("root")).render(<App />);
