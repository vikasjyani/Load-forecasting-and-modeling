import os
from flask import current_app, flash, redirect, render_template, request, url_for, send_from_directory
from werkzeug.utils import secure_filename
from app.demand_projection import bp
from app.utils.file_manager import ProjectManager, validate_file_upload
from .file_handlers import load_demand_config, save_demand_config, validate_and_parse_demand_input_excel, save_demand_forecast_results, MODEL_OPTIONS as FH_MODEL_OPTIONS, DEFAULT_DEMAND_CONFIG
from .models import forecast_slr, forecast_wam, forecast_mlr
import os
import pandas as pd
from datetime import datetime

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
                    raw_value = request.form.get(form_field_name)

                    if raw_value is not None:
                        try:
                            if param_attrs.get("type") == "number":
                                params[param_name] = int(raw_value) # Or float, based on needs
                            elif param_attrs.get("type") == "checkbox":
                                params[param_name] = raw_value == "on" # if value is "on"
                            else: # text, multiselect (comma separated)
                                params[param_name] = str(raw_value)
                        except ValueError:
                            params[param_name] = param_attrs.get("default") # Use default if conversion fails
                            flash(f"Invalid value for {param_attrs.get('label', param_name)} in {sector} for {model_code}. Using default.", "warning")
                    else:
                         params[param_name] = param_attrs.get("default") # Use default if not in form

            new_sector_models_config[sector].append({
                "model_name": model_code,
                "enabled": is_enabled,
                "parameters": params
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
        if sector_name not in demand_config.get('sector_models', {}):
            flash(f"No model configuration found for sector '{sector_name}'. Skipping.", "warning")
            continue

        for model_config in demand_config['sector_models'].get(sector_name, []):
            if model_config.get('enabled', False):
                historical_sector_series = historical_df.set_index('Year')[sector_name].sort_index()
                # TODO: Add logic here to handle exclude_covid_years if needed, by filtering historical_sector_series

                model_name = model_config['model_name']
                params = model_config.get('parameters', {})
                forecast_df = None

                try:
                    if model_name == 'SLR':
                        forecast_df = forecast_slr(historical_sector_series, configured_target_years, sector_name, **params)
                    elif model_name == 'WAM':
                        forecast_df = forecast_wam(historical_sector_series, configured_target_years, sector_name, **params)
                    elif model_name == 'MLR':
                        # MLR requires the full DataFrame and list of independent variables
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


                # Attempt to generate consolidated results
                consolidated_output_filepath = generate_consolidated_results(
                    project_path_abs,
                    scenario_name,
                    output_filepath, # Pass path of the main results file
                    demand_config    # Pass the config used for the forecast
                )
                if consolidated_output_filepath:
                    flash(f"Consolidated results for scenario '{scenario_name}' generated: {os.path.basename(consolidated_output_filepath)}", 'info')
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
                           results_files=results_files,
                           scenario_name=scenario_name_display,
                           project_name=current_app.config.get('CURRENT_PROJECT_NAME'))


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
