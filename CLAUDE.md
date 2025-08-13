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
- **Database Encryption**: All scenario data is encrypted using Fernet (AES-256)
- Encryption key is stored in `.env` file (never commit this!)
- Transparent encryption/decryption via `encrypted_database.py` module

## Service Management

Three scripts are provided for managing the API and frontend services:

```bash
# Check status and auto-start if needed
./check_services.sh

# Stop all services
./stop_services.sh  

# Full restart
./restart_services.sh
```

Services run on:
- **API**: http://localhost:8020 (docs at /docs)
- **Frontend**: http://localhost:5177

## Testing

### Fat-Tail Algorithm Tests
The project includes comprehensive test suite for the Kou Log-Safe fat-tail algorithm:

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test categories
uv run pytest tests/test_fat_tail_impacts.py -v  # Portfolio impact tests
uv run pytest tests/test_parameter_bounds.py -v  # Parameter validation
uv run pytest tests/test_toggle_behavior.py -v   # Toggle determinism
uv run pytest tests/test_annual_distributions.py -v  # Distribution tests
```

### CI/CD Pipeline
GitHub Actions workflow (`.github/workflows/test_fat_tails.yml`) runs on every push and weekly to:
- Test across Python 3.9, 3.10, 3.11
- Verify parameter stability
- Check performance benchmarks (<1.0s for 10,000 simulations)
- Ensure portfolio impacts stay within guardrails

## Recent Updates (2025-08-13)

### Database Encryption Implementation
- **Implemented Fernet encryption** for all sensitive financial data
- **Transparent encryption/decryption** - works seamlessly with existing code
- **Portable solution** - uses pure Python cryptography library (no system dependencies)
- **Environment-based configuration** - encryption key in `.env` file

### Fat-Tail Algorithm Optimization
- **Implemented Kou Log-Safe algorithm** via fractional factorial optimization
- **Achieved target impacts**: Standard -2.9%, Extreme -4.5%, High Frequency -3.9%
- **Added Black Swan coordination** to prevent double-counting extreme events
- **Created comprehensive test suite** with 38 tests and CI guardrails
- **Parameter version control** in `params/kou_params_v1.json`

### Frontend Improvements
- **Dynamic age breakdown table**: Now starts at first 5-year multiple after user's current age
- Previously hardcoded to [70, 75, 80, 85, 90], now dynamically calculated

### Project Structure
- Modularized Monte Carlo engine into `src/backend/monte_carlo/` package
- Separated models, database, and config from main.py
- Added test infrastructure in `tests/` directory
- Created parameter versioning in `params/` directory

## Known Configuration

### Dependencies (requirements.txt)
- fastapi, uvicorn, numpy, pydantic, SQLAlchemy
- scipy, tabulate (for optimization)
- pytest, pytest-cov (for testing)

### Frontend (package.json expected):
```bash
cd frontend
npm install  # Install dependencies
npm run dev  # Start development server
```

## Important Notes

- **Always use `uv` for Python package management** (not pip directly)
- **Fat-tail impact target**: 2-5% reduction in portfolio success rate
- **Default simulation count**: 10,000 (configurable via n_simulations)
- **Database location**: `data/retire.db` (SQLite)
- **Test coverage requirement**: Minimum 90% for monte_carlo package