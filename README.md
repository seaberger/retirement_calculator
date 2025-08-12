# Retirement Monte Carlo Simulator

A full‑stack financial simulation tool for retirement planning, built with **FastAPI** (backend) and **React** (frontend). This platform models multiple account types, asset allocations, consulting income, lump sums, and discretionary purchases — running 10,000 Monte Carlo simulations with fat‑tail events for realistic risk assessment.

## Features
- **Multi‑account portfolio modeling** — 401k, IRA, taxable, cash, crypto, CDs with custom allocations.
- **Correlated Monte Carlo engine** — Student‑t distribution, fat‑tail shocks, correlation matrix.
- **Custom events** — consulting income ladders, lump sums, Social Security, toy purchases.
- **Taxes and spending** — effective‑rate tax model, inflation, reduced spending after target age.
- **Interactive UI** — edit inputs, run simulations, view percentile bands, save scenarios to SQLite.
- **Data persistence** — scenarios saved/loaded from local SQLite database.

## Requirements
- **Backend**: Python 3.9+
- **Frontend**: Node.js 18+
- **Package Manager**: [uv](https://github.com/astral-sh/uv)

## Installation & Setup
### Backend (using uv)
```bash
# Create virtual environment
uv venv .venv

# Install dependencies
uv pip install -r requirements.txt

# Run the backend server
cd src/backend
uv run uvicorn main:app --reload --port 8020
```
Backend runs on http://localhost:8020.

### Frontend
Use the provided `App.jsx` in a Vite React project, or run directly in the ChatGPT Canvas preview.
```bash
npm create vite@latest frontend -- --template react
cd frontend
npm install
# Replace src/App.jsx with provided App.jsx
npm run dev
```
Frontend runs on http://localhost:5173 by default and connects to backend at http://localhost:8020.

## Screenshots

### Personal Information Tab
![Personal Info Tab](screenshots/personal-tab.png)
*Configure your age, retirement status, and income projections. Features include:*
- Retirement toggle (I'm retired / I'm not retired)
- Dynamic retirement age field for pre-retirees
- Regular income with growth projections
- Multiple retirement income streams (Social Security, pensions, etc.)

### Simulation Results
![Simulation Results](screenshots/results-view.png)
*View Monte Carlo simulation results with:*
- Portfolio balance projection chart showing median and confidence bands
- Lucky (80th percentile) vs Unlucky (20th percentile) scenarios
- Detailed age-by-age breakdown table
- Market return analysis across percentiles
- Success probability metrics

## Usage
1. Start backend and frontend.
2. Open frontend in your browser.
3. Adjust inputs: accounts, incomes, lump sums, consulting ladder, toy purchases.
4. Click **Show Me** to generate projections.
5. View median, 20th, and 80th percentile paths with band chart.
6. Save/Load scenarios using the buttons in the Personal tab.

## File Structure
```
backend/
  main.py               # FastAPI backend & simulation engine
  requirements.txt      # Python dependencies
frontend/
  src/App.jsx           # React UI
```

## License
MIT License — free to modify and use.


