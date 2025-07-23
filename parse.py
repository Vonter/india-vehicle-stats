import polars as pl
import pandas as pd
import os
from bs4 import BeautifulSoup
import glob
import calendar
from pathlib import Path
import logging
import json

# Configuration
RAW_DIR = "raw/"
COMBINED_PARQUET = "data/vehicle-statistics.parquet"
COMBINED_CSV = "data/vehicle-statistics.csv.gz"
PROCESSED_FILES_JSON = ".processed.json"
RTO_MAPPING_FILE = "raw/rtos.txt"
METADATA_COLS = ['State', 'RTO', 'RTO Name', 'Year', 'Month']
DATA_TYPES = {'permit_category': 'Permit Category', 'permit_purpose': 'Permit Purpose', 'permit_type': 'Permit Type', 'registration_class': 'Registration Class', 'registration_category': 'Registration Category', 'registration_fuel': 'Registration Fuel', 'registration_manufacturer': 'Registration Manufacturer', 'registration_standard': 'Registration Standard', 'revenue_fee': 'Revenue (Fee)', 'revenue_tax': 'Revenue (Tax)', 'transaction_transaction': 'Transaction'}

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

def load_rto_mapping(file_path=RTO_MAPPING_FILE):
    """Load RTO code to name mapping from rtos.txt file."""
    rto_mapping = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if ' - ' in line and '(' in line:
                    # Split on ' - ' from the RIGHT to handle dashes in RTO names
                    # This handles cases like "TC OFFICE - STA OFFICE - KL99( date )"
                    parts = line.rsplit(' - ', 1)
                    if len(parts) == 2:
                        rto_name, code_part = parts
                        rto_name = rto_name.strip()
                        # Extract RTO code (everything before the opening parenthesis)
                        rto_code = code_part.split('(')[0].strip()
                        
                        if rto_code and rto_name:
                            # Store the full RTO code (like "RJ267", "GJ30") as the key
                            rto_mapping[rto_code] = rto_name
                        
        logger.info(f"Loaded {len(rto_mapping)} RTO mappings")
        return rto_mapping
    except Exception as e:
        logger.error(f"Error loading RTO mapping: {e}")
        return {}

def extract_metadata(filename, rto_mapping=None):
    """Extract metadata from the HTML filename and path structure."""
    parts = filename.split('/')
    state = parts[-6]
    rto_number = int(parts[-5])
    full_rto_code = f"{state}{rto_number}"
    rto_name = rto_mapping.get(full_rto_code) if rto_mapping else f"{state}{rto_number}"
    
    return {
        'State': state,
        'RTO': rto_number,
        'RTO Name': rto_name,
        'Year': parts[-4],
        'Month': str(list(calendar.month_abbr).index(parts[-3].title())),
        'Metric': DATA_TYPES['_'.join(parts[-2:]).replace('.html', '')]
    }

def process_html_file(html_file, rto_mapping=None):
    """Process a single HTML file and return a DataFrame."""
    metadata = extract_metadata(html_file, rto_mapping)
    if not metadata:
        return None, None

    with open(html_file, 'r') as file:
        soup = BeautifulSoup(file.read(), 'html.parser')
    
    tables = soup.find_all('table')
    if len(tables) < 2:
        return None, None
    
    def clean_text(text):
        return text.strip().replace("Click Here For Month Wise Chart", "").replace('"', '').replace(',', '').strip()
    
    data = {}
    is_transaction = metadata['Metric'] == 'Transaction'
    
    for row in tables[1].find_all('tr'):
        cells = row.find_all(['th', 'td'])
        
        if is_transaction and len(cells) >= 3 and cells[0].text.strip().isdigit():
            purpose, count = clean_text(cells[1].text), clean_text(cells[2].text)
            if purpose and count:
                data[purpose] = count
        elif not is_transaction and len(cells) >= 2:
            key, value = clean_text(cells[0].text), clean_text(cells[1].text)
            if key:
                data[key] = value
    
    if not data:
        return None, None
        
    # Create DataFrame and add metadata
    df = pl.DataFrame([data])
    for col, value in metadata.items():
        if col != 'Metric':
            df = df.with_columns(pl.lit(value).alias(col))
            
    return df, metadata['Metric']

def format_and_combine_dfs(dfs):
    """Format and combine a list of DataFrames."""
    if not dfs:
        return None
        
    # Get all columns and standardize
    all_cols = set(METADATA_COLS)
    for df in dfs:
        all_cols.update(df.columns)
    
    # Standardize and combine DataFrames
    standardized_dfs = []
    for df in dfs:
        missing_cols = all_cols - set(df.columns)
        for col in missing_cols:
            df = df.with_columns(pl.lit('0').alias(col))
        standardized_dfs.append(df.select(list(all_cols)))
    
    combined_df = pl.concat(standardized_dfs)
    
    # Format columns
    data_cols = [col for col in combined_df.columns if col not in METADATA_COLS]
    for col in data_cols:
        combined_df = combined_df.with_columns([
            pl.col(col).str.replace(".00", "", literal=True).replace("", "0").cast(pl.Int64)
        ])
    
    combined_df = combined_df.with_columns([
        pl.col('RTO').cast(pl.Int64),
        pl.col('Year').cast(pl.Int64),
        pl.col('Month').cast(pl.Int64)
    ]).sort(METADATA_COLS)
    
    return combined_df

def get_dir_key(file_path):
    """Get directory key from file path in format state/rto/year."""
    parts = file_path.split('/')
    return '/'.join(parts[1:4]) if len(parts) >= 4 else None

def load_processed_counts(file_path=PROCESSED_FILES_JSON):
    """Load the processed file counts from JSON."""
    try:
        return json.load(open(file_path)) if os.path.exists(file_path) else {}
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error loading processed counts: {e}")
        return {}

def save_processed_counts(counts, file_path=PROCESSED_FILES_JSON):
    """Save the processed file counts to JSON."""
    try:
        json.dump(counts, open(file_path, 'w'), indent=2)
    except Exception as e:
        logger.error(f"Error saving processed counts: {e}")

def process_directory_to_long_format(dir_files, rto_mapping=None):
    """Process all files in a directory and convert to long format."""
    data_by_type = {dtype: [] for dtype in DATA_TYPES.values()}
    successful_count = 0
    
    # Process each file and group by data type
    for html_file in dir_files:
        if (result := process_html_file(html_file, rto_mapping)) and result[0] is not None:
            df, data_type = result
            if data_type in DATA_TYPES.values():
                data_by_type[data_type].append(df)
                successful_count += 1
    
    # Convert each data type to long format
    long_dfs = []
    for data_type, dfs in data_by_type.items():
        if len(dfs) > 0:
            dir_df = format_and_combine_dfs(dfs)
            value_cols = [col for col in dir_df.columns if col not in METADATA_COLS]
            long_dfs.append(
                dir_df.with_columns(pl.lit(data_type).alias("Metric"))
                .unpivot(
                    index=METADATA_COLS + ["Metric"],
                    on=value_cols,
                    variable_name="Name",
                    value_name="Count"
                )
            )
    
    return (pl.concat(long_dfs) if long_dfs else None, successful_count)

def main():
    # Initialize directory and load processed counts
    Path(os.path.dirname(COMBINED_PARQUET)).mkdir(parents=True, exist_ok=True)
    processed_counts = load_processed_counts()
    
    # Load RTO mapping
    rto_mapping = load_rto_mapping()
    
    # Group files by directory
    files_by_dir = {}
    for file in glob.glob(os.path.join(RAW_DIR, '**', "*.html"), recursive=True):
        if dir_key := get_dir_key(file):
            files_by_dir.setdefault(dir_key, []).append(file)
    
    # Process each directory
    all_processed_dfs = []
    for dir_key, dir_files in files_by_dir.items():
        if processed_counts.get(dir_key, 0) >= len(dir_files):
            logger.info(f"Directory {dir_key} already processed.")
            continue
        logger.info(f"Processing {dir_key}")
        if dir_result := process_directory_to_long_format(dir_files, rto_mapping):
            dir_df, successful_count = dir_result
            if dir_df is not None:
                all_processed_dfs.append(dir_df)
                processed_counts[dir_key] = successful_count    
    if not all_processed_dfs:
        logger.info("No new data to process.") 
        return
        
    # Combine all processed DataFrames
    processed_df = pl.concat(all_processed_dfs)
    existing_df = pl.scan_parquet(COMBINED_PARQUET).collect() if os.path.exists(COMBINED_PARQUET) else pl.DataFrame()
    final_df = pl.concat([existing_df, processed_df])

    # Deduplicate and save to Parquet
    key_columns = [col for col in final_df.columns if col != 'Count']
    final_df = final_df.sort(key_columns).unique(subset=key_columns, keep='any').sort(key_columns)

    # Save to Parquet
    final_df.write_parquet(COMBINED_PARQUET)

    # Save to compressed CSV
    final_df.to_pandas().to_csv(COMBINED_CSV, compression='gzip')

    # Save processed counts once at the end
    save_processed_counts(processed_counts)
    
    logger.info("Processing completed!")

if __name__ == "__main__":
    main()
