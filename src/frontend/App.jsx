import React, { useEffect, useMemo, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, Area, AreaChart } from "recharts";

export default function App() {
  const [api, setApi] = useState("http://localhost:8020");
  const [scenario, setScenario] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch(`${api}/api/default_scenario`).then(r => r.json()).then(setScenario).catch(console.error);
  }, [api]);

  const runSim = async () => {
    if (!scenario) return;
    setLoading(true);
    try {
      const res = await fetch(`${api}/api/simulate`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(scenario) });
      const data = await res.json();
      setResult(data);
    } finally { setLoading(false); }
  };

  const chartData = useMemo(() => {
    if (!result) return [];
    return result.ages.map((age, i) => ({ age, median: result.median[i], p20: result.p20[i], p80: result.p80[i] }));
  }, [result]);

  const number = (x) => new Intl.NumberFormat().format(Math.round(x));

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        <header className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">Retirement Monte Carlo Simulator</h1>
          <div className="flex items-center gap-2">
            <input className="border rounded px-2 py-1" value={api} onChange={e=>setApi(e.target.value)} />
            <button onClick={runSim} className="px-3 py-1.5 rounded bg-blue-600 text-white disabled:opacity-50" disabled={!scenario || loading}>{loading?"Running…":"Run 10,000 sims"}</button>
          </div>
        </header>

        {!scenario ? (
          <p>Loading default scenario…</p>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* LEFT: Key fields */}
            <div className="lg:col-span-1 space-y-4">
              <Panel title="Basics">
                <Field label="Scenario Name" value={scenario.name} onChange={v=>setScenario({...scenario, name:v})} />
                <div className="grid grid-cols-2 gap-2">
                  <Field label="Current Age" type="number" value={scenario.current_age} onChange={v=>setScenario({...scenario, current_age:+v})} />
                  <Field label="End Age" type="number" value={scenario.end_age} onChange={v=>setScenario({...scenario, end_age:+v})} />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <Field label="Sims" type="number" value={scenario.sims} onChange={v=>setScenario({...scenario, sims:+v})} />
                  <Field label="Inflation" type="number" step="0.005" value={scenario.spending.inflation} onChange={v=>setScenario({...scenario, spending:{...scenario.spending, inflation:+v}})} />
                </div>
              </Panel>

              <Panel title="Spending">
                <Field label="Base Annual" type="number" value={scenario.spending.base_annual} onChange={v=>setScenario({...scenario, spending:{...scenario.spending, base_annual:+v}})} />
                <Field label="Reduced Annual" type="number" value={scenario.spending.reduced_annual} onChange={v=>setScenario({...scenario, spending:{...scenario.spending, reduced_annual:+v}})} />
                <Field label="Reduce At Age" type="number" value={scenario.spending.reduce_at_age} onChange={v=>setScenario({...scenario, spending:{...scenario.spending, reduce_at_age:+v}})} />
              </Panel>

              <Panel title="Taxes">
                <Field label="Effective Rate" type="number" step="0.01" value={scenario.taxes.effective_rate} onChange={v=>setScenario({...scenario, taxes:{...scenario.taxes, effective_rate:+v}})} />
                <Field label="Taxable Portfolio %" type="number" step="0.01" value={scenario.taxes.taxable_portfolio_ratio} onChange={v=>setScenario({...scenario, taxes:{...scenario.taxes, taxable_portfolio_ratio:+v}})} />
                <Field label="Taxable Income %" type="number" step="0.01" value={scenario.taxes.taxable_income_ratio} onChange={v=>setScenario({...scenario, taxes:{...scenario.taxes, taxable_income_ratio:+v}})} />
              </Panel>

              <Panel title="Fat Tails">
                <Toggle label="Enable Fat Tails" checked={scenario.cma.fat_tails} onChange={c=>setScenario({...scenario, cma:{...scenario.cma, fat_tails:c}})} />
                <div className="grid grid-cols-3 gap-2">
                  <Field label="t df" type="number" value={scenario.cma.t_df} onChange={v=>setScenario({...scenario, cma:{...scenario.cma, t_df:+v}})} />
                  <Field label="Tail Prob" type="number" step="0.005" value={scenario.cma.tail_prob} onChange={v=>setScenario({...scenario, cma:{...scenario.cma, tail_prob:+v}})} />
                  <Field label="Tail Boost (-)" type="number" step="0.005" value={scenario.cma.tail_boost} onChange={v=>setScenario({...scenario, cma:{...scenario.cma, tail_boost:+v}})} />
                </div>
              </Panel>
            </div>

            {/* RIGHT: Chart & summary */}
            <div className="lg:col-span-2 space-y-4">
              <Panel title="Portfolio Paths (median with 20–80 band)">
                {!result ? (
                  <p className="text-sm text-slate-600">Run the simulation to see results.</p>
                ) : (
                  <div className="h-80">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={chartData}>
                        <defs>
                          <linearGradient id="p20p80" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopOpacity={0.2} />
                            <stop offset="100%" stopOpacity={0.05} />
                          </linearGradient>
                        </defs>
                        <XAxis dataKey="age" />
                        <YAxis tickFormatter={(v)=>`$${(v/1e6).toFixed(1)}m`} />
                        <Tooltip formatter={(v)=>`$${number(v)}`} />
                        <Legend />
                        <Area type="monotone" dataKey="p80" strokeOpacity={0} fillOpacity={0.15} fill="url(#p20p80)" name="80th %" />
                        <Area type="monotone" dataKey="p20" strokeOpacity={0} fillOpacity={0.15} fill="url(#p20p80)" name="20th %" />
                        <Line type="monotone" dataKey="median" strokeWidth={2} name="Median" />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </Panel>

              {result && (
                <Panel title="Summary">
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <div className="text-slate-500">End Bal P20</div>
                      <div className="font-semibold">${number(result.end_balance_percentiles.p20)}</div>
                    </div>
                    <div>
                      <div className="text-slate-500">End Bal P50</div>
                      <div className="font-semibold">${number(result.end_balance_percentiles.p50)}</div>
                    </div>
                    <div>
                      <div className="text-slate-500">End Bal P80</div>
                      <div className="font-semibold">${number(result.end_balance_percentiles.p80)}</div>
                    </div>
                  </div>
                </Panel>
              )}
            </div>
          </div>
        )}

        {scenario && (
          <Panel title="Accounts & Events">
            <Section title="Accounts">
              {scenario.accounts.map((a, idx) => (
                <div key={idx} className="grid grid-cols-6 gap-2 items-end">
                  <Field label="Type" value={a.kind} onChange={v=>updateAcc(idx, { kind: v })} />
                  <Field label="Balance" type="number" value={a.balance} onChange={v=>updateAcc(idx, { balance:+v })} />
                  <Field label="Stocks" type="number" step="0.01" value={a.stocks} onChange={v=>updateAcc(idx, { stocks:+v })} />
                  <Field label="Bonds" type="number" step="0.01" value={a.bonds} onChange={v=>updateAcc(idx, { bonds:+v })} />
                  <Field label="Crypto" type="number" step="0.01" value={a.crypto} onChange={v=>updateAcc(idx, { crypto:+v })} />
                  <Field label="CDs" type="number" step="0.01" value={a.cds} onChange={v=>updateAcc(idx, { cds:+v })} />
                </div>
              ))}
              <button className="mt-2 px-3 py-1 rounded bg-slate-200" onClick={()=>setScenario({...scenario, accounts:[...scenario.accounts, {kind:"Taxable", balance:0, stocks:0.6, bonds:0.3, crypto:0.0, cds:0.0, cash:0.1}]})}>+ Add Account</button>
            </Section>

            <Section title="Income Streams (incl. Social Security)">
              {scenario.incomes.map((s, idx) => (
                <div key={idx} className="grid grid-cols-5 gap-2 items-end">
                  <Field label="Start Age" type="number" value={s.start_age} onChange={v=>updateIncome(idx,{start_age:+v})} />
                  <Field label="End Age" type="number" value={s.end_age} onChange={v=>updateIncome(idx,{end_age:+v})} />
                  <Field label="Monthly" type="number" value={s.monthly} onChange={v=>updateIncome(idx,{monthly:+v})} />
                  <Field label="COLA" type="number" step="0.005" value={s.cola} onChange={v=>updateIncome(idx,{cola:+v})} />
                </div>
              ))}
              <button className="mt-2 px-3 py-1 rounded bg-slate-200" onClick={()=>setScenario({...scenario, incomes:[...scenario.incomes, {start_age:65,end_age:90,monthly:2000,cola:0.02}]})}>+ Add Income</button>
            </Section>

            <Section title="Lump Sums (Home sales, 401k rollovers, etc)">
              {scenario.lumps.map((l, idx) => (
                <div key={idx} className="grid grid-cols-3 gap-2 items-end">
                  <Field label="Age" type="number" value={l.age} onChange={v=>updateLump(idx,{age:+v})} />
                  <Field label="Amount" type="number" value={l.amount} onChange={v=>updateLump(idx,{amount:+v})} />
                  <Field label="Description" value={l.description} onChange={v=>updateLump(idx,{description:v})} />
                </div>
              ))}
              <button className="mt-2 px-3 py-1 rounded bg-slate-200" onClick={()=>setScenario({...scenario, lumps:[...scenario.lumps, {age:60, amount:100000, description:"Other"}]})}>+ Add Lump</button>
            </Section>

            <Section title="Consulting Ladder & Toys">
              <div className="grid grid-cols-4 gap-2 items-end">
                <Field label="Start Age" type="number" value={scenario.consulting.start_age} onChange={v=>setScenario({...scenario, consulting:{...scenario.consulting, start_age:+v}})} />
                <Field label="Years" type="number" value={scenario.consulting.years} onChange={v=>setScenario({...scenario, consulting:{...scenario.consulting, years:+v}})} />
                <Field label="Start Amount" type="number" value={scenario.consulting.start_amount} onChange={v=>setScenario({...scenario, consulting:{...scenario.consulting, start_amount:+v}})} />
                <Field label="Growth" type="number" step="0.01" value={scenario.consulting.growth} onChange={v=>setScenario({...scenario, consulting:{...scenario.consulting, growth:+v}})} />
              </div>
              <div className="mt-3 space-y-2">
                {scenario.toys.map((t, idx)=> (
                  <div key={idx} className="grid grid-cols-3 gap-2 items-end">
                    <Field label="Age" type="number" value={t.age} onChange={v=>updateToy(idx,{age:+v})} />
                    <Field label="Amount" type="number" value={t.amount} onChange={v=>updateToy(idx,{amount:+v})} />
                    <Field label="Desc" value={t.description} onChange={v=>updateToy(idx,{description:v})} />
                  </div>
                ))}
                <button className="px-3 py-1 rounded bg-slate-200" onClick={()=>setScenario({...scenario, toys:[...scenario.toys, {age:57,amount:50000,description:"Toy"}]})}>+ Add Toy</button>
              </div>
            </Section>

            <div className="flex gap-2">
              <button className="px-3 py-1.5 rounded bg-emerald-600 text-white" onClick={runSim}>Run Again</button>
              <button className="px-3 py-1.5 rounded bg-slate-700 text-white" onClick={async()=>{
                const res = await fetch(`${api}/api/scenarios`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(scenario)});
                const data = await res.json();
                alert(`Saved scenario #${data.id}: ${data.name}`);
              }}>Save Scenario</button>
            </div>
          </Panel>
        )}

      </div>
    </div>
  );

  function updateAcc(idx, patch){
    const next = [...scenario.accounts];
    next[idx] = { ...next[idx], ...patch };
    setScenario({ ...scenario, accounts: next });
  }
  function updateIncome(idx, patch){
    const next = [...scenario.incomes];
    next[idx] = { ...next[idx], ...patch };
    setScenario({ ...scenario, incomes: next });
  }
  function updateLump(idx, patch){
    const next = [...scenario.lumps];
    next[idx] = { ...next[idx], ...patch };
    setScenario({ ...scenario, lumps: next });
  }
  function updateToy(idx, patch){
    const next = [...scenario.toys];
    next[idx] = { ...next[idx], ...patch };
    setScenario({ ...scenario, toys: next });
  }
}

function Panel({ title, children }){
  return (
    <section className="bg-white rounded-2xl shadow p-4">
      <h2 className="text-lg font-semibold mb-3">{title}</h2>
      {children}
    </section>
  );
}
function Section({title, children}){
  return (
    <div className="mt-4">
      <div className="text-sm font-medium text-slate-700 mb-2">{title}</div>
      <div className="space-y-2">{children}</div>
    </div>
  );
}
function Field({label, value, onChange, type="text", step}){
  return (
    <label className="block">
      <div className="text-xs text-slate-600 mb-1">{label}</div>
      <input type={type} step={step} className="w-full border rounded px-2 py-1" value={value} onChange={(e)=>onChange(e.target.value)} />
    </label>
  );
}
function Toggle({label, checked, onChange}){
  return (
    <label className="flex items-center gap-2">
      <input type="checkbox" checked={checked} onChange={(e)=>onChange(e.target.checked)} />
      <span className="text-sm">{label}</span>
    </label>
  );
}