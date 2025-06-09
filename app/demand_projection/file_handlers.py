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
    "SLR": {
        "label": "Simple Linear Regression", # Changed "name" to "label" for consistency with other UI elements
        "params": { # Renamed "parameters" to "params" for brevity, matching usage
            "confidence_pct": {"type": "float", "default": 0.1, "label": "Confidence Pct (0.0-1.0)", "min": 0.01, "max": 0.5, "step": 0.01}
        }
    },
    "WAM": {
        "label": "Weighted Average Method",
        "params": {
            "window_size_option": {
                "type": "select_with_custom",
                "label": "Window Size (Years)",
                "options": [
                    {"value": "3", "label": "3 Years (Short-term)"},
                    {"value": "5", "label": "5 Years (Medium-term)"},
                    {"value": "7", "label": "7 Years (Long-term)"}, # Changed 10 to 7 for variety
                    {"value": "custom", "label": "Custom Value"}
                ],
                "default_select": "3",
                "custom_input_name": "window_size_custom",
                "custom_input_default": 3,
                "custom_input_type": "number",
                "custom_input_min": 1,
                "custom_input_max": 20 # Max historical years to average
            },
            # The actual parameter stored in demand_config.json for WAM will be 'window_size' (numeric)
            "confidence_pct": {"type": "float", "default": 0.1, "label": "Confidence Pct (0.0-1.0)", "min": 0.01, "max": 0.5, "step": 0.01}
        }
    },
    "MLR": {
        "label": "Multiple Linear Regression",
        "params": {
            "independent_vars": {"type": "text", "default": "GDP,Population", "label": "Independent Variables (comma-separated)"}, # Moved from main MLR in previous plan
            "confidence_pct": {"type": "float", "default": 0.1, "label": "Confidence Pct (0.0-1.0)", "min": 0.01, "max": 0.5, "step": 0.01}
        }
    }
    # Note: The actual 'window_size' (numeric) will be derived from 'window_size_option'
    # and 'window_size_custom' in the route logic before saving to demand_config.json
    # and before passing to the forecast_wam model.
    # The 'confidence_pct' was added to all models for consistency.
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
    Generates a consolidated demand forecast CSV using primary model selections
    from display_settings.json.

    Args:
        project_path_abs (str): Absolute path to the project.
        scenario_name_from_form (str): Original scenario name (from form when forecast was run). Used for naming the output file.
        main_forecast_filepath (str): Path to the detailed `demand_forecast_[scenario]_[timestamp].csv` file.
        scenario_base_name_for_settings (str): Base name for display settings (e.g., "ScenarioA_20231115_103000").
    """
    display_settings = load_display_settings(project_path_abs, scenario_base_name_for_settings)
    primary_models = display_settings.get('primary_models', {})

    if not primary_models:
        print(f"Info: No primary models selected in display_settings for scenario '{scenario_base_name_for_settings}'. Consolidated file will not be generated based on primary model selections.")
        # Fallback or alternative logic could be added here, e.g., use first enabled model as before,
        # or simply do not generate the file if explicit primary selections are required.
        # For this implementation, if no primary_models dict exists or it's empty, we don't consolidate.
        return None

    try:
        main_df = pd.read_csv(main_forecast_filepath)
    except FileNotFoundError:
        print(f"Error: Main forecast file not found at {main_forecast_filepath}") # Replace with proper logging
        return None
    except Exception as e:
        print(f"Error reading main forecast file {main_forecast_filepath}: {e}") # Replace with proper logging
        return None

    if main_df.empty:
        print(f"Warning: Main forecast file {main_forecast_filepath} is empty. No consolidated results generated.")
        return None

    consolidated_rows = []
    available_sectors_in_main_df = main_df['Sector'].unique()

    for sector_name in available_sectors_in_main_df:
        chosen_model = primary_models.get(sector_name)

        if chosen_model and chosen_model != "": # Check if a specific model was selected (not empty string for "-- Auto --")
            sector_model_df = main_df[
                (main_df['Sector'] == sector_name) &
                (main_df['Model'] == chosen_model)
            ]

            if not sector_model_df.empty:
                cols_to_select = ['Year', 'Sector', 'Model', 'Value'] # Start with essential
                if 'Lower_Bound' in sector_model_df.columns: cols_to_select.append('Lower_Bound')
                if 'Upper_Bound' in sector_model_df.columns: cols_to_select.append('Upper_Bound')
                if 'Comment' in sector_model_df.columns: cols_to_select.append('Comment')

                temp_df = sector_model_df[cols_to_select].copy()
                consolidated_rows.append(temp_df)
            else:
                print(f"Warning: No data found in main forecast for explicitly selected primary model '{chosen_model}' for sector '{sector_name}'.")
        else:
            # If chosen_model is None (sector not in primary_models keys) or "" (explicitly set to Auto)
            print(f"Info: Sector '{sector_name}' will not be included in consolidated results as no specific primary model was selected (or was set to Auto).")

    if not consolidated_rows:
        print(f"Warning: No data to consolidate for scenario '{scenario_name_from_form}' based on primary model selections. Consolidated file will not be saved/updated.")
        return None

    consolidated_df = pd.concat(consolidated_rows, ignore_index=True)

    # Use the original scenario name (from form when forecast was run) for the output file.
    safe_output_scenario_name = "".join(c if c.isalnum() or c in ('_', '-') else '_' for c in scenario_name_from_form)
    if not safe_output_scenario_name: safe_output_scenario_name = "scenario"

    consolidated_filename = f"consolidated_demand_forecast_{safe_output_scenario_name}.csv"

    output_dir = os.path.join(project_path_abs, 'results', 'demand_projection')
    consolidated_filepath = os.path.join(output_dir, consolidated_filename)

    try:
        consolidated_df.to_csv(consolidated_filepath, index=False)
        print(f"Consolidated results (from primary selections) for scenario '{scenario_name_from_form}' saved to {consolidated_filepath}")
        return consolidated_filepath
    except Exception as e:
        print(f"Error saving primary-selection consolidated results to CSV {consolidated_filepath}: {e}")
        return None

# ---- Display Settings File Handling ----

def get_display_settings_filepath(project_path_abs, scenario_base_name):
    """Constructs the path to the display_settings_SCENARIO.json file."""
    results_dir = os.path.join(project_path_abs, 'results', 'demand_projection')
    return os.path.join(results_dir, f"display_settings_{scenario_base_name}.json")

def load_display_settings(project_path_abs, scenario_base_name):
    """Loads display settings. (Helper, actual loading might be direct in route)"""
    filepath = get_display_settings_filepath(project_path_abs, scenario_base_name)
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, Exception) as e:
            print(f"Error loading display settings from {filepath}: {e}")
            return {} # Return empty if error
    return {} # Return empty if not found

def save_display_settings(project_path_abs, scenario_base_name, new_settings_data):
    """
    Saves display settings, merging new_settings_data with existing data.
    Specifically, new_settings_data is expected to be a dict like {'primary_models': {...}}
    or {'td_losses': [...]}, etc.
    """
    filepath = get_display_settings_filepath(project_path_abs, scenario_base_name)

    current_settings = {}
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                current_settings = json.load(f)
        except (json.JSONDecodeError, Exception) as e:
            print(f"Warning: Could not read existing display settings from {filepath}. Will overwrite if saving. Error: {e}")
            current_settings = {} # Start fresh if existing is corrupt

    # Merge new data. If new_settings_data contains 'primary_models', it will update that key.
    # If it contains other keys, they will be added/updated too.
    for key, value in new_settings_data.items():
        current_settings[key] = value

    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(current_settings, f, indent=2)
        print(f"Display settings saved successfully to {filepath}")
        return True
    except Exception as e:
        print(f"Error saving display settings to {filepath}: {e}")
        return False

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
