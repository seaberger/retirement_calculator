"""
Application configuration and constants.
"""

from typing import List

# Asset classes used throughout the application
ASSETS: List[str] = ["stocks", "bonds", "crypto", "cds", "cash"]

# API configuration
API_VERSION = "1.0.0"
API_TITLE = "Retirement Calculator API"
API_DESCRIPTION = "Monte Carlo simulation engine for retirement planning with fat-tail modeling"

# CORS configuration
CORS_ORIGINS = ["*"]  # In production, replace with specific origins
CORS_CREDENTIALS = True
CORS_METHODS = ["*"]
CORS_HEADERS = ["*"]

# Simulation defaults
DEFAULT_SIMULATIONS = 10000
MIN_SIMULATIONS = 500
MAX_SIMULATIONS = 100000

# Fat-tail engine selection
# Options: "optionB" (log-safe), "research" (arithmetic), "current" (existing)
DEFAULT_FAT_TAIL_ENGINE = "optionB"

# Performance settings
USE_PARALLEL_PROCESSING = False  # Set to True if using multiprocessing
CHUNK_SIZE = 1000  # For batched processing

# Logging configuration
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"