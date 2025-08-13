"""
FastAPI application for retirement calculator with Monte Carlo simulation.
"""

# Standard library imports
import json

# Third-party imports
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Local application imports
try:
    # Try relative imports (when running as module)
    from .config import (
        API_TITLE, API_DESCRIPTION, API_VERSION,
        CORS_ORIGINS, CORS_CREDENTIALS, CORS_METHODS, CORS_HEADERS
    )
    from .database import engine, ScenarioRow, get_session
    from .models import (
        Scenario, Account, ConsultingLadder, Spending, 
        IncomeStream, LumpEvent, ToyPurchase
    )
    from .monte_carlo import Engine
except ImportError:
    # Fall back to absolute imports (when running directly)
    from config import (
        API_TITLE, API_DESCRIPTION, API_VERSION,
        CORS_ORIGINS, CORS_CREDENTIALS, CORS_METHODS, CORS_HEADERS
    )
    from database import engine, ScenarioRow, get_session
    from models import (
        Scenario, Account, ConsultingLadder, Spending, 
        IncomeStream, LumpEvent, ToyPurchase
    )
    from monte_carlo import Engine


# ============================
# FastAPI Application
# ============================
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=CORS_CREDENTIALS,
    allow_methods=CORS_METHODS,
    allow_headers=CORS_HEADERS,
)


# ============================
# API Routes
# ============================
@app.get("/")
def root():
    """Root endpoint with API information."""
    return {
        "message": API_TITLE,
        "version": API_VERSION,
        "docs": "Visit /docs for API documentation"
    }


@app.get("/api/default_scenario")
def default_scenario() -> Scenario:
    """Get a default example scenario for testing."""
    return Scenario(
        name="Example",
        current_age=45,
        end_age=90,
        accounts=[
            Account(kind="401k", balance=800_000, stocks=0.7, bonds=0.3),
            Account(kind="Taxable", balance=400_000, stocks=0.6, bonds=0.3, cash=0.1),
            Account(kind="IRA", balance=300_000, stocks=0.6, bonds=0.4),
        ],
        consulting=ConsultingLadder(
            start_age=46, 
            years=9, 
            start_amount=100_000, 
            growth=0.02
        ),
        spending=Spending(
            base_annual=80_000, 
            reduced_annual=60_000, 
            reduce_at_age=65, 
            inflation=0.025
        ),
        incomes=[
            IncomeStream(start_age=55, end_age=60, monthly=2000, cola=0.02),  # Post-retirement consulting
            IncomeStream(start_age=67, end_age=90, monthly=3000, cola=0.02),  # Social Security
            IncomeStream(start_age=67, end_age=90, monthly=2000, cola=0.02),  # Spouse Social Security
        ],
        lumps=[
            LumpEvent(age=65, amount=200_000, description="Home downsizing"),
        ],
        toys=[
            ToyPurchase(age=65, amount=30_000, description="Dream vacation")
        ],
    )


@app.post("/api/simulate")
def simulate(scenario: Scenario):
    """
    Run Monte Carlo simulation for a given scenario.
    
    Args:
        scenario: The retirement scenario to simulate
        
    Returns:
        Simulation results with percentiles and success probability
    """
    try:
        # Optional: Allow selecting fat-tail engine via query param or header
        # For now, use the default from config
        eng = Engine(scenario)
        result = eng.run()
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/scenarios")
def list_scenarios():
    """List all saved scenarios."""
    with get_session() as s:
        rows = s.query(ScenarioRow).all()
        return [{"id": r.id, "name": r.name} for r in rows]


@app.get("/api/scenarios/{sid}")
def get_scenario(sid: int):
    """Get a specific saved scenario by ID."""
    with get_session() as s:
        row = s.get(ScenarioRow, sid)
        if not row:
            raise HTTPException(404, "Scenario not found")
        return json.loads(row.payload)


@app.post("/api/scenarios")
def save_scenario(scenario: Scenario):
    """Save or update a scenario."""
    with get_session() as s:
        # Upsert by name
        row = s.query(ScenarioRow).filter_by(name=scenario.name).first()
        if row is None:
            row = ScenarioRow(name=scenario.name, payload=scenario.model_dump_json())
            s.add(row)
        else:
            row.payload = scenario.model_dump_json()
        s.commit()
        return {"id": row.id, "name": row.name}


@app.delete("/api/scenarios/{sid}")
def delete_scenario(sid: int):
    """Delete a saved scenario."""
    with get_session() as s:
        row = s.get(ScenarioRow, sid)
        if not row:
            raise HTTPException(404, "Scenario not found")
        s.delete(row)
        s.commit()
        return {"message": "Scenario deleted", "id": sid}


# Optional: Health check endpoint
@app.get("/health")
def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "service": API_TITLE}