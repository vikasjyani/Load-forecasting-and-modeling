import os
from datetime import datetime
import pandas as pd
import json
from copy import deepcopy
from flask import current_app

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
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_scenario_name = "".join(c if c.isalnum() or c in ('_', '-') else '_' for c in scenario_name)
    if not safe_scenario_name:
        safe_scenario_name = "forecast_scenario"
        current_app.logger.warning(f"Original scenario name '{scenario_name}' was empty or invalid, using '{safe_scenario_name}'.")

    filename = f"demand_forecast_{safe_scenario_name}_{timestamp}.csv"
    output_dir = os.path.join(project_path_abs, 'results', 'demand_projection')

    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError as e:
        current_app.logger.error(f"OSError creating directory {output_dir} for forecast results: {e}", exc_info=True)
        return None # Cannot proceed if directory cannot be made

    filepath = os.path.join(output_dir, filename)

    try:
        results_df.to_csv(filepath, index=False, float_format='%.3f') # Standardize float format
        current_app.logger.info(f"Demand forecast results for scenario '{scenario_name}' saved to {filepath}")
        return filepath
    except (IOError, OSError) as e:
        current_app.logger.error(f"IOError/OSError saving forecast results for scenario '{scenario_name}' to {filepath}: {e}", exc_info=True)
        return None
    except Exception as e: # Catch any other unexpected errors during CSV writing
        current_app.logger.error(f"Unexpected error saving forecast results for scenario '{scenario_name}' to {filepath}: {e}", exc_info=True)
        return None

# ---- Demand Configuration File Handling ----

def get_demand_config_filepath(project_path_abs):
    """
    Constructs the path to the demand_config.json file.
    Logs an error if project_path_abs is None or invalid.
    """
    if not project_path_abs or not isinstance(project_path_abs, str):
        current_app.logger.error(f"Invalid project_path_abs '{project_path_abs}' provided to get_demand_config_filepath.")
        return None # Or raise ValueError
    return os.path.join(project_path_abs, 'config', 'demand_config.json')

def load_demand_config(project_path_abs):
    """
    Loads the demand forecast configuration from demand_config.json.
    Returns a default configuration if the file is not found or invalid.
    """
    config_filepath = get_demand_config_filepath(project_path_abs)
    if not config_filepath: # Error already logged by helper
        return deepcopy(DEFAULT_DEMAND_CONFIG)

    if not os.path.exists(config_filepath):
        current_app.logger.info(f"Demand config file not found at {config_filepath}. Returning default config.")
        return deepcopy(DEFAULT_DEMAND_CONFIG)
    try:
        with open(config_filepath, 'r', encoding='utf-8') as f: # Specify encoding
            config_data = json.load(f)

        # Basic validation: ensure top-level keys exist
        if not isinstance(config_data, dict) or \
           "global_settings" not in config_data or \
           "sector_models" not in config_data:
            current_app.logger.warning(f"Loaded demand config from {config_filepath} is malformed or missing essential keys ('global_settings', 'sector_models'). Returning default config.")
            # Optionally, backup/rename corrupted file here
            return deepcopy(DEFAULT_DEMAND_CONFIG) # Or merge, but safer to return default if structure is compromised

        current_app.logger.debug(f"Successfully loaded demand configuration from {config_filepath}")
        return config_data

    except json.JSONDecodeError as e:
        current_app.logger.error(f"Error decoding JSON from demand config file {config_filepath}: {e}", exc_info=True)
        return deepcopy(DEFAULT_DEMAND_CONFIG)
    except (IOError, OSError) as e:
        current_app.logger.error(f"IOError/OSError reading demand config file {config_filepath}: {e}", exc_info=True)
        return deepcopy(DEFAULT_DEMAND_CONFIG)
    except Exception as e: # Catch any other unexpected errors
        current_app.logger.error(f"Unexpected error loading demand config from {config_filepath}: {e}", exc_info=True)
        return deepcopy(DEFAULT_DEMAND_CONFIG)


def save_demand_config(project_path_abs, config_data):
    """
    Saves the given configuration data to demand_config.json.
    """
    config_filepath = get_demand_config_filepath(project_path_abs)
    if not config_filepath: # Error already logged by helper
        return False

    try:
        config_dir = os.path.dirname(config_filepath)
        if not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)
            current_app.logger.info(f"Created config directory {config_dir} for demand_config.json.")

        with open(config_filepath, 'w', encoding='utf-8') as f: # Specify encoding
            json.dump(config_data, f, indent=2) # Using indent=2 for consistency
        current_app.logger.info(f"Demand configuration saved successfully to {config_filepath}")
        return True
    except OSError as e: # Specifically for makedirs or file open/write issues related to OS
        current_app.logger.error(f"OSError saving demand configuration to {config_filepath}: {e}", exc_info=True)
        return False
    except (TypeError, ValueError) as e: # For json.dump errors if config_data is not serializable
        current_app.logger.error(f"JSON serialization error saving demand configuration to {config_filepath}: {e}", exc_info=True)
        return False
    except Exception as e: # Catch any other unexpected errors
        current_app.logger.error(f"Unexpected error saving demand configuration to {config_filepath}: {e}", exc_info=True)
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

    # Renamed arguments for clarity within this specific function's scope
    # scenario_name_for_output_file = scenario_name_from_form (original name from run)
    # scenario_name_for_settings_lookup = scenario_base_name_for_settings (timestamped base)

    display_settings = load_display_settings(project_path_abs, scenario_base_name_for_settings) # load_display_settings is already refactored
    primary_models = display_settings.get('primary_models', {})

    if not primary_models:
        current_app.logger.info(f"No primary models selected in display_settings for scenario base '{scenario_base_name_for_settings}'. Consolidated file will not be generated based on primary model selections.")
        return None

    try:
        main_df = pd.read_csv(main_forecast_filepath)
    except FileNotFoundError:
        current_app.logger.error(f"Main forecast file not found at {main_forecast_filepath} for consolidation.", exc_info=True)
        return None
    except pd.errors.EmptyDataError:
        current_app.logger.warning(f"Main forecast file {main_forecast_filepath} is empty. No consolidated results generated.")
        return None
    except pd.errors.ParserError as e:
        current_app.logger.error(f"Error parsing main forecast CSV file {main_forecast_filepath}: {e}", exc_info=True)
        return None
    except Exception as e:
        current_app.logger.error(f"Unexpected error reading main forecast file {main_forecast_filepath}: {e}", exc_info=True)
        return None

    consolidated_rows = []
    try:
        available_sectors_in_main_df = main_df['Sector'].unique()

        for sector_name in available_sectors_in_main_df:
            chosen_model = primary_models.get(sector_name)

            if chosen_model and chosen_model != "":
                sector_model_df = main_df[
                    (main_df['Sector'] == sector_name) &
                    (main_df['Model'] == chosen_model)
                ]

                if not sector_model_df.empty:
                    cols_to_select = ['Year', 'Sector', 'Model', 'Value']
                    if 'Lower_Bound' in sector_model_df.columns: cols_to_select.append('Lower_Bound')
                    if 'Upper_Bound' in sector_model_df.columns: cols_to_select.append('Upper_Bound')
                    if 'Comment' in sector_model_df.columns: cols_to_select.append('Comment')

                    temp_df = sector_model_df[cols_to_select].copy()
                    consolidated_rows.append(temp_df)
                else:
                    current_app.logger.warning(f"No data found in main forecast for explicitly selected primary model '{chosen_model}' for sector '{sector_name}' in scenario '{scenario_base_name_for_settings}'.")
            else:
                current_app.logger.info(f"Sector '{sector_name}' in scenario '{scenario_base_name_for_settings}' will not be included in consolidated results as no specific primary model was selected (or was set to Auto).")
    except KeyError as e:
        current_app.logger.error(f"KeyError during consolidation data processing for scenario '{scenario_base_name_for_settings}'. Expected column '{e}' not found in main_df.", exc_info=True)
        return None
    except Exception as e: # Catch other pandas or general errors
        current_app.logger.error(f"Unexpected error during data consolidation for scenario '{scenario_base_name_for_settings}': {e}", exc_info=True)
        return None


    if not consolidated_rows:
        current_app.logger.warning(f"No data to consolidate for scenario '{scenario_name_from_form}' based on primary model selections. Consolidated file will not be saved/updated.")
        return None

    consolidated_df = pd.concat(consolidated_rows, ignore_index=True)

    safe_output_scenario_name = "".join(c if c.isalnum() or c in ('_', '-') else '_' for c in scenario_name_from_form)
    if not safe_output_scenario_name:
        safe_output_scenario_name = "default_scenario"
        current_app.logger.warning(f"Original scenario name for output '{scenario_name_from_form}' was empty or invalid, using '{safe_output_scenario_name}'.")

    consolidated_filename = f"consolidated_demand_forecast_{safe_output_scenario_name}.csv"
    output_dir = os.path.join(project_path_abs, 'results', 'demand_projection')
    # os.makedirs not needed here as save_demand_forecast_results should have created it.
    consolidated_filepath = os.path.join(output_dir, consolidated_filename)

    try:
        consolidated_df.to_csv(consolidated_filepath, index=False, float_format='%.3f') # Standardize float format
        current_app.logger.info(f"Consolidated results (from primary selections) for scenario '{scenario_name_from_form}' saved to {consolidated_filepath}")
        return consolidated_filepath
    except (IOError, OSError) as e:
        current_app.logger.error(f"IOError/OSError saving primary-selection consolidated results to {consolidated_filepath}: {e}", exc_info=True)
        return None
    except Exception as e: # Catch any other unexpected errors during CSV writing
        current_app.logger.error(f"Unexpected error saving primary-selection consolidated results to {consolidated_filepath}: {e}", exc_info=True)
        return None

# ---- Display Settings File Handling ----

def get_display_settings_filepath(project_path_abs, scenario_base_name):
    """
    Constructs the path to the display_settings_SCENARIO.json file.
    Logs an error if project_path_abs or scenario_base_name is None or invalid.
    """
    if not all([project_path_abs, scenario_base_name, isinstance(project_path_abs, str), isinstance(scenario_base_name, str)]):
        current_app.logger.error(f"Invalid arguments for get_display_settings_filepath: project_path='{project_path_abs}', scenario_base='{scenario_base_name}'.")
        return None
    results_dir = os.path.join(project_path_abs, 'results', 'demand_projection')
    return os.path.join(results_dir, f"display_settings_{scenario_base_name}.json")

def load_display_settings(project_path_abs, scenario_base_name):
    """
    Loads display settings for a given scenario.
    Returns an empty dictionary if the file is not found or is invalid.
    """
    filepath = get_display_settings_filepath(project_path_abs, scenario_base_name)
    if not filepath: # Error already logged by helper
        return {}

    if not os.path.exists(filepath):
        current_app.logger.info(f"Display settings file not found for scenario '{scenario_base_name}' at {filepath}. Returning empty settings.")
        return {}

    try:
        with open(filepath, 'r', encoding='utf-8') as f: # Specify encoding
            settings = json.load(f)
        if not isinstance(settings, dict):
            current_app.logger.warning(f"Display settings data in {filepath} for scenario '{scenario_base_name}' is not a dictionary. Returning empty settings.")
            return {}
        current_app.logger.debug(f"Successfully loaded display settings for scenario '{scenario_base_name}' from {filepath}")
        return settings
    except json.JSONDecodeError as e:
        current_app.logger.error(f"Error decoding JSON from display settings file {filepath} for scenario '{scenario_base_name}': {e}", exc_info=True)
        return {}
    except (IOError, OSError) as e:
        current_app.logger.error(f"IOError/OSError reading display settings file {filepath} for scenario '{scenario_base_name}': {e}", exc_info=True)
        return {}
    except Exception as e: # Catch any other unexpected errors
        current_app.logger.error(f"Unexpected error loading display settings for scenario '{scenario_base_name}' from {filepath}: {e}", exc_info=True)
        return {}


def save_display_settings(project_path_abs, scenario_base_name, new_settings_data):
    """
    Saves display settings, merging new_settings_data with existing data.
    Specifically, new_settings_data is expected to be a dict like {'primary_models': {...}}
    or {'td_losses': [...]}, etc.
    """
    filepath = get_display_settings_filepath(project_path_abs, scenario_base_name)
    if not filepath: # Error already logged by helper
        return False

    current_settings = {}
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f: # Specify encoding
                current_settings = json.load(f)
            if not isinstance(current_settings, dict): # Ensure what we loaded is a dict
                current_app.logger.warning(f"Existing display settings file {filepath} for scenario '{scenario_base_name}' is not a valid JSON object. It will be overwritten.")
                current_settings = {}
        except json.JSONDecodeError as e:
            current_app.logger.warning(f"Could not decode JSON from existing display settings file {filepath} for scenario '{scenario_base_name}'. It will be overwritten. Error: {e}", exc_info=True)
            current_settings = {}
        except (IOError, OSError) as e:
            current_app.logger.error(f"IOError/OSError reading existing display settings file {filepath} for scenario '{scenario_base_name}': {e}. Attempting to overwrite.", exc_info=True)
            current_settings = {} # Attempt to overwrite if unreadable
        except Exception as e: # Catch any other unexpected errors
             current_app.logger.error(f"Unexpected error reading existing display settings for scenario '{scenario_base_name}' from {filepath}: {e}. Attempting to overwrite.", exc_info=True)
             current_settings = {}


    # Merge new data. If new_settings_data contains 'primary_models', it will update that key.
    # If it contains other keys (e.g. 'td_losses'), they will be added/updated too.
    for key, value in new_settings_data.items():
        current_settings[key] = value # This replaces keys like 'primary_models' or 'td_losses' entirely if present in new_settings_data

    try:
        # Ensure the directory exists (results/demand_projection)
        # get_display_settings_filepath constructs path in results_dir, which should exist if main forecast was saved.
        # For safety, ensure dir for settings file itself.
        results_dir = os.path.dirname(filepath)
        os.makedirs(results_dir, exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f: # Specify encoding
            json.dump(current_settings, f, indent=2)
        current_app.logger.info(f"Display settings for scenario '{scenario_base_name}' saved successfully to {filepath}")
        return True
    except OSError as e:
        current_app.logger.error(f"OSError saving display settings for scenario '{scenario_base_name}' to {filepath}: {e}", exc_info=True)
        return False
    except (TypeError, ValueError) as e: # For json.dump errors
        current_app.logger.error(f"JSON serialization error saving display settings for scenario '{scenario_base_name}' to {filepath}: {e}", exc_info=True)
        return False
    except Exception as e: # Catch any other unexpected errors
        current_app.logger.error(f"Unexpected error saving display settings for scenario '{scenario_base_name}' to {filepath}: {e}", exc_info=True)
        return False

# ---- Input Excel File Validation and Parsing ----

def validate_and_parse_demand_input_excel(file_path):
    REQUIRED_SHEET_HISTORICAL = 'Historical_Data'
    # Minimum required columns. More specific demand columns will be identified.
    REQUIRED_COLUMNS_HISTORICAL = ['Year']

    try:
        excel_file = pd.ExcelFile(file_path)
    except FileNotFoundError:
        current_app.logger.error(f"Validation Error: File not found at {file_path}", exc_info=True) # Log stack trace for unexpected not found
        return False, f"Validation Error: File not found at specified path.", None
    except ValueError as e:
        current_app.logger.error(f"Validation Error: Could not read Excel file {file_path}. It might be corrupted or not a valid .xlsx file. Detail: {e}", exc_info=True)
        return False, f"Validation Error: Could not read Excel file. It might be corrupted or not a valid .xlsx file.", None
    except Exception as e:
        current_app.logger.error(f"Validation Error: Unexpected error reading Excel file {file_path}: {e}", exc_info=True)
        return False, f"Validation Error: Unexpected error reading Excel file.", None

    available_sheets = excel_file.sheet_names
    if REQUIRED_SHEET_HISTORICAL not in available_sheets:
        msg = f"Validation Error: Missing required sheet: '{REQUIRED_SHEET_HISTORICAL}'. Found sheets: {', '.join(available_sheets) if available_sheets else 'None'}"
        current_app.logger.warning(msg + f" (File: {file_path})")
        return False, msg, None

    try:
        historical_df = excel_file.parse(REQUIRED_SHEET_HISTORICAL)
    except Exception as e:
        msg = f"Validation Error: Could not parse '{REQUIRED_SHEET_HISTORICAL}' sheet. Error: {e}"
        current_app.logger.error(msg + f" (File: {file_path})", exc_info=True)
        return False, msg, None

    missing_cols = [col for col in REQUIRED_COLUMNS_HISTORICAL if col not in historical_df.columns]
    if missing_cols:
        cols_found_str = ', '.join(list(historical_df.columns))
        msg = f"Validation Error: Missing required column(s) in '{REQUIRED_SHEET_HISTORICAL}' sheet: {', '.join(missing_cols)}. Found columns: {cols_found_str}"
        current_app.logger.warning(msg + f" (File: {file_path})")
        return False, msg, None

    if historical_df.empty:
        msg = f"Validation Error: '{REQUIRED_SHEET_HISTORICAL}' sheet is empty."
        current_app.logger.warning(msg + f" (File: {file_path})")
        return False, msg, None

    try:
        if not pd.api.types.is_numeric_dtype(historical_df['Year']):
            msg = f"Validation Error: 'Year' column in '{REQUIRED_SHEET_HISTORICAL}' must be numeric. Found type: {historical_df['Year'].dtype}."
            current_app.logger.warning(msg + f" (File: {file_path})")
            return False, msg, None

        if historical_df['Year'].duplicated().any():
            msg = f"Validation Error: Duplicate values found in 'Year' column in '{REQUIRED_SHEET_HISTORICAL}'. Years must be unique."
            current_app.logger.warning(msg + f" (File: {file_path})")
            return False, msg, None

        demand_columns = []
        for col in historical_df.columns:
            if col.lower() != 'year'.lower():
                if pd.api.types.is_numeric_dtype(historical_df[col]):
                    demand_columns.append(col)
                else:
                    current_app.logger.info(f"Info: Column '{col}' in '{REQUIRED_SHEET_HISTORICAL}' from {file_path} is not numeric and not 'Year'. It will not be treated as a demand column.")

        if not demand_columns:
            msg = f"Validation Error: No numeric demand data columns found in '{REQUIRED_SHEET_HISTORICAL}' sheet (besides 'Year'). Ensure demand columns are numeric."
            current_app.logger.warning(msg + f" (File: {file_path})")
            return False, msg, None

    except KeyError as e: # Should not happen if missing_cols check is robust, but for safety
        msg = f"Validation Error: Expected column '{e}' not found during data type checks for '{REQUIRED_SHEET_HISTORICAL}' sheet."
        current_app.logger.error(msg + f" (File: {file_path})", exc_info=True)
        return False, msg, None
    except Exception as e: # Catch other pandas/numpy errors during type checks
        msg = f"Validation Error: Unexpected error during data validation of '{REQUIRED_SHEET_HISTORICAL}' sheet: {e}"
        current_app.logger.error(msg + f" (File: {file_path})", exc_info=True)
        return False, msg, None

    assumptions_df = None
    REQUIRED_SHEET_ASSUMPTIONS = 'Assumptions'
    if REQUIRED_SHEET_ASSUMPTIONS in available_sheets:
        try:
            assumptions_df = excel_file.parse(REQUIRED_SHEET_ASSUMPTIONS)
            if assumptions_df.empty:
                 current_app.logger.info(f"Info: '{REQUIRED_SHEET_ASSUMPTIONS}' sheet is present but empty in {file_path}.")
            elif not all(col in assumptions_df.columns for col in ['Parameter', 'Value']):
                 current_app.logger.warning(f"Warning: '{REQUIRED_SHEET_ASSUMPTIONS}' sheet in {file_path} is present but might be missing 'Parameter' or 'Value' columns.")
        except Exception as e:
            current_app.logger.error(f"Error parsing '{REQUIRED_SHEET_ASSUMPTIONS}' sheet from {file_path}: {e}", exc_info=True)
            assumptions_df = None
    else:
        current_app.logger.info(f"Info: Optional sheet '{REQUIRED_SHEET_ASSUMPTIONS}' not found in {file_path}.")


    parsed_data = {
        'historical_data': historical_df,
        'identified_demand_columns': demand_columns
    }
    if assumptions_df is not None:
        parsed_data['assumptions_data'] = assumptions_df

    success_msg = f"File validated successfully. Identified demand columns: {', '.join(demand_columns)}."
    current_app.logger.info(success_msg + f" (File: {file_path})")
    return True, success_msg, parsed_data
