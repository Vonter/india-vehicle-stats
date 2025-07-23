#!/usr/bin/env python3

import polars as pl
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import matplotlib.dates as mdates
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import pandas as pd
from datetime import datetime

# Constants
DATA_FILE = "data/vehicle-statistics.parquet"
OUTPUT_DIR = Path("viz")

# Create output directory
OUTPUT_DIR.mkdir(exist_ok=True)

@dataclass
class ChartConfig:
    """Configuration for chart generation."""
    title: str
    xlabel: str
    ylabel: str
    filename: str
    date_format: str = '%Y-%m'
    date_interval: int = 6
    top_n: int = 10

class VehicleVizGenerator:
    """Main class for generating vehicle statistics visualizations."""
    
    def __init__(self):
        self.setup_style()
        self.data = self.load_data()
    
    def setup_style(self):
        """Set up hrbrthemes-inspired plotting style."""
        plt.style.use('default')
        
        plt.rcParams.update({
            'figure.figsize': (16, 10),
            'figure.dpi': 300,
            'savefig.dpi': 300,
            
            # Font settings
            'font.family': 'sans-serif',
            'font.sans-serif': ['Arial', 'DejaVu Sans', 'Liberation Sans', 'sans-serif'],
            'font.size': 11,
            'axes.titlesize': 14,
            'axes.labelsize': 12,
            'xtick.labelsize': 10,
            'ytick.labelsize': 10,
            'legend.fontsize': 10,
            
            # Colors and appearance
            'axes.facecolor': 'white',
            'figure.facecolor': 'white',
            'axes.edgecolor': '#cccccc',
            'axes.linewidth': 1,
            'axes.grid': True,
            'grid.color': '#f0f0f0',
            'grid.linewidth': 0.8,
            'grid.alpha': 0.7,
            
            # Spines
            'axes.spines.left': True,
            'axes.spines.bottom': True,
            'axes.spines.top': False,
            'axes.spines.right': False,
            
            # Ticks
            'xtick.bottom': True,
            'xtick.top': False,
            'ytick.left': True,
            'ytick.right': False,
            'xtick.color': '#666666',
            'ytick.color': '#666666',
            
            # Legend
            'legend.frameon': False,
            'legend.numpoints': 1,
            'legend.scatterpoints': 1,
        })
    
    def load_data(self) -> pl.DataFrame:
        """Load vehicle statistics data from parquet file."""
        print("Loading vehicle statistics data...")
        
        df = pl.read_parquet(DATA_FILE)
        print(f"Loaded {len(df)} records")
        
        # Filter for Registration Manufacturer data only
        manufacturer_df = df.filter(pl.col("Metric") == "Registration Manufacturer")
        print(f"Filtered to {len(manufacturer_df)} Registration Manufacturer records")
        
        # Filter out current month data
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month
        
        # Exclude data from the current month
        filtered_df = manufacturer_df.filter(
            ~((pl.col("Year") == current_year) & (pl.col("Month") == current_month))
        )
        
        excluded_count = len(manufacturer_df) - len(filtered_df)
        print(f"Excluded {excluded_count} records from current month ({current_year}-{current_month:02d})")
        print(f"Final dataset contains {len(filtered_df)} records")
        
        return filtered_df
    
    def prepare_time_series_data(self, df: pl.DataFrame, group_col: str) -> pd.DataFrame:
        """Prepare data for time series visualization."""
        # Group by the specified column and time, sum the counts
        if group_col == "RTO_Name":
            # Create a combined RTO identifier for better labeling
            grouped = (
                df.with_columns(
                    pl.concat_str([pl.col("State"), pl.lit("-"), pl.col("RTO Name")]).alias("RTO_Name")
                )
                .group_by(["RTO_Name", "Year", "Month"])
                .agg(pl.col("Count").sum().alias("Count"))
                .sort(["RTO_Name", "Year", "Month"])
            )
        else:
            grouped = (
                df.group_by([group_col, "Year", "Month"])
                .agg(pl.col("Count").sum().alias("Count"))
                .sort([group_col, "Year", "Month"])
            )
        
        # Convert to pandas for easier matplotlib plotting
        result_pd = grouped.to_pandas()
        result_pd['Date'] = pd.to_datetime(result_pd[['Year', 'Month']].assign(day=1))
        
        # Pivot and prepare for plotting
        result_pivot = result_pd.pivot(index='Date', columns=group_col, values='Count')
        result_pivot = result_pivot.fillna(0).reset_index()
        
        return result_pivot
    
    def get_top_n_columns(self, df: pd.DataFrame, n: int = 10) -> List[str]:
        """Get top N columns by total values."""
        numeric_cols = df.select_dtypes(include=['number']).columns
        return df[numeric_cols].sum(axis=0).sort_values(ascending=False).index[:n].tolist()
    
    def create_plot_layout(self) -> Tuple[plt.Figure, plt.Axes]:
        """Create a figure and axes with consistent layout."""
        fig = plt.figure(figsize=(16, 10))
        # Fixed axes positioning to ensure consistent plot area across all charts
        # [left, bottom, width, height] in figure coordinates
        ax = fig.add_axes([0.08, 0.15, 0.65, 0.77])
        return fig, ax
    
    def get_color_palette(self, n_colors: int) -> List[str]:
        """Get a color palette similar to hrbrthemes."""
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
                  '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        if n_colors <= len(colors):
            return colors[:n_colors]
        else:
            return sns.color_palette("husl", n_colors).as_hex()
    
    def format_axes(self, ax: plt.Axes, config: ChartConfig):
        """Format axes with consistent styling."""
        ax.set_title(config.title, fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel(config.xlabel, fontsize=12, fontweight='bold')
        ax.set_ylabel(config.ylabel, fontsize=12, fontweight='bold')
        
        # Format x-axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter(config.date_format))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=config.date_interval))
        
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Format y-axis with commas
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}'))
        
        # Fixed legend positioning to ensure consistency across all charts  
        # Position legend in a fixed location relative to the figure
        ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', 
                 borderaxespad=0, frameon=False, fontsize=9)
    
    def create_line_chart(self, df: pd.DataFrame, config: ChartConfig):
        """Create a line chart with consistent styling."""
        # Get top N columns
        top_cols = self.get_top_n_columns(df, config.top_n)
        
        # Create plot
        fig, ax = self.create_plot_layout()
        colors = self.get_color_palette(len(top_cols))
        
        # Plot lines
        for i, col in enumerate(top_cols):
            if col in df.columns:  # Check if column exists
                ax.plot(df['Date'], df[col], label=col, linewidth=1.5, color=colors[i])
        
        # Format axes
        self.format_axes(ax, config)
        
        # Save plot with consistent parameters
        output_path = OUTPUT_DIR / config.filename
        plt.savefig(output_path, dpi=300, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        plt.close()
        
        print(f"Saved chart to {output_path}")
    
    def generate_rto_vehicles_over_time(self):
        """Generate total vehicles registered in each RTO."""
        print("Generating RTO vehicles chart...")
        
        # Prepare data
        result = self.prepare_time_series_data(self.data, "RTO_Name")
        
        # Create chart
        config = ChartConfig(
            title='Total Vehicles Registered by RTO',
            xlabel='Month',
            ylabel='Number of Vehicles Registered',
            filename='rtos.png',
            top_n=10
        )
        
        self.create_line_chart(result, config)
    
    def generate_manufacturer_vehicles_over_time(self):
        """Generate total vehicles registered by manufacturer."""
        print("Generating manufacturer vehicles chart...")
        
        # Prepare data  
        result = self.prepare_time_series_data(self.data, "Name")
        
        # Create chart
        config = ChartConfig(
            title='Total Vehicles Registered by Manufacturer',
            xlabel='Month',
            ylabel='Number of Vehicles Registered',
            filename='manufacturers.png',
            top_n=10
        )
        
        self.create_line_chart(result, config)
    
    def generate_all_charts(self):
        """Generate all visualization charts."""
        print("\nGenerating vehicle visualization charts...")
        
        chart_methods = [
            self.generate_rto_vehicles_over_time,
            self.generate_manufacturer_vehicles_over_time
        ]
        
        for method in chart_methods:
            method()
        
        print("\nAll vehicle visualization charts generated successfully!")
        print(f"Chart files saved to: {OUTPUT_DIR}")

def main():
    """Main function to generate all visualization charts."""
    generator = VehicleVizGenerator()
    generator.generate_all_charts()

if __name__ == "__main__":
    main()