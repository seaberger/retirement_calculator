# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Retirement Monte Carlo Simulator** with a Python FastAPI backend and React frontend. The application runs Monte Carlo simulations to model retirement portfolio outcomes with configurable parameters for spending, income, taxes, and market assumptions.

## Architecture

### Backend (Modular Structure)
- **FastAPI** server (`src/backend/main.py`) - API routes only
- **Monte Carlo Package** (`src/backend/monte_carlo/`)
  - `engine.py` - Core simulation engine with pluggable fat-tail models
  - `fat_tails_kou_logsafe.py` - Production fat-tail implementation (2-5% impact)
  - `fat_tails_research.py` - Alternative implementation for comparison
- **Data Models** (`src/backend/models.py`) - Pydantic schemas
- **Database** (`src/backend/database.py`) - SQLite configuration
- **Configuration** (`src/backend/config.py`) - Application settings

#### Key Features:
- Multi-asset allocation (stocks, bonds, crypto, CDs, cash)
- **Kou Log-Safe Fat-Tail Algorithm** - Realistic market dynamics
  - Works in log-space to prevent impossible returns
  - Calibrated for 2-5% impact on success rates
  - Student-t body with Kou double-exponential jumps
- Correlated asset returns with proper covariance
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
- **Kou Log-Safe Fat-Tail Implementation**:
  - Default engine set in `config.py`: `DEFAULT_FAT_TAIL_ENGINE = "kou_logsafe"`
  - Performs all calculations in log-space to prevent <-100% returns
  - Uses pilot simulation (40,000 runs) for mean correction
  - Calibrated to achieve 2-5% reduction in success rates (industry standard)
  - See `docs/kou_logsafe_test_results.md` for full test results
- Database file `retire.db` is stored in the `data/` directory at the project root

## Testing Fat-Tail Implementations

Run the comprehensive comparison test:
```bash
uv run python temp_tests/compare_fat_tail_engines.py
```

This will test all three engines (kou_logsafe, research, current) and show which achieves the target 2-5% impact.