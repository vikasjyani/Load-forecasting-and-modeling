import os
from flask import current_app, flash, redirect, render_template, request, url_for, send_from_directory, jsonify
from werkzeug.utils import secure_filename
from app.demand_projection import bp
from app.utils.file_manager import ProjectManager, validate_file_upload
from .file_handlers import load_demand_config, save_demand_config, validate_and_parse_demand_input_excel, save_demand_forecast_results, MODEL_OPTIONS as FH_MODEL_OPTIONS, DEFAULT_DEMAND_CONFIG
from .models import forecast_slr, forecast_wam, forecast_mlr
from .utils import get_interpolated_td_loss
import os
import pandas as pd
import numpy as np # For np.nan
from datetime import datetime
import json
import re

# Make model options available to routes in this blueprint
AVAILABLE_MODELS_CONFIG = FH_MODEL_OPTIONS


@bp.route('/upload_page') # This will now be the configuration page as well
def upload_page():
    logger = current_app.logger
    try:
        project_path_abs = current_app.config.get('CURRENT_PROJECT_PATH_ABS')
        project_name = current_app.config.get('CURRENT_PROJECT_NAME', 'N/A')

        template_context = {
            'active_project_path': project_path_abs,
            'current_project_name_g': project_name,
            'excel_file_exists': False,
            'input_file_validated': False,
            'available_sectors': [],
            'demand_config': deepcopy(DEFAULT_DEMAND_CONFIG),
            'model_options': AVAILABLE_MODELS_CONFIG,
            'excel_validation_message': "Excel file not found or not yet uploaded.",
            'datetime': datetime
        }

        if not project_path_abs:
            flash("No project loaded. Please load or create a project first to access this page.", "warning")
            return render_template('upload_demand_data.html', **template_context)

        template_context['demand_config'] = load_demand_config(project_path_abs) # Robust load

        input_file_path = os.path.join(project_path_abs, 'inputs', 'input_demand_file.xlsx')
        if os.path.exists(input_file_path):
            template_context['excel_file_exists'] = True
            logger.info(f"Excel input file found at {input_file_path} for project {project_name}.")
            is_valid, msg, parsed_data = validate_and_parse_demand_input_excel(input_file_path) # Robust validation

            if is_valid and parsed_data:
                template_context['available_sectors'] = parsed_data.get('identified_demand_columns', [])
                template_context['input_file_validated'] = True
                template_context['excel_validation_message'] = msg

                made_changes_to_config = False
                if template_context['available_sectors']:
                    if "sector_models" not in template_context['demand_config']:
                         template_context['demand_config']["sector_models"] = {}
                    for sector in template_context['available_sectors']:
                        if sector not in template_context['demand_config']["sector_models"]:
                            logger.info(f"New sector '{sector}' identified in project '{project_name}'. Initializing default model config.")
                            template_context['demand_config']["sector_models"][sector] = []
                            for model_code, model_details in AVAILABLE_MODELS_CONFIG.items():
                                template_context['demand_config']["sector_models"][sector].append({
                                    "model_name": model_code, "enabled": False,
                                    "parameters": {p_name: p_attrs.get("default") for p_name, p_attrs in model_details.get("params", {}).items()}
                                })
                            made_changes_to_config = True
                    if made_changes_to_config:
                        if save_demand_config(project_path_abs, template_context['demand_config']): # Robust save
                             flash("New sectors identified. Model configuration initialized with defaults (disabled). Please review and save.", "info")
                        else:
                             flash("New sectors identified, but failed to auto-save initial model configuration. Manual save required.", "warning")
            else:
                template_context['input_file_validated'] = False
                template_context['excel_validation_message'] = f"Uploaded Excel file validation failed: {msg}"
                flash(template_context['excel_validation_message'], "danger")
        else:
            template_context['excel_validation_message'] = "input_demand_file.xlsx not found in project's 'inputs' directory. Please upload it."
            # No flash here, as it's normal state if no file uploaded yet.

        return render_template('upload_demand_data.html', **template_context)

    except Exception as e:
        logger.error(f"Unhandled error in Demand Projection configuration page (upload_page): {e}", exc_info=True)
        flash("An unexpected server error occurred while loading the configuration page. Please try again or contact support.", "danger")
        return redirect(url_for('main.home'))


@bp.route('/save_demand_configuration', methods=['POST'])
def save_demand_configuration_route():
    logger = current_app.logger
    try:
        project_path_abs = current_app.config.get('CURRENT_PROJECT_PATH_ABS')
        project_name = current_app.config.get('CURRENT_PROJECT_NAME', 'N/A')
        if not project_path_abs:
            logger.error("Save demand config: No project loaded.")
            flash('No project loaded. Cannot save configuration.', 'danger')
            return redirect(url_for('main.home'))

        logger.info(f"Attempting to save demand configuration for project: {project_name}")

        available_sectors = []
        input_file_path = os.path.join(project_path_abs, 'inputs', 'input_demand_file.xlsx')
        if os.path.exists(input_file_path):
            is_valid, msg, parsed_data = validate_and_parse_demand_input_excel(input_file_path)
            if is_valid and parsed_data:
                available_sectors = parsed_data.get('identified_demand_columns', [])
            else:
                logger.error(f"Save demand config: input_demand_file.xlsx for project {project_name} is missing or invalid: {msg}")
                flash(f"Cannot save configuration: input_demand_file.xlsx is missing or invalid: {msg}", 'danger')
                return redirect(url_for('demand_projection.upload_page'))
        else:
            logger.error(f"Save demand config: input_demand_file.xlsx not found for project {project_name}.")
            flash("Cannot save configuration: input_demand_file.xlsx not found.", 'danger')
            return redirect(url_for('demand_projection.upload_page'))

        if not available_sectors:
            logger.warning(f"Save demand config: No demand sectors identified from input file for project {project_name}.")
            flash("Cannot save configuration: No demand sectors identified from the input file.", 'warning')
            return redirect(url_for('demand_projection.upload_page'))

        current_config = load_demand_config(project_path_abs)
        new_sector_models_config = {}

        for sector in available_sectors:
            new_sector_models_config[sector] = []
            for model_code, model_detail in AVAILABLE_MODELS_CONFIG.items():
                is_enabled = request.form.get(f"{sector}|{model_code}|enabled") == "on"
                params = {}
                if is_enabled: # Only parse params if model is enabled
                    for param_name, param_attrs in model_detail.get("params", {}).items():
                        form_field_name = f"{sector}|{model_code}|{param_name}"
                        try:
                            if model_code == "WAM" and param_name == "window_size_option":
                                wam_option_val = request.form.get(form_field_name)
                                actual_window_size = param_attrs.get("custom_input_default", 3)
                                custom_input_field_name = f"{sector}|{model_code}|{param_attrs.get('custom_input_name')}"
                                if wam_option_val == "custom":
                                    actual_window_size = int(request.form.get(custom_input_field_name, actual_window_size))
                                elif wam_option_val:
                                    actual_window_size = int(wam_option_val)

                                min_val = param_attrs.get("custom_input_min", 1)
                                max_val = param_attrs.get("custom_input_max", 20)
                                if not (min_val <= actual_window_size <= max_val):
                                    logger.warning(f"Window size {actual_window_size} for WAM in {sector} for project {project_name} clamped to range ({min_val}-{max_val}).")
                                    actual_window_size = max(min_val, min(actual_window_size, max_val))
                                params["window_size"] = actual_window_size
                                continue

                            raw_value = request.form.get(form_field_name)
                            if raw_value is not None and raw_value != '':
                                if param_attrs.get("type") == "number": params[param_name] = int(raw_value)
                                elif param_attrs.get("type") == "float":
                                    val = float(raw_value)
                                    p_min, p_max = param_attrs.get("min"), param_attrs.get("max")
                                    if p_min is not None and val < p_min: val = p_min
                                    if p_max is not None and val > p_max: val = p_max
                                    params[param_name] = val
                                elif param_attrs.get("type") == "checkbox": params[param_name] = raw_value == "on"
                                else: params[param_name] = str(raw_value)
                            else: params[param_name] = param_attrs.get("default")
                        except ValueError as ve:
                            params[param_name] = param_attrs.get("default")
                            logger.warning(f"Invalid value for param '{param_name}' in {sector}|{model_code} for project {project_name}. Using default. Error: {ve}")
                            flash(f"Invalid value for '{param_attrs.get('label', param_name)}' in sector '{sector}' for model '{model_code}'. Using default: '{params[param_name]}'.", "warning")

                new_sector_models_config[sector].append({
                    "model_name": model_code, "enabled": is_enabled,
                    "parameters": params if is_enabled else {p_name: p_attrs.get("default") for p_name, p_attrs in model_detail.get("params", {}).items()}
                })

        current_config['sector_models'] = new_sector_models_config

        # Handle global settings
        try:
            raw_target_years = request.form.get('global_target_years', '').strip()
            current_config['global_settings']['target_years'] = sorted(list(set([int(y.strip()) for y in raw_target_years.split(',') if y.strip().isdigit()]))) if raw_target_years else []
        except ValueError:
            logger.warning(f"Invalid target years format: '{raw_target_years}' for project {project_name}. Not updated.", exc_info=True)
            flash("Target years format was invalid. Global setting for target years not updated.", "warning")
            # Keep existing or default if error by not overwriting if current_config already has valid one

        current_config['global_settings']['exclude_covid_years'] = request.form.get('global_exclude_covid') == 'on'
        try:
            start_year_str = request.form.get('global_forecast_start_year', '').strip()
            current_config['global_settings']['forecast_start_year'] = int(start_year_str) if start_year_str else None
        except ValueError:
            logger.warning(f"Invalid Forecast Start Year '{start_year_str}' for project {project_name}. Resetting.", exc_info=True)
            current_config['global_settings']['forecast_start_year'] = None # Reset or keep old
            flash("Invalid Forecast Start Year provided. It has been reset or kept as previous.", "warning")

        if save_demand_config(project_path_abs, current_config): # Robust save
            logger.info(f"Demand forecast configuration saved successfully for project {project_name}.")
            flash('Demand forecast configuration saved successfully.', 'success')
        else:
            logger.error(f"Failed to save demand forecast configuration for project {project_name}.")
            flash('Error saving demand forecast configuration. Check server logs.', 'danger')

        return redirect(url_for('demand_projection.upload_page'))

    except Exception as e:
        logger.error(f"Unhandled error in save_demand_configuration_route for project {current_app.config.get('CURRENT_PROJECT_NAME', 'N/A')}: {e}", exc_info=True)
        flash("An unexpected server error occurred while saving the configuration. Please try again or contact support.", "danger")
        return redirect(url_for('demand_projection.upload_page'))

@bp.route('/run_forecast', methods=['POST'])
def run_forecast_route():
    logger = current_app.logger
    project_path_abs = current_app.config.get('CURRENT_PROJECT_PATH_ABS')
    project_name = current_app.config.get('CURRENT_PROJECT_NAME', 'N/A')

    if not project_path_abs:
        logger.error("Run forecast: No project loaded.")
        flash('No project loaded. Cannot run forecast.', 'danger')
        return redirect(url_for('main.home'))

    logger.info(f"Attempting to run forecast for project: {project_name}")

    try:
        scenario_name = request.form.get('scenario_name', '').strip()
        if not scenario_name:
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            scenario_name = f"forecast_{timestamp}"
            logger.info(f"Scenario name was empty for project {project_name}, defaulted to '{scenario_name}'.")
            flash(f"Scenario name was empty, defaulted to '{scenario_name}'.", "info")

        # Load configurations and data
        demand_config = load_demand_config(project_path_abs) # Robust
        if not demand_config or "global_settings" not in demand_config or "sector_models" not in demand_config:
            logger.error(f"Demand configuration is missing or malformed for project {project_name}.")
            flash("Demand configuration not found or invalid. Please configure models first.", "danger")
            return redirect(url_for('demand_projection.upload_page'))

        input_excel_path = os.path.join(project_path_abs, 'inputs', 'input_demand_file.xlsx')
        if not os.path.exists(input_excel_path):
            logger.error(f"Input Excel file not found for project {project_name} at {input_excel_path}.")
            flash(f"Input Excel file (input_demand_file.xlsx) not found in project '{project_name}'.", "danger")
            return redirect(url_for('demand_projection.upload_page'))

        is_valid_excel, msg_excel, parsed_excel_data = validate_and_parse_demand_input_excel(input_excel_path) # Robust
        if not is_valid_excel:
            logger.warning(f"Input Excel file validation failed for project {project_name}: {msg_excel}")
            flash(f"Input Excel file validation failed: {msg_excel}", "danger")
            return redirect(url_for('demand_projection.upload_page'))

        historical_df = parsed_excel_data['historical_data']
        identified_demand_columns = parsed_excel_data['identified_demand_columns']

        configured_target_years = demand_config.get('global_settings', {}).get('target_years', [])
        if not configured_target_years:
            logger.warning(f"Target years not configured for forecast in project {project_name}.")
            flash("Target years for forecasting are not configured. Please set them in Global Settings.", "danger")
            return redirect(url_for('demand_projection.upload_page'))

        # Optional: Implement filtering based on exclude_covid_years or forecast_start_year from demand_config
        # exclude_years_list = []
        # if demand_config.get('global_settings', {}).get('exclude_covid_years'): # Example
        #     exclude_years_list.extend([2020, 2021]) # This should be configurable

        all_forecast_results = []
        for sector_name in identified_demand_columns:
            try:
                historical_sector_series_full = historical_df.set_index('Year')[sector_name].sort_index().dropna()
                is_user_forecasted = False

                if not historical_sector_series_full.empty:
                    min_target_year = min(configured_target_years)
                    max_target_year = max(configured_target_years)
                    if historical_sector_series_full.index.max() >= max_target_year:
                        user_forecast_values = [historical_sector_series_full.get(t_year) for t_year in configured_target_years]
                        if all(pd.notna(val) for val in user_forecast_values):
                            is_user_forecasted = True
                            user_forecast_data = [{'Year': t_year, 'Sector': sector_name, 'Model': 'User_Provided',
                                                   'Value': val, 'Lower_Bound': val, 'Upper_Bound': val,
                                                   'Comment': 'Data taken directly from input file.'}
                                                  for t_year, val in zip(configured_target_years, user_forecast_values)]
                            all_forecast_results.append(pd.DataFrame(user_forecast_data))
                            logger.info(f"Sector '{sector_name}' in project {project_name} uses user-provided data for forecast period.")
                            flash(f"Sector '{sector_name}' uses user-provided data for the forecast period {min_target_year}-{max_target_year}.", "info")

                if is_user_forecasted: continue

                if sector_name not in demand_config.get('sector_models', {}):
                    logger.warning(f"No model configuration found for sector '{sector_name}' in project {project_name}. Skipping automated forecast.")
                    flash(f"No model configuration found for sector '{sector_name}'. Skipping automated forecast.", "warning")
                    continue

                min_hist_year_for_model_input = min(configured_target_years) if configured_target_years else (historical_sector_series_full.index.max() + 1 if not historical_sector_series_full.empty else datetime.now().year)
                training_data_series = historical_sector_series_full[historical_sector_series_full.index < min_hist_year_for_model_input]
                # if exclude_years_list: # Example of filtering
                #    training_data_series = training_data_series[~training_data_series.index.isin(exclude_years_list)]


                for model_config in demand_config['sector_models'].get(sector_name, []):
                    if model_config.get('enabled', False):
                        model_name = model_config['model_name']
                        params = model_config.get('parameters', {})
                        forecast_df = None
                        logger.debug(f"Running model {model_name} for sector {sector_name} in project {project_name} with params {params}")
                        try:
                            if model_name == 'SLR': forecast_df = forecast_slr(training_data_series, configured_target_years, sector_name, **params)
                            elif model_name == 'WAM': forecast_df = forecast_wam(training_data_series, configured_target_years, sector_name, **params)
                            elif model_name == 'MLR':
                                iv_str = params.get('independent_vars', '')
                                iv_list = [v.strip() for v in iv_str.split(',') if v.strip()]
                                if not iv_list:
                                     logger.warning(f"MLR for {sector_name} (project {project_name}) enabled but no independent variables configured.")
                                     flash(f"MLR for {sector_name} enabled but no independent variables configured. Skipping.", "warning")
                                     continue
                                missing_iv = [v for v in iv_list if v not in historical_df.columns]
                                if missing_iv:
                                    logger.warning(f"MLR for {sector_name} (project {project_name}) skipped. Missing IVs: {missing_iv}")
                                    flash(f"MLR for {sector_name} skipped. Missing independent variable(s) in historical data: {', '.join(missing_iv)}", "warning")
                                    continue
                                mlr_input_df = historical_df[['Year', sector_name] + iv_list] # Pass full historical for placeholder
                                forecast_df = forecast_mlr(mlr_input_df, configured_target_years, sector_name, independent_vars=iv_list, **params)

                            if forecast_df is not None and not forecast_df.empty: all_forecast_results.append(forecast_df)
                            elif forecast_df is not None: logger.info(f"Model {model_name} for sector {sector_name} (project {project_name}) produced empty results.")
                        except Exception as model_e:
                            logger.error(f"Error running model {model_name} for sector {sector_name} in project {project_name}: {model_e}", exc_info=True)
                            flash(f"Error running model {model_name} for sector {sector_name}: {str(model_e)[:100]}...", "danger")
            except KeyError as ke:
                logger.error(f"KeyError processing sector {sector_name} in project {project_name}: {ke}. Likely missing column in Excel.", exc_info=True)
                flash(f"Error processing sector '{sector_name}': Expected column not found. Please check Excel file structure.", "danger")
            except Exception as sector_e:
                logger.error(f"Unexpected error processing sector {sector_name} in project {project_name}: {sector_e}", exc_info=True)
                flash(f"An error occurred while processing sector '{sector_name}'.", "danger")


        if all_forecast_results:
            final_results_df = pd.concat(all_forecast_results, ignore_index=True)
            output_filepath = save_demand_forecast_results(project_path_abs, scenario_name, final_results_df) # Robust save
            if output_filepath:
                logger.info(f"Forecast scenario '{scenario_name}' for project {project_name} run successfully. Results: {output_filepath}")
                flash(f"Forecast scenario '{scenario_name}' run successfully. Results saved to {os.path.basename(output_filepath)}", 'success')
                try:
                    pm = ProjectManager(current_app.config['PROJECT_ROOT_ABS'])
                    project_folder = os.path.basename(project_path_abs)
                    metadata_update = {'last_forecast_run': {'scenario': scenario_name, 'timestamp': datetime.now().isoformat() + 'Z',
                                                             'file': os.path.basename(output_filepath), 'module': 'demand_projection'}}
                    if pm.update_project_metadata(project_folder, metadata_update): # Robust update
                        logger.info(f"Project metadata updated for {project_folder} after forecast run '{scenario_name}'.")
                    else: # update_project_metadata already logs its error
                        flash(f"Failed to update project metadata for {project_folder} after forecast run. Check server logs.", "warning")

                    scenario_base_name_for_settings = os.path.basename(output_filepath).replace('demand_forecast_', '').replace('.csv', '')
                    consolidated_output_filepath = generate_consolidated_results(project_path_abs, scenario_name, output_filepath, scenario_base_name_for_settings) # Robust
                    if consolidated_output_filepath:
                        logger.info(f"Consolidated results for scenario '{scenario_name}' (project {project_name}) generated: {consolidated_output_filepath}")
                        flash(f"Consolidated results (based on primary models) for scenario '{scenario_name}' generated: {os.path.basename(consolidated_output_filepath)}", 'info')
                        metadata_update['last_forecast_run']['consolidated_file'] = os.path.basename(consolidated_output_filepath)
                        pm.update_project_metadata(project_folder, metadata_update)
                    else: # generate_consolidated_results logs its own errors/warnings
                        flash(f"Could not generate/save consolidated results for scenario '{scenario_name}'. Check server logs.", 'warning')
                except Exception as e_meta:
                    logger.error(f"Error updating metadata or generating consolidated results for project {project_name}, scenario '{scenario_name}': {e_meta}", exc_info=True)
                    flash(f"Failed to update project metadata or generate consolidated file after saving forecast: {str(e_meta)[:100]}...", "warning")
            else:
                logger.error(f"Forecast scenario '{scenario_name}' for project {project_name} run, but failed to save results.")
                flash(f"Forecast scenario '{scenario_name}' run, but failed to save results. Check server logs.", 'danger')
        else:
            logger.warning(f"No forecast results generated for scenario '{scenario_name}' in project {project_name}. Check config and data.")
            flash("No forecast results generated. Check model configurations, input data, and target years.", 'warning')

        return redirect(url_for('demand_projection.upload_page'))

    except Exception as e:
        logger.error(f"Unhandled error in run_forecast_route for project {current_app.config.get('CURRENT_PROJECT_NAME', 'N/A')}: {e}", exc_info=True)
        flash("An unexpected server error occurred while running the forecast. Please try again or contact support.", "danger")
        return redirect(url_for('demand_projection.upload_page'))


@bp.route('/results_page')
def results_page_route():
    logger = current_app.logger
    project_path_abs = current_app.config.get('CURRENT_PROJECT_PATH_ABS')
    project_name = current_app.config.get('CURRENT_PROJECT_NAME', 'N/A')

    template_context = {
        "available_scenarios": [], "selected_scenario_id": None,
        "results_files": [], "scenario_name_display": "N/A", # Changed from results_files_for_selected_scenario
        "project_name": project_name, "current_project_name_g": project_name, # For base template consistency
        "active_consolidated_file": None, "active_display_settings_file": None
    }

    if not project_path_abs:
        flash('No project loaded. Please load or create one first to view results.', 'warning')
        return render_template('results_demand.html', **template_context)

    logger.info(f"Loading results page for project: {project_name}")
    results_dir = os.path.join(project_path_abs, 'results', 'demand_projection')

    try:
        if os.path.exists(results_dir):
            for filename in sorted(os.listdir(results_dir), reverse=True):
                if filename.startswith('demand_forecast_') and filename.endswith('.csv'):
                    try:
                        # Improved parsing for scenario_name_part and timestamp_part
                        match = re.match(r"demand_forecast_(.+)_(\d{8}_\d{6})\.csv", filename)
                        if match:
                            scenario_name_part = match.group(1)
                            timestamp_part = match.group(2).replace('_', ':') # Format for display
                            display_name = f"{scenario_name_part} (Run: {timestamp_part[:8]} {timestamp_part[9:]})"
                        else: # Fallback if regex doesn't match (e.g. old filename format)
                            scenario_name_part = filename[len('demand_forecast_'):filename.rfind('_', 0, filename.rfind('_'))]
                            timestamp_part = filename[filename.rfind('_', 0, filename.rfind('_'))+1:].replace('.csv','')
                            display_name = f"{scenario_name_part} ({timestamp_part})"

                        template_context["available_scenarios"].append({
                            'id': filename,
                            'display_name': display_name,
                            'scenario_name_short': scenario_name_part
                        })
                    except Exception as e_parse: # Catch errors during filename parsing
                        logger.error(f"Error parsing scenario filename '{filename}': {e_parse}", exc_info=True)
                        template_context["available_scenarios"].append({'id': filename, 'display_name': filename, 'scenario_name_short': filename}) # Add with raw filename
        else:
            logger.info(f"Results directory not found for project {project_name} at {results_dir}.")
            flash("Results directory not found for this project. Run a forecast to create it.", "info")
    except OSError as e:
        logger.error(f"OSError scanning results directory {results_dir} for project {project_name}: {e}", exc_info=True)
        flash("Error accessing forecast results directory.", "danger")
        return render_template('results_demand.html', **template_context) # Render with empty results

    selected_scenario_id_req = request.args.get('scenario_id')
    template_context["selected_scenario_id"] = selected_scenario_id_req

    if selected_scenario_id_req and any(s['id'] == selected_scenario_id_req for s in template_context["available_scenarios"]):
        selected_scenario_details = next((s for s in template_context["available_scenarios"] if s['id'] == selected_scenario_id_req), None)
        template_context["scenario_name_display"] = selected_scenario_details['display_name'] if selected_scenario_details else "N/A"

        main_file_path = os.path.join(results_dir, selected_scenario_id_req)
        if os.path.exists(main_file_path):
            template_context["results_files"].append({'name': selected_scenario_id_req, 'type': 'Detailed Forecast CSV (All Models)'})

        if selected_scenario_details:
            short_scenario_name_from_id = selected_scenario_details['scenario_name_short']
            # Consolidated file name convention: consolidated_demand_forecast_{original_scenario_name_from_form}.csv
            consolidated_file = f"consolidated_demand_forecast_{short_scenario_name_from_id}.csv"
            if os.path.exists(os.path.join(results_dir, consolidated_file)):
                template_context["results_files"].append({'name': consolidated_file, 'type': 'Consolidated Forecast CSV (Primary Models)'})
                template_context["active_consolidated_file"] = consolidated_file
            else:
                 logger.info(f"Consolidated file not found: {os.path.join(results_dir, consolidated_file)} for short name {short_scenario_name_from_id}")

        # Placeholder for display settings file logic (not typically downloaded but used by other views)
        # scenario_base_name = selected_scenario_id_req.replace('demand_forecast_', '').replace('.csv', '')
        # template_context["active_display_settings_file"] = f"display_settings_{scenario_base_name}.json"
        # if not os.path.exists(os.path.join(results_dir, template_context["active_display_settings_file"])):
        #    template_context["active_display_settings_file"] = None

    elif selected_scenario_id_req:
        logger.warning(f"Scenario ID '{selected_scenario_id_req}' provided in URL but not found in scanned files for project {project_name}.")
        flash(f"Details for scenario ID '{selected_scenario_id_req}' could not be loaded. It might have been removed or is invalid.", "warning")
        template_context["selected_scenario_id"] = None

    if not template_context["available_scenarios"] and not selected_scenario_id_req :
         logger.info(f"No forecast results found for project {project_name}.")
         flash("No forecast results found for this project. Please run a forecast first.", "info")

    return render_template('results_demand.html', **template_context)


@bp.route('/download_result/<path:filename>') # Use <path:filename> for more flexibility if subdirs were used
def download_result_route(filename):
    logger = current_app.logger
    project_path_abs = current_app.config.get('CURRENT_PROJECT_PATH_ABS')
    project_name = current_app.config.get('CURRENT_PROJECT_NAME', 'N/A')

    if not project_path_abs:
        logger.error(f"Download attempt failed: No project loaded. Requested file: {filename}")
        flash('No project loaded. Cannot download file.', 'danger')
        return redirect(url_for('main.home'))

    results_dir = os.path.join(project_path_abs, 'results', 'demand_projection')

    # Security: Use secure_filename on the filename component.
    # If filename could contain subdirectories (e.g. "subdir/file.csv"),
    # os.path.normpath and checking it's within results_dir is important.
    # For now, assuming flat structure in results/demand_projection.
    safe_filename = secure_filename(os.path.basename(filename)) # Ensure it's just a filename

    if not safe_filename: # secure_filename might return empty string for malicious/weird names
        logger.warning(f"Download attempt with invalid filename: '{filename}' for project {project_name}.")
        flash("Invalid filename specified for download.", "danger")
        return redirect(url_for('.results_page_route'))

    # Further check: ensure the resolved path is actually within results_dir (prevent '..')
    # This is implicitly handled by send_from_directory if directory is absolute and filename is just a name.
    # For added safety:
    target_path = os.path.join(results_dir, safe_filename)
    if not os.path.normpath(target_path).startswith(os.path.normpath(results_dir)):
        logger.error(f"Potential path traversal attempt: '{filename}' resolved to '{target_path}' outside of '{results_dir}' for project {project_name}.")
        flash("Invalid file path for download.", "danger")
        abort(404) # Or redirect

    logger.info(f"Attempting to send file: {safe_filename} from directory: {results_dir} for project {project_name}")
    try:
        return send_from_directory(results_dir, safe_filename, as_attachment=True)
    except FileNotFoundError:
        logger.error(f"File '{safe_filename}' not found in results directory '{results_dir}' for project {project_name}.", exc_info=True)
        flash(f"File '{safe_filename}' not found. It might have been moved or deleted.", "danger")
        return redirect(url_for('.results_page_route'))
    except Exception as e:
        logger.error(f"An error occurred while trying to download '{safe_filename}' for project {project_name}: {e}", exc_info=True)
        flash(f"An error occurred while trying to download '{safe_filename}'. Please try again or contact support.", "danger")
        return redirect(url_for('.results_page_route'))


@bp.route('/scenario_results/<path:scenario_filename>/sector_detail')
def view_sector_detail_route(scenario_filename):
    logger = current_app.logger
    project_path_abs = current_app.config.get('CURRENT_PROJECT_PATH_ABS')
    project_name = current_app.config.get('CURRENT_PROJECT_NAME', 'N/A')
    active_view = request.args.get('view', 'sector_forecasts')

    # Initialize context with defaults to ensure all keys are present in all return paths
    template_context = {
        "scenario_filename": secure_filename(scenario_filename), # Secure early
        "display_scenario_name": "N/A", "available_sectors": [], "selected_sector": None,
        "sector_data_df": pd.DataFrame(), "sector_data_json": "[]",
        "primary_model_selected": None, "all_models_in_data": [],
        "all_models_in_data_for_all_sectors": {}, "current_display_settings": {},
        "project_name": project_name, "current_project_name_g": project_name,
        "active_view": active_view,
        "final_consolidated_table_data": [], "total_net_demand_table_data": []
    }

    if not project_path_abs:
        logger.warning("View sector detail: No project loaded.")
        flash('No project loaded. Please load or create one first.', 'warning')
        return render_template('sector_detail_demand.html', **template_context)

    logger.info(f"Loading sector detail page for scenario '{template_context['scenario_filename']}' in project '{project_name}', view: '{active_view}'.")
    results_dir = os.path.join(project_path_abs, 'results', 'demand_projection')

    # Validate scenario_filename against discovered files
    valid_detailed_files = []
    try:
        if os.path.exists(results_dir):
            for f_name in os.listdir(results_dir):
                if f_name.startswith('demand_forecast_') and f_name.endswith('.csv'):
                    valid_detailed_files.append(f_name)
    except OSError as e:
        logger.error(f"OSError listing files in results directory {results_dir}: {e}", exc_info=True)
        flash("Error accessing results directory. Cannot display sector details.", "danger")
        return render_template('sector_detail_demand.html', **template_context)

    if template_context["scenario_filename"] not in valid_detailed_files:
        logger.warning(f"Invalid scenario file '{template_context['scenario_filename']}' requested for project '{project_name}'.")
        flash(f"Invalid or non-existent scenario file specified: {template_context['scenario_filename']}", "danger")
        return redirect(url_for('.results_page_route'))

    main_forecast_filepath = os.path.join(results_dir, template_context["scenario_filename"])
    main_df = None
    try:
        main_df = pd.read_csv(main_forecast_filepath)
        if main_df.empty:
            logger.warning(f"Scenario forecast file {template_context['scenario_filename']} is empty for project {project_name}.")
            flash(f"Scenario file {template_context['scenario_filename']} is empty. No details to display.", "warning")
            # Allow page to render to show "empty" state and navigation.
    except FileNotFoundError: # Should be caught by above check, but as safeguard
        logger.error(f"File not found for scenario '{template_context['scenario_filename']}' in project '{project_name}' despite being in valid list.", exc_info=True)
        flash(f"Scenario forecast file not found: {template_context['scenario_filename']}", "danger")
        return redirect(url_for('.results_page_route'))
    except pd.errors.ParserError as e:
        logger.error(f"Error parsing CSV for scenario '{template_context['scenario_filename']}' in project '{project_name}': {e}", exc_info=True)
        flash(f"Error reading scenario file {template_context['scenario_filename']}. File may be corrupted.", "danger")
        main_df = pd.DataFrame() # Use empty df to prevent further errors
    except Exception as e:
        logger.error(f"Unexpected error reading scenario file {template_context['scenario_filename']} for project '{project_name}': {e}", exc_info=True)
        flash(f"Unexpected error reading scenario file {template_context['scenario_filename']}.", "danger")
        return redirect(url_for('.results_page_route'))

    if main_df is not None and not main_df.empty:
        try:
            template_context["available_sectors"] = sorted(main_df['Sector'].unique().tolist())

            match = re.match(r"demand_forecast_(.+)_(\d{8}_\d{6})\.csv", template_context["scenario_filename"])
            if match: template_context["display_scenario_name"] = f"{match.group(1)} ({match.group(2).replace('_', ' ')})"
            else: template_context["display_scenario_name"] = template_context["scenario_filename"] # Fallback

            scenario_base_name = template_context["scenario_filename"].replace('demand_forecast_', '').replace('.csv', '')
            template_context["current_display_settings"] = load_display_settings(project_path_abs, scenario_base_name)

            # Prepare all_models_in_data_for_all_sectors for the sidebar
            for sector_iter_sidebar in template_context["available_sectors"]:
                models_for_sector = main_df[main_df['Sector'] == sector_iter_sidebar]['Model'].unique().tolist()
                template_context["all_models_in_data_for_all_sectors"][sector_iter_sidebar] = sorted(list(set(models_for_sector)))

            if active_view == 'sector_forecasts':
                selected_sector_arg = request.args.get('sector_name')
                if not selected_sector_arg or selected_sector_arg not in template_context["available_sectors"]:
                    template_context["selected_sector"] = template_context["available_sectors"][0] if template_context["available_sectors"] else None
                else: template_context["selected_sector"] = selected_sector_arg

                if template_context["selected_sector"]:
                    sector_data_df_filtered = main_df[main_df['Sector'] == template_context["selected_sector"]].sort_values(by=['Model', 'Year'])
                    template_context["sector_data_df"] = sector_data_df_filtered
                    if not sector_data_df_filtered.empty:
                        template_context["sector_data_json"] = sector_data_df_filtered.to_json(orient='records')
                    template_context["primary_model_selected"] = template_context["current_display_settings"].get('primary_models', {}).get(template_context["selected_sector"])
                    template_context["all_models_in_data"] = sector_data_df_filtered['Model'].unique().tolist()

            elif active_view == 'final_consolidated':
                primary_models_config = template_context["current_display_settings"].get('primary_models', {})
                td_loss_config = template_context["current_display_settings"].get('td_losses', [])
                final_rows = []
                unique_years_main = sorted(main_df['Year'].unique())

                for sector_iter_final in template_context["available_sectors"]:
                    chosen_model = primary_models_config.get(sector_iter_final)
                    if chosen_model and chosen_model != "":
                        sector_df_filtered = main_df[(main_df['Sector'] == sector_iter_final) & (main_df['Model'] == chosen_model)]
                        if not sector_df_filtered.empty:
                            for year_iter_final in unique_years_main:
                                gross_row = sector_df_filtered[sector_df_filtered['Year'] == year_iter_final]
                                gross_val, low_b, up_b, comm = np.nan, np.nan, np.nan, ''
                                if not gross_row.empty:
                                    gross_val = gross_row['Value'].iloc[0]
                                    low_b = gross_row.get('Lower_Bound', pd.Series(np.nan)).iloc[0] # Handle missing bound/comment cols
                                    up_b = gross_row.get('Upper_Bound', pd.Series(np.nan)).iloc[0]
                                    comm = gross_row.get('Comment', pd.Series('')).iloc[0]
                                else: comm = 'Year not forecasted by chosen primary model'

                                loss_pct = get_interpolated_td_loss(year_iter_final, td_loss_config)
                                loss_amt = gross_val * loss_pct if pd.notna(gross_val) else np.nan
                                net_val = gross_val * (1 - loss_pct) if pd.notna(gross_val) else np.nan
                                final_rows.append({'Year': year_iter_final, 'Sector': sector_iter_final, 'Primary_Model': chosen_model,
                                                   'Gross_Demand': gross_val, 'Gross_Lower_Bound': low_b, 'Gross_Upper_Bound': up_b,
                                                   'T_D_Loss_Pct': loss_pct * 100, 'T_D_Loss_Amount': loss_amt,
                                                   'Net_Demand': net_val, 'Model_Comment': comm})
                final_df_calc = pd.DataFrame(final_rows)
                if not final_df_calc.empty:
                    template_context['final_consolidated_table_data'] = final_df_calc.to_dict(orient='records')
                    total_net_df_calc = final_df_calc.groupby('Year')['Net_Demand'].sum().reset_index()
                    total_net_df_calc.rename(columns={'Net_Demand': 'Total_Net_Demand'}, inplace=True)
                    template_context['total_net_demand_table_data'] = total_net_df_calc.to_dict(orient='records')

        except KeyError as ke:
            logger.error(f"KeyError processing data for scenario '{template_context['scenario_filename']}' in project '{project_name}': {ke}", exc_info=True)
            flash(f"Error processing data for selected scenario: A required data column ('{ke}') might be missing.", "danger")
        except Exception as e_proc:
            logger.error(f"Unexpected error processing data for scenario '{template_context['scenario_filename']}' in project '{project_name}': {e_proc}", exc_info=True)
            flash(f"An unexpected error occurred while processing data for the selected scenario: {str(e_proc)[:100]}", "danger")

    return render_template('sector_detail_demand.html', **template_context)


@bp.route('/save_primary_models/<path:scenario_filename>', methods=['POST'])
def save_primary_models_route(scenario_filename):
    logger = current_app.logger
    project_path_abs = current_app.config.get('CURRENT_PROJECT_PATH_ABS')
    project_name = current_app.config.get('CURRENT_PROJECT_NAME', 'N/A')

    if not project_path_abs:
        logger.error(f"Save primary models: No project loaded. Requested for scenario file: {scenario_filename}")
        return jsonify({'message': 'No project loaded. Cannot save settings.'}), 400

    logger.info(f"Attempting to save primary models for scenario_filename '{scenario_filename}' in project '{project_name}'.")

    safe_scenario_filename_from_path = secure_filename(scenario_filename)
    results_dir_val = os.path.join(project_path_abs, 'results', 'demand_projection')

    # Validate scenario_filename by checking if its corresponding main forecast file exists
    main_forecast_filepath_to_check = os.path.join(results_dir_val, safe_scenario_filename_from_path)
    if not os.path.exists(main_forecast_filepath_to_check) or not safe_scenario_filename_from_path.startswith("demand_forecast_"):
        logger.warning(f"Save primary models: Invalid scenario file specified '{safe_scenario_filename_from_path}' for project '{project_name}'.")
        return jsonify({'message': 'Invalid or non-existent scenario file specified.'}), 400

    scenario_base_name = safe_scenario_filename_from_path.replace('demand_forecast_', '').replace('.csv', '')

    try:
        primary_model_selections = request.get_json()
        if not isinstance(primary_model_selections, dict):
            logger.warning(f"Save primary models: Invalid JSON payload for scenario '{scenario_base_name}', project '{project_name}'. Payload: {primary_model_selections}")
            return jsonify({'message': 'Invalid data format. Expected a JSON object mapping sectors to model names.'}), 400

        # Data integrity check (optional, but good)
        # For example, ensure all sectors in payload are valid for this scenario, and models are valid.
        # This might be too complex if list of sectors/models needs another file read here.
        # For now, assume payload structure is { "SectorName": "ModelName", ... }

        existing_settings = load_display_settings(project_path_abs, scenario_base_name) # Robust load
        existing_settings['primary_models'] = primary_model_selections

        if save_display_settings(project_path_abs, scenario_base_name, existing_settings): # Robust save
            logger.info(f"Primary model selections saved successfully for scenario '{scenario_base_name}', project '{project_name}'.")

            # Attempt to regenerate consolidated results
            main_forecast_filepath = os.path.join(results_dir_val, safe_scenario_filename_from_path)

            scenario_name_from_form = scenario_base_name # Fallback
            match = re.search(r"(.+)_(\d{8}_\d{6})", scenario_base_name)
            if match: scenario_name_from_form = match.group(1)
            else: logger.warning(f"Could not parse original scenario name from base '{scenario_base_name}' for project '{project_name}'. Using base name for consolidated file naming.")

            consolidated_filepath = generate_consolidated_results(
                project_path_abs, scenario_name_from_form,
                main_forecast_filepath, scenario_base_name
            ) # Robust generation

            if consolidated_filepath:
                logger.info(f"Consolidated file updated/created: {consolidated_filepath} for scenario '{scenario_base_name}', project '{project_name}'.")
                try:
                    pm = ProjectManager(current_app.config['PROJECT_ROOT_ABS'])
                    project_folder = os.path.basename(project_path_abs)
                    metadata = pm.get_project_metadata(project_folder) # Robust get
                    if metadata and metadata.get('last_forecast_run', {}).get('file') == safe_scenario_filename_from_path:
                        updated_last_run = metadata['last_forecast_run'].copy()
                        updated_last_run['consolidated_file'] = os.path.basename(consolidated_filepath)
                        updated_last_run['primary_models_set_at'] = datetime.now().isoformat() + 'Z'
                        if pm.update_project_metadata(project_folder, {'last_forecast_run': updated_last_run}): # Robust update
                           logger.info(f"Project metadata 'last_forecast_run' updated for {project_folder} with new consolidated file info.")
                        else: # update_project_metadata logs its own error
                           flash("Project metadata for 'last_forecast_run' could not be updated with new consolidated file info.", "warning") # Won't be seen
                           logger.warning(f"Project metadata 'last_forecast_run' for {project_folder} could not be updated with new consolidated file info from save_primary_models.")
                except Exception as e_meta:
                    logger.error(f"Error updating project metadata for project {project_name} after primary model save for scenario '{scenario_base_name}': {e_meta}", exc_info=True)
                    # Don't let metadata update failure make the whole operation fail.

                return jsonify({'message': f"Primary model selections saved. Consolidated file '{os.path.basename(consolidated_filepath)}' updated/created.",
                                'consolidated_file': os.path.basename(consolidated_filepath)}), 200
            else: # generate_consolidated_results logs its own issues
                logger.warning(f"Primary models saved for scenario '{scenario_base_name}', project '{project_name}', but consolidated file was NOT updated.")
                return jsonify({'message': "Primary model selections saved. Consolidated file NOT updated (e.g., no sectors had explicit primary models, or no data matched).",
                                'consolidated_file': None}), 200
        else: # save_display_settings logs its own error
            logger.error(f"Failed to save display settings (with primary models) for scenario '{scenario_base_name}', project '{project_name}'.")
            return jsonify({'message': 'Error saving primary model selections to display settings file.'}), 500

    except ValueError as ve: # Catch JSON decoding errors or other ValueErrors
        logger.error(f"ValueError in save_primary_models for scenario '{scenario_filename}', project '{project_name}': {ve}", exc_info=True)
        return jsonify({'message': f'Invalid data submitted: {ve}'}), 400
    except Exception as e:
        logger.error(f"Unhandled error in save_primary_models_route for scenario '{scenario_filename}', project '{project_name}': {e}", exc_info=True)
        return jsonify({'message': 'An unexpected server error occurred while saving primary model selections.'}), 500


@bp.route('/save_td_losses/<path:scenario_filename>', methods=['POST'])
def save_td_losses_route(scenario_filename):
    logger = current_app.logger
    project_path_abs = current_app.config.get('CURRENT_PROJECT_PATH_ABS')
    project_name = current_app.config.get('CURRENT_PROJECT_NAME', 'N/A')

    if not project_path_abs:
        logger.error(f"Save T&D losses: No project loaded. Requested for scenario file: {scenario_filename}")
        return jsonify({'message': 'No project loaded. Cannot save T&D losses.'}), 400

    logger.info(f"Attempting to save T&D losses for scenario_filename '{scenario_filename}' in project '{project_name}'.")
    safe_scenario_filename_from_path = secure_filename(scenario_filename)
    results_dir_val = os.path.join(project_path_abs, 'results', 'demand_projection')

    main_forecast_filepath_to_check = os.path.join(results_dir_val, safe_scenario_filename_from_path)
    if not os.path.exists(main_forecast_filepath_to_check) or not safe_scenario_filename_from_path.startswith("demand_forecast_"):
        logger.warning(f"Save T&D losses: Invalid scenario file specified '{safe_scenario_filename_from_path}' for project '{project_name}'.")
        return jsonify({'message': 'Invalid or non-existent scenario file specified for T&D losses.'}), 400

    scenario_base_name = safe_scenario_filename_from_path.replace('demand_forecast_', '').replace('.csv', '')

    try:
        payload = request.get_json()
        if not isinstance(payload, list):
            logger.warning(f"Save T&D losses: Invalid JSON payload type for scenario '{scenario_base_name}', project '{project_name}'. Expected list, got {type(payload)}.")
            return jsonify({'message': 'Invalid data format. Expected a list of T&D entries.'}), 400

        valid_td_entries = []
        for i, entry in enumerate(payload):
            if isinstance(entry, dict) and 'year' in entry and 'loss_pct' in entry:
                try:
                    year = int(entry['year'])
                    loss_pct = float(entry['loss_pct'])
                    if 1900 <= year <= 2100 and 0.0 <= loss_pct <= 100.0:
                        valid_td_entries.append({'year': year, 'loss_pct': loss_pct})
                    else:
                        logger.warning(f"Save T&D losses: Invalid T&D entry data (range error) for scenario '{scenario_base_name}', project '{project_name}'. Entry {i}: Year {year}, Loss {loss_pct}%")
                except (ValueError, TypeError) as e_type:
                    logger.warning(f"Save T&D losses: Invalid type in T&D entry for scenario '{scenario_base_name}', project '{project_name}'. Entry {i}: {entry}. Error: {e_type}")
            else:
                logger.warning(f"Save T&D losses: Malformed T&D entry object for scenario '{scenario_base_name}', project '{project_name}'. Entry {i}: {entry}")

        valid_td_entries.sort(key=lambda x: x['year'])
        settings_to_save = {'td_losses': valid_td_entries}

        if save_display_settings(project_path_abs, scenario_base_name, settings_to_save): # Robust save
            logger.info(f"T&D loss configuration saved successfully for scenario '{scenario_base_name}', project '{project_name}'.")

            # After saving T&D losses, regenerate the consolidated file as it depends on these losses.
            main_forecast_filepath = os.path.join(results_dir_val, safe_scenario_filename_from_path)
            scenario_name_from_form = scenario_base_name # Fallback
            match = re.search(r"(.+)_(\d{8}_\d{6})", scenario_base_name)
            if match: scenario_name_from_form = match.group(1)
            else: logger.warning(f"Could not parse original scenario name from base '{scenario_base_name}' for project '{project_name}' (T&D save). Using base for consolidated name.")

            consolidated_filepath = generate_consolidated_results(
                project_path_abs, scenario_name_from_form,
                main_forecast_filepath, scenario_base_name
            ) # Robust generation

            if consolidated_filepath:
                logger.info(f"Consolidated file updated/created after T&D save: {consolidated_filepath} for scenario '{scenario_base_name}', project '{project_name}'.")
                try: # Update metadata for the consolidated file
                    pm = ProjectManager(current_app.config['PROJECT_ROOT_ABS'])
                    project_folder = os.path.basename(project_path_abs)
                    metadata = pm.get_project_metadata(project_folder)
                    if metadata and metadata.get('last_forecast_run', {}).get('file') == safe_scenario_filename_from_path:
                        updated_last_run = metadata['last_forecast_run'].copy()
                        updated_last_run['consolidated_file'] = os.path.basename(consolidated_filepath)
                        updated_last_run['td_losses_set_at'] = datetime.now().isoformat() + 'Z' # New timestamp for T&D update
                        if pm.update_project_metadata(project_folder, {'last_forecast_run': updated_last_run}):
                           logger.info(f"Project metadata 'last_forecast_run' updated for {project_folder} with new consolidated file after T&D save.")
                        else:
                           logger.warning(f"Project metadata 'last_forecast_run' for {project_folder} could not be updated after T&D save.")
                except Exception as e_meta_td:
                    logger.error(f"Error updating project metadata for project {project_name} after T&D save for scenario '{scenario_base_name}': {e_meta_td}", exc_info=True)

                return jsonify({'message': f"T&D loss configuration saved. Consolidated file '{os.path.basename(consolidated_filepath)}' updated/created.",
                                'consolidated_file': os.path.basename(consolidated_filepath)}), 200
            else:
                logger.warning(f"T&D losses saved for scenario '{scenario_base_name}', project '{project_name}', but consolidated file was NOT updated.")
                return jsonify({'message': "T&D loss configuration saved. Consolidated file NOT updated (e.g. no primary models set).",
                                'consolidated_file': None}), 200
        else: # save_display_settings logs its own error
            logger.error(f"Failed to save display settings (with T&D losses) for scenario '{scenario_base_name}', project '{project_name}'.")
            return jsonify({'message': 'Error saving T&D loss configuration to display settings file.'}), 500

    except ValueError as ve: # Catch JSON decoding errors or other ValueErrors
        logger.error(f"ValueError in save_td_losses for scenario '{scenario_filename}', project '{project_name}': {ve}", exc_info=True)
        return jsonify({'message': f'Invalid data submitted: {ve}'}), 400
    except Exception as e:
        logger.error(f"Unhandled error in save_td_losses_route for scenario '{scenario_filename}', project '{project_name}': {e}", exc_info=True)
        return jsonify({'message': 'An unexpected server error occurred while saving T&D loss configuration.'}), 500


@bp.route('/download_final_consolidated_csv/<path:scenario_filename>')
def download_final_consolidated_csv_route(scenario_filename):
    logger = current_app.logger
    project_path_abs = current_app.config.get('CURRENT_PROJECT_PATH_ABS')
    project_name = current_app.config.get('CURRENT_PROJECT_NAME', 'N/A')

    if not project_path_abs:
        logger.error(f"Download final consolidated CSV: No project loaded. Requested for scenario file: {scenario_filename}")
        flash('No project loaded. Cannot download file.', 'danger')
        return redirect(url_for('main.home'))

    logger.info(f"Attempting to generate and download final consolidated CSV for scenario_filename '{scenario_filename}' in project '{project_name}'.")
    safe_scenario_filename = secure_filename(scenario_filename)
    results_dir = os.path.join(project_path_abs, 'results', 'demand_projection')

    # Validate scenario_filename by checking if its corresponding main forecast file exists
    main_forecast_filepath = os.path.join(results_dir, safe_scenario_filename)
    if not os.path.exists(main_forecast_filepath) or not safe_scenario_filename.startswith("demand_forecast_"):
        logger.warning(f"Download final consolidated CSV: Invalid or non-existent main forecast file '{safe_scenario_filename}' for project '{project_name}'.")
        flash(f"Invalid or non-existent scenario file specified for download: {safe_scenario_filename}", "danger")
        return redirect(url_for('.results_page_route'))

    try:
        main_df = pd.read_csv(main_forecast_filepath)
        if main_df.empty:
            logger.warning(f"Download final consolidated CSV: Main forecast file '{safe_scenario_filename}' is empty for project '{project_name}'.")
            flash(f"Main forecast file '{safe_scenario_filename}' is empty. Cannot generate consolidated CSV.", "warning")
            return redirect(url_for('.view_sector_detail_route', scenario_filename=safe_scenario_filename, view='final_consolidated'))
    except pd.errors.ParserError as e_parse:
        logger.error(f"Error parsing main forecast CSV file {main_forecast_filepath} for project {project_name}: {e_parse}", exc_info=True)
        flash(f"Error reading main forecast file '{safe_scenario_filename}'. File may be corrupted.", "danger")
        return redirect(url_for('.results_page_route'))
    except Exception as e_read:
        logger.error(f"Unexpected error reading main forecast file {main_forecast_filepath} for project {project_name}: {e_read}", exc_info=True)
        flash(f"Error reading main forecast file '{safe_scenario_filename}': {str(e_read)[:100]}", "danger")
        return redirect(url_for('.results_page_route'))

    scenario_base_name = safe_scenario_filename.replace('demand_forecast_', '').replace('.csv', '')
    current_display_settings = load_display_settings(project_path_abs, scenario_base_name) # Robust
    primary_models_config = current_display_settings.get('primary_models', {})
    td_loss_config = current_display_settings.get('td_losses', [])

    if not primary_models_config:
        logger.warning(f"Download final consolidated CSV: No primary models selected for scenario '{scenario_base_name}', project '{project_name}'.")
        flash(f"No primary models selected for scenario '{scenario_base_name}'. Cannot generate this consolidated CSV.", "warning")
        return redirect(url_for('.view_sector_detail_route', scenario_filename=safe_scenario_filename, view='final_consolidated'))

    final_consolidated_data_rows = []
    try:
        available_sectors_sorted = sorted(main_df['Sector'].unique().tolist())
        unique_years = sorted(main_df['Year'].unique())

        for sector_name in available_sectors_sorted:
            chosen_model = primary_models_config.get(sector_name)
            if chosen_model and chosen_model != "":
                sector_df = main_df[(main_df['Sector'] == sector_name) & (main_df['Model'] == chosen_model)]
                for year_val in unique_years: # Renamed to avoid conflict
                    gross_demand_row = sector_df[sector_df['Year'] == year_val]
                    gross_value, lower_b, upper_b, comment_text = np.nan, np.nan, np.nan, ''
                    if not gross_demand_row.empty:
                        gross_value = gross_demand_row['Value'].iloc[0]
                        lower_b = gross_demand_row.get('Lower_Bound', pd.Series(np.nan)).iloc[0]
                        upper_b = gross_demand_row.get('Upper_Bound', pd.Series(np.nan)).iloc[0]
                        comment_text = gross_demand_row.get('Comment', pd.Series('')).iloc[0]
                    else: comment_text = 'Year not forecasted by chosen primary model'

                    td_loss_pct = get_interpolated_td_loss(year_val, td_loss_config) # Robust
                    td_loss_amt = gross_value * td_loss_pct if pd.notna(gross_value) else np.nan
                    net_val = gross_value * (1 - td_loss_pct) if pd.notna(gross_value) else np.nan

                    final_consolidated_data_rows.append({
                        'Year': year_val, 'Sector': sector_name, 'Primary_Model': chosen_model,
                        'Gross_Demand': gross_value, 'Gross_Lower_Bound': lower_b, 'Gross_Upper_Bound': upper_b,
                        'T&D_Loss_Pct': td_loss_pct * 100, 'T&D_Loss_Amount': td_loss_amt,
                        'Net_Demand': net_val, 'Model_Comment': comment_text
                    })
    except KeyError as ke:
        logger.error(f"KeyError generating final consolidated data for {safe_scenario_filename}, project {project_name}: {ke}", exc_info=True)
        flash(f"Error generating data: Missing expected column '{ke}'.", "danger")
        return redirect(url_for('.view_sector_detail_route', scenario_filename=safe_scenario_filename, view='final_consolidated'))
    except Exception as e_proc:
        logger.error(f"Unexpected error generating final consolidated data for {safe_scenario_filename}, project {project_name}: {e_proc}", exc_info=True)
        flash(f"Unexpected error generating data: {str(e_proc)[:100]}.", "danger")
        return redirect(url_for('.view_sector_detail_route', scenario_filename=safe_scenario_filename, view='final_consolidated'))

    if not final_consolidated_data_rows:
        logger.warning(f"No data for final consolidated CSV for {safe_scenario_filename}, project {project_name} (primary models might not be set for any sector).")
        flash("No data to generate for the final consolidated CSV based on current primary model selections.", 'warning')
        return redirect(url_for('.view_sector_detail_route', scenario_filename=safe_scenario_filename, view='final_consolidated'))

    final_df_to_save = pd.DataFrame(final_consolidated_data_rows)
    column_order = ['Year', 'Sector', 'Primary_Model', 'Gross_Demand', 'Gross_Lower_Bound', 'Gross_Upper_Bound',
                    'T&D_Loss_Pct', 'T&D_Loss_Amount', 'Net_Demand', 'Model_Comment']
    final_df_to_save = final_df_to_save.reindex(columns=column_order)

    scenario_name_for_output = scenario_base_name # Fallback
    match = re.search(r"(.+)_(\d{8}_\d{6})", scenario_base_name)
    if match: scenario_name_for_output = match.group(1)

    output_filename = f"consolidated_demand_forecast_{scenario_name_for_output}.csv" # Overwrites previous consolidated
    output_filepath = os.path.join(results_dir, output_filename)

    try:
        final_df_to_save.to_csv(output_filepath, index=False, float_format='%.2f')
        logger.info(f"Final consolidated CSV saved: {output_filepath} for project {project_name}")
    except Exception as e_csv:
        logger.error(f"Error saving final consolidated CSV to {output_filepath} for project {project_name}: {e_csv}", exc_info=True)
        flash(f"Error saving final consolidated CSV: {str(e_csv)[:100]}", "danger")
        return redirect(url_for('.view_sector_detail_route', scenario_filename=safe_scenario_filename, view='final_consolidated'))

    try:
        pm = ProjectManager(current_app.config['PROJECT_ROOT_ABS'])
        project_folder = os.path.basename(project_path_abs)
        metadata = pm.get_project_metadata(project_folder) # Robust
        if metadata and metadata.get('last_forecast_run', {}).get('file') == safe_scenario_filename:
            updated_last_run = metadata['last_forecast_run'].copy()
            updated_last_run['consolidated_file'] = output_filename # Update to this new user-driven one
            updated_last_run['final_consolidation_at'] = datetime.now().isoformat() + 'Z'
            if not pm.update_project_metadata(project_folder, {'last_forecast_run': updated_last_run}): # Robust
                 logger.warning(f"Metadata (last_forecast_run.consolidated_file) update failed for project {project_name} after final consolidated CSV generation.")
                 # Non-critical if this fails, file is still served.
    except Exception as e_meta_final:
        logger.error(f"Error updating project metadata for project {project_name} after final consolidated CSV: {e_meta_final}", exc_info=True)
        # Non-critical, proceed to send file.

    logger.info(f"Sending final consolidated file {output_filename} for project {project_name}.")
    return send_from_directory(results_dir, output_filename, as_attachment=True)


# Helper function to get final net demand for a scenario
def _get_final_net_demand_for_scenario(project_path_abs, scenario_filename_full):
    """
    Calculates final net demand (per sector and total) for a given scenario file.
    Returns a tuple: (detailed_df, total_df, error_message_str_or_none).
    detailed_df has ['Year', 'Sector', 'Net_Demand'].
    total_df has ['Year', 'Total_Net_Demand'].
    """
    logger = current_app.logger # Use logger for internal messages
    results_dir = os.path.join(project_path_abs, 'results', 'demand_projection')
    # Caller should ensure scenario_filename_full is already secured or validated against a list of known files.
    # For this helper, we assume scenario_filename_full is the actual, existing filename.
    safe_scenario_filename = scenario_filename_full

    main_forecast_filepath = os.path.join(results_dir, safe_scenario_filename)

    try:
        main_df = pd.read_csv(main_forecast_filepath)
        if main_df.empty:
            logger.warning(f"_get_final_net_demand: Main forecast file '{safe_scenario_filename}' is empty.")
            return None, None, f"Source forecast data file '{safe_scenario_filename}' is empty."
    except FileNotFoundError:
        logger.error(f"_get_final_net_demand: Main forecast file '{safe_scenario_filename}' not found at {main_forecast_filepath}.", exc_info=True)
        return None, None, f"Source forecast data file '{safe_scenario_filename}' not found."
    except pd.errors.ParserError as e_parse:
        logger.error(f"_get_final_net_demand: Error parsing CSV '{main_forecast_filepath}': {e_parse}", exc_info=True)
        return None, None, f"Error reading data from '{safe_scenario_filename}'. File may be corrupted."
    except Exception as e_read:
        logger.error(f"_get_final_net_demand: Unexpected error reading '{main_forecast_filepath}': {e_read}", exc_info=True)
        return None, None, f"Unexpected error reading data file '{safe_scenario_filename}'."

    scenario_base_name = safe_scenario_filename.replace('demand_forecast_', '').replace('.csv', '')
    display_settings = load_display_settings(project_path_abs, scenario_base_name) # Robust load
    primary_models_config = display_settings.get('primary_models', {})
    td_loss_config = display_settings.get('td_losses', [])

    if not primary_models_config:
        logger.info(f"_get_final_net_demand: No primary models selected for scenario '{scenario_base_name}'.")
        return None, None, f"No primary models selected for scenario '{scenario_base_name}'. Cannot calculate final net demand."

    final_data_rows = []
    try:
        available_sectors = sorted(main_df['Sector'].unique().tolist())
        unique_years = sorted(main_df['Year'].unique())

        for sector_name in available_sectors:
            chosen_model = primary_models_config.get(sector_name)
            if chosen_model and chosen_model != "": # Specific model was selected
                sector_df = main_df[(main_df['Sector'] == sector_name) & (main_df['Model'] == chosen_model)]
                for year_val in unique_years: # Use a different var name for year
                    gross_demand_row = sector_df[sector_df['Year'] == year_val]
                    gross_value = np.nan # Default to NaN
                    if not gross_demand_row.empty:
                        gross_value = gross_demand_row['Value'].iloc[0]

                    td_loss_pct_decimal = get_interpolated_td_loss(year_val, td_loss_config) # Robust util
                    net_demand_val = gross_value * (1 - td_loss_pct_decimal) if pd.notna(gross_value) else np.nan

                    # Only add rows where net_demand could be calculated (i.e., gross_value was not NaN)
                    # Or, decide to include all years for all chosen sectors, with NaNs propagated.
                    # Current logic: if gross_value is NaN, net_demand will be NaN.
                    final_data_rows.append({'Year': year_val, 'Sector': sector_name, 'Net_Demand': net_demand_val})
            # else: If no primary model for sector, or "Auto", it's skipped from this specific net demand calculation.
    except KeyError as ke:
        logger.error(f"_get_final_net_demand: KeyError processing data for scenario '{scenario_base_name}': {ke}. Expected column missing.", exc_info=True)
        return None, None, f"Data processing error for scenario '{scenario_base_name}': Missing column '{ke}'."
    except Exception as e_proc:
        logger.error(f"_get_final_net_demand: Unexpected error processing data for scenario '{scenario_base_name}': {e_proc}", exc_info=True)
        return None, None, f"Unexpected data processing error for scenario '{scenario_base_name}'."

    if not final_data_rows:
        logger.warning(f"_get_final_net_demand: No final net demand data generated for scenario '{scenario_base_name}' based on primary model selections.")
        return None, None, "No final net demand data generated (e.g., no primary models selected or no matching data)."

    detailed_final_df = pd.DataFrame(final_data_rows)
    # Filter out rows where Net_Demand is NaN, if any sector chosen had no forecast for some years.
    # This ensures that groupby().sum() doesn't fail or produce weird results if NaNs are summed.
    detailed_final_df.dropna(subset=['Net_Demand'], inplace=True)

    total_final_df = None
    if not detailed_final_df.empty:
        total_final_df = detailed_final_df.groupby('Year')['Net_Demand'].sum().reset_index()
        total_final_df.rename(columns={'Net_Demand': 'Total_Net_Demand'}, inplace=True)
    else: # If all rows were NaN and got dropped
        logger.warning(f"_get_final_net_demand: All processed rows had NaN Net_Demand for scenario '{scenario_base_name}'.")
        return detailed_final_df, None, "All processed rows had NaN Net_Demand. Totals cannot be computed."

    return detailed_final_df, total_final_df, None


@bp.route('/compare_scenarios')
def compare_scenarios_route():
    logger = current_app.logger
    project_path_abs = current_app.config.get('CURRENT_PROJECT_PATH_ABS')
    project_name = current_app.config.get('CURRENT_PROJECT_NAME', 'N/A')

    template_context = {
        "available_scenarios": [], "scenario_a_id": None, "scenario_b_id": None,
        "comparison_table": [], "plot_data_json": "{}", "error_message": None,
        "project_name": project_name, "current_project_name_g": project_name,
        "scenario_a_display_name": "N/A", "scenario_b_display_name": "N/A"
    }

    if not project_path_abs:
        logger.warning("Compare scenarios: No project loaded.")
        flash('No project loaded. Please load or create one first.', 'warning')
        return render_template('compare_scenarios.html', **template_context)

    logger.info(f"Loading compare scenarios page for project: {project_name}")
    results_dir = os.path.join(project_path_abs, 'results', 'demand_projection')

    try:
        if os.path.exists(results_dir):
            for filename in sorted(os.listdir(results_dir), reverse=True): # Sort for consistent order
                if filename.startswith('demand_forecast_') and filename.endswith('.csv'):
                    try:
                        match = re.match(r"demand_forecast_(.+)_(\d{8}_\d{6})\.csv", filename)
                        if match:
                            scenario_name_part, timestamp_part = match.group(1), match.group(2).replace('_', ':')
                            display_name = f"{scenario_name_part} (Run: {timestamp_part[:8]} {timestamp_part[9:]})"
                        else:
                            scenario_name_part = filename[len('demand_forecast_'):filename.rfind('_', 0, filename.rfind('_'))] if '_' in filename else filename[len('demand_forecast_'):-4]
                            timestamp_part = filename[filename.rfind('_', 0, filename.rfind('_'))+1:].replace('.csv','') if '_' in filename else "N/A"
                            display_name = f"{scenario_name_part} ({timestamp_part})"
                        template_context["available_scenarios"].append({'id': filename, 'display_name': display_name})
                    except Exception as e_parse:
                         logger.error(f"Error parsing scenario filename '{filename}' in project {project_name}: {e_parse}", exc_info=True)
                         template_context["available_scenarios"].append({'id': filename, 'display_name': filename}) # Fallback
        else:
            logger.info(f"Results directory not found for project {project_name} at {results_dir}. No scenarios to compare.")
            flash("No forecast results found to compare for this project.", "info")
            # Render with empty available_scenarios

    except OSError as e:
        logger.error(f"OSError scanning results directory {results_dir} for project {project_name}: {e}", exc_info=True)
        template_context["error_message"] = "Error accessing forecast results directory."
        flash(template_context["error_message"], "danger")
        return render_template('compare_scenarios.html', **template_context)

    scenario_a_id = request.args.get('scenario_a')
    scenario_b_id = request.args.get('scenario_b')
    template_context["scenario_a_id"] = scenario_a_id
    template_context["scenario_b_id"] = scenario_b_id

    if scenario_a_id:
        template_context["scenario_a_display_name"] = next((s['display_name'] for s in template_context["available_scenarios"] if s['id'] == scenario_a_id), "N/A")
    if scenario_b_id:
        template_context["scenario_b_display_name"] = next((s['display_name'] for s in template_context["available_scenarios"] if s['id'] == scenario_b_id), "N/A")

    if scenario_a_id and scenario_b_id:
        if scenario_a_id == scenario_b_id:
            template_context["error_message"] = "Please select two different scenarios for comparison."
        else:
            logger.info(f"Comparing scenarios: '{scenario_a_id}' vs '{scenario_b_id}' for project {project_name}")
            # _get_final_net_demand_for_scenario is already robust and logs its errors
            detail_a_df, total_a_df, err_a = _get_final_net_demand_for_scenario(project_path_abs, scenario_a_id)
            detail_b_df, total_b_df, err_b = _get_final_net_demand_for_scenario(project_path_abs, scenario_b_id)

            current_error = ""
            if err_a: current_error += f"Scenario A ({template_context['scenario_a_display_name']}): {err_a}"
            if err_b: current_error += (" | " if current_error else "") + f"Scenario B ({template_context['scenario_b_display_name']}): {err_b}"
            template_context["error_message"] = current_error if current_error else None


            if detail_a_df is not None and detail_b_df is not None:
                try:
                    comp_df = pd.merge(
                        detail_a_df.rename(columns={'Net_Demand': 'Net_Demand_A'}),
                        detail_b_df.rename(columns={'Net_Demand': 'Net_Demand_B'}),
                        on=['Year', 'Sector'], how='outer'
                    )
                    comp_df['Difference (A-B)'] = comp_df['Net_Demand_A'].fillna(0) - comp_df['Net_Demand_B'].fillna(0)
                    template_context["comparison_table"] = comp_df.to_dict(orient='records')

                    if total_a_df is not None and total_b_df is not None:
                        plot_df = pd.merge(total_a_df, total_b_df, on='Year', how='outer', suffixes=('_A', '_B'))
                        plot_df.rename(columns={'Total_Net_Demand_A': 'Scenario A', 'Total_Net_Demand_B': 'Scenario B'}, inplace=True)
                        plot_df = plot_df.sort_values(by='Year')
                        plot_df.fillna(value=np.nan, inplace=True) # Ensure actual NaNs for Chart.js skipGaps

                        plot_data_dict = {
                            'years': plot_df['Year'].tolist(),
                            'scenario_a_total_net': plot_df['Scenario A'].where(pd.notna(plot_df['Scenario A']), None).tolist(), # Convert NaN to None for JSON
                            'scenario_b_total_net': plot_df['Scenario B'].where(pd.notna(plot_df['Scenario B']), None).tolist(),
                            'scenario_a_name': template_context["scenario_a_display_name"],
                            'scenario_b_name': template_context["scenario_b_display_name"]
                        }
                        template_context["plot_data_json"] = json.dumps(plot_data_dict)
                    else:
                        if not template_context["error_message"]: template_context["error_message"] = "Could not generate total net demand for plotting for one or both scenarios."
                        logger.warning(f"Plot data generation failed for scenario comparison between '{scenario_a_id}' and '{scenario_b_id}' in project {project_name}.")
                except Exception as e_comp:
                    logger.error(f"Error during comparison data processing for {scenario_a_id} vs {scenario_b_id} in project {project_name}: {e_comp}", exc_info=True)
                    template_context["error_message"] = f"Error generating comparison: {str(e_comp)[:100]}"

            elif not template_context["error_message"]:
                 template_context["error_message"] = "Failed to process one or both scenarios fully for comparison. Check individual scenario processing."
                 logger.warning(f"Comparison failed due to incomplete data for {scenario_a_id} or {scenario_b_id} in project {project_name}.")

    if template_context["error_message"]:
        flash(template_context["error_message"], "danger")

    return render_template('compare_scenarios.html', **template_context)


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
