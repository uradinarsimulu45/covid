#!/usr/bin/env python3
"""
covid_tracker.py

Simple COVID-19 Data Tracker:
- Fetches global and country data from disease.sh public API
- Prints summary (global / selected country)
- Downloads historical time-series and plots new cases over time
- Saves plot as PNG

Usage examples:
    python covid_tracker.py --country India
    python covid_tracker.py --country "United States" --days 180 --saveplot myplot.png
    python covid_tracker.py          # shows global summary and instructions
"""

import argparse
import sys
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

API_BASE = "https://disease.sh/v3/covid-19"

def fetch_global_summary():
    url = f"{API_BASE}/all"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json()

def fetch_country_summary(country):
    url = f"{API_BASE}/countries/{country}"
    r = requests.get(url, timeout=10, params={"strict": True})
    r.raise_for_status()
    return r.json()

def fetch_country_historical(country, days=365):
    # days can be 'all' or an integer
    url = f"{API_BASE}/historical/{country}"
    r = requests.get(url, timeout=10, params={"lastdays": str(days)})
    r.raise_for_status()
    return r.json()

def pretty_print_global(data):
    print("\nGlobal summary:")
    print(f"  Updated: {datetime.utcfromtimestamp(data.get('updated', 0)/1000).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"  Cases: {data.get('cases'):,}")
    print(f"  Today Cases: {data.get('todayCases'):,}")
    print(f"  Deaths: {data.get('deaths'):,}")
    print(f"  Today Deaths: {data.get('todayDeaths'):,}")
    print(f"  Recovered: {data.get('recovered'):,}")
    print(f"  Active: {data.get('active'):,}")
    print(f"  Critical: {data.get('critical'):,}")

def pretty_print_country(data):
    country = data.get("country", "Unknown")
    print(f"\n{country} summary:")
    print(f"  Updated: {datetime.utcfromtimestamp(data.get('updated', 0)/1000).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"  Cases: {data.get('cases'):,} (Today: {data.get('todayCases'):,})")
    print(f"  Deaths: {data.get('deaths'):,} (Today: {data.get('todayDeaths'):,})")
    print(f"  Recovered: {data.get('recovered'):,}")
    print(f"  Active: {data.get('active'):,}")
    print(f"  Tests: {data.get('tests'):,}")
    print(f"  Population: {data.get('population'):,}")

def plot_new_cases(historical_json, savepath=None, country_label="Country"):
    """
    historical_json sample structure:
    {
      "country": "India",
      "timeline": {
         "cases": {"1/22/20": n, "1/23/20": n2, ...},
         "deaths": {...},
         "recovered": {...}
      }
    }
    """
    timeline = historical_json.get("timeline") or historical_json  # API sometimes returns direct timeline for 'all'
    cases = timeline.get("cases")
    if not cases:
        raise ValueError("No 'cases' data in historical data")

    # Convert to DataFrame
    df = pd.Series(cases).rename("cumulative_cases")
    # Parse dates like "1/22/20" -> datetime
    df.index = pd.to_datetime(df.index, format="%m/%d/%y")
    df = df.sort_index()

    # Calculate daily new cases
    new_cases = df.diff().fillna(0)
    # Rolling 7-day average
    new_cases_7d = new_cases.rolling(window=7, min_periods=1).mean()

    plt.figure(figsize=(10, 5))
    plt.plot(new_cases.index, new_cases.values, label="Daily new cases")
    plt.plot(new_cases_7d.index, new_cases_7d.values, label="7-day average")
    plt.title(f"Daily new COVID-19 cases — {country_label}")
    plt.xlabel("Date")
    plt.ylabel("New cases")
    plt.legend()
    plt.tight_layout()

    if savepath:
        plt.savefig(savepath)
        print(f"Saved plot to: {savepath}")
    else:
        plt.show()

def main():
    parser = argparse.ArgumentParser(description="COVID-19 Data Tracker (simple)")
    parser.add_argument("--country", "-c", type=str, help="Country name (e.g. India or 'United States')")
    parser.add_argument("--days", "-d", type=int, default=365, help="Number of historical days for plot (default 365). Use 0 or negative for 'all' if supported.")
    parser.add_argument("--saveplot", "-s", type=str, default=None, help="If provided, save the plot to this filename (PNG).")
    args = parser.parse_args()

    try:
        global_summary = fetch_global_summary()
        pretty_print_global(global_summary)
    except Exception as e:
        print("Failed to fetch global summary:", e)
        sys.exit(1)

    if not args.country:
        print("\nNo country specified. To view country details and plot, run with --country \"India\"")
        return

    country = args.country
    try:
        country_summary = fetch_country_summary(country)
        pretty_print_country(country_summary)
    except requests.HTTPError as he:
        print(f"\nError fetching country summary for '{country}': {he}")
        return
    except Exception as e:
        print(f"\nUnexpected error fetching country summary: {e}")
        return

    # Historical
    days_param = "all" if (args.days <= 0) else args.days
    try:
        hist = fetch_country_historical(country, days=days_param)
        # The API sometimes returns {"country": "...", "timeline": {...}}
        label = hist.get("country") or country
        plot_new_cases(hist, savepath=args.saveplot, country_label=label)
    except Exception as e:
        print(f"Could not fetch or plot historical data: {e}")

if __name__ == "__main__":
    main()
