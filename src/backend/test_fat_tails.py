#!/usr/bin/env python3
"""
Test script to compare different fat-tail implementations.
Run this to determine which engine produces the best results.
"""

import sys
import time
import json
import requests
from typing import Dict, Any

# Test configuration
BASE_URL = "http://localhost:8020"
TEST_SCENARIOS = [
    {
        "name": "Well-Funded",
        "current_age": 55,
        "end_age": 90,
        "accounts": [
            {"kind": "401k", "balance": 1000000, "stocks": 0.6, "bonds": 0.4},
            {"kind": "Taxable", "balance": 500000, "stocks": 0.5, "bonds": 0.5}
        ],
        "spending": {
            "base_annual": 60000,
            "reduced_annual": 60000,
            "reduce_at_age": 65,
            "inflation": 0.025
        }
    },
    {
        "name": "Marginal",
        "current_age": 45,
        "end_age": 90,
        "accounts": [
            {"kind": "401k", "balance": 800000, "stocks": 0.7, "bonds": 0.3},
            {"kind": "Taxable", "balance": 400000, "stocks": 0.6, "bonds": 0.3, "cash": 0.1},
            {"kind": "IRA", "balance": 300000, "stocks": 0.6, "bonds": 0.4}
        ],
        "consulting": {
            "start_age": 46,
            "years": 10,
            "start_amount": 100000,
            "growth": 0.02
        },
        "spending": {
            "base_annual": 100000,
            "reduced_annual": 70000,
            "reduce_at_age": 65,
            "inflation": 0.025
        }
    }
]


def test_scenario(scenario: Dict[str, Any], fat_tails: bool = False, 
                  engine: str = None) -> Dict[str, Any]:
    """Test a single scenario configuration."""
    # Add fat-tail configuration
    scenario["cma"] = {
        "fat_tails": fat_tails,
        "t_df": 12,  # Use moderate df
        "tail_boost": 1.0,
        "tail_prob": 0.020
    }
    scenario["sims"] = 10000
    
    # Note: In production, we'd pass engine selection via header or query param
    # For now, it uses the default from config
    
    start_time = time.time()
    response = requests.post(f"{BASE_URL}/api/simulate", json=scenario)
    elapsed = time.time() - start_time
    
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        return None
    
    result = response.json()
    result["elapsed_time"] = elapsed
    return result


def compare_engines():
    """Compare different fat-tail implementations."""
    print("=" * 70)
    print("FAT-TAIL ENGINE COMPARISON TEST")
    print("=" * 70)
    print("Testing different implementations to find optimal configuration")
    print("Target: 2-5% reduction in success rate with fat-tails enabled\n")
    
    for scenario_config in TEST_SCENARIOS:
        scenario_name = scenario_config["name"]
        print(f"\n{'='*70}")
        print(f"SCENARIO: {scenario_name}")
        print(f"{'='*70}")
        
        # Test without fat-tails (baseline)
        print("\n1. BASELINE (No Fat-Tails)")
        baseline = test_scenario(scenario_config.copy(), fat_tails=False)
        if baseline:
            print(f"   Success Rate: {baseline['success_prob']*100:.1f}%")
            print(f"   Median End Balance: ${baseline['end_balance_percentiles']['p50']:,.0f}")
            print(f"   Computation Time: {baseline['elapsed_time']:.2f}s")
        
        # Test with fat-tails (current engine)
        print("\n2. FAT-TAILS (Current Implementation)")
        fattail = test_scenario(scenario_config.copy(), fat_tails=True)
        if fattail:
            print(f"   Success Rate: {fattail['success_prob']*100:.1f}%")
            print(f"   Median End Balance: ${fattail['end_balance_percentiles']['p50']:,.0f}")
            print(f"   Computation Time: {fattail['elapsed_time']:.2f}s")
            
            if baseline:
                impact = (fattail['success_prob'] - baseline['success_prob']) * 100
                print(f"   Impact: {impact:+.1f}% (absolute)")
                
                # Check if within target range
                if -5 <= impact <= -2:
                    print("   ✅ WITHIN TARGET RANGE")
                elif impact > -2:
                    print("   ⚠️  TOO MILD")
                else:
                    print("   ❌ TOO EXTREME")
        
        # Note: To test different engines, modify config.DEFAULT_FAT_TAIL_ENGINE
        # and restart the server, then run this test again
        
    print("\n" + "=" * 70)
    print("RECOMMENDATIONS")
    print("=" * 70)
    print("1. If impact is too extreme (< -5%): Reduce jump parameters")
    print("2. If impact is too mild (> -2%): Increase jump frequency slightly")
    print("3. Test both optionB (log-safe) and research (arithmetic) engines")
    print("4. Select engine with best balance of accuracy and performance")


def test_annual_returns():
    """Analyze the distribution of annual returns."""
    print("\n" + "=" * 70)
    print("ANNUAL RETURN DISTRIBUTION TEST")
    print("=" * 70)
    
    # Simple 1-year test to check return distributions
    test_scenario = {
        "name": "ReturnTest",
        "current_age": 55,
        "end_age": 56,  # Just 1 year
        "accounts": [
            {"kind": "401k", "balance": 1000000, "stocks": 1.0}  # 100% stocks
        ],
        "spending": {"base_annual": 0, "reduced_annual": 0, "reduce_at_age": 65},
        "cma": {"fat_tails": True, "t_df": 12},
        "sims": 50000
    }
    
    result = test_scenario(test_scenario, fat_tails=True)
    if result:
        # The median end balance tells us about the return distribution
        median = result['end_balance_percentiles']['p50']
        p20 = result['end_balance_percentiles']['p20']
        p80 = result['end_balance_percentiles']['p80']
        
        # Calculate implied returns
        median_return = (median / 1000000) - 1
        p20_return = (p20 / 1000000) - 1
        p80_return = (p80 / 1000000) - 1
        
        print(f"\nImplied Annual Returns (from $1M starting):")
        print(f"  P20: {p20_return*100:.1f}%")
        print(f"  P50: {median_return*100:.1f}%")
        print(f"  P80: {p80_return*100:.1f}%")
        
        print(f"\nTarget (approximate):")
        print(f"  Mean: ~8% (stocks)")
        print(f"  P20: ~-10% to -15%")
        print(f"  P50: ~7% to 9%")
        print(f"  P80: ~25% to 30%")


if __name__ == "__main__":
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code != 200:
            print("Error: Server not responding correctly")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to server at", BASE_URL)
        print("Make sure the FastAPI server is running: uvicorn main:app --reload --port 8020")
        sys.exit(1)
    
    # Run tests
    compare_engines()
    test_annual_returns()
    
    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
    print("\nNext Steps:")
    print("1. Modify config.DEFAULT_FAT_TAIL_ENGINE to test different engines")
    print("2. Restart server and run this test again")
    print("3. Compare results and select best engine")
    print("4. Fine-tune parameters as needed")