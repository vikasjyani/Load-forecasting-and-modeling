import os
from datetime import datetime
import pandas as pd
import json
from copy import deepcopy

DEFAULT_DEMAND_CONFIG = {
    "global_settings": {
        "target_years": [2030, 2035, 2040], # Default future years for forecasting
        "exclude_covid_years": False, # Option to exclude specific years like COVID period from historical data
        "forecast_start_year": None # Can be set to override default start (e.g. last historical year + 1)
    },
    "sector_models": {} # To be populated based on identified demand columns from input_demand_file.xlsx
    # Example structure for sector_models:
    # "SectorA_Demand": [
    #   {"model_name": "SLR", "parameters": {}, "enabled": True},
    #   {"model_name": "WAM", "parameters": {"window_size": 3}, "enabled": False}
    # ],
    # "SectorB_Demand": [
    #   {"model_name": "MLR", "parameters": {"independent_vars": ["GDP", "Population"]}, "enabled": True}
    # ]
}

MODEL_OPTIONS = {
    "SLR": {"label": "Simple Linear Regression", "params": {}},
    "WAM": {"label": "Weighted Average Model", "params": {"window_size": {"type": "number", "default": 3, "label": "Window Size"}}},
    "MLR": {"label": "Multiple Linear Regression", "params": {"independent_vars": {"type": "text", "default": "GDP,Population", "label": "Independent Variables (comma-separated)"}}},
    # Add more models and their parameters here
}


def save_demand_forecast_results(project_path_abs, scenario_name, results_df):
    """
    Saves the demand forecast results to a CSV file in the project's results directory.

    Args:
        project_path_abs (str): Absolute path to the current project directory.
        scenario_name (str): Name of the forecast scenario.
        results_df (pd.DataFrame): DataFrame containing the forecast results.

    Returns:
        str: The full path to the saved results file, or None if saving fails.
    """
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"demand_forecast_{scenario_name}_{timestamp}.csv"

        output_dir = os.path.join(project_path_abs, 'results', 'demand_projection')
        os.makedirs(output_dir, exist_ok=True)

        filepath = os.path.join(output_dir, filename)

        # Sanitize scenario_name for filename
        safe_scenario_name = "".join(c if c.isalnum() or c in ('_', '-') else '_' for c in scenario_name)
        if not safe_scenario_name:
            safe_scenario_name = "forecast_scenario" # Default if all chars were invalid

        filename = f"demand_forecast_{safe_scenario_name}_{timestamp}.csv"

        output_dir = os.path.join(project_path_abs, 'results', 'demand_projection')
        os.makedirs(output_dir, exist_ok=True)

        filepath = os.path.join(output_dir, filename)

        results_df.to_csv(filepath, index=False)
        print(f"Demand forecast results for scenario '{scenario_name}' saved to {filepath}")
        return filepath
    except Exception as e:
        print(f"Error saving demand forecast results to CSV for scenario '{scenario_name}': {e}") # Log error properly
        # Consider raising the exception or returning a more specific error indicator if needed by calling code.
        return None

# ---- Demand Configuration File Handling ----

def get_demand_config_filepath(project_path_abs):
    """Constructs the path to the demand_config.json file."""
    return os.path.join(project_path_abs, 'config', 'demand_config.json')

def load_demand_config(project_path_abs):
    """
    Loads the demand forecast configuration from demand_config.json.
    Returns a default configuration if the file is not found or invalid.
    """
    config_filepath = get_demand_config_filepath(project_path_abs)
    if not os.path.exists(config_filepath):
        print(f"Info: Demand config file not found at {config_filepath}. Returning default config.")
        return deepcopy(DEFAULT_DEMAND_CONFIG)
    try:
        with open(config_filepath, 'r') as f:
            config_data = json.load(f)
            # Basic validation: ensure top-level keys exist
            if "global_settings" not in config_data or "sector_models" not in config_data:
                print(f"Warning: Loaded demand config from {config_filepath} is missing essential keys. Merging with default.")
                default_copy = deepcopy(DEFAULT_DEMAND_CONFIG)
                # Merge loaded data into default to preserve what's there but ensure structure
                default_copy.update(config_data) # Naive update, might need more sophisticated merge
                return default_copy
            return config_data
    except json.JSONDecodeError as e:
        print(f"Error: Could not decode JSON from {config_filepath}. Error: {e}. Returning default config.")
        return deepcopy(DEFAULT_DEMAND_CONFIG)
    except Exception as e:
        print(f"Error loading demand config from {config_filepath}: {e}. Returning default config.")
        return deepcopy(DEFAULT_DEMAND_CONFIG)

def save_demand_config(project_path_abs, config_data):
    """
    Saves the given configuration data to demand_config.json.
    """
    config_filepath = get_demand_config_filepath(project_path_abs)
    try:
        os.makedirs(os.path.dirname(config_filepath), exist_ok=True) # Ensure config directory exists
        with open(config_filepath, 'w') as f:
            json.dump(config_data, f, indent=4)
        print(f"Demand configuration saved successfully to {config_filepath}")
        return True
    except Exception as e:
        print(f"Error saving demand configuration to {config_filepath}: {e}")
        return False

# ---- Consolidated Results Generation ----

def generate_consolidated_results(project_path_abs, scenario_name, main_forecast_filepath, demand_config):
    """
    Generates a consolidated demand forecast CSV from the main forecast results.
    It picks the first enabled model for each sector based on the demand_config.
    """
    try:
        main_df = pd.read_csv(main_forecast_filepath)
    except FileNotFoundError:
        print(f"Error: Main forecast file not found at {main_forecast_filepath}") # Replace with logging
        return None
    except Exception as e:
        print(f"Error reading main forecast file {main_forecast_filepath}: {e}") # Replace with logging
        return None

    if main_df.empty:
        print(f"Warning: Main forecast file {main_forecast_filepath} is empty. No consolidated results generated.")
        return None

    consolidated_rows = []

    # Iterate through sectors defined in the demand_config to ensure we process based on configuration
    for sector_name, model_configs in demand_config.get('sector_models', {}).items():
        first_enabled_model_name = None
        # Find the first enabled model for this sector from the config
        for mc in model_configs:
            if mc.get('enabled', False):
                first_enabled_model_name = mc.get('model_name')
                break

        if first_enabled_model_name:
            # Filter the main DataFrame for this sector and the chosen model
            sector_model_df = main_df[
                (main_df['Sector'] == sector_name) &
                (main_df['Model'] == first_enabled_model_name)
            ]

            if not sector_model_df.empty:
                # Select relevant columns: Year, Sector, Value.
                # Add Lower_Bound and Upper_Bound if they exist and are needed downstream.
                cols_to_select = ['Year', 'Sector', 'Value']
                if 'Lower_Bound' in sector_model_df.columns: cols_to_select.append('Lower_Bound')
                if 'Upper_Bound' in sector_model_df.columns: cols_to_select.append('Upper_Bound')

                temp_df = sector_model_df[cols_to_select].copy()
                consolidated_rows.append(temp_df)
            else:
                print(f"Warning: No results found in main forecast for sector '{sector_name}' with model '{first_enabled_model_name}'.")
        else:
            # This case indicates a mismatch or an issue if a sector was expected to have an enabled model
            print(f"Info: No enabled model found in config for sector '{sector_name}' during consolidation. This sector will not be in consolidated results.")

    if not consolidated_rows:
        print(f"Warning: No data to consolidate for scenario '{scenario_name}'. This might happen if no models were enabled or no results were generated.")
        return None

    consolidated_df = pd.concat(consolidated_rows, ignore_index=True)

    # Define filename for consolidated results
    safe_scenario_name = "".join(c if c.isalnum() or c in ('_', '-') else '_' for c in scenario_name)
    if not safe_scenario_name: safe_scenario_name = "scenario" # Default if all chars were invalid

    # Standardized filename, should overwrite for a given scenario if re-run
    consolidated_filename = f"consolidated_demand_forecast_{safe_scenario_name}.csv"

    output_dir = os.path.join(project_path_abs, 'results', 'demand_projection')
    # os.makedirs(output_dir, exist_ok=True) # Should already exist from main save_demand_forecast_results
    consolidated_filepath = os.path.join(output_dir, consolidated_filename)

    try:
        consolidated_df.to_csv(consolidated_filepath, index=False)
        print(f"Consolidated results for scenario '{scenario_name}' saved to {consolidated_filepath}") # Replace with logging
        return consolidated_filepath
    except Exception as e:
        print(f"Error saving consolidated results to CSV {consolidated_filepath}: {e}") # Replace with logging
        return None

# ---- Input Excel File Validation and Parsing ----

def validate_and_parse_demand_input_excel(file_path):
    REQUIRED_SHEET_HISTORICAL = 'Historical_Data'
    # Minimum required columns. More specific demand columns will be identified.
    REQUIRED_COLUMNS_HISTORICAL = ['Year']

    try:
        excel_file = pd.ExcelFile(file_path)
    except FileNotFoundError:
        return False, f"Validation Error: File not found at {file_path}", None
    except ValueError as e: # xlsxwriter related error if file is not a valid zip file
        return False, f"Validation Error: Could not read Excel file. It might be corrupted or not a valid .xlsx file. Detail: {e}", None
    except Exception as e: # Catch other pandas related errors during file open
        return False, f"Validation Error: Error reading Excel file: {e}", None

    available_sheets = excel_file.sheet_names
    if REQUIRED_SHEET_HISTORICAL not in available_sheets:
        return False, f"Validation Error: Missing required sheet: '{REQUIRED_SHEET_HISTORICAL}'. Found sheets: {', '.join(available_sheets) if available_sheets else 'None'}", None

    try:
        historical_df = excel_file.parse(REQUIRED_SHEET_HISTORICAL)
    except Exception as e:
        return False, f"Validation Error: Could not parse '{REQUIRED_SHEET_HISTORICAL}' sheet. Error: {e}", None


    missing_cols = [col for col in REQUIRED_COLUMNS_HISTORICAL if col not in historical_df.columns]
    if missing_cols:
        return False, f"Validation Error: Missing required column(s) in '{REQUIRED_SHEET_HISTORICAL}' sheet: {', '.join(missing_cols)}. Found columns: {', '.join(list(historical_df.columns))}", None

    if historical_df.empty:
        return False, f"Validation Error: '{REQUIRED_SHEET_HISTORICAL}' sheet is empty.", None

    if not pd.api.types.is_numeric_dtype(historical_df['Year']):
        return False, f"Validation Error: 'Year' column in '{REQUIRED_SHEET_HISTORICAL}' must be numeric. Found type: {historical_df['Year'].dtype}.", None

    # Check for duplicate years
    if historical_df['Year'].duplicated().any():
        return False, f"Validation Error: Duplicate values found in 'Year' column in '{REQUIRED_SHEET_HISTORICAL}'. Years must be unique.", None

    # Identify potential demand columns (numeric, not 'Year')
    demand_columns = []
    for col in historical_df.columns:
        if col.lower() != 'year'.lower(): # Case-insensitive check for 'Year'
            if pd.api.types.is_numeric_dtype(historical_df[col]):
                demand_columns.append(col)
            else:
                # Optional: Could warn about non-numeric columns found that are not 'Year'
                print(f"Info: Column '{col}' in '{REQUIRED_SHEET_HISTORICAL}' is not numeric and not 'Year'. It will not be treated as a demand column.")

    if not demand_columns:
        return False, f"Validation Error: No numeric demand data columns found in '{REQUIRED_SHEET_HISTORICAL}' sheet (besides 'Year'). Ensure demand columns are numeric.", None

    # Placeholder for 'Assumptions' sheet
    assumptions_df = None
    REQUIRED_SHEET_ASSUMPTIONS = 'Assumptions' # Example, can be made more flexible
    if REQUIRED_SHEET_ASSUMPTIONS in available_sheets:
        try:
            assumptions_df = excel_file.parse(REQUIRED_SHEET_ASSUMPTIONS)
            # Potential validation for assumptions_df here (e.g., ['Parameter', 'Value'] columns)
            if assumptions_df.empty:
                 print(f"Info: '{REQUIRED_SHEET_ASSUMPTIONS}' sheet is present but empty.")
            elif not all(col in assumptions_df.columns for col in ['Parameter', 'Value']):
                 print(f"Warning: '{REQUIRED_SHEET_ASSUMPTIONS}' sheet is present but might be missing 'Parameter' or 'Value' columns.")

        except Exception as e:
            print(f"Info: Could not parse '{REQUIRED_SHEET_ASSUMPTIONS}' sheet. Error: {e}")
            # Not returning False here, as Assumptions might be optional or handled differently.
            assumptions_df = None # Ensure it's None if parsing fails or sheet is problematic

    parsed_data = {
        'historical_data': historical_df,
        'identified_demand_columns': demand_columns
    }
    if assumptions_df is not None: # Only add if successfully parsed and not empty (or handle empty as needed)
        parsed_data['assumptions_data'] = assumptions_df

    return True, f"File validated successfully. Identified demand columns: {', '.join(demand_columns)}.", parsed_data
