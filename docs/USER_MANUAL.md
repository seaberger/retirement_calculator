# Retirement Calculator User Manual

## Table of Contents
1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Service Management](#service-management)
4. [Using the Web Interface](#using-the-web-interface)
5. [API Documentation](#api-documentation)
6. [Configuration Options](#configuration-options)
7. [Understanding the Simulations](#understanding-the-simulations)
8. [Troubleshooting](#troubleshooting)

---

## Overview

The Retirement Calculator is a sophisticated Monte Carlo simulation tool that helps you model retirement portfolio outcomes. It runs 10,000+ simulations to provide probabilistic insights into your financial future, accounting for market volatility, spending patterns, income streams, and taxes.

### Key Features
- **Monte Carlo Simulations**: 10,000 scenarios with realistic market dynamics
- **Multi-Asset Portfolios**: Stocks, bonds, crypto, CDs, and cash allocations
- **Income Modeling**: Social Security, pensions, consulting, and other income
- **Tax Calculations**: Effective tax rate modeling for withdrawals
- **Fat-Tail Events**: Realistic modeling of market crashes and extreme events
- **Interactive Visualization**: Real-time charts showing portfolio paths

---

## Getting Started

### Prerequisites
- Python 3.9+ with `uv` package manager
- Node.js 16+ with npm
- macOS or Linux (Windows with WSL)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/seaberger/retirement_calculator.git
   cd retirement_calculator
   ```

2. **Install Python dependencies**:
   ```bash
   uv venv .venv
   uv pip install -r requirements.txt
   ```

3. **Install frontend dependencies**:
   ```bash
   cd frontend
   npm install
   cd ..
   ```

---

## Service Management

### Quick Start

The easiest way to manage services is using the provided scripts:

```bash
# Start both services (if not running)
./check_services.sh

# Stop all services
./stop_services.sh

# Restart everything
./restart_services.sh
```

### Service Scripts Explained

#### `check_services.sh` - Health Check & Auto-Start
This script is your main tool for ensuring services are running properly.

**What it does**:
1. Checks if API is running on port 8020
2. Verifies API health endpoint responds
3. Checks if frontend is running on port 5177
4. Automatically starts any service that's not running
5. Shows service URLs and status summary

**Output example**:
```
=========================================
   Retirement Calculator Service Check   
=========================================

✓ API is running and healthy on port 8020
✓ Frontend is running on port 5177

Service Summary:
✓ API:
  - URL: http://localhost:8020
  - Docs: http://localhost:8020/docs
  - Health: http://localhost:8020/health

✓ Frontend:
  - URL: http://localhost:5177
```

#### `stop_services.sh` - Clean Shutdown
Stops both services cleanly by killing processes on their respective ports.

**What it does**:
1. Finds processes using ports 8020 and 5177
2. Terminates them gracefully
3. Confirms services are stopped

#### `restart_services.sh` - Full Restart
Performs a complete restart of both services.

**What it does**:
1. Calls `stop_services.sh` to stop everything
2. Waits 2 seconds for clean shutdown
3. Calls `check_services.sh` to start fresh instances

### Manual Service Management

If you prefer manual control:

**Start API backend**:
```bash
cd src/backend
uv run uvicorn main:app --reload --port 8020
```

**Start frontend**:
```bash
cd frontend
npm run dev
```

**Check if services are running**:
```bash
# Check API
curl http://localhost:8020/health

# Check frontend
curl http://localhost:5177
```

---

## Using the Web Interface

### Accessing the Application

1. Start the services: `./check_services.sh`
2. Open your browser to: **http://localhost:5177**

### Main Interface Sections

#### 1. Basic Information
- **Current Age**: Your age today (e.g., 55)
- **End Age**: Age to simulate until (e.g., 95)
- **Effective Tax Rate**: Your estimated tax rate on withdrawals (e.g., 0.12 for 12%)

#### 2. Accounts
Add your investment accounts with their current balances and asset allocations:

- **Balance**: Current account value
- **Asset Allocation** (must sum to 100%):
  - Stocks %
  - Bonds %
  - Crypto %
  - CDs %
  - Cash %

**Example**: 
- 401(k): $800,000 (60% stocks, 40% bonds)
- IRA: $400,000 (70% stocks, 30% bonds)
- Brokerage: $300,000 (50% stocks, 30% bonds, 20% cash)

#### 3. Spending
Configure your retirement spending:

- **Pre-Retirement**: Annual spending before retirement
- **Post-Retirement**: Annual spending after retirement
- **COLA** (Cost of Living Adjustment): Annual inflation rate
- **Retirement Age**: When you plan to retire

#### 4. Income Streams
Add various income sources:

- **Social Security**: Starting age and annual amount
- **Pensions**: Multiple pensions with different start ages
- **Other Income**: Rental income, annuities, etc.

Each income stream can have:
- Start age
- Annual amount
- Years of duration (0 = lifetime)
- COLA adjustment rate

#### 5. Special Events

**Lump Sums** (one-time cash inflows):
- Home sale proceeds
- Inheritance
- Business sale
- 401(k) rollovers

**Toy Purchases** (large discretionary spending):
- Boat, RV, or vacation home
- Major renovations
- Dream vacations

#### 6. Market Assumptions

Configure expected market returns and volatility:

- **Stocks**: Mean return and standard deviation
- **Bonds**: Mean return and standard deviation  
- **Crypto**: Mean return and standard deviation
- **CDs**: Fixed rate
- **Cash**: Fixed rate (usually lowest)

**Fat-Tail Settings** (advanced):
- **Enabled**: Turn on realistic extreme events
- **Magnitude**: Standard or Extreme
- **Frequency**: Standard or High
- **Skew**: Negative, Neutral, or Positive

#### 7. Black Swan Events
Model extreme market crashes:

- **Enabled**: Activate crash modeling
- **Probability**: Annual chance (e.g., 3.33% = once per 30 years)
- **Age Range**: When you're most vulnerable
- **Portfolio Drop**: Severity of crash (e.g., 50%)

### Running Simulations

1. Configure all parameters
2. Click **"Run Simulation"**
3. Wait ~2-3 seconds for 10,000 simulations
4. Review results

### Understanding Results

#### Success Metrics
- **Success Probability**: Percentage of simulations where money doesn't run out
- **Median Net Worth**: Expected portfolio value at end age
- **Portfolio Balance Distribution**: 20th, 50th, and 80th percentiles

#### Breakdown By Age Table
Shows portfolio values at 5-year intervals:
- **Unlucky** (20th percentile): Bad market outcomes
- **Median** (50th percentile): Expected outcome
- **Lucky** (80th percentile): Good market outcomes

#### Portfolio Paths Chart
Visual representation showing:
- 100 randomly selected simulation paths
- Color coding: Green (successful), Red (failed)
- Y-axis: Portfolio value over time
- X-axis: Age progression

### Saving and Loading Scenarios

**Save a scenario**:
1. Configure all parameters
2. Enter a name in "Scenario Name"
3. Click **"Save Scenario"**

**Load a scenario**:
1. Click **"View Saved Scenarios"**
2. Select from the list
3. Click **"Load"** next to desired scenario

---

## API Documentation

### Base URL
```
http://localhost:8020
```

### Interactive API Docs
Visit **http://localhost:8020/docs** for interactive Swagger documentation.

### Key Endpoints

#### Health Check
```http
GET /health
```
Returns service status.

#### Get Default Scenario
```http
GET /api/default_scenario
```
Returns a pre-configured baseline scenario for editing.

#### Run Simulation
```http
POST /api/simulate
```
**Request Body**: Complete scenario configuration (JSON)
**Response**: Simulation results with percentiles and paths

**Example Request**:
```json
{
  "current_age": 55,
  "end_age": 95,
  "accounts": [
    {
      "balance": 1500000,
      "stocks": 0.6,
      "bonds": 0.4,
      "crypto": 0,
      "cds": 0,
      "cash": 0
    }
  ],
  "spending": {
    "base_amount": 100000,
    "retirement_amount": 80000,
    "cola": 0.03,
    "retirement_age": 65
  },
  "income_streams": [
    {
      "name": "Social Security",
      "start_age": 70,
      "amount": 40000,
      "cola": 0.02,
      "years": 0
    }
  ]
}
```

#### Save Scenario
```http
POST /api/scenario/{name}
```
Saves scenario configuration to database.

#### Load Scenario
```http
GET /api/scenario/{name}
```
Retrieves saved scenario by name.

#### List Scenarios
```http
GET /api/scenarios
```
Returns all saved scenario names.

---

## Configuration Options

### Monte Carlo Settings

Located in `src/backend/config.py`:

```python
# Simulation parameters
DEFAULT_N_SIMULATIONS = 10000  # Number of Monte Carlo runs
DEFAULT_FAT_TAIL_ENGINE = "kou_logsafe"  # Fat-tail algorithm

# Performance settings
PARALLEL_PROCESSING = True
MAX_WORKERS = 4
```

### Fat-Tail Parameters

Located in `params/kou_params_v1.json`:
- Controls extreme event modeling
- Calibrated for 2-5% impact on success rates
- Version controlled for reproducibility

### Database Location

SQLite database stored at: `data/retire.db`

---

## Understanding the Simulations

### Monte Carlo Method

The calculator runs 10,000+ independent simulations, each representing a possible future:

1. **Random Market Returns**: Each year gets different returns based on historical patterns
2. **Correlation**: Asset classes move together realistically
3. **Sequence of Returns**: Early losses have bigger impact (sequence risk)
4. **Fat Tails**: Extreme events occur more often than normal distribution predicts

### Key Concepts

#### Success Rate
Percentage of simulations where portfolio lasts until end age without depleting.

#### Percentiles Explained
- **20th percentile**: Only 20% of outcomes were worse (unlucky)
- **50th percentile**: Half better, half worse (median)
- **80th percentile**: Only 20% of outcomes were better (lucky)

#### Fat-Tail Events
Realistic modeling of market extremes:
- **Standard**: ~3% impact on success rate
- **Extreme Magnitude**: Larger crashes when they occur
- **High Frequency**: Crashes happen more often
- **Negative Skew**: More downside than upside risk

### Withdrawal Strategy

The simulator uses a "spend from portfolio" approach:
1. Calculate total spending need
2. Subtract income (Social Security, pensions, etc.)
3. Withdraw remainder from portfolio
4. Apply taxes to withdrawal
5. Rebalance portfolio to target allocation

---

## Troubleshooting

### Common Issues

#### Services Won't Start

**Problem**: Port already in use error
```bash
# Find and kill process on port
lsof -ti:8020 | xargs kill -9
lsof -ti:5177 | xargs kill -9

# Restart services
./restart_services.sh
```

**Problem**: Dependencies not installed
```bash
# Python dependencies
uv pip install -r requirements.txt

# Frontend dependencies
cd frontend && npm install
```

#### Simulation Errors

**Problem**: "Failed to run simulation" error
- Check API is running: `curl http://localhost:8020/health`
- Verify all percentages sum to 100% in asset allocations
- Ensure all required fields are filled

**Problem**: Unrealistic results
- Review market assumptions (are returns too high/low?)
- Check if fat-tail settings are appropriate
- Verify spending isn't exceeding income + safe withdrawal rate

#### Performance Issues

**Problem**: Simulations taking too long
- Default is 10,000 simulations (~2-3 seconds)
- Reduce to 5,000 for faster results (less accurate)
- Check CPU usage - other processes may be interfering

### Log Files

When using service scripts, logs are saved to:
- **API logs**: `api.log`
- **Frontend logs**: `frontend.log`

Check these for detailed error messages:
```bash
tail -f api.log  # Watch API logs
tail -f frontend.log  # Watch frontend logs
```

### Getting Help

1. Check the logs for error messages
2. Verify services are running: `./check_services.sh`
3. Try restarting: `./restart_services.sh`
4. Review this manual's configuration section
5. Check `CLAUDE.md` for technical details
6. Submit issues to: https://github.com/seaberger/retirement_calculator/issues

---

## Advanced Usage

### Running Custom Simulations

You can bypass the UI and call the API directly:

```python
import requests

scenario = {
    "current_age": 55,
    "end_age": 95,
    "n_simulations": 10000,
    # ... full scenario config
}

response = requests.post(
    "http://localhost:8020/api/simulate",
    json=scenario
)

results = response.json()
print(f"Success Rate: {results['success_prob']*100:.1f}%")
```

### Modifying Market Models

Edit `src/backend/monte_carlo/fat_tails_kou_logsafe.py` to adjust:
- Jump parameters
- Correlation matrices
- Asset-specific volatility

### Adding New Features

1. Backend: Add to `src/backend/models.py` and `main.py`
2. Frontend: Modify `frontend/src/App.jsx`
3. Test: Add tests to `tests/` directory
4. Document: Update this manual and `CLAUDE.md`

---

## Security Considerations

### ✅ Current Security Status

**Your financial data is now ENCRYPTED** using industry-standard AES-256 encryption:
- All sensitive scenario data is encrypted at rest in the SQLite database
- Encryption/decryption happens transparently when you use the application
- The encryption key is stored in your `.env` file (keep this secure!)
- Even with database access, data cannot be read without the encryption key

### Protecting Your Data

#### For Personal Use

1. **File System Security**:
   - Keep your computer password-protected
   - Use full-disk encryption (FileVault on Mac, BitLocker on Windows)
   - Don't share the `data/retire.db` file

2. **Network Security**:
   - Only run the application locally (localhost)
   - Don't expose ports 8020 or 5177 to the internet
   - Use a firewall to block external access

3. **Backup Security**:
   - Encrypt any backups of the database
   - Store backups securely (encrypted cloud storage)
   - Don't commit the database to version control

#### Encryption Details

The application uses:
- **Fernet encryption** (symmetric cryptography)
- **PBKDF2** key derivation with 100,000 iterations
- **AES-256** in CBC mode
- **Base64** encoding for storage

### Quick Security Checklist

For personal use, ensure:
- [x] Database encryption is enabled (check `.env` file)
- [ ] `.env` file is backed up securely
- [ ] Computer has password protection
- [ ] Full-disk encryption is enabled
- [ ] Services only accessible on localhost
- [ ] Database file has restricted permissions
- [ ] `.env` file is in `.gitignore` (never commit!)
- [ ] Regular encrypted backups of both database and `.env`

### Setting File Permissions

Restrict database access to your user only:

```bash
# Restrict database file permissions
chmod 600 data/retire.db

# Restrict entire data directory
chmod 700 data/
```

### What Data is Stored

The SQLite database stores:
- Account balances and allocations
- Income and spending projections
- Simulation parameters and results
- Saved scenario configurations

**Note**: No passwords or authentication credentials are stored (current version has no user system).

### Security Implementation

**Current (v1.1)**: 
- ✅ Single-user, local-only application
- ✅ **Encrypted SQLite database (Fernet/AES-256)**
- ✅ Transparent encryption/decryption
- ✅ Environment-based key management

**Future Enhancements (v2.0)**:
- User authentication system
- Multi-user support with per-user encryption
- HTTPS for all communications
- Audit logging

**Future (v3.0)**:
- Multi-factor authentication
- Role-based access control
- Audit logging
- Compliance features (GDPR, CCPA)

### Reporting Security Issues

If you discover a security vulnerability:
1. **Do not** create a public GitHub issue
2. Email security concerns to the maintainer
3. Include steps to reproduce the issue
4. Allow time for a fix before disclosure

---

## Appendix

### Keyboard Shortcuts
- **Refresh page**: Cmd+R (Mac) / Ctrl+R (Windows)
- **Open developer tools**: Cmd+Option+I (Mac) / F12 (Windows)

### File Structure
```
retirement_calculator/
├── src/
│   ├── backend/          # Python API
│   │   ├── main.py       # FastAPI routes
│   │   ├── models.py     # Data models
│   │   └── monte_carlo/  # Simulation engine
│   └── frontend/         # React app
│       └── src/App.jsx   # Main UI
├── tests/                # Test suite
├── params/               # Configuration files
├── docs/                 # Documentation
├── check_services.sh     # Service management
├── stop_services.sh      # Stop services
├── restart_services.sh   # Restart services
└── docs/
    └── USER_MANUAL.md    # This file
```

### Version Information
- **Current Version**: 1.0.0
- **Last Updated**: 2025-08-13
- **Python**: 3.9+
- **Node.js**: 16+
- **Database**: SQLite 3

---

*For technical documentation and development details, see `CLAUDE.md`*