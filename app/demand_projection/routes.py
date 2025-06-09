import os
from flask import current_app, flash, redirect, render_template, request, url_for, send_from_directory, jsonify
from werkzeug.utils import secure_filename
from app.demand_projection import bp
from app.utils.file_manager import ProjectManager, validate_file_upload
from .file_handlers import load_demand_config, save_demand_config, validate_and_parse_demand_input_excel, save_demand_forecast_results, MODEL_OPTIONS as FH_MODEL_OPTIONS, DEFAULT_DEMAND_CONFIG
from .models import forecast_slr, forecast_wam, forecast_mlr
import os
import pandas as pd
from datetime import datetime
import json # For loading display_settings.json
import re # For scenario name extraction

# Make model options available to routes in this blueprint
AVAILABLE_MODELS_CONFIG = FH_MODEL_OPTIONS


@bp.route('/upload_page') # This will now be the configuration page as well
def upload_page():
    project_path_abs = current_app.config.get('CURRENT_PROJECT_PATH_ABS')
    available_sectors = []
    demand_config = {}
    input_file_validated = False
    excel_file_exists = False
    excel_validation_message = "Excel file not found or not yet uploaded."

    if not project_path_abs:
        flash("No project loaded. Please load or create a project first.", "warning")
        # Still render the page, but with limited functionality
        return render_template('upload_demand_data.html',
                               active_project_path=project_path_abs,
                               excel_file_exists=excel_file_exists,
                               input_file_validated=input_file_validated,
                               available_sectors=available_sectors,
                               demand_config=deepcopy(DEFAULT_DEMAND_CONFIG), # from file_handlers via import
                               model_options=AVAILABLE_MODELS_CONFIG,
                               excel_validation_message=excel_validation_message)

    # Try to load existing config first
    demand_config = load_demand_config(project_path_abs)

    # Check for input file and validate it to get sectors
    input_file_path = os.path.join(project_path_abs, 'inputs', 'input_demand_file.xlsx')
    if os.path.exists(input_file_path):
        excel_file_exists = True
        is_valid, msg, parsed_data = validate_and_parse_demand_input_excel(input_file_path)
        if is_valid and parsed_data:
            available_sectors = parsed_data.get('identified_demand_columns', [])
            input_file_validated = True
            excel_validation_message = msg # Success message from validation
             # If config is empty for sectors, pre-populate it
            if not demand_config.get("sector_models"):
                for sector in available_sectors:
                    demand_config["sector_models"][sector] = [] # Initialize if not present
        else:
            # File exists but is invalid
            input_file_validated = False
            excel_validation_message = f"Previously uploaded Excel file is invalid: {msg}"
            flash(excel_validation_message, "danger")
    else:
        excel_file_exists = False
        excel_validation_message = "input_demand_file.xlsx not found in project's 'inputs' directory. Please upload it first."
        # flash(excel_validation_message, "info") # Potentially too noisy

    return render_template('upload_demand_data.html',
                           active_project_path=project_path_abs,
                           excel_file_exists=excel_file_exists,
                           input_file_validated=input_file_validated,
                           available_sectors=available_sectors,
                           demand_config=demand_config,
                           model_options=AVAILABLE_MODELS_CONFIG,
                           excel_validation_message=excel_validation_message,
                           datetime=datetime) # Pass datetime for use in template default scenario name


@bp.route('/save_demand_configuration', methods=['POST'])
def save_demand_configuration_route():
    project_path_abs = current_app.config.get('CURRENT_PROJECT_PATH_ABS')
    if not project_path_abs:
        flash('No project loaded. Cannot save configuration.', 'error')
        return redirect(url_for('main.home'))

    # Re-get available_sectors from the validated excel file to ensure consistency
    # This is important because form submission might not contain all sector names if some had no models enabled.
    available_sectors = []
    input_file_path = os.path.join(project_path_abs, 'inputs', 'input_demand_file.xlsx')
    if os.path.exists(input_file_path):
        is_valid, msg, parsed_data = validate_and_parse_demand_input_excel(input_file_path)
        if is_valid and parsed_data:
            available_sectors = parsed_data.get('identified_demand_columns', [])
        else:
            flash(f"Cannot save configuration: input_demand_file.xlsx is missing or invalid: {msg}", 'danger')
            return redirect(url_for('demand_projection.upload_page'))
    else:
        flash("Cannot save configuration: input_demand_file.xlsx not found.", 'danger')
        return redirect(url_for('demand_projection.upload_page'))

    if not available_sectors:
        flash("Cannot save configuration: No demand sectors identified from the input file.", 'warning')
        return redirect(url_for('demand_projection.upload_page'))

    current_config = load_demand_config(project_path_abs) # Load existing to preserve global_settings
    new_sector_models_config = {}

    for sector in available_sectors:
        new_sector_models_config[sector] = []
        for model_code, model_detail in AVAILABLE_MODELS_CONFIG.items():
            is_enabled = request.form.get(f"{sector}|{model_code}|enabled") == "on"
            params = {}
            if is_enabled:
                for param_name, param_attrs in model_detail.get("params", {}).items():
                    form_field_name = f"{sector}|{model_code}|{param_name}"
                    # Special handling for WAM window_size_option
                    if model_code == "WAM" and param_name == "window_size_option":
                        wam_option_val = request.form.get(form_field_name) # This is 'window_size_option' itself
                        actual_window_size = param_attrs.get("custom_input_default", 3) # Fallback default

                        custom_input_field_name = f"{sector}|{model_code}|{param_attrs.get('custom_input_name')}"

                        if wam_option_val == "custom":
                            try:
                                actual_window_size = int(request.form.get(custom_input_field_name, actual_window_size))
                            except (ValueError, TypeError):
                                flash(f"Invalid custom window size for WAM in {sector}. Using default {actual_window_size}.", "warning")
                        elif wam_option_val: # "3", "5", "7"
                            try:
                                actual_window_size = int(wam_option_val)
                            except ValueError:
                                flash(f"Invalid pre-set window size option '{wam_option_val}' for WAM in {sector}. Using default {actual_window_size}.", "warning")

                        # Validate against min/max if provided
                        min_val = param_attrs.get("custom_input_min", 1)
                        max_val = param_attrs.get("custom_input_max", 20)
                        if not (min_val <= actual_window_size <= max_val):
                            flash(f"Window size {actual_window_size} for WAM in {sector} is outside allowed range ({min_val}-{max_val}). Clamping to nearest valid.", "warning")
                            actual_window_size = max(min_val, min(actual_window_size, max_val))

                        params["window_size"] = actual_window_size # Store the resolved numeric window_size
                        # We don't store window_size_option or window_size_custom in JSON, only the numeric window_size.
                        continue # Move to next param for WAM, as window_size_option is fully processed.

                    # General parameter processing
                    raw_value = request.form.get(form_field_name)
                    if raw_value is not None and raw_value != '':
                        try:
                            if param_attrs.get("type") == "number":
                                params[param_name] = int(raw_value)
                            elif param_attrs.get("type") == "float":
                                val = float(raw_value)
                                p_min = param_attrs.get("min")
                                p_max = param_attrs.get("max")
                                if p_min is not None and val < p_min: val = p_min
                                if p_max is not None and val > p_max: val = p_max
                                params[param_name] = val
                            elif param_attrs.get("type") == "checkbox": # For boolean params if any
                                params[param_name] = raw_value == "on"
                            else: # text
                                params[param_name] = str(raw_value)
                        except ValueError:
                            params[param_name] = param_attrs.get("default")
                            flash(f"Invalid value for '{param_attrs.get('label', param_name)}' in sector '{sector}' for model '{model_code}'. Using default: '{params[param_name]}'.", "warning")
                    else: # If field not in form or empty, use default
                         params[param_name] = param_attrs.get("default")

            new_sector_models_config[sector].append({
                "model_name": model_code,
                "enabled": is_enabled,
                "parameters": params if is_enabled else {p_name: p_attrs.get("default") for p_name, p_attrs in model_detail.get("params", {}).items()}
            })

    current_config['sector_models'] = new_sector_models_config

    # Handle global settings from form
    current_config['global_settings']['target_years'] = [int(y.strip()) for y in request.form.get('global_target_years', '').split(',') if y.strip().isdigit()]
    current_config['global_settings']['exclude_covid_years'] = request.form.get('global_exclude_covid') == 'on'
    try:
        start_year_str = request.form.get('global_forecast_start_year', '').strip()
        current_config['global_settings']['forecast_start_year'] = int(start_year_str) if start_year_str else None
    except ValueError:
        current_config['global_settings']['forecast_start_year'] = None
        flash("Invalid Forecast Start Year provided, it has been ignored.", "warning")


    if save_demand_config(project_path_abs, current_config):
        flash('Demand forecast configuration saved successfully.', 'success')
    else:
        flash('Error saving demand forecast configuration.', 'error')

    return redirect(url_for('demand_projection.upload_page'))

@bp.route('/run_forecast', methods=['POST'])
def run_forecast_route():
    project_path_abs = current_app.config.get('CURRENT_PROJECT_PATH_ABS')
    if not project_path_abs:
        flash('No project loaded. Cannot run forecast.', 'error')
        return redirect(url_for('main.home'))

    scenario_name = request.form.get('scenario_name', '').strip()
    if not scenario_name:
        scenario_name = f"forecast_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        flash(f"Scenario name was empty, defaulted to '{scenario_name}'.", "info")

    # Load configurations and data
    demand_config = load_demand_config(project_path_abs)
    if not demand_config: # Should always return default if not found, but check anyway
        flash("Demand configuration not found or invalid. Please configure models first.", "danger")
        return redirect(url_for('demand_projection.upload_page'))

    input_excel_path = os.path.join(project_path_abs, 'inputs', 'input_demand_file.xlsx')
    if not os.path.exists(input_excel_path):
        flash(f"Input Excel file (input_demand_file.xlsx) not found in project '{current_app.config.get('CURRENT_PROJECT_NAME')}'.", "danger")
        return redirect(url_for('demand_projection.upload_page'))

    is_valid_excel, msg_excel, parsed_excel_data = validate_and_parse_demand_input_excel(input_excel_path)
    if not is_valid_excel:
        flash(f"Input Excel file validation failed: {msg_excel}", "danger")
        return redirect(url_for('demand_projection.upload_page'))

    historical_df = parsed_excel_data['historical_data']
    identified_demand_columns = parsed_excel_data['identified_demand_columns']

    configured_target_years = demand_config.get('global_settings', {}).get('target_years', [])
    if not configured_target_years:
        flash("Target years for forecasting are not configured in global settings of demand_config.json.", "danger")
        return redirect(url_for('demand_projection.upload_page'))

    # Optional: Use forecast_start_year from config to filter historical_df if needed
    # forecast_start_year = demand_config.get('global_settings', {}).get('forecast_start_year')
    # exclude_covid_years = demand_config.get('global_settings', {}).get('exclude_covid_years', False)
    # Logic to filter historical_df based on these settings can be added here.

    all_forecast_results = []
    for sector_name in identified_demand_columns:
        historical_sector_series_full = historical_df.set_index('Year')[sector_name].sort_index().dropna()
        is_user_forecasted = False

        if not historical_sector_series_full.empty and configured_target_years:
            min_target_year = min(configured_target_years)
            max_target_year = max(configured_target_years)

            if historical_sector_series_full.index.max() >= max_target_year:
                user_forecast_values_for_target_years = []
                all_target_years_present_with_data = True
                for t_year in configured_target_years:
                    if t_year in historical_sector_series_full.index and pd.notna(historical_sector_series_full.loc[t_year]):
                        user_forecast_values_for_target_years.append(historical_sector_series_full.loc[t_year])
                    else:
                        all_target_years_present_with_data = False
                        break

                if all_target_years_present_with_data:
                    is_user_forecasted = True
                    user_forecast_data = []
                    for i, t_year in enumerate(configured_target_years):
                        val = user_forecast_values_for_target_years[i]
                        user_forecast_data.append({
                            'Year': t_year, 'Sector': sector_name, 'Model': 'User_Provided',
                            'Value': val, 'Lower_Bound': val, 'Upper_Bound': val, # No uncertainty for user data
                            'Comment': 'Data taken directly from input file for forecast period.'
                        })
                    forecast_df = pd.DataFrame(user_forecast_data)
                    all_forecast_results.append(forecast_df)
                    flash(f"Sector '{sector_name}' uses user-provided data for the forecast period {min_target_year}-{max_target_year}.", "info")

        if is_user_forecasted:
            continue # Move to the next sector

        # If not user_forecasted, proceed with configured models
        if sector_name not in demand_config.get('sector_models', {}):
            flash(f"No model configuration found for sector '{sector_name}'. Skipping automated forecast.", "warning")
            continue

        min_hist_year_for_model_input = min(configured_target_years) if configured_target_years else (historical_sector_series_full.index.max() + 1 if not historical_sector_series_full.empty else datetime.now().year)
        training_data_series = historical_sector_series_full[historical_sector_series_full.index < min_hist_year_for_model_input]

        # TODO: Add logic here to handle exclude_covid_years if needed, by filtering training_data_series

        for model_config in demand_config['sector_models'].get(sector_name, []):
            if model_config.get('enabled', False): # is_user_forecasted check is already done
                model_name = model_config['model_name']
                params = model_config.get('parameters', {})
                forecast_df = None

                try:
                    if model_name == 'SLR':
                        forecast_df = forecast_slr(training_data_series, configured_target_years, sector_name, **params)
                    elif model_name == 'WAM':
                        forecast_df = forecast_wam(training_data_series, configured_target_years, sector_name, **params)
                    elif model_name == 'MLR':
                        # MLR needs historical data for independent vars as well.
                        # The training_data_series for dependent var is already filtered up to min_hist_year_for_model_input.
                        # historical_df (full df) needs to be passed, and MLR model internally should split.
                        # Or, we prepare a specific historical_df_for_mlr_training.
                        # For MLR, the independent variables also need to be from the historical part for training.
                        # The current forecast_mlr is a placeholder.
                        # When implementing real MLR, ensure it uses data prior to min_hist_year_for_model_input for training.
                        # And it will need future assumptions for independent variables for the prediction part.
                        # For now, we pass the full historical_df as the placeholder expects it.
                        # This part needs refinement when MLR is fully implemented.
                        # Assuming independent_vars are stored in params like {'independent_vars': 'GDP,Population'}
                        # This needs careful setup in config and model.
                        iv_str = params.get('independent_vars', '')
                        iv_list = [v.strip() for v in iv_str.split(',') if v.strip()]
                        if not iv_list:
                             flash(f"MLR for {sector_name} enabled but no independent variables configured. Skipping.", "warning")
                             continue
                        # Check if all independent variables are in historical_df columns
                        missing_iv = [v for v in iv_list if v not in historical_df.columns]
                        if missing_iv:
                            flash(f"MLR for {sector_name} skipped. Missing independent variable(s) in historical data: {', '.join(missing_iv)}", "warning")
                            continue

                        # Pass only relevant columns for MLR, including the target sector and independent vars
                        mlr_input_df = historical_df[['Year', sector_name] + iv_list]
                        forecast_df = forecast_mlr(mlr_input_df, configured_target_years, sector_name, independent_vars=iv_list, **params)

                    if forecast_df is not None and not forecast_df.empty:
                        all_forecast_results.append(forecast_df)
                    elif forecast_df is not None and forecast_df.empty:
                         flash(f"Model {model_name} for sector {sector_name} produced empty results.", "info")
                except Exception as e:
                    flash(f"Error running model {model_name} for sector {sector_name}: {e}", "danger")
                    # Continue to next model/sector

    if all_forecast_results:
        final_results_df = pd.concat(all_forecast_results, ignore_index=True)
        output_filepath = save_demand_forecast_results(project_path_abs, scenario_name, final_results_df)
        if output_filepath:
            flash(f"Forecast scenario '{scenario_name}' run successfully. Results saved to {os.path.basename(output_filepath)}", 'success')
            try:
                pm = ProjectManager(current_app.config['PROJECT_ROOT_ABS'])
                project_folder = os.path.basename(project_path_abs) # e.g. 'my_project1'
                metadata_update = {
                    'last_forecast_run': {
                        'scenario': scenario_name,
                        'timestamp': datetime.now().isoformat() + 'Z',
                        'file': os.path.basename(output_filepath),
                        'module': 'demand_projection' # For context if other modules also save results
                    }
                }
                # Append to a list of runs if you want to keep history, or overwrite like here
                # existing_metadata = pm.get_project_metadata(project_folder)
                # if 'forecast_runs' not in existing_metadata: existing_metadata['forecast_runs'] = []
                # existing_metadata['forecast_runs'].append(metadata_update['last_forecast_run'])
                # pm.update_project_metadata(project_folder, {'forecast_runs': existing_metadata['forecast_runs']})

                if pm.update_project_metadata(project_folder, metadata_update):
                    print(f"Project metadata updated successfully for {project_folder}")
                else:
                    flash(f"Failed to update project metadata for {project_folder} (update_project_metadata returned False)", "warning")


                # Attempt to generate consolidated results using primary model selections
                # Derive scenario_base_name for settings from the output_filepath (which includes timestamp)
                # output_filepath is like: .../demand_forecast_ScenarioA_20231115103000.csv
                scenario_base_name_for_settings = os.path.basename(output_filepath).replace('demand_forecast_', '').replace('.csv', '')

                consolidated_output_filepath = generate_consolidated_results(
                    project_path_abs,
                    scenario_name, # This is scenario_name_from_form, used for naming the consolidated output
                    output_filepath,
                    scenario_base_name_for_settings # Used for loading display_settings.json
                )
                if consolidated_output_filepath:
                    flash(f"Consolidated results (based on primary models) for scenario '{scenario_name}' generated: {os.path.basename(consolidated_output_filepath)}", 'info')
                    # Optionally, update project metadata again with consolidated file info
                    # This could be added to the 'last_forecast_run' dict or as a separate key.
                    metadata_update['last_forecast_run']['consolidated_file'] = os.path.basename(consolidated_output_filepath)
                    pm.update_project_metadata(project_folder, metadata_update) # Update again with consolidated file info
                else:
                    flash(f"Could not generate consolidated results for scenario '{scenario_name}'. Check logs.", 'warning')

            except Exception as e_meta: # Catch errors from ProjectManager or metadata logic
                flash(f"Failed to update project metadata after saving forecast: {e_meta}", "warning")
        else:
            flash(f"Forecast scenario '{scenario_name}' run, but failed to save results (main results file not created).", 'error')
    else:
        flash("No forecast results generated. Check model configurations, input data, and target years.", 'warning')

    return redirect(url_for('demand_projection.upload_page'))


@bp.route('/results_page')
def results_page_route():
    project_path_abs = current_app.config.get('CURRENT_PROJECT_PATH_ABS')
    if not project_path_abs:
        flash('No project loaded. Cannot display results.', 'warning')
        return redirect(url_for('main.home'))

    project_folder = os.path.basename(project_path_abs)
    pm = ProjectManager(current_app.config['PROJECT_ROOT_ABS'])
    metadata = pm.get_project_metadata(project_folder)

    results_files = []
    scenario_name_display = "N/A"

    if metadata:
        last_forecast_run = metadata.get('last_forecast_run', {})
        if last_forecast_run:
            scenario_name_display = last_forecast_run.get('scenario', 'N/A')
            results_dir = os.path.join(project_path_abs, 'results', 'demand_projection')

            main_file = last_forecast_run.get('file')
            consolidated_file = last_forecast_run.get('consolidated_file')

            if main_file and os.path.exists(os.path.join(results_dir, main_file)):
                results_files.append({
                    'name': main_file,
                    'type': 'Detailed Forecast CSV (All Models)',
                    'scenario': scenario_name_display
                })
            if consolidated_file and os.path.exists(os.path.join(results_dir, consolidated_file)):
                results_files.append({
                    'name': consolidated_file,
                    'type': 'Consolidated Forecast CSV (Primary Models)',
                    'scenario': scenario_name_display
                })
        else:
            flash("No forecast run metadata found. Run a forecast to see results.", "info")
    else:
        flash("Project metadata not found. Cannot display results.", "error")
        # This case might indicate a more significant issue if a project is loaded but has no metadata.

    return render_template('results_demand.html',
                           available_scenarios=available_scenarios,
                           selected_scenario_id=selected_scenario_id,
                           results_files=results_files_for_selected_scenario,
                           scenario_name_display=display_scenario_name,
                           project_name=current_app.config.get('CURRENT_PROJECT_NAME'),
                           active_consolidated_file=active_scenario_consolidated_file,
                           active_display_settings_file=active_scenario_display_settings_file)


@bp.route('/download_result/<filename>')
def download_result_route(filename):
    project_path_abs = current_app.config.get('CURRENT_PROJECT_PATH_ABS')
    if not project_path_abs:
        flash('No project loaded. Cannot download file.', 'error')
        return redirect(url_for('main.home'))

    results_dir = os.path.join(project_path_abs, 'results', 'demand_projection')
    safe_filename = secure_filename(filename) # Important for security

    try:
        return send_from_directory(results_dir, safe_filename, as_attachment=True)
    except FileNotFoundError:
        flash(f"File '{safe_filename}' not found in results directory.", "error")
        return redirect(url_for('.results_page_route')) # Redirect back to results page
    except Exception as e:
        flash(f"An error occurred while trying to download '{safe_filename}': {e}", "error")
        return redirect(url_for('.results_page_route'))


@bp.route('/scenario_results/<path:scenario_filename>/sector_detail') # Use <path:..> for filenames with potential slashes/dots
def view_sector_detail_route(scenario_filename):
    project_path_abs = current_app.config.get('CURRENT_PROJECT_PATH_ABS')
    if not project_path_abs:
        flash('No project loaded. Please load or create one first.', 'warning')
        return redirect(url_for('main.home'))

    results_dir = os.path.join(project_path_abs, 'results', 'demand_projection')

    # Validate scenario_filename against discovered files to prevent path traversal using secure_filename as a base
    # This ensures scenario_filename is a real, expected file.
    # First, get a list of valid detailed forecast files.
    valid_detailed_files = []
    if os.path.exists(results_dir):
        for f_name in os.listdir(results_dir):
            if f_name.startswith('demand_forecast_') and f_name.endswith('.csv'):
                valid_detailed_files.append(f_name)

    safe_scenario_filename = secure_filename(scenario_filename) # Basic sanitization
    if safe_scenario_filename not in valid_detailed_files:
        flash(f"Invalid or non-existent scenario file specified: {safe_scenario_filename}", "danger")
        return redirect(url_for('.results_page_route')) # Redirect to scenario selection

    main_forecast_filepath = os.path.join(results_dir, safe_scenario_filename)

    try:
        main_df = pd.read_csv(main_forecast_filepath)
    except FileNotFoundError:
        flash(f"Scenario forecast file not found: {safe_scenario_filename}", "danger")
        return redirect(url_for('.results_page_route'))
    except Exception as e:
        flash(f"Error reading scenario file {safe_scenario_filename}: {e}", "danger")
        return redirect(url_for('.results_page_route'))

    if main_df.empty:
        flash(f"Scenario file {safe_scenario_filename} is empty.", "warning")
        # Allow viewing empty state or redirect

    available_sectors_sorted = sorted(main_df['Sector'].unique().tolist())

    selected_sector = request.args.get('sector_name')
    if not selected_sector or selected_sector not in available_sectors_sorted:
        selected_sector = available_sectors_sorted[0] if available_sectors_sorted else None

    sector_data_df = pd.DataFrame() # Empty df if no sector selected or data
    sector_data_json_for_plot = "[]" # Empty JSON array

    if selected_sector:
        sector_data_df = main_df[main_df['Sector'] == selected_sector].sort_values(by=['Model', 'Year'])
        if not sector_data_df.empty:
            sector_data_json_for_plot = sector_data_df.to_json(orient='records')

    # Derive display name for scenario (crude, can be improved with regex or more structured filename)
    try:
        scenario_name_part = safe_scenario_filename[len('demand_forecast_'):safe_scenario_filename.rfind('_', 0, safe_scenario_filename.rfind('_'))]
        timestamp_part = safe_scenario_filename[safe_scenario_filename.rfind('_', 0, safe_scenario_filename.rfind('_'))+1:].replace('.csv','')
        display_scenario_name = f"{scenario_name_part} ({timestamp_part})"
    except Exception: # pylint: disable=broad-except
        display_scenario_name = safe_scenario_filename


    # Load Display Settings (for primary model - Phase 3.C)
    scenario_base_name = safe_scenario_filename.replace('demand_forecast_', '').replace('.csv', '')
    display_settings_filepath = os.path.join(results_dir, f"display_settings_{scenario_base_name}.json")
    current_display_settings = {}
    primary_model_for_selected_sector = None
    if os.path.exists(display_settings_filepath):
        try:
            with open(display_settings_filepath, 'r') as f:
                current_display_settings = json.load(f)
            primary_model_for_selected_sector = current_display_settings.get('primary_models', {}).get(selected_sector)
        except (json.JSONDecodeError, Exception) as e: # pylint: disable=broad-except
            flash(f"Could not load display settings: {e}", "warning")
            current_display_settings = {} # Reset on error


    all_models_in_sector_data = sector_data_df['Model'].unique().tolist() if selected_sector and not sector_data_df.empty else []

    # Prepare all_models_in_data_for_all_sectors for the sidebar
    all_models_in_data_for_all_sectors = {}
    if not main_df.empty: # Ensure main_df is loaded and not empty
        for sector_iter in available_sectors_sorted:
            models_for_sector = main_df[main_df['Sector'] == sector_iter]['Model'].unique().tolist()
            all_models_in_data_for_all_sectors[sector_iter] = sorted(list(set(models_for_sector))) # Ensure uniqueness and sort

    return render_template('sector_detail_demand.html',
                           scenario_filename=safe_scenario_filename,
                           display_scenario_name=display_scenario_name,
                           available_sectors=available_sectors_sorted,
                           selected_sector=selected_sector,
                           sector_data_df=sector_data_df, # Pass DataFrame for table
                           sector_data_json=sector_data_json_for_plot, # Pass JSON for JS chart
                           primary_model_selected=primary_model_for_selected_sector,
                           all_models_in_data=all_models_in_sector_data, # For the currently displayed sector (title, etc.)
                           all_models_in_data_for_all_sectors=all_models_in_data_for_all_sectors, # For the sidebar
                           current_display_settings=current_display_settings, # Pass full settings for robust pre-selection
                           project_name=current_app.config.get('CURRENT_PROJECT_NAME'))


@bp.route('/save_primary_models/<path:scenario_filename>', methods=['POST'])
def save_primary_models_route(scenario_filename):
    project_path_abs = current_app.config.get('CURRENT_PROJECT_PATH_ABS')
    if not project_path_abs:
        return jsonify({'message': 'No project loaded. Cannot save settings.'}), 400 # Bad Request

    # Validate scenario_filename to ensure it's an expected file (security)
    # This logic should mirror how valid_detailed_files is generated in view_sector_detail_route
    results_dir_val = os.path.join(project_path_abs, 'results', 'demand_projection')
    valid_files = []
    if os.path.exists(results_dir_val):
        for f_name in os.listdir(results_dir_val):
            if f_name.startswith('demand_forecast_') and f_name.endswith('.csv'):
                valid_files.append(f_name)

    safe_scenario_filename_from_path = secure_filename(scenario_filename)
    if safe_scenario_filename_from_path not in valid_files:
        return jsonify({'message': 'Invalid scenario file specified.'}), 400

    # Derive scenario_base_name from the validated filename
    scenario_base_name = safe_scenario_filename_from_path.replace('demand_forecast_', '').replace('.csv', '')

    primary_model_selections = request.get_json()
    if not isinstance(primary_model_selections, dict):
        return jsonify({'message': 'Invalid data format. Expected JSON object.'}), 400

    # Load existing settings to preserve other keys (e.g., T&D losses)
    # The load_display_settings in file_handlers can be used, or direct logic here:
    existing_settings = load_display_settings(project_path_abs, scenario_base_name) # from file_handlers

    # Update only the 'primary_models' key
    existing_settings['primary_models'] = primary_model_selections

    if save_display_settings(project_path_abs, scenario_base_name, existing_settings):
        # Attempt to regenerate consolidated results
        main_forecast_filepath = os.path.join(project_path_abs, 'results', 'demand_projection', safe_scenario_filename_from_path)

        # Extract scenario_name_from_form using regex
        scenario_name_from_form = scenario_base_name # Fallback
        match = re.search(r"(.+)_(\d{8}_\d{6})", scenario_base_name) # scenario_base_name is already without prefix/suffix
        if match:
            scenario_name_from_form = match.group(1)
        else:
            # This fallback might occur if scenario_base_name doesn't have the expected timestamp format
            # This could happen if original scenario_filename was unusual.
            # For safety, use scenario_base_name which is secure_filename'd and stripped, but might include timestamp.
            print(f"Warning: Could not parse scenario name and timestamp from '{scenario_base_name}'. Using base name for consolidated file naming.")


        consolidated_filepath = generate_consolidated_results(
            project_path_abs,
            scenario_name_from_form, # User-defined part of scenario name for output file
            main_forecast_filepath,    # Full path to the detailed forecast CSV
            scenario_base_name         # Base name (with timestamp) for loading display_settings
        )

        if consolidated_filepath:
            # Update metadata with the newly generated consolidated file (if different, or to confirm update)
            try:
                pm = ProjectManager(current_app.config['PROJECT_ROOT_ABS'])
                project_folder = os.path.basename(project_path_abs)
                # Load existing metadata to update last_forecast_run specifically
                metadata = pm.get_project_metadata(project_folder)
                if metadata and 'last_forecast_run' in metadata:
                    # Ensure we are updating the correct scenario's metadata if multiple runs exist in a list
                    # For now, assuming last_forecast_run is a single dict for the scenario matching scenario_base_name.
                    # This might need adjustment if last_forecast_run is a list of all runs.
                    # Let's assume it refers to the one matching scenario_base_name, which is implicitly handled
                    # if a new forecast run always overwrites 'last_forecast_run'.
                    # If scenario_filename in metadata matches safe_scenario_filename_from_path:
                    if metadata['last_forecast_run'].get('file') == safe_scenario_filename_from_path :
                         metadata['last_forecast_run']['consolidated_file'] = os.path.basename(consolidated_filepath)
                         metadata['last_forecast_run']['primary_models_set_at'] = datetime.now().isoformat() + 'Z'
                         pm.update_project_metadata(project_folder, {'last_forecast_run': metadata['last_forecast_run']})
                    else:
                        # This case means we're saving primary models for a scenario that isn't the absolute 'last_forecast_run'
                        # in project metadata. This is fine, the consolidated file is still updated.
                        # We might want to store a list of all forecast runs and their settings in project.json.
                        # For now, just don't update the global 'last_forecast_run' if it's for a different scenario.
                        print(f"Info: Primary models saved for {safe_scenario_filename_from_path}, but it's not the one marked as 'last_forecast_run' in project.json.")

                else: # No last_forecast_run in metadata, or no metadata
                    # This could happen if a forecast was run before metadata structure was in place
                    # Or if the metadata points to a different scenario filename
                    # Still, the display_settings and consolidated file specific to this scenario_base_name are updated.
                    pass


            except Exception as e_meta:
                flash(f"Metadata update failed after saving primary models: {e_meta}", "warning") # This flash won't be seen by user due to jsonify

            return jsonify({'message': f"Primary model selections saved. Consolidated file '{os.path.basename(consolidated_filepath)}' updated/created.",
                            'consolidated_file': os.path.basename(consolidated_filepath)}), 200
        else:
            return jsonify({'message': "Primary model selections saved. Consolidated file NOT updated (e.g., no sectors had explicit primary models, or no data matched).",
                            'consolidated_file': None}), 200
    else:
        return jsonify({'message': 'Error saving primary model selections to file.'}), 500


@bp.route('/upload_demand_file', methods=['POST'])
def upload_demand_file():
    if not current_app.config.get('CURRENT_PROJECT_PATH_ABS'):
        flash('No project is currently loaded. Please load or create a project first.', 'error')
        return redirect(url_for('demand_projection.upload_page'))

    if 'file' not in request.files:
        flash('No file part in the request.', 'error')
        return redirect(url_for('demand_projection.upload_page'))

    file = request.files['file']

    if file.filename == '':
        flash('No selected file.', 'error')
        return redirect(url_for('demand_projection.upload_page'))

    # The real validate_file_upload will be in app.utils.file_manager

    is_file_struct_valid, msg_file_struct = validate_file_upload(file, allowed_extensions={'xlsx'})

    if not is_file_struct_valid:
        flash(msg_file_struct, 'error')
        return redirect(url_for('demand_projection.upload_page'))

    try:
        project_path_abs = current_app.config['CURRENT_PROJECT_PATH_ABS']
        inputs_folder = os.path.join(project_path_abs, 'inputs')
        os.makedirs(inputs_folder, exist_ok=True) # Ensure inputs folder exists

        # Standardized filename
        filename = secure_filename('input_demand_file.xlsx')

        file_path = os.path.join(inputs_folder, filename)
        file.save(file_path)
        # flash(f'File "{filename}" uploaded successfully to project inputs.', 'success') # Flash after validation

        # Now validate the content of the uploaded file
        # from .file_handlers import validate_and_parse_demand_input_excel # Already imported
        is_content_valid, msg_content, parsed_data = validate_and_parse_demand_input_excel(file_path)

        if not is_content_valid:
            # Add 'danger' category for bootstrap styling if available in template
            flash(f"Uploaded file '{filename}' has validation errors: {msg_content}", 'danger')
            # Optionally, remove or quarantine the file
            # try:
            #     os.remove(file_path)
            #     flash(f"Invalid file '{filename}' has been removed.", 'info')
            # except OSError as e_remove:
            #     flash(f"Could not remove invalid file '{filename}': {e_remove}", 'error')
        else:
            flash(f"File '{filename}' uploaded and validated successfully. {msg_content}", 'success')
            # Auto-initialize config if it's empty for these sectors
            current_demand_config = load_demand_config(project_path_abs)
            if parsed_data and 'identified_demand_columns' in parsed_data:
                made_changes_to_config = False
                for sector in parsed_data['identified_demand_columns']:
                    if sector not in current_demand_config['sector_models']:
                        current_demand_config['sector_models'][sector] = []
                        for model_code, model_details in AVAILABLE_MODELS_CONFIG.items():
                            current_demand_config['sector_models'][sector].append({
                                "model_name": model_code,
                                "enabled": False, # Default to disabled
                                "parameters": {p_name: p_attrs.get("default") for p_name, p_attrs in model_details.get("params", {}).items()}
                            })
                        made_changes_to_config = True
                if made_changes_to_config:
                    save_demand_config(project_path_abs, current_demand_config)
                    flash("New sectors identified from Excel and added to demand configuration with default models (disabled). Please review.", "info")


    except Exception as e:
        flash(f'An error occurred during file upload or processing: {str(e)}', 'error')
        # Log the exception e for debugging
        print(f"Error saving file: {e}")

    return redirect(url_for('demand_projection.upload_page'))
