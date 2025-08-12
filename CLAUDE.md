# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Retirement Monte Carlo Simulator** with a Python FastAPI backend and React frontend. The application runs Monte Carlo simulations to model retirement portfolio outcomes with configurable parameters for spending, income, taxes, and market assumptions.

## Architecture

### Backend (`src/backend/main.py`)
- **FastAPI** server with SQLite database for scenario persistence
- **Monte Carlo engine** that simulates portfolio trajectories with:
  - Multi-asset allocation (stocks, bonds, crypto, CDs, cash)
  - Fat-tail market returns using Student-t distribution
  - Correlated asset returns
  - Tax calculations (effective rate model)
  - Income streams, lump sums, and spending patterns

### Frontend (`src/frontend/App.jsx`)
- **Single-file React application** with Tailwind CSS
- **Recharts** for portfolio path visualization
- Real-time scenario editing and simulation execution
- Connects to backend at `http://localhost:8020`

## Development Commands

### Backend Setup with uv
```bash
# Create virtual environment (if not already created)
uv venv .venv

# Install dependencies using uv
uv pip install -r requirements.txt

# Run the backend server with uv
cd src/backend
uv run uvicorn main:app --reload --port 8020
# Server runs at http://localhost:8020

# To install new packages
uv pip install <package-name>
```

### Frontend
The frontend is a single JSX file designed to run in a React environment with:
- React, Recharts, and Tailwind CSS dependencies
- No build process specified - appears to be for canvas/preview environments

## Key Features & Data Flow

1. **Default Scenario**: GET `/api/default_scenario` returns baseline configuration
2. **Simulation**: POST `/api/simulate` runs Monte Carlo with 10,000 simulations (configurable)
3. **Scenario Management**: Save/load scenarios to SQLite database
4. **Portfolio Modeling**: 
   - Accounts with asset allocations
   - Income streams with COLA adjustments
   - Lump sum events (home sales, rollovers)
   - Toy purchases (large discretionary spending)
   - Consulting income ladder

## Important Implementation Details

- The backend uses **numpy** for vectorized Monte Carlo calculations
- Portfolio returns are computed using weighted asset allocations across all accounts
- Tax model applies effective rates to both income and portfolio withdrawals
- Fat-tail market shocks add asymmetric negative events with configurable probability
- Database file `retire.db` is stored in the `data/` directory at the project root