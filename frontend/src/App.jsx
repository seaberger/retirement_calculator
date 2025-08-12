import React, { useEffect, useMemo, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, Area, AreaChart, CartesianGrid } from "recharts";

export default function App() {
  const [api, setApi] = useState("http://localhost:8020");
  const [scenario, setScenario] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("personal");
  const [showResults, setShowResults] = useState(false);
  const [savedScenarios, setSavedScenarios] = useState([]);
  const [saveModalOpen, setSaveModalOpen] = useState(false);
  const [scenarioName, setScenarioName] = useState("");

  useEffect(() => {
    fetch(`${api}/api/default_scenario`).then(r => r.json()).then(setScenario).catch(console.error);
    loadScenarioList();
  }, [api]);

  const loadScenarioList = async () => {
    try {
      const res = await fetch(`${api}/api/scenarios`);
      const data = await res.json();
      setSavedScenarios(data);
    } catch (err) {
      console.error('Failed to load scenarios:', err);
    }
  };

  const loadScenario = async (id) => {
    try {
      const res = await fetch(`${api}/api/scenarios/${id}`);
      const data = await res.json();
      setScenario(data);
      alert(`Loaded scenario: ${data.name}`);
    } catch (err) {
      console.error('Failed to load scenario:', err);
      alert('Failed to load scenario');
    }
  };

  const saveScenario = async () => {
    if (!scenarioName.trim()) {
      alert('Please enter a scenario name');
      return;
    }
    try {
      const scenarioToSave = { ...scenario, name: scenarioName };
      const res = await fetch(`${api}/api/scenarios`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(scenarioToSave)
      });
      const data = await res.json();
      alert(`Saved scenario: ${data.name}`);
      setSaveModalOpen(false);
      setScenarioName('');
      loadScenarioList();
    } catch (err) {
      console.error('Failed to save scenario:', err);
      alert('Failed to save scenario');
    }
  };

  const runSim = async () => {
    if (!scenario) return;
    setLoading(true);
    try {
      const res = await fetch(`${api}/api/simulate`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(scenario) });
      const data = await res.json();
      setResult(data);
      setShowResults(true);
    } finally { setLoading(false); }
  };

  const chartData = useMemo(() => {
    if (!result) return [];
    return result.ages.map((age, i) => ({ age, median: result.median[i], p20: result.p20[i], p80: result.p80[i] }));
  }, [result]);

  const number = (x) => new Intl.NumberFormat('en-US', { style: 'decimal', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(Math.round(x));
  const currency = (x) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(Math.round(x));
  const percent = (x) => `${(x * 100).toFixed(2)}%`;

  const tabs = [
    { id: 'personal', label: 'Personal', icon: '👤' },
    { id: 'portfolio', label: 'Portfolio', icon: '💼' },
    { id: 'expenses', label: 'Expenses', icon: '💰' },
    { id: 'settings', label: 'Settings', icon: '⚙️' },
  ];

  if (!scenario) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-lg text-gray-600">Loading retirement calculator...</div>
      </div>
    );
  }

  if (showResults && result) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-7xl mx-auto p-8">
          <div className="mb-8">
            <div className="flex items-center justify-between mb-2">
              <h1 className="text-4xl font-light text-gray-900">Simulation Results</h1>
              <button
                onClick={() => setShowResults(false)}
                className="px-6 py-2.5 bg-gray-600 text-white rounded-lg font-medium hover:bg-gray-700 transition-colors"
              >
                ← Back to Edit
              </button>
            </div>
            <p className="text-gray-600">We ran 10,000 simulations based on your information.</p>
          </div>

          <div className="flex gap-4 mb-8">
            <button
              onClick={() => {
                setShowResults(false);
                setActiveTab('personal');
              }}
              className="px-6 py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors"
            >
              Edit Inputs
            </button>
            <button
              onClick={async () => {
                const res = await fetch(`${api}/api/scenarios`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(scenario)});
                const data = await res.json();
                alert(`Saved scenario: ${data.name}`);
              }}
              className="px-6 py-2.5 bg-white text-gray-700 border border-gray-300 rounded-lg font-medium hover:bg-gray-50 transition-colors"
            >
              Save
            </button>
          </div>

          <div className="bg-white rounded-xl shadow-sm p-8 mb-8">
            <h2 className="text-2xl font-semibold text-gray-900 mb-6">Portfolio Balance Through Time</h2>
            <div className="h-96">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="colorP20" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#E5E7EB" stopOpacity={0.8}/>
                      <stop offset="95%" stopColor="#E5E7EB" stopOpacity={0.1}/>
                    </linearGradient>
                    <linearGradient id="colorP80" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#DBEAFE" stopOpacity={0.8}/>
                      <stop offset="95%" stopColor="#DBEAFE" stopOpacity={0.1}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                  <XAxis 
                    dataKey="age" 
                    stroke="#6B7280"
                    style={{ fontSize: '14px' }}
                  />
                  <YAxis 
                    tickFormatter={(v) => `$${(v/1e6).toFixed(1)}M`} 
                    stroke="#6B7280"
                    style={{ fontSize: '14px' }}
                  />
                  <Tooltip 
                    formatter={(v) => currency(v)}
                    contentStyle={{ borderRadius: '8px', border: '1px solid #E5E7EB' }}
                  />
                  <Legend />
                  <Area 
                    type="monotone" 
                    dataKey="p80" 
                    stroke="none" 
                    fill="url(#colorP80)" 
                    name="Lucky to unlucky range"
                  />
                  <Area 
                    type="monotone" 
                    dataKey="p20" 
                    stroke="none" 
                    fill="url(#colorP20)" 
                    name=""
                    legendType="none"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="median" 
                    stroke="#2563EB" 
                    strokeWidth={3} 
                    name="Trial with median ending balance"
                    dot={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-sm p-8 mb-8">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 text-center">PORTFOLIO BALANCE AT AGE {scenario.end_age}</h3>
            <div className="grid grid-cols-3 gap-8 mb-8">
              <div className="text-center p-6 border border-gray-200 rounded-lg">
                <div className="text-sm text-gray-500 mb-2">Unlucky</div>
                <div className="text-xs text-gray-400 mb-3">20th percentile</div>
                <div className="text-3xl font-semibold text-gray-900 mb-2">
                  ${(result.end_balance_percentiles.p20 / 1e6).toFixed(2)}m
                </div>
                <div className="text-sm text-gray-600">{percent((Math.pow(result.end_balance_percentiles.p20 / (scenario.accounts.reduce((sum, acc) => sum + acc.balance, 0)), 1/(scenario.end_age - scenario.current_age)) - 1))} return</div>
              </div>
              <div className="text-center p-6 border-2 border-blue-500 rounded-lg bg-blue-50">
                <div className="text-sm text-gray-700 font-medium mb-2">Median</div>
                <div className="text-xs text-gray-500 mb-3">50th percentile</div>
                <div className="text-3xl font-semibold text-blue-600 mb-2">
                  ${(result.end_balance_percentiles.p50 / 1e6).toFixed(2)}m
                </div>
                <div className="text-sm text-gray-600">{percent((Math.pow(result.end_balance_percentiles.p50 / (scenario.accounts.reduce((sum, acc) => sum + acc.balance, 0)), 1/(scenario.end_age - scenario.current_age)) - 1))} return</div>
              </div>
              <div className="text-center p-6 border border-gray-200 rounded-lg">
                <div className="text-sm text-gray-500 mb-2">Lucky</div>
                <div className="text-xs text-gray-400 mb-3">80th percentile</div>
                <div className="text-3xl font-semibold text-gray-900 mb-2">
                  ${(result.end_balance_percentiles.p80 / 1e6).toFixed(2)}m
                </div>
                <div className="text-sm text-gray-600">{percent((Math.pow(result.end_balance_percentiles.p80 / (scenario.accounts.reduce((sum, acc) => sum + acc.balance, 0)), 1/(scenario.end_age - scenario.current_age)) - 1))} return</div>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-sm p-8">
            <h3 className="text-2xl font-semibold text-gray-900 mb-6">Breakdown By Age</h3>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b-2 border-gray-200">
                    <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Age</th>
                    <th colSpan="3" className="text-center py-3 px-4 text-sm font-medium text-gray-700">Market Return *</th>
                    <th colSpan="3" className="text-center py-3 px-4 text-sm font-medium text-gray-700">Portfolio Balance</th>
                  </tr>
                  <tr className="border-b border-gray-200 text-xs text-gray-500">
                    <th></th>
                    <th className="text-center py-2 px-4">Unlucky<br/>20th percentile</th>
                    <th className="text-center py-2 px-4">Median<br/>50th percentile</th>
                    <th className="text-center py-2 px-4">Lucky<br/>80th percentile</th>
                    <th className="text-center py-2 px-4">Unlucky<br/>20th percentile</th>
                    <th className="text-center py-2 px-4">Median<br/>50th percentile</th>
                    <th className="text-center py-2 px-4">Lucky<br/>80th percentile</th>
                  </tr>
                </thead>
                <tbody>
                  {[70, 75, 80, 85, 90].map(age => {
                    const idx = result.ages.indexOf(age);
                    if (idx === -1) return null;
                    
                    // Calculate annualized returns from current age to this age
                    const yearsFromStart = age - scenario.current_age;
                    const initialBalance = scenario.accounts.reduce((sum, acc) => sum + acc.balance, 0);
                    
                    // Calculate annualized returns for each percentile
                    const returnP20 = initialBalance > 0 && result.p20[idx] > 0 
                      ? (Math.pow(result.p20[idx] / initialBalance, 1 / yearsFromStart) - 1) * 100 
                      : 0;
                    const returnMedian = initialBalance > 0 && result.median[idx] > 0
                      ? (Math.pow(result.median[idx] / initialBalance, 1 / yearsFromStart) - 1) * 100
                      : 0;
                    const returnP80 = initialBalance > 0 && result.p80[idx] > 0
                      ? (Math.pow(result.p80[idx] / initialBalance, 1 / yearsFromStart) - 1) * 100
                      : 0;
                    
                    return (
                      <tr key={age} className="border-b border-gray-100 hover:bg-gray-50">
                        <td className="py-3 px-4 font-medium">{age}</td>
                        <td className="text-center py-3 px-4">{returnP20.toFixed(2)}%</td>
                        <td className="text-center py-3 px-4">{returnMedian.toFixed(2)}%</td>
                        <td className="text-center py-3 px-4">{returnP80.toFixed(2)}%</td>
                        <td className="text-center py-3 px-4">{currency(result.p20[idx])}</td>
                        <td className="text-center py-3 px-4 font-medium">{currency(result.median[idx])}</td>
                        <td className="text-center py-3 px-4">{currency(result.p80[idx])}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              <p className="text-xs text-gray-500 mt-4">* Nominal time-weighted annualized return</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-5xl mx-auto p-8">
        <div className="mb-8">
          <h1 className="text-4xl font-light text-gray-900 mb-6">Portfolio Simulator</h1>
          
          {/* Tab Navigation */}
          <div className="flex gap-8 mb-8">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 pb-3 px-1 border-b-2 transition-colors ${
                  activeTab === tab.id 
                    ? 'border-blue-600 text-blue-600' 
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                <span className="text-xl">{tab.icon}</span>
                <span className="font-medium">{tab.label}</span>
              </button>
            ))}
            <div className="flex-1"></div>
            <button
              onClick={runSim}
              disabled={loading}
              className="px-6 py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              {loading ? "Running..." : "Show Me"}
            </button>
          </div>
        </div>

        {/* Tab Content */}
        <div className="bg-white rounded-xl shadow-sm p-8">
          {activeTab === 'personal' && (
            <div>
              <div className="flex items-start justify-between mb-6">
                <div>
                  <h2 className="text-2xl font-semibold text-gray-900 mb-2">Personal Info</h2>
                  <p className="text-gray-600">Age, income, and other personal information.</p>
                </div>
                <div className="flex gap-3">
                  <button
                    onClick={() => {
                      setScenarioName(scenario.name || 'My Scenario');
                      setSaveModalOpen(true);
                    }}
                    className="px-4 py-2 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 transition-colors"
                  >
                    Save Scenario
                  </button>
                  <select
                    onChange={(e) => {
                      if (e.target.value) {
                        loadScenario(parseInt(e.target.value));
                      }
                    }}
                    className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">Load Scenario...</option>
                    {savedScenarios.map(s => (
                      <option key={s.id} value={s.id}>{s.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="space-y-8">
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-4">Basics</h3>
                  <div className="grid grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm text-gray-600 mb-2">First Name</label>
                      <input 
                        type="text" 
                        placeholder="Optional"
                        className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                        value={scenario.name}
                        onChange={e => setScenario({...scenario, name: e.target.value})}
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-gray-600 mb-2">Birthdate</label>
                      <input 
                        type="text" 
                        placeholder="MM / YYYY"
                        className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-6 mt-6">
                    <div>
                      <label className="block text-sm text-gray-600 mb-2">Current Age</label>
                      <div className="flex items-center gap-2">
                        <input 
                          type="number" 
                          className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                          value={scenario.current_age}
                          onChange={e => setScenario({...scenario, current_age: +e.target.value})}
                        />
                        <span className="text-gray-500">years</span>
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm text-gray-600 mb-2">Life Expectancy</label>
                      <div className="flex items-center gap-2">
                        <input 
                          type="number" 
                          className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                          value={scenario.end_age}
                          onChange={e => setScenario({...scenario, end_age: +e.target.value})}
                        />
                        <span className="text-gray-500">years</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-4">Regular Income</h3>
                  <div className="grid grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm text-gray-600 mb-2">Annual Income</label>
                      <div className="flex items-center gap-2">
                        <span className="text-gray-500">$</span>
                        <input 
                          type="number" 
                          className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                          value={0}
                          onChange={() => {}}
                        />
                        <span className="text-gray-500">/ yr</span>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">Gross annual income (before taxes)</p>
                    </div>
                    <div>
                      <label className="block text-sm text-gray-600 mb-2">Growth</label>
                      <div className="flex items-center gap-2">
                        <input 
                          type="number" 
                          step="0.1"
                          className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                          value={scenario.consulting.growth * 100}
                          onChange={e => setScenario({...scenario, consulting: {...scenario.consulting, growth: +e.target.value / 100}})}
                        />
                        <span className="text-gray-500">%</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-4">Retirement Income</h3>
                  
                  {scenario.incomes.map((income, idx) => (
                    <div key={idx} className="mb-6 p-4 border border-gray-200 rounded-lg">
                      <div className="grid grid-cols-4 gap-4">
                        <div>
                          <label className="block text-sm text-gray-600 mb-2">Monthly Amount</label>
                          <div className="flex items-center gap-2">
                            <span className="text-gray-500">$</span>
                            <input 
                              type="number" 
                              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                              value={income.monthly}
                              onChange={e => updateIncome(idx, {monthly: +e.target.value})}
                            />
                            <span className="text-gray-500">/ mo</span>
                          </div>
                        </div>
                        <div>
                          <label className="block text-sm text-gray-600 mb-2">Start Age</label>
                          <input 
                            type="number" 
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                            value={income.start_age}
                            onChange={e => updateIncome(idx, {start_age: +e.target.value})}
                          />
                        </div>
                        <div>
                          <label className="block text-sm text-gray-600 mb-2">End Age</label>
                          <input 
                            type="number" 
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                            value={income.end_age}
                            onChange={e => updateIncome(idx, {end_age: +e.target.value})}
                          />
                        </div>
                        <div>
                          <label className="block text-sm text-gray-600 mb-2">Growth</label>
                          <div className="flex items-center gap-2">
                            <input 
                              type="number" 
                              step="0.1"
                              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                              value={income.cola * 100}
                              onChange={e => updateIncome(idx, {cola: +e.target.value / 100})}
                            />
                            <span className="text-gray-500">%</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                  
                  <button 
                    onClick={() => setScenario({...scenario, incomes: [...scenario.incomes, {start_age: 65, end_age: 90, monthly: 2000, cola: 0.02}]})}
                    className="text-blue-600 hover:text-blue-700 font-medium"
                  >
                    + Add Income Stream
                  </button>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'portfolio' && (
            <div>
              <h2 className="text-2xl font-semibold text-gray-900 mb-2">Portfolio</h2>
              <p className="text-gray-600 mb-8">Current balance, asset allocation, and contributions.</p>

              <div className="space-y-8">
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-4">Accounts</h3>
                  {scenario.accounts.map((account, idx) => (
                    <div key={idx} className="mb-4 p-4 border border-gray-200 rounded-lg">
                      <div className="grid grid-cols-7 gap-3">
                        <div>
                          <label className="block text-xs text-gray-600 mb-1">Type</label>
                          <input 
                            type="text" 
                            className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                            value={account.kind}
                            onChange={e => updateAcc(idx, {kind: e.target.value})}
                          />
                        </div>
                        <div>
                          <label className="block text-xs text-gray-600 mb-1">Balance</label>
                          <input 
                            type="number" 
                            className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                            value={account.balance}
                            onChange={e => updateAcc(idx, {balance: +e.target.value})}
                          />
                        </div>
                        <div>
                          <label className="block text-xs text-gray-600 mb-1">Stocks %</label>
                          <input 
                            type="number" 
                            step="0.01"
                            className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                            value={account.stocks * 100}
                            onChange={e => updateAcc(idx, {stocks: +e.target.value / 100})}
                          />
                        </div>
                        <div>
                          <label className="block text-xs text-gray-600 mb-1">Bonds %</label>
                          <input 
                            type="number" 
                            step="0.01"
                            className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                            value={account.bonds * 100}
                            onChange={e => updateAcc(idx, {bonds: +e.target.value / 100})}
                          />
                        </div>
                        <div>
                          <label className="block text-xs text-gray-600 mb-1">Crypto %</label>
                          <input 
                            type="number" 
                            step="0.01"
                            className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                            value={account.crypto * 100}
                            onChange={e => updateAcc(idx, {crypto: +e.target.value / 100})}
                          />
                        </div>
                        <div>
                          <label className="block text-xs text-gray-600 mb-1">CDs %</label>
                          <input 
                            type="number" 
                            step="0.01"
                            className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                            value={account.cds * 100}
                            onChange={e => updateAcc(idx, {cds: +e.target.value / 100})}
                          />
                        </div>
                        <div>
                          <label className="block text-xs text-gray-600 mb-1">Cash %</label>
                          <input 
                            type="number" 
                            step="0.01"
                            className="w-full px-2 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                            value={account.cash * 100}
                            onChange={e => updateAcc(idx, {cash: +e.target.value / 100})}
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                  <button 
                    onClick={() => setScenario({...scenario, accounts: [...scenario.accounts, {kind: "Taxable", balance: 0, stocks: 0.6, bonds: 0.3, crypto: 0, cds: 0, cash: 0.1}]})}
                    className="text-blue-600 hover:text-blue-700 font-medium"
                  >
                    + Add Account
                  </button>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-4">Lump Sum Events</h3>
                  {scenario.lumps.map((lump, idx) => (
                    <div key={idx} className="mb-3 grid grid-cols-3 gap-3">
                      <div>
                        <input 
                          type="number" 
                          placeholder="Age"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                          value={lump.age}
                          onChange={e => updateLump(idx, {age: +e.target.value})}
                        />
                      </div>
                      <div>
                        <input 
                          type="number" 
                          placeholder="Amount"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                          value={lump.amount}
                          onChange={e => updateLump(idx, {amount: +e.target.value})}
                        />
                      </div>
                      <div>
                        <input 
                          type="text" 
                          placeholder="Description"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                          value={lump.description}
                          onChange={e => updateLump(idx, {description: e.target.value})}
                        />
                      </div>
                    </div>
                  ))}
                  <button 
                    onClick={() => setScenario({...scenario, lumps: [...scenario.lumps, {age: 60, amount: 100000, description: ""}]})}
                    className="text-blue-600 hover:text-blue-700 font-medium"
                  >
                    + Add Lump Sum
                  </button>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'expenses' && (
            <div>
              <h2 className="text-2xl font-semibold text-gray-900 mb-2">Expenses</h2>
              <p className="text-gray-600 mb-8">Retirement distributions, taxes, and other portfolio withdrawals.</p>

              <div className="space-y-8">
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-4">Regular Distributions</h3>
                  <div className="grid grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm text-gray-600 mb-2">Retirement Living Expenses</label>
                      <div className="flex items-center gap-2">
                        <span className="text-gray-500">$</span>
                        <input 
                          type="number" 
                          className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                          value={scenario.spending.base_annual / 12}
                          onChange={e => setScenario({...scenario, spending: {...scenario.spending, base_annual: +e.target.value * 12}})}
                        />
                        <span className="text-gray-500">/ mo</span>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">Monthly living expenses in retirement</p>
                    </div>
                    <div>
                      <label className="block text-sm text-gray-600 mb-2">Inflation</label>
                      <div className="flex items-center gap-2">
                        <input 
                          type="number" 
                          step="0.1"
                          className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                          value={scenario.spending.inflation * 100}
                          onChange={e => setScenario({...scenario, spending: {...scenario.spending, inflation: +e.target.value / 100}})}
                        />
                        <span className="text-gray-500">%</span>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">Annual</p>
                    </div>
                  </div>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-4">Taxes</h3>
                  <div className="grid grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm text-gray-600 mb-2">Taxable Portion of Portfolio</label>
                      <div className="flex items-center gap-2">
                        <input 
                          type="number" 
                          step="1"
                          className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                          value={scenario.taxes.taxable_portfolio_ratio * 100}
                          onChange={e => setScenario({...scenario, taxes: {...scenario.taxes, taxable_portfolio_ratio: +e.target.value / 100}})}
                        />
                        <span className="text-gray-500">%</span>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">Estimated % of your portfolio subject to taxes upon withdrawal</p>
                    </div>
                    <div>
                      <label className="block text-sm text-gray-600 mb-2">Taxable Portion of Retirement Income</label>
                      <div className="flex items-center gap-2">
                        <input 
                          type="number" 
                          step="1"
                          className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                          value={scenario.taxes.taxable_income_ratio * 100}
                          onChange={e => setScenario({...scenario, taxes: {...scenario.taxes, taxable_income_ratio: +e.target.value / 100}})}
                        />
                        <span className="text-gray-500">%</span>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">Estimated % of Social Security, pension, and other income subject to taxes</p>
                    </div>
                  </div>
                  <div className="mt-6">
                    <label className="block text-sm text-gray-600 mb-2">Effective Tax Rate</label>
                    <div className="flex items-center gap-2 max-w-xs">
                      <input 
                        type="number" 
                        step="1"
                        className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                        value={scenario.taxes.effective_rate * 100}
                        onChange={e => setScenario({...scenario, taxes: {...scenario.taxes, effective_rate: +e.target.value / 100}})}
                      />
                      <span className="text-gray-500">%</span>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">Effective tax rate for taxable portfolio withdrawals and retirement income</p>
                  </div>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-4">Special Withdrawals</h3>
                  <p className="text-sm text-gray-600 mb-4">Irregular withdrawals from your portfolio (e.g., purchase vacation home).</p>
                  {scenario.toys.map((toy, idx) => (
                    <div key={idx} className="mb-3 grid grid-cols-3 gap-3">
                      <div>
                        <input 
                          type="number" 
                          placeholder="Age"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                          value={toy.age}
                          onChange={e => updateToy(idx, {age: +e.target.value})}
                        />
                      </div>
                      <div>
                        <input 
                          type="number" 
                          placeholder="Amount"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                          value={toy.amount}
                          onChange={e => updateToy(idx, {amount: +e.target.value})}
                        />
                      </div>
                      <div>
                        <input 
                          type="text" 
                          placeholder="Description"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                          value={toy.description}
                          onChange={e => updateToy(idx, {description: e.target.value})}
                        />
                      </div>
                    </div>
                  ))}
                  <button 
                    onClick={() => setScenario({...scenario, toys: [...scenario.toys, {age: 60, amount: 50000, description: ""}]})}
                    className="text-blue-600 hover:text-blue-700 font-medium"
                  >
                    + Add
                  </button>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'settings' && (
            <div>
              <h2 className="text-2xl font-semibold text-gray-900 mb-2">Settings</h2>
              <p className="text-gray-600 mb-8">Investment return, volatility, and other statistical settings.</p>

              <div className="space-y-8">
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-4">Capital Market Assumptions</h3>
                  <p className="text-sm text-gray-600 mb-4">
                    Specify the expected return, volatility (standard deviation), and correlation coefficient for all asset classes.
                    <span className="italic font-medium"> We advise caution when deviating from the default assumptions.</span>
                  </p>

                  {/* Crypto Presets */}
                  <div className="mb-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
                    <div className="text-sm font-medium text-gray-700 mb-3">Crypto Settings (Based on 10-Year Bitcoin History)</div>
                    <div className="flex gap-4">
                      <label className="flex items-center gap-2">
                        <input 
                          type="radio" 
                          name="cryptoPreset" 
                          className="text-blue-600"
                          checked={
                            Math.abs(scenario.cma.exp_ret.crypto - 0.20) < 0.01 && 
                            Math.abs(scenario.cma.vol.crypto - 0.80) < 0.01
                          }
                          onChange={() => setScenario({
                            ...scenario, 
                            cma: {
                              ...scenario.cma,
                              exp_ret: {...scenario.cma.exp_ret, crypto: 0.20},
                              vol: {...scenario.cma.vol, crypto: 0.80}
                            }
                          })}
                        />
                        <span className="text-sm">Conservative (20% / 80%)</span>
                      </label>
                      <label className="flex items-center gap-2">
                        <input 
                          type="radio" 
                          name="cryptoPreset" 
                          className="text-blue-600"
                          checked={
                            Math.abs(scenario.cma.exp_ret.crypto - 0.35) < 0.01 && 
                            Math.abs(scenario.cma.vol.crypto - 1.50) < 0.01
                          }
                          onChange={() => setScenario({
                            ...scenario, 
                            cma: {
                              ...scenario.cma,
                              exp_ret: {...scenario.cma.exp_ret, crypto: 0.35},
                              vol: {...scenario.cma.vol, crypto: 1.50}
                            }
                          })}
                        />
                        <span className="text-sm">Moderate (35% / 150%)</span>
                      </label>
                      <label className="flex items-center gap-2">
                        <input 
                          type="radio" 
                          name="cryptoPreset" 
                          className="text-blue-600"
                          checked={
                            Math.abs(scenario.cma.exp_ret.crypto - 0.47) < 0.01 && 
                            Math.abs(scenario.cma.vol.crypto - 2.00) < 0.01
                          }
                          onChange={() => setScenario({
                            ...scenario, 
                            cma: {
                              ...scenario.cma,
                              exp_ret: {...scenario.cma.exp_ret, crypto: 0.47},
                              vol: {...scenario.cma.vol, crypto: 2.00}
                            }
                          })}
                        />
                        <span className="text-sm">Historical (47% / 200%)</span>
                      </label>
                    </div>
                  </div>

                  <div className="grid grid-cols-6 gap-4 text-center">
                    <div></div>
                    <div className="text-sm font-medium text-gray-700">Stocks</div>
                    <div className="text-sm font-medium text-gray-700">Bonds</div>
                    <div className="text-sm font-medium text-gray-700">Crypto</div>
                    <div className="text-sm font-medium text-gray-700">CDs</div>
                    <div className="text-sm font-medium text-gray-700">Cash</div>
                  </div>

                  <div className="grid grid-cols-6 gap-4 items-center mt-4">
                    <div className="text-sm text-gray-600">Expected Return</div>
                    {['stocks', 'bonds', 'crypto', 'cds', 'cash'].map(asset => (
                      <div key={asset} className="flex items-center gap-1">
                        <input 
                          type="number" 
                          step="0.1"
                          className="w-full px-2 py-2 text-center border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                          value={(scenario.cma.exp_ret[asset] * 100).toFixed(1)}
                          onChange={e => setScenario({
                            ...scenario, 
                            cma: {
                              ...scenario.cma,
                              exp_ret: {...scenario.cma.exp_ret, [asset]: +e.target.value / 100}
                            }
                          })}
                        />
                        <span className="text-gray-500 text-sm">%</span>
                      </div>
                    ))}
                  </div>

                  <div className="grid grid-cols-6 gap-4 items-center mt-4">
                    <div className="text-sm text-gray-600">Standard Deviation</div>
                    {['stocks', 'bonds', 'crypto', 'cds', 'cash'].map(asset => (
                      <div key={asset} className="flex items-center gap-1">
                        <input 
                          type="number" 
                          step="0.1"
                          className="w-full px-2 py-2 text-center border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                          value={(scenario.cma.vol[asset] * 100).toFixed(1)}
                          onChange={e => setScenario({
                            ...scenario, 
                            cma: {
                              ...scenario.cma,
                              vol: {...scenario.cma.vol, [asset]: +e.target.value / 100}
                            }
                          })}
                        />
                        <span className="text-gray-500 text-sm">%</span>
                      </div>
                    ))}
                  </div>

                  <button 
                    onClick={() => {
                      setScenario({
                        ...scenario, 
                        cma: {
                          ...scenario.cma,
                          exp_ret: {stocks: 0.08, bonds: 0.045, crypto: 0.20, cds: 0.04, cash: 0.03},
                          vol: {stocks: 0.17, bonds: 0.07, crypto: 0.80, cds: 0.02, cash: 0.01},
                        }
                      });
                    }}
                    className="mt-6 px-6 py-2.5 bg-white text-blue-600 border-2 border-blue-600 rounded-lg font-medium hover:bg-blue-50 transition-colors"
                  >
                    Restore Defaults
                  </button>
                </div>

                <div>
                  <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-4">Fat Tails</h3>
                  <p className="text-sm text-gray-600 mb-4">
                    Markets in real life are more volatile than indicated by statistical models traditionally used to simulate investment performance (e.g., the normal bell curve). 
                    By default, our model fattens the tails of the probability distribution to more realistically replicate market volatility. 
                    <span className="italic font-medium"> We strongly suggest that you keep Fat Tails switched on.</span>
                  </p>
                  
                  <label className="flex items-center gap-3 mb-6">
                    <input 
                      type="checkbox" 
                      className="w-5 h-5 text-blue-600 rounded"
                      checked={scenario.cma.fat_tails}
                      onChange={e => setScenario({...scenario, cma: {...scenario.cma, fat_tails: e.target.checked}})}
                    />
                    <span className="text-sm font-medium">Include Fat Tails</span>
                  </label>

                  {scenario.cma.fat_tails && (
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm text-gray-600 mb-2">Magnitude of tail events</label>
                        <div className="flex gap-2">
                          <button 
                            onClick={() => setScenario({...scenario, cma: {...scenario.cma, tail_boost: 0.08}})}
                            className={`flex-1 px-4 py-2 rounded-lg border-2 ${scenario.cma.tail_boost === 0.08 ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-700 border-gray-300'}`}
                          >
                            Standard
                          </button>
                          <button 
                            onClick={() => setScenario({...scenario, cma: {...scenario.cma, tail_boost: 0.16}})}
                            className={`flex-1 px-4 py-2 rounded-lg border-2 ${scenario.cma.tail_boost === 0.16 ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-700 border-gray-300'}`}
                          >
                            Extreme
                          </button>
                        </div>
                      </div>

                      <div>
                        <label className="block text-sm text-gray-600 mb-2">Frequency of tail events</label>
                        <div className="flex gap-2">
                          <button 
                            onClick={() => setScenario({...scenario, cma: {...scenario.cma, tail_prob: 0.06}})}
                            className={`flex-1 px-4 py-2 rounded-lg border-2 ${scenario.cma.tail_prob === 0.06 ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-700 border-gray-300'}`}
                          >
                            Standard
                          </button>
                          <button 
                            onClick={() => setScenario({...scenario, cma: {...scenario.cma, tail_prob: 0.12}})}
                            className={`flex-1 px-4 py-2 rounded-lg border-2 ${scenario.cma.tail_prob === 0.12 ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-700 border-gray-300'}`}
                          >
                            High
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Save Modal */}
      {saveModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-96">
            <h3 className="text-lg font-semibold mb-4">Save Scenario</h3>
            <input
              type="text"
              placeholder="Enter scenario name"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 mb-4"
              value={scenarioName}
              onChange={(e) => setScenarioName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') saveScenario();
              }}
            />
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => {
                  setSaveModalOpen(false);
                  setScenarioName('');
                }}
                className="px-4 py-2 text-gray-600 hover:text-gray-800"
              >
                Cancel
              </button>
              <button
                onClick={saveScenario}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}
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