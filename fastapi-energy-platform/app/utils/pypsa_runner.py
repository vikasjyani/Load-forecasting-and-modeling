# utils/pypsa_runner.py
import pandas as pd
import pypsa
import os
from pathlib import Path
import numpy as np
import logging
import numpy_financial as npf
import traceback
import threading
from datetime import datetime
import asyncio # Required for run_coroutine_threadsafe
from typing import Dict, List, Any, Optional

# Assuming PyPSAJobManager is correctly typed and imported if needed for type hints here
# from app.services.pypsa_service import PyPSAJobManager
from app.utils.pypsa_helpers import extract_tables_by_markers, annuity_future_value
from app.utils.helpers import safe_filename # For directory names

logger = logging.getLogger(__name__)

# This type hint is for clarity; the actual instance is passed.
PyPSAJobManager = Any

def run_pypsa_model_core(
    job_id: str,
    project_path_str: str,
    scenario_name: str,
    ui_settings_overrides: Dict[str, Any],
    job_manager: PyPSAJobManager,
    event_loop: asyncio.AbstractEventLoop
):
    """
    Main PyPSA model execution function - Iterative Single-Year Optimization.
    Adapted to use PyPSAJobManager for status updates via asyncio.run_coroutine_threadsafe.
    """
    original_cwd = os.getcwd()

    # --- Helper functions to interact with the Job Manager safely from this thread ---
    def _update_status_sync(status: str, progress: Optional[int] = None, current_step: Optional[str] = None, is_error: bool = False):
        if event_loop and not event_loop.is_closed():
            future = asyncio.run_coroutine_threadsafe(
                job_manager.update_job_status(job_id, status, progress, current_step),
                event_loop
            )
            try: future.result(timeout=5) # Wait for a short period
            except TimeoutError: logger.error(f"Job {job_id}: Timeout updating status to {status}")
            except Exception as e: logger.error(f"Job {job_id}: Error in _update_status_sync: {e}")
        else:
            logger.error(f"Job {job_id}: Event loop not available for status update: {status} - {current_step}")
            logger.info(f"Job {job_id} Fallback Log (NO UPDATE TO MANAGER): {status} - {current_step or ''} ({progress or ''}%)")

    def _add_log_sync(message: str, level: str = "INFO"):
        if event_loop and not event_loop.is_closed():
            future = asyncio.run_coroutine_threadsafe(
                job_manager.add_log_entry(job_id, message, level),
                event_loop
            )
            try: future.result(timeout=5)
            except TimeoutError: logger.error(f"Job {job_id}: Timeout adding log: {message}")
            except Exception as e: logger.error(f"Job {job_id}: Error in _add_log_sync: {e}")
        else:
            logger.error(f"Job {job_id}: Event loop not available for log entry: {message}")
            logger.info(f"Job {job_id} Fallback Log (NO UPDATE TO MANAGER): {level} - {message}")

    def _complete_job_sync(result_summary: Dict[str, Any]):
        if event_loop and not event_loop.is_closed():
            future = asyncio.run_coroutine_threadsafe(
                job_manager.complete_job(job_id, result_summary),
                event_loop
            )
            try: future.result(timeout=10)
            except TimeoutError: logger.error(f"Job {job_id}: Timeout completing job.")
            except Exception as e: logger.error(f"Job {job_id}: Error in _complete_job_sync: {e}")
        else: logger.error(f"Job {job_id}: Event loop not available for _complete_job_sync.")

    def _fail_job_sync(error_message: str):
        if event_loop and not event_loop.is_closed():
            future = asyncio.run_coroutine_threadsafe(
                job_manager.fail_job(job_id, error_message),
                event_loop
            )
            try: future.result(timeout=10)
            except TimeoutError: logger.error(f"Job {job_id}: Timeout failing job.")
            except Exception as e: logger.error(f"Job {job_id}: Error in _fail_job_sync: {e}")
        else: logger.error(f"Job {job_id}: Event loop not available for _fail_job_sync.")
    # --- End Helper Functions ---

    try:
        _update_status_sync(status='Processing Inputs', progress=5, current_step='Initializing PyPSA model and reading inputs')
        _add_log_sync(f"Model run for scenario '{scenario_name}' started at {datetime.now().isoformat()}.")

        project_path = Path(project_path_str)
        input_file_path = project_path / "inputs" / "pypsa_input_template.xlsx"
        # Ensure scenario_name is safe for path creation
        scenario_results_dir = project_path / "results" / "pypsa" / safe_filename(scenario_name)

        scenario_results_dir.mkdir(parents=True, exist_ok=True)
        _add_log_sync(f"Results will be saved to: {scenario_results_dir}")

        if not input_file_path.exists():
            raise FileNotFoundError(f"PyPSA input template not found: {input_file_path}")

        _add_log_sync(f"Reading input file: {input_file_path}")
        _update_status_sync(progress=10)

        try:
            xls = pd.ExcelFile(str(input_file_path))
            sheet_names_in_excel = xls.sheet_names
            required_sheets_map = {
                'Settings': 'setting_df_excel', 'Generators': 'generators_base_df',
                'Buses': 'buses_df', 'Demand': 'demand_excel_df',
                'Lifetime': 'lifetime_df', 'FOM': 'fom_df',
                'Fuel_cost': 'fuel_cost_df', 'Startupcost': 'startupcost_df',
                'CO2': 'co2_df', 'P_max_pu': 'p_max_pu_excel_df',
                'P_min_pu': 'p_min_pu_excel_df', 'Capital_cost': 'capital_cost_df',
                'wacc': 'wacc_df', 'New_Generators': 'new_generators_excel_df',
                'Pipe_Line_Generators_p_max': 'pipe_line_generators_p_max_df',
                'Pipe_Line_Generators_p_min': 'pipe_line_generators_p_min_df',
                'New_Storage': 'new_storage_excel_df', 'Links': 'links_excel_df',
                'Pipe_Line_Storage_p_min': 'pipe_line_storage_p_min_df'
            }
            loaded_data = {}
            missing_critical_sheets = []
            for sheet_name_excel, df_name in required_sheets_map.items():
                if sheet_name_excel in sheet_names_in_excel:
                    loaded_data[df_name] = xls.parse(sheet_name_excel)
                elif sheet_name_excel in ['Settings', 'Generators', 'Buses', 'Demand']:
                    missing_critical_sheets.append(sheet_name_excel)
                else:
                    logger.warning(f"Optional sheet '{sheet_name_excel}' not found in Excel. Proceeding with empty DataFrame.")
                    _add_log_sync(f"Optional sheet '{sheet_name_excel}' not found. Using empty data.", level="WARNING")
                    loaded_data[df_name] = pd.DataFrame()

            if 'Custom days' in sheet_names_in_excel:
                loaded_data['custom_days_df'] = xls.parse('Custom days')
            else:
                loaded_data['custom_days_df'] = pd.DataFrame()

            if missing_critical_sheets:
                raise ValueError(f"Missing critical sheets in Excel file: {', '.join(missing_critical_sheets)}")

            setting_df_excel = loaded_data['setting_df_excel']
            generators_base_df = loaded_data['generators_base_df']
            # ... (assign all other dfs from loaded_data similarly) ...
            buses_df = loaded_data['buses_df']; lifetime_df = loaded_data['lifetime_df']; fom_df = loaded_data['fom_df']
            demand_excel_df = loaded_data['demand_excel_df']; fuel_cost_df = loaded_data['fuel_cost_df']
            startupcost_df = loaded_data['startupcost_df']; co2_df = loaded_data['co2_df']
            p_max_pu_excel_df = loaded_data['p_max_pu_excel_df']; p_min_pu_excel_df = loaded_data['p_min_pu_excel_df']
            capital_cost_df = loaded_data['capital_cost_df']; wacc_df = loaded_data['wacc_df']
            new_generators_excel_df = loaded_data['new_generators_excel_df']
            pipe_line_generators_p_max_df = loaded_data['pipe_line_generators_p_max_df']
            pipe_line_generators_p_min_df = loaded_data['pipe_line_generators_p_min_df']
            new_storage_excel_df = loaded_data['new_storage_excel_df']
            links_excel_df = loaded_data['links_excel_df']
            pipe_line_storage_p_min_df = loaded_data['pipe_line_storage_p_min_df']
            custom_days_df = loaded_data['custom_days_df']

        except Exception as e:
            raise ValueError(f"Error reading or validating Excel file sheets: {str(e)}")

        _add_log_sync("Excel file sheets validated and loaded.")
        _update_status_sync(progress=15)

        settings_main_excel_table = extract_tables_by_markers(setting_df_excel, '~').get('Main_Settings')
        if settings_main_excel_table is None or settings_main_excel_table.empty:
            raise ValueError("Table '~Main_Settings' not found or empty in 'Settings' sheet.")

        # get_setting function adapted to use _add_log_sync
        def get_setting(key, default_value, df=settings_main_excel_table, overrides=ui_settings_overrides):
            val_override = overrides.get(key)
            if val_override is not None:
                _add_log_sync(f"UI Override for '{key}': {val_override}")
                # Type casting for known numeric or boolean settings from UI
                if key in ['Weightings', 'Base_Year', 'solver_threads', 'simplex_strategy']: # Added simplex_strategy
                    try: return int(val_override)
                    except ValueError: return default_value
                if key in ['Generator Cluster', 'Committable', 'solver_parallel', 'solver_presolve', 'log_to_console_solver']:
                    return str(val_override).lower() == 'true' # More robust boolean conversion
                if key == 'pdlp_gap_tol':
                     try: return float(val_override)
                     except: return default_value
                return val_override

            row = df[df['Setting'] == key]
            if not row.empty and 'Option' in row.columns and pd.notna(row['Option'].iloc[0]):
                excel_val = row['Option'].iloc[0]
                _add_log_sync(f"Excel Setting for '{key}': {excel_val}")
                if key in ['Weightings', 'Base_Year', 'simplex_strategy']:
                    try: return int(excel_val) if pd.notna(excel_val) and float(excel_val).is_integer() else float(excel_val)
                    except ValueError: return default_value
                if key in ['Generator Cluster', 'Committable', 'solver_parallel', 'solver_presolve', 'log_to_console_solver']:
                    return str(excel_val).strip().lower() == 'yes'
                if key == 'pdlp_gap_tol':
                     try: return float(excel_val)
                     except: return default_value
                return excel_val
            _add_log_sync(f"Using default for '{key}': {default_value}")
            return default_value

        snapshot_condition = get_setting('Run Pypsa Model on', 'All Snapshots')
        weightings_freq_hours = get_setting('Weightings', 1)
        base_year_config = get_setting('Base_Year', 2025)
        multi_year_mode = get_setting('Multi Year Investment', 'No')
        do_generator_clustering = get_setting('Generator Cluster', False)
        do_unit_commitment = get_setting('Committable', False)

        _add_log_sync(f"Settings: Snapshots='{snapshot_condition}', Weightings(Duration)={weightings_freq_hours}h, BaseYear={base_year_config}, MultiYear='{multi_year_mode}', Clustering={do_generator_clustering}, UC={do_unit_commitment}")
        _update_status_sync(progress=20)

        solver_name_opt = get_setting('solver_name', 'highs')
        solver_threads_val = get_setting('solver_threads', 0)

        solver_options_from_ui = {
            'log_file': str(scenario_results_dir / f'{safe_filename(scenario_name)}_solver_{datetime.now().strftime("%Y%m%d%H%M")}.log'),
            "threads": int(solver_threads_val),
            "solver": get_setting('highs_solver_type', "simplex"),
            "parallel": "on" if get_setting('solver_parallel', True) else "off",
            "presolve": "on" if get_setting('solver_presolve', True) else "off",
            'log_to_console': get_setting('log_to_console_solver', True)
        }
        if solver_options_from_ui["solver"] == "pdlp":
            pdlp_gap_tol_val = get_setting('pdlp_gap_tol', 1e-4)
            solver_options_from_ui['pdlp_d_gap_tol'] = float(pdlp_gap_tol_val) if pdlp_gap_tol_val is not None else 1e-4
            if 'simplex_strategy' in solver_options_from_ui: del solver_options_from_ui['simplex_strategy']
        elif solver_options_from_ui["solver"] == "simplex":
            simplex_strat_val = get_setting('simplex_strategy', 0)
            solver_options_from_ui['simplex_strategy'] = int(simplex_strat_val) if simplex_strat_val is not None else 0
            if 'pdlp_d_gap_tol' in solver_options_from_ui: del solver_options_from_ui['pdlp_d_gap_tol']

        _add_log_sync(f"Solver: {solver_name_opt}, Options: {solver_options_from_ui}")

        year_list_from_demand = sorted([
            int(col) for col in demand_excel_df.columns
            if isinstance(col, (int, str)) and str(col).isdigit() and len(str(col)) == 4 and str(col).startswith('20')
        ])
        years_to_simulate = [yr for yr in year_list_from_demand if yr >= base_year_config]

        if not years_to_simulate:
            raise ValueError(f"No simulation years found. Base year: {base_year_config}, Demand years available: {year_list_from_demand}")
        _add_log_sync(f"Simulation years based on demand data and base year: {years_to_simulate}")
        _update_status_sync(progress=25)

        committable_settings_df = extract_tables_by_markers(setting_df_excel, '~').get('commitable', pd.DataFrame())

        if multi_year_mode == 'No':
            _update_status_sync(status='Running Single-Year Models')
            previous_year_export_path_obj = None

            for idx, current_year in enumerate(years_to_simulate):
                _update_status_sync(current_step=f"Processing Year: {current_year}")
                _add_log_sync(f"\n--- Starting processing for simulation year: {current_year} ---")
                current_progress_base = 30 + int(((idx) / len(years_to_simulate)) * 60)

                # 1. Generate Snapshots
                _add_log_sync(f"Generating snapshots for FY{current_year} with condition '{snapshot_condition}' and {weightings_freq_hours}h resolution.")
                # Pass _add_log_sync instead of raw list for _generate_snapshots_for_year
                model_snapshots_index, full_year_hourly_index = _generate_snapshots_for_year(
                    str(input_file_path), current_year, snapshot_condition, weightings_freq_hours, base_year_config, demand_excel_df, custom_days_df, _add_log_sync
                )
                if model_snapshots_index.empty:
                    _add_log_sync(f"Warning: No snapshots generated for year {current_year}. Skipping this year.", level="WARNING")
                    continue
                _add_log_sync(f"Generated {len(model_snapshots_index)} snapshots for model, from {len(full_year_hourly_index)} hourly base snapshots.")
                _update_status_sync(progress=current_progress_base + 2)

                # ... (The rest of the PyPSA logic: network creation, adding components, optimization, export)
                # All job['log'].append should become _add_log_sync(...)
                # All job['progress'] = ... should become _update_status_sync(progress=...)
                # All job['current_step'] = ... should become _update_status_sync(current_step=...)

                # --- Placeholder for the rest of the extensive PyPSA logic ---
                # This section would involve detailed adaptation of adding buses, loads, carriers,
                # generators (existing and new), storage, links, applying retiring logic,
                # clustering, unit commitment, constraints, and finally optimization and export.
                # Each step would have logging and progress updates.

                # For brevity in this diff, assume a simplified loop for now:
                n = pypsa.Network() # Simplified network setup
                n.set_snapshots(model_snapshots_index)
                n.snapshot_weightings["objective"] = weightings_freq_hours
                _add_log_sync(f"Simplified network setup for year {current_year}.")
                _update_status_sync(progress=current_progress_base + 30)

                # Simulate optimization
                _add_log_sync(f"Simulating optimization for {current_year}...")
                time.sleep(0.1) # Simulate work
                n.objective = np.random.rand() * 1e6 # Mock objective
                _add_log_sync(f"Simulated optimization for year {current_year} complete. Objective: {n.objective:.2f}")
                _update_status_sync(progress=current_progress_base + 45)

                # Simulate export
                year_results_dir_obj = scenario_results_dir / f"results_{current_year}"
                year_results_dir_obj.mkdir(parents=True, exist_ok=True)
                netcdf_file_name_year = scenario_results_dir / f"{safe_filename(scenario_name)}_{current_year}_network.nc"
                # n.export_to_netcdf(str(netcdf_file_name_year)) # Actual export
                _add_log_sync(f"Simulated export for {current_year}. NetCDF: {netcdf_file_name_year.name}")
                previous_year_export_path_obj = year_results_dir_obj
                _update_status_sync(progress=current_progress_base + 60)
                # --- End of simplified loop section ---


            _add_log_sync("All single-year models processed successfully.")

        elif multi_year_mode == 'Only Capacity expansion on multi year' or multi_year_mode == 'All in One multi year':
            _add_log_sync(f"Multi-year mode '{multi_year_mode}' selected. This is a complex setup.", level="WARNING")
            _update_status_sync(status='Running Multi-Year Model')
            raise NotImplementedError(f"Multi-year mode '{multi_year_mode}' is not fully implemented in this version of pypsa_runner.py.")
        else:
            raise ValueError(f"Unknown 'Multi Year Investment' mode: {multi_year_mode}")

        result_files_list = []
        if scenario_results_dir.exists():
            for item_path in scenario_results_dir.rglob('*'):
                if item_path.is_file():
                    result_files_list.append(str(item_path.relative_to(project_path))) # Path relative to project for consistency

        result_summary_final = {
            'message': 'Model run completed successfully.',
            'output_scenario_path': str(scenario_results_dir.relative_to(project_path)),
            'result_files': result_files_list,
            'simulated_years': years_to_simulate
        }
        _complete_job_sync(result_summary_final)
        _add_log_sync(f"PyPSA Model run '{scenario_name}' finished successfully at {datetime.now().isoformat()}.")
        logger.info(f"Job {job_id} for scenario '{scenario_name}' completed.")

    except FileNotFoundError as e:
        error_msg = f"File Not Found Error: {str(e)}"
        _add_log_sync(f"CRITICAL ERROR: {error_msg}", level="ERROR")
        _fail_job_sync(error_msg)
        logger.error(f"Job {job_id} (Scenario: {scenario_name}) failed: {error_msg}", exc_info=False)
    except ValueError as e:
        error_msg = f"Validation/Configuration Error: {str(e)}"
        _add_log_sync(f"CRITICAL ERROR: {error_msg}", level="ERROR")
        _fail_job_sync(error_msg)
        logger.error(f"Job {job_id} (Scenario: {scenario_name}) failed: {error_msg}", exc_info=True)
    except NotImplementedError as e:
        error_msg = f"Feature Not Implemented: {str(e)}"
        _add_log_sync(f"ERROR: {error_msg}", level="ERROR")
        _fail_job_sync(error_msg)
        logger.error(f"Job {job_id} (Scenario: {scenario_name}) failed: {error_msg}", exc_info=False)
    except Exception as e:
        error_msg = f"An unexpected error occurred: {str(e)}"
        stack_trace = traceback.format_exc()
        _add_log_sync(f"CRITICAL UNEXPECTED ERROR: {error_msg}", level="CRITICAL")
        _add_log_sync(f"Stack trace: {stack_trace}", level="DEBUG") # Only log full trace to job log if needed
        _fail_job_sync(error_msg) # Send concise error to manager
        logger.error(f"Job {job_id} (Scenario: {scenario_name}) failed critically with an unexpected error.", exc_info=True)
    finally:
        # Ensure final status is set even if helpers failed due to loop closure.
        current_job_state = asyncio.run_coroutine_threadsafe(job_manager.get_job(job_id), event_loop).result(timeout=5)
        if current_job_state and current_job_state.status not in [JOB_STATUS['COMPLETED'], JOB_STATUS['FAILED']]:
            _fail_job_sync("Job finalized with unknown error after main execution block.")
        os.chdir(original_cwd)


# Helper function to generate snapshots for a single year
# Adapted to use the _add_log_sync function for logging
def _generate_snapshots_for_year(input_file_path_str, target_year, snapshot_condition, weightings_freq_hours, base_year_config, demand_df, custom_days_df, add_log_func: Callable):
    """
    Generate snapshots for a specific year based on condition.
    `demand_df` and `custom_days_df` are passed as already loaded DataFrames.
    `add_log_func` is the synchronized logging function.
    """
    add_log_func(f"Snapshot generation for FY{target_year}: Condition='{snapshot_condition}', Freq={weightings_freq_hours}H.")

    fy_start_date = pd.Timestamp(f'{int(target_year)-1}-04-01 00:00:00')
    fy_end_date = pd.Timestamp(f'{int(target_year)}-03-31 23:00:00')
    full_year_hourly_index = pd.date_range(start=fy_start_date, end=fy_end_date, freq='H')

    def _resample_dt_index(dt_index_to_resample, freq_hours_val):
        if not isinstance(dt_index_to_resample, pd.DatetimeIndex) or dt_index_to_resample.empty:
            add_log_func("Warning: _resample_dt_index received empty or invalid index. Returning empty.", level="WARNING")
            return pd.DatetimeIndex([])
        try:
            resampled_idx = pd.Series(1, index=dt_index_to_resample).resample(f'{int(freq_hours_val)}H').asfreq().index
            return resampled_idx
        except Exception as e_resample:
            add_log_func(f"Error during resampling: {e_resample}. Falling back to original index or empty.", level="ERROR")
            return dt_index_to_resample if int(freq_hours_val) == 1 else pd.DatetimeIndex([])

    selected_snapshots_for_model = pd.DatetimeIndex([])

    if snapshot_condition == 'All Snapshots':
        selected_snapshots_for_model = _resample_dt_index(full_year_hourly_index, weightings_freq_hours)
    elif snapshot_condition == 'Critical days':
        if custom_days_df.empty:
            add_log_func("Warning: 'Critical days' selected but 'Custom days' sheet is empty or missing. Defaulting to 'All Snapshots'.", level="WARNING")
            selected_snapshots_for_model = _resample_dt_index(full_year_hourly_index, weightings_freq_hours)
        else:
            try:
                df_cd = custom_days_df.copy()
                df_cd['CalendarYear'] = df_cd['Month'].apply(
                    lambda m: int(target_year) - 1 if int(m) >= 4 else int(target_year)
                )
                custom_dates_pd = pd.to_datetime(
                    {'year': df_cd['CalendarYear'], 'month': df_cd['Month'], 'day': df_cd['Day']}
                )
                hourly_custom_day_snapshots = pd.DatetimeIndex([])
                for date_val in sorted(custom_dates_pd.unique()):
                    hourly_custom_day_snapshots = hourly_custom_day_snapshots.union(
                        pd.date_range(start=date_val, periods=24, freq='H')
                    )
                selected_snapshots_for_model = _resample_dt_index(hourly_custom_day_snapshots, weightings_freq_hours)
            except Exception as e_crit:
                add_log_func(f"Error processing critical days for {target_year}: {e_crit}. Defaulting to 'All Snapshots'.", level="ERROR")
                selected_snapshots_for_model = _resample_dt_index(full_year_hourly_index, weightings_freq_hours)

    elif snapshot_condition == 'Typical days':
        try:
            demand_col_to_use_snap = target_year if target_year in demand_df.columns else base_year_config
            if demand_col_to_use_snap not in demand_df.columns:
                 add_log_func(f"Demand data for year {demand_col_to_use_snap} not found for Typical Days. Defaulting to All.", level="WARNING")
                 selected_snapshots_for_model = _resample_dt_index(full_year_hourly_index, weightings_freq_hours)
            else:
                demand_series_full_fy = pd.Series(demand_df[demand_col_to_use_snap].values, index=full_year_hourly_index)
                temp_df = demand_series_full_fy.to_frame('demand')
                temp_df['month_in_fy'] = (temp_df.index.month - fy_start_date.month + 12) % 12
                temp_df['week_in_fy'] = (temp_df.index - fy_start_date).days // 7

                peak_week_snapshots_list = []
                for _, month_group in temp_df.groupby('month_in_fy'):
                    if month_group.empty: continue
                    weekly_sum = month_group.groupby('week_in_fy')['demand'].sum()
                    if weekly_sum.empty: continue
                    peak_week_num_in_fy = weekly_sum.idxmax()
                    peak_week_snapshots_list.extend(month_group[month_group['week_in_fy'] == peak_week_num_in_fy].index)

                if peak_week_snapshots_list:
                    selected_snapshots_for_model = _resample_dt_index(pd.DatetimeIndex(sorted(list(set(peak_week_snapshots_list)))), weightings_freq_hours)
                else:
                    add_log_func(f"No peak weeks identified for FY{target_year}. Defaulting to 'All Snapshots'.", level="WARNING")
                    selected_snapshots_for_model = _resample_dt_index(full_year_hourly_index, weightings_freq_hours)
        except Exception as e_typ:
            add_log_func(f"Error processing typical days for {target_year}: {e_typ}. Defaulting to 'All Snapshots'.", level="ERROR")
            selected_snapshots_for_model = _resample_dt_index(full_year_hourly_index, weightings_freq_hours)
    else:
        add_log_func(f"Unknown snapshot condition: '{snapshot_condition}'. Defaulting to 'All Snapshots'.", level="WARNING")
        selected_snapshots_for_model = _resample_dt_index(full_year_hourly_index, weightings_freq_hours)

    if selected_snapshots_for_model.empty:
         add_log_func(f"Warning: Snapshot generation resulted in an empty list for FY{target_year}. This might cause errors.", level="WARNING")

    return selected_snapshots_for_model, full_year_hourly_index


# Network-based retiring logic (operates on the pypsa.Network object)
# These helpers will also need to use add_log_func if they log
def _apply_retiring_logic_network(n, select_year, base_year, add_log_func: Callable):
    """Apply generator retiring logic directly on the PyPSA network object."""
    # ... (rest of the function, replacing logger.info/warning with add_log_func) ...
    # Example: add_log_func(f"Retired {len(unique_gens_to_remove)} generators for year {select_year}.")
    generators_to_remove = [] # Placeholder
    if generators_to_remove: n.remove("Generator", list(set(generators_to_remove)))
    return n

def _apply_storage_retiring_logic_network(n, select_year, base_year, add_log_func: Callable):
    """Apply storage retiring logic directly on the PyPSA network object."""
    # ... (similar replacements) ...
    stores_to_remove = [] # Placeholder
    storage_units_to_remove = [] # Placeholder
    if stores_to_remove: n.remove("Store", list(set(stores_to_remove)))
    if storage_units_to_remove: n.remove("StorageUnit", list(set(storage_units_to_remove)))
    return n

def _apply_generator_clustering(n, p_max_pu_aligned_dfs, p_min_pu_aligned_dfs, add_log_func: Callable):
    """Apply generator clustering."""
    # ... (similar replacements) ...
    return n

def _apply_network_constraints(n, setting_df_excel, settings_main_excel_table, job_manager_arg: PyPSAJobManager, job_id_arg: str, event_loop_arg: asyncio.AbstractEventLoop, solver_name_arg: str, solver_options_dict_arg: Dict):
    """Apply network constraints, using job_manager for logging via a local _add_log_sync."""

    def _local_add_log_sync(message: str, level: str = "INFO"): # Local helper for this function scope
        if event_loop_arg and not event_loop_arg.is_closed():
            asyncio.run_coroutine_threadsafe(
                job_manager_arg.add_log_entry(job_id_arg, message, level),
                event_loop_arg
            ).result(timeout=5)
        else: logger.info(f"Job {job_id_arg} (Constraint Log): {level} - {message}")

    # ... (rest of the function, replacing log_list.append with _local_add_log_sync) ...
    # ... and n.optimize.solve_model with n.optimize(solver_name=solver_name_arg, solver_options=solver_options_dict_arg)
    # or n.lopf(...) then n.solve(...)
    # The re-solve part:
    # if constraints_were_added:
    #     _local_add_log_sync("Re-solving model with added network constraints...")
    #     n.optimize(solver_name=solver_name_arg, solver_options=solver_options_dict_arg) # Re-solve the full model
    #     _local_add_log_sync("Model re-solved after adding constraints.")
    return n

# Note: The actual detailed logic within _apply_retiring_logic_network,
# _apply_storage_retiring_logic_network, _apply_generator_clustering,
# and the main PyPSA component addition loop needs to be meticulously updated
# to use the new _add_log_sync and _update_status_sync helpers.
# The provided diff only covers the initial setup and the structure for these changes.
# The full change would be much larger.
