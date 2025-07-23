#!/usr/bin/env python3
"""
Data chunking script to create JSON files for the Svelte vehicle statistics app.
Processes the parquet data and creates separate JSON files for:
- Country level aggregation with month-wise metrics
- State level aggregations with month-wise metrics
- RTO level data with month-wise metrics

Usage: python data.py
"""

import polars as pl
import json
from pathlib import Path
import logging
from datetime import datetime

# Configuration
PARQUET_FILE = "data/vehicle-statistics.parquet"
OUTPUT_DIR = "viz/static/data"
COUNTRY_FILE = "country.json"
STATES_FILE = "states.json"

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger()


def clean_name_values(df):
    """Clean Name values by stripping leading hyphens."""
    logger.info("Cleaning Name values...")
    return df.with_columns(
        pl.col("Name").str.replace(r"^-+", "").alias("Name")
    )


def rename_metrics(df):
    """Rename Registration metrics to Vehicle metrics."""
    logger.info("Renaming metrics...")
    metric_renames = {
        "Registration Category": "Vehicle Category",
        "Registration Class": "Vehicle Class", 
        "Registration Fuel": "Vehicle Fuel",
        "Registration Manufacturer": "Vehicle Manufacturer",
        "Registration Standard": "Vehicle Standard"
    }
    
    # Apply renames using polars replace functionality
    df_renamed = df
    for old_name, new_name in metric_renames.items():
        df_renamed = df_renamed.with_columns(
            pl.when(pl.col("Metric") == old_name)
            .then(pl.lit(new_name))
            .otherwise(pl.col("Metric"))
            .alias("Metric")
        )
    
    return df_renamed


def load_data():
    """Load the vehicle statistics data from parquet file."""
    logger.info("Loading vehicle statistics data...")
    df = pl.read_parquet(PARQUET_FILE)
    logger.info(f"Loaded {len(df)} records with {len(df.columns)} columns")
    
    # Clean name values
    df = clean_name_values(df)
    
    # Rename metrics
    df = rename_metrics(df)
    
    # Filter out current month/year data
    current_date = datetime.now()
    current_year = current_date.year
    current_month = current_date.month
    
    logger.info(f"Filtering out current month/year data: {current_year}-{current_month:02d}")
    initial_count = len(df)
    df = df.filter(
        ~((pl.col("Year") == current_year) & (pl.col("Month") == current_month))
    )
    filtered_count = len(df)
    logger.info(f"Filtered out {initial_count - filtered_count} records from current month/year")
    logger.info(f"Remaining records: {filtered_count}")
    
    return df


def create_optimized_metrics_structure(df_metrics):
    """Convert metrics DataFrame to optimized JSON structure grouped by Metric-Name combinations.
    
    Creates structure: metrics[metric][name] = [{year, month, count}, ...]
    This monthly array structure enables efficient client-side filtering for year/month routes.
    """
    metrics_dict = {}
    
    for row in df_metrics.rows(named=True):
        metric = row["Metric"]
        name = row["Name"]
        year = row["Year"]
        month = row["Month"]
        count = row["count"]
        
        # Create nested structure: Metric -> Name -> monthly data
        if metric not in metrics_dict:
            metrics_dict[metric] = {}
        
        if name not in metrics_dict[metric]:
            metrics_dict[metric][name] = []
        
        metrics_dict[metric][name].append({
            "year": year,
            "month": month,
            "count": count
        })
    
    # Sort monthly data by year and month for each metric-name combination
    for metric in metrics_dict:
        for name in metrics_dict[metric]:
            metrics_dict[metric][name].sort(key=lambda x: (x["year"], x["month"]))
    
    return metrics_dict


def create_simple_metrics_structure(df_metrics):
    """Convert metrics DataFrame to simple totals structure grouped by Metric-Name combinations."""
    metrics_dict = {}
    
    for row in df_metrics.rows(named=True):
        metric = row["Metric"]
        name = row["Name"]
        count = row["count"]
        
        # Create nested structure: Metric -> Name -> total
        if metric not in metrics_dict:
            metrics_dict[metric] = {}
        
        if name not in metrics_dict[metric]:
            metrics_dict[metric][name] = 0
        
        metrics_dict[metric][name] += count
    
    return metrics_dict



def create_country_aggregation(df):
    """Create country-level aggregation with month-wise metrics."""
    logger.info("Creating country-level aggregation...")
    
    # Aggregate by Metric, Name, Year, and Month
    country_metrics = (
        df.group_by(["Metric", "Name", "Year", "Month"])
        .agg(pl.col("Count").sum().alias("count"))
        .sort(["Metric", "Name", "Year", "Month"])
    )
    
    # Create optimized structure
    metrics_structure = create_optimized_metrics_structure(country_metrics)
    
    # Get state summaries for navigation
    state_summaries = (
        df.group_by("State")
        .agg([
            pl.col("Count").sum().alias("total_count"),
            pl.col("RTO").n_unique().alias("rto_count")
        ])
        .sort("total_count", descending=True)
    )
    
    # Create state-wise metric breakdowns for aggregation functionality (simple totals only)
    logger.info("Creating state-wise metric breakdowns...")
    state_metric_breakdowns = {}
    states = df.select("State").unique().to_series().to_list()
    
    for state in states:
        state_df = df.filter(pl.col("State") == state)
        # Aggregate to totals only, no monthly breakdown needed
        state_metrics = (
            state_df.group_by(["Metric", "Name"])
            .agg(pl.col("Count").sum().alias("count"))
        )
        state_metric_breakdowns[state] = create_simple_metrics_structure(state_metrics)
    
    # Enhance state summaries with metric breakdowns
    enhanced_states = []
    for state_data in state_summaries.to_dicts():
        state_name = state_data["State"]
        enhanced_states.append({
            **state_data,
            "metrics": state_metric_breakdowns.get(state_name, {})
        })
    
    return {
        "level": "country",
        "name": "India",
        "metrics": metrics_structure,
        "states": enhanced_states
    }


def create_state_aggregations(df):
    """Create state-level aggregations for each state with month-wise metrics."""
    logger.info("Creating state-level aggregations...")
    
    states_data = {}
    states = df.select("State").unique().to_series().to_list()
    
    for state in states:
        state_df = df.filter(pl.col("State") == state)
        
        # State metrics aggregation with monthly breakdown
        state_metrics = (
            state_df.group_by(["Metric", "Name", "Year", "Month"])
            .agg(pl.col("Count").sum().alias("count"))
            .sort(["Metric", "Name", "Year", "Month"])
        )
        
        # Create optimized structure
        metrics_structure = create_optimized_metrics_structure(state_metrics)
        
        # RTO summaries for navigation
        rto_summaries = (
            state_df.group_by(["RTO", "RTO Name"])
            .agg(pl.col("Count").sum().alias("total_count"))
            .sort("total_count", descending=True)
        )
        
        # Create RTO-wise metric breakdowns for aggregation functionality (simple totals only)
        logger.info(f"Creating RTO-wise metric breakdowns for {state}...")
        rto_metric_breakdowns = {}
        rtos = state_df.select(["RTO", "RTO Name"]).unique()
        
        for rto_row in rtos.rows(named=True):
            rto_code = rto_row["RTO"]
            rto_df = state_df.filter(pl.col("RTO") == rto_code)
            # Aggregate to totals only, no monthly breakdown needed
            rto_metrics = (
                rto_df.group_by(["Metric", "Name"])
                .agg(pl.col("Count").sum().alias("count"))
            )
            rto_metric_breakdowns[rto_code] = create_simple_metrics_structure(rto_metrics)
        
        # Enhance RTO summaries with metric breakdowns
        enhanced_rtos = []
        for rto_data in rto_summaries.to_dicts():
            rto_code = rto_data["RTO"]
            enhanced_rtos.append({
                **rto_data,
                "metrics": rto_metric_breakdowns.get(rto_code, {})
            })
        
        states_data[state] = {
            "level": "state",
            "state": state,
            "name": f"State {state}",
            "metrics": metrics_structure,
            "rtos": enhanced_rtos
        }
        
        logger.info(f"Processed state: {state}")
    
    return states_data


def create_rto_data(df):
    """Create RTO-level data for each state and RTO combination with month-wise metrics."""
    logger.info("Creating RTO-level data...")
    
    rto_data = {}
    state_rto_combinations = df.select(["State", "RTO", "RTO Name"]).unique()
    
    for row in state_rto_combinations.rows(named=True):
        state = row["State"]
        rto = row["RTO"]
        rto_name = row["RTO Name"]
        
        rto_df = df.filter((pl.col("State") == state) & (pl.col("RTO") == rto))
        
        # RTO metrics with monthly breakdown
        rto_metrics = (
            rto_df.group_by(["Metric", "Name", "Year", "Month"])
            .agg(pl.col("Count").sum().alias("count"))
            .sort(["Metric", "Name", "Year", "Month"])
        )
        
        # Create optimized structure
        metrics_structure = create_optimized_metrics_structure(rto_metrics)
        
        key = f"{state}_{rto}"
        rto_data[key] = {
            "level": "rto",
            "state": state,
            "rto": rto,
            "name": rto_name or f"{state} RTO {rto}",
            "metrics": metrics_structure
        }
        
        logger.info(f"Processed RTO: {state}-{rto}")
    
    return rto_data


def save_json_files(country_data, states_data, rto_data):
    """Save all data to organized JSON files."""
    logger.info("Saving JSON files...")
    
    # Create output directory
    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save country data
    country_file = output_dir / COUNTRY_FILE
    with open(country_file, 'w', encoding='utf-8') as f:
        json.dump(country_data, f, ensure_ascii=False, separators=(',', ':'))
    logger.info(f"Saved country data: {country_file}")
    
    # Save states index
    states_index_file = output_dir / STATES_FILE
    states_index = {state: f"state_{state}.json" for state in states_data.keys()}
    with open(states_index_file, 'w', encoding='utf-8') as f:
        json.dump(states_index, f, ensure_ascii=False, separators=(',', ':'))
    logger.info(f"Saved states index: {states_index_file}")
    
    # Save individual state files
    for state, data in states_data.items():
        state_file = output_dir / f"state_{state}.json"
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
        logger.info(f"Saved state data: {state_file}")
    
    # Save RTO files organized by state
    for key, data in rto_data.items():
        rto_file = output_dir / f"rto_{key}.json"
        with open(rto_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    
    logger.info(f"Saved {len(rto_data)} RTO files")
    
    # Create metadata file
    from datetime import datetime
    metadata = {
        "generated_at": datetime.now().isoformat(),
        "total_states": len(states_data),
        "total_rtos": len(rto_data),
        "available_states": list(states_data.keys()),
        "file_structure": {
            "country": COUNTRY_FILE,
            "states_index": STATES_FILE,
            "state_pattern": "state_{STATE}.json",
            "rto_pattern": "rto_{STATE}_{RTO}.json"
        },
        "data_aggregation": {
            "yearly_data": "Year data is aggregated client-side from existing country/state JSON files",
            "monthly_data": "Monthly data is aggregated client-side from existing country/state JSON files",
            "structure": "Each JSON contains metrics[metric][name] = [{year, month, count}, ...] for client-side filtering"
        }
    }
    
    metadata_file = output_dir / "metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, separators=(',', ':'))
    logger.info(f"Saved metadata: {metadata_file}")


def main():
    """Main execution function."""
    try:
        # Load data
        df = load_data()
        
        # Create main aggregations
        country_data = create_country_aggregation(df)
        states_data = create_state_aggregations(df)
        rto_data = create_rto_data(df)
        
        # Save files (no longer saving year or monthly JSON files)
        save_json_files(country_data, states_data, rto_data)
        
        logger.info("Data chunking completed successfully!")
        logger.info(f"Generated files:")
        logger.info(f"  - 1 country file")
        logger.info(f"  - {len(states_data)} state files")
        logger.info(f"  - {len(rto_data)} RTO files")
        logger.info(f"  - 1 metadata file")
        logger.info(f"Year and monthly data will be aggregated client-side from existing files")
        
    except Exception as e:
        logger.error(f"Error during data processing: {e}")
        raise


if __name__ == "__main__":
    main() 