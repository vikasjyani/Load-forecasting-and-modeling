# app/utils/helpers.py
"""
Helper utilities for the Energy Futures Platform (FastAPI version)
"""
import os
import shutil
import pandas as pd
import numpy as np
import json
import logging
from pathlib import Path
from datetime import datetime
from fastapi import UploadFile # Used for type hinting if a helper processes UploadFile directly
from typing import Union, List, Dict, Any, Optional, Tuple # Added Optional, Any, Tuple
import asyncio # For async operations

# Assuming constants are now in fastapi-energy-platform/app/utils/constants.py
from app.utils.constants import (
    PROJECT_STRUCTURE, TEMPLATE_FILES, ERROR_MESSAGES,
    VALIDATION_RULES, DEFAULT_PATHS # Review DEFAULT_PATHS for FastAPI context
)

logger = logging.getLogger(__name__)

def slugify(text: str) -> str:
    """
    Convert text to a safe slug for use in IDs and filenames.
    A slug is a URL-friendly version of a string, typically lowercase,
    with words separated by hyphens, and special characters removed.

    Args:
        text (str): The input string to slugify.

    Returns:
        str: The slugified string.
    """
    import re
    from unicodedata import normalize

    text = str(text).lower().strip()
    text = normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^\w\s-]', '', text) # Remove non-alphanumeric, non-space, non-hyphen
    text = re.sub(r'[-\s]+', '-', text)  # Replace spaces and multiple hyphens with single hyphen
    return text

def safe_filename(filename: str) -> str:
    """
    Creates a filename that is safe for use in most filesystems.
    Removes directory path components and limits characters to alphanumeric,
    dots, hyphens, and underscores. Other characters are replaced with underscores.

    Args:
        filename (str): The original filename.

    Returns:
        str: The sanitized filename. Returns an empty string if input is empty.
    """
    if not filename:
        return ""

    name_part = Path(filename).name # Get only the filename part, remove directory paths
    # Replace any character not in the allowed set with an underscore
    sanitized_name = "".join(c if c.isalnum() or c in ('.', '-', '_') else '_' for c in name_part)
    # Prevent names like ".." or "."
    if sanitized_name in {".", ".."}:
        return "_"
    return sanitized_name


def ensure_directory(path: Union[Path, str]) -> bool:
    """
    Ensures that a directory exists at the given path.
    If the directory (or any parent directories) does not exist, it creates them.

    Args:
        path (Union[Path, str]): The path to the directory. Can be a Path object or a string.

    Returns:
        bool: True if the directory exists or was successfully created, False otherwise.
    """
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Failed to create directory {path}: {e}", exc_info=True)
        return False

async def create_project_structure(project_path: Union[Path, str], template_root_path: Optional[Union[Path, str]] = None) -> Dict[str, Any]:
    """
    Creates a standard project folder structure at the given project_path.
    Optionally copies template files from template_root_path into the 'inputs' subdirectory.

    Args:
        project_path (Union[Path, str]): The root path where the project structure will be created.
        template_root_path (Optional[Union[Path, str]]): Absolute or resolvable path to the root
                                                          directory containing template files.
                                                          If None, template copying is skipped.

    Returns:
        Dict[str, Any]: A dictionary containing:
            - 'success' (bool): True if structure creation was successful.
            - 'message' (str): A status message.
            - 'created_folders' (List[str]): List of folders created.
            - 'copied_templates' (List[str]): List of template filenames copied.
            - 'metadata_path' (str): Path to the created project metadata JSON file.
            - 'error' (str, optional): Error message if success is False.
    """
    project_path = Path(project_path)
    logger.info(f"Attempting to create project structure at: {project_path}")

    if not ensure_directory(project_path): # ensure_directory is sync again
        return {
            'success': False, 'message': f'Failed to create main project directory: {project_path}',
            'created_folders': [], 'copied_templates': [], 'metadata_path': '', 'error': 'Directory creation failed.'
        }

    created_folders: List[str] = []
    for folder_name, subfolders_dict in PROJECT_STRUCTURE.items(): # PROJECT_STRUCTURE from constants
        folder_path = project_path / folder_name
        if ensure_directory(folder_path): # ensure_directory is sync again
            created_folders.append(folder_name)
            if isinstance(subfolders_dict, dict): # If subfolders are defined
                for subfolder_name in subfolders_dict.keys():
                    subfolder_path = folder_path / subfolder_name
                    if ensure_directory(subfolder_path): # ensure_directory is sync again
                        created_folders.append(f"{folder_name}/{subfolder_name}")

    copied_templates: List[str] = []
    if template_root_path:
        template_root_path = Path(template_root_path)
        # Use asyncio.to_thread for path checks
        template_root_exists = await asyncio.to_thread(template_root_path.exists)
        template_root_is_dir = await asyncio.to_thread(template_root_path.is_dir)

        if template_root_exists and template_root_is_dir:
            inputs_folder = project_path / 'inputs' # Standard inputs folder
            ensure_directory(inputs_folder) # ensure_directory is sync again

            for template_source_filename, template_dest_filename in TEMPLATE_FILES.items(): # TEMPLATE_FILES from constants
                source_path = template_root_path / template_source_filename
                source_path_exists = await asyncio.to_thread(source_path.exists)
                source_path_is_file = await asyncio.to_thread(source_path.is_file)

                if source_path_exists and source_path_is_file:
                    dest_path = inputs_folder / template_dest_filename
                    try:
                        await asyncio.to_thread(shutil.copy2, source_path, dest_path) # shutil.copy2 is blocking
                        copied_templates.append(template_dest_filename)
                        logger.debug(f"Copied template: {source_path} -> {dest_path}")
                    except Exception as e_copy:
                        logger.warning(f"Failed to copy template {source_path} to {dest_path}: {e_copy}")
                else:
                    logger.warning(f"Template source file not found or not a file: {source_path}")
        else:
            logger.warning(f"Template root path not found or not a directory: {template_root_path}")

    project_metadata = {
        'project_name': project_path.name,
        # await asyncio.to_thread(project_path.resolve) if path can be non-existent or complex
        'project_path': str(await asyncio.to_thread(project_path.resolve)), # Store absolute path
        'created_at': datetime.now().isoformat(),
        'last_modified_at': datetime.now().isoformat(),
        'version': '1.0', # Application version or project file format version
        'folders_created': created_folders,
        'templates_copied': copied_templates
    }

    metadata_dir = project_path / 'config' # Standard config folder
    await ensure_directory(metadata_dir) # Added await
    metadata_file_path = metadata_dir / 'project_metadata.json'

    try:
        # Asynchronous file write for json.dump
        def _dump_json():
            with open(metadata_file_path, 'w') as f:
                json.dump(project_metadata, f, indent=4)

        await asyncio.to_thread(_dump_json)
        logger.info(f"Project metadata saved to {metadata_file_path}")
    except Exception as e_meta:
        logger.warning(f"Failed to create project metadata file at {metadata_file_path}: {e_meta}")
        # Decide if this is a critical failure or just a warning

    logger.info(f"Project structure created successfully at {project_path}")
    return {
        'success': True, 'message': 'Project structure created successfully.',
        'created_folders': created_folders, 'copied_templates': copied_templates,
        'metadata_path': str(metadata_file_path)
    }


async def validate_project_structure(project_path: Union[Path, str]) -> Dict[str, Any]:
    """
    Validates if the given project_path adheres to the expected project structure. (Asynchronous version)
    Checks for existence of defined folders and essential template files.

    Args:
        project_path (Union[Path, str]): The path to the project directory.

    Returns:
        Dict[str, Any]: A dictionary containing validation status and details:
            - 'status' (str): 'success', 'warning', or 'error'.
            - 'message' (str): A summary message of the validation.
            - 'valid' (bool): True if the core structure is valid (all main folders exist).
            - 'can_fix' (bool): True if some missing parts (like templates) can potentially be fixed.
            - 'missing_folders' (List[str]): List of expected folders that are missing.
            - 'existing_folders' (List[str]): List of expected folders that were found.
            - 'missing_templates' (List[str]): List of expected template files missing from 'inputs'.
            - 'existing_templates' (List[str]): List of template files found in 'inputs'.
            - 'error' (str, optional): Error message if a critical validation step failed.
    """
    project_path = Path(project_path)
    project_exists = await asyncio.to_thread(project_path.exists)
    if not project_exists:
        return {
            'status': 'error', 'valid': False, 'can_fix': False,
            'message': ERROR_MESSAGES.get('FILE_NOT_FOUND', 'File not found.').replace('file', f'project path "{project_path}"'),
            'missing_folders': list(PROJECT_STRUCTURE.keys()), 'existing_folders': [],
            'missing_templates': list(TEMPLATE_FILES.values()), 'existing_templates': []
        }

    project_is_dir = await asyncio.to_thread(project_path.is_dir)
    if not project_is_dir:
        return {
            'status': 'error', 'valid': False, 'can_fix': False,
            'message': f'The path "{project_path}" is not a directory.',
            'missing_folders': list(PROJECT_STRUCTURE.keys()), 'existing_folders': [],
            'missing_templates': list(TEMPLATE_FILES.values()), 'existing_templates': []
        }

    missing_folders, existing_folders = [], []
    for folder_name, subfolders_dict in PROJECT_STRUCTURE.items():
        folder_path = project_path / folder_name
        folder_exists = await asyncio.to_thread(folder_path.exists)
        folder_is_dir = await asyncio.to_thread(folder_path.is_dir)
        if not (folder_exists and folder_is_dir):
            missing_folders.append(folder_name)
        else:
            existing_folders.append(folder_name)
            if isinstance(subfolders_dict, dict): # Check subfolders
                for subfolder_name in subfolders_dict.keys():
                    subfolder_path = folder_path / subfolder_name
                    subfolder_exists = await asyncio.to_thread(subfolder_path.exists)
                    subfolder_is_dir = await asyncio.to_thread(subfolder_path.is_dir)
                    if not (subfolder_exists and subfolder_is_dir):
                        missing_folders.append(f"{folder_name}/{subfolder_name}")
                    else:
                        existing_folders.append(f"{folder_name}/{subfolder_name}")

    inputs_folder = project_path / 'inputs'
    missing_templates, existing_templates = [], []
    inputs_folder_exists = await asyncio.to_thread(inputs_folder.exists)
    inputs_folder_is_dir = await asyncio.to_thread(inputs_folder.is_dir)

    if inputs_folder_exists and inputs_folder_is_dir:
        for template_dest_name in TEMPLATE_FILES.values():
            template_file_path = inputs_folder / template_dest_name
            template_exists = await asyncio.to_thread(template_file_path.exists)
            if not template_exists:
                missing_templates.append(template_dest_name)
            else:
                existing_templates.append(template_dest_name)
    else: # If inputs folder itself is missing, all templates are missing
        missing_templates.extend(list(TEMPLATE_FILES.values()))


    is_struct_valid = not missing_folders
    is_templ_ok = not missing_templates

    status = 'success'
    message = 'Project structure and templates are valid.'
    can_fix = False

    if not is_struct_valid:
        status = 'error'
        message = f'Project structure is invalid. Missing critical folders: {", ".join(missing_folders)}.'
        can_fix = True # Can attempt to recreate structure
    elif not is_templ_ok: # Structure is valid, but templates might be missing
        status = 'warning'
        message = f'Project structure is valid, but some template files are missing: {", ".join(missing_templates)}.'
        can_fix = True # Can attempt to copy templates

    return {
        'status': status, 'message': message, 'valid': is_struct_valid, 'can_fix': can_fix,
        'missing_folders': missing_folders, 'existing_folders': existing_folders,
        'missing_templates': missing_templates, 'existing_templates': existing_templates
    }

async def copy_missing_templates(project_path: Union[Path, str], missing_templates: List[str], template_root_path: Union[Path, str]) -> Dict[str, Any]:
    """
    Copies specified missing template files from the template_root_path to the (Asynchronous version)
    project's 'inputs' directory.

    Args:
        project_path (Union[Path, str]): Path to the target project.
        missing_templates (List[str]): A list of destination filenames of templates that are missing.
        template_root_path (Union[Path, str]): Path to the directory containing the source template files.

    Returns:
        Dict[str, Any]: A dictionary reporting the outcome:
            - 'success' (bool): True if all attempted copies were successful or no copies needed.
            - 'copied' (List[str]): List of filenames successfully copied.
            - 'failed' (List[str]): List of filenames that failed to copy.
            - 'message' (str): Summary message of the operation.
    """
    project_path = Path(project_path)
    template_root_path = Path(template_root_path)

    if not missing_templates:
        return {'success': True, 'copied': [], 'failed': [], 'message': 'No missing templates specified to copy.'}

    template_root_exists = await asyncio.to_thread(template_root_path.exists)
    template_root_is_dir = await asyncio.to_thread(template_root_path.is_dir)
    if not (template_root_exists and template_root_is_dir):
        return {'success': False, 'copied': [], 'failed': missing_templates, 'message': 'Template source directory not found or is not a directory.'}

    inputs_folder = project_path / 'inputs'
    if not ensure_directory(inputs_folder): # ensure_directory is sync again
        return {'success': False, 'copied': [], 'failed': missing_templates, 'message': f'Failed to ensure inputs directory exists at {inputs_folder}.'}

    copied_list, failed_list = [], []
    # TEMPLATE_FILES maps source filename to destination filename. We need to find the source name.
    source_to_dest_map = {v: k for k, v in TEMPLATE_FILES.items()}

    async def copy_single_template(dest_filename_item: str):
        source_filename_item = source_to_dest_map.get(dest_filename_item)
        if not source_filename_item:
            logger.warning(f"No source mapping found for destination template '{dest_filename_item}'. Skipping.")
            failed_list.append(dest_filename_item)
            return

        source_path_item = template_root_path / source_filename_item
        dest_path_item = inputs_folder / dest_filename_item
        try:
            source_exists = await asyncio.to_thread(source_path_item.exists)
            source_is_file = await asyncio.to_thread(source_path_item.is_file)
            if source_exists and source_is_file:
                await asyncio.to_thread(shutil.copy2, source_path_item, dest_path_item)
                copied_list.append(dest_filename_item)
                logger.info(f"Successfully copied template: {source_path_item} -> {dest_path_item}")
            else:
                logger.warning(f"Template source file not found or not a file: {source_path_item}")
                failed_list.append(dest_filename_item)
        except Exception as e_copy_item:
            logger.error(f"Error copying template {source_filename_item} to {dest_path_item}: {e_copy_item}")
            failed_list.append(dest_filename_item)

    tasks = [copy_single_template(dest_file) for dest_file in missing_templates]
    if tasks:
        await asyncio.gather(*tasks)

    is_operation_success = not failed_list
    message = f"Copied {len(copied_list)} templates."
    if failed_list:
        message += f" Failed to copy {len(failed_list)} templates: {', '.join(failed_list)}."

    return {'success': is_operation_success, 'copied': copied_list, 'failed': failed_list, 'message': message}


def find_special_symbols(df: pd.DataFrame, marker: str) -> List[Tuple[int, int, str]]:
    """
    Finds cells in a DataFrame that start with a specific marker string.

    Args:
        df (pd.DataFrame): The DataFrame to search.
        marker (str): The marker string to look for at the beginning of cell content.

    Returns:
        List[Tuple[int, int, str]]: A list of tuples, where each tuple contains:
            - (int): Row index of the marked cell.
            - (int): Column index (integer position) of the marked cell.
            - (str): The content of the cell after removing the marker prefix and stripping whitespace.
                     Empty string if cell content is just the marker.
    """
    markers_found = []
    try:
        for r_idx, row_series in df.iterrows(): # r_idx is the DataFrame index label
            for c_idx_pos, cell_value in enumerate(row_series.values): # c_idx_pos is integer position
                if isinstance(cell_value, str) and cell_value.startswith(marker):
                    content_after_marker = cell_value[len(marker):].strip()
                    markers_found.append((r_idx, c_idx_pos, content_after_marker))
    except Exception as e:
        logger.error(f"Error finding special symbols ('{marker}') in DataFrame: {e}", exc_info=True)
    return markers_found

def extract_table(df: pd.DataFrame, header_row_idx: int, data_start_col_idx: int) -> pd.DataFrame:
    """
    Extracts a table from a DataFrame. The table is defined by a header row
    and data starting from a specific column in the row immediately below the header.
    The table extends downwards and rightwards until empty cells are encountered
    in the first column of data and in the header row, respectively.

    Args:
        df (pd.DataFrame): The DataFrame containing the table.
        header_row_idx (int): The 0-indexed integer row index where the table's header is located.
        data_start_col_idx (int): The 0-indexed integer column index where the table's data (and header) begins.

    Returns:
        pd.DataFrame: The extracted table with headers set from the specified header_row_idx.
                      Returns an empty DataFrame if extraction fails or table is invalid.
    """
    try:
        if not (0 <= header_row_idx < len(df) and 0 <= data_start_col_idx < len(df.columns)):
            logger.warning(f"Invalid start indices for table extraction: header_row={header_row_idx}, data_col={data_start_col_idx}.")
            return pd.DataFrame()

        data_start_row_idx = header_row_idx + 1
        if data_start_row_idx >= len(df): # No data rows possible
            logger.warning(f"No data rows available below header at row {header_row_idx}.")
            return pd.DataFrame()

        # Determine end_row for data: first row where the data_start_col_idx is null/empty
        end_row_data = data_start_row_idx
        while end_row_data < len(df) and pd.notnull(df.iloc[end_row_data, data_start_col_idx]):
            end_row_data += 1

        # Determine end_col for header/data: first col in header_row_idx where value is null/empty
        end_col_data = data_start_col_idx
        while end_col_data < len(df.columns) and pd.notnull(df.iloc[header_row_idx, end_col_data]):
            end_col_data += 1

        if data_start_row_idx >= end_row_data or data_start_col_idx >= end_col_data:
            logger.warning(f"Table dimensions are invalid or no data found for table starting with header at ({header_row_idx},{data_start_col_idx}).")
            return pd.DataFrame()

        table_headers = df.iloc[header_row_idx, data_start_col_idx:end_col_data].tolist()
        table_body = df.iloc[data_start_row_idx:end_row_data, data_start_col_idx:end_col_data].copy()

        table_body.columns = table_headers
        table_body.reset_index(drop=True, inplace=True)
        return table_body
    except Exception as e:
        logger.error(f"Error extracting table with header at ({header_row_idx},{data_start_col_idx}): {e}", exc_info=True)
        return pd.DataFrame()


def extract_tables_by_markers(df: pd.DataFrame, marker_prefix: str) -> Dict[str, pd.DataFrame]:
    """
    Extracts multiple tables from a DataFrame. Each table is identified by a cell
    starting with `marker_prefix` (e.g., "~TableName"). The content after the
    prefix is used as the table's name. The header for each table is assumed
    to be in the row immediately following the marker cell, starting at the same column as the marker.

    Args:
        df (pd.DataFrame): The DataFrame to search for tables.
        marker_prefix (str): The prefix string that identifies a marker cell (e.g., "~").

    Returns:
        Dict[str, pd.DataFrame]: A dictionary where keys are table names (extracted from markers)
                                 and values are the extracted pandas DataFrames.
    """
    marker_positions = find_special_symbols(df, marker_prefix) # List of (row_idx, col_idx_pos, table_name)
    extracted_tables = {}
    for r_marker_idx, c_marker_idx_pos, table_name in marker_positions:
        if not table_name: # Skip if marker has no name after it
            logger.warning(f"Marker '{marker_prefix}' found at ({r_marker_idx},{c_marker_idx_pos}) but no table name provided. Skipping.")
            continue

        header_row_for_table = r_marker_idx + 1 # Header is one row below the marker
        data_col_for_table = c_marker_idx_pos  # Data starts at the same column as the marker

        logger.info(f"Attempting to extract table '{table_name}' marked at df index {r_marker_idx}, column position {c_marker_idx_pos}. Expecting header at row index {header_row_for_table}.")

        try:
            table_df = extract_table(df, header_row_for_table, data_col_for_table)
            if not table_df.empty:
                extracted_tables[table_name] = table_df
                logger.info(f"Successfully extracted table '{table_name}' with {len(table_df)} rows and {len(table_df.columns)} columns.")
            else:
                logger.warning(f"Extraction for table '{table_name}' (marker at df index {r_marker_idx}, col pos {c_marker_idx_pos}) resulted in an empty DataFrame.")
        except Exception as e_extract: # Catch errors from extract_table
            logger.error(f"Error during extraction of table '{table_name}': {e_extract}", exc_info=True)
            extracted_tables[table_name] = pd.DataFrame() # Store empty DF on error
    return extracted_tables


def interpolate_td_losses_for_range(range_start_year: int, range_end_year: int, points: List[Dict[str, float]]) -> Dict[int, float]:
    """
    Interpolates (and extrapolates) T&D loss percentages for a given range of years.
    Loss percentages are based on a list of known (year, loss_percentage) points.
    Extrapolation uses the first/last known loss percentage for years outside the points' range.

    Args:
        range_start_year (int): The first year of the desired interpolation/extrapolation range.
        range_end_year (int): The last year of the desired range.
        points (List[Dict[str, float]]): A list of dictionaries, each with 'year' (int)
                                         and 'losses' (float, as percentage e.g., 10.0 for 10%) keys.
                                         Points do not need to be pre-sorted.

    Returns:
        Dict[int, float]: A dictionary mapping each year in the target range to its
                          interpolated/extrapolated loss percentage, rounded to 4 decimal places.
                          Returns a dictionary with 0.0 losses if input `points` is empty.
    """
    if not points:
        logger.warning("No T&D loss points provided; defaulting to 0.0 losses for all years in range.")
        return {year: 0.0 for year in range(range_start_year, range_end_year + 1)}

    try:
        # Validate and clean points: ensure 'year' and 'losses' exist and are numeric
        valid_points = []
        for p in points:
            try:
                year = int(p['year'])
                loss = float(p['losses'])
                if 0 <= loss <= 100: # Basic sanity check for percentage
                    valid_points.append({'year': year, 'losses': loss})
                else:
                    logger.warning(f"Invalid loss percentage {loss} for year {year} in T&D points. Skipping point.")
            except (KeyError, ValueError, TypeError) as e_p:
                logger.warning(f"Skipping invalid T&D loss point {p} due to {e_p}")

        if not valid_points:
            logger.warning("No valid T&D loss points after cleaning; defaulting to 0.0 losses.")
            return {year: 0.0 for year in range(range_start_year, range_end_year + 1)}

        sorted_points = sorted(valid_points, key=lambda p_item: p_item['year'])
        point_years = np.array([p_item['year'] for p_item in sorted_points])
        point_losses = np.array([p_item['losses'] for p_item in sorted_points])

        interpolated_losses_map: Dict[int, float] = {}
        for year_to_interpolate in range(range_start_year, range_end_year + 1):
            # np.interp handles extrapolation by using first/last values
            loss_value = np.interp(year_to_interpolate, point_years, point_losses)
            interpolated_losses_map[year_to_interpolate] = round(float(loss_value), 4)

        return interpolated_losses_map
    except Exception as e_interp:
        logger.error(f"Error during T&D loss interpolation: {e_interp}", exc_info=True)
        # Fallback to 0.0 losses for all years in the range on unexpected error
        return {year: 0.0 for year in range(range_start_year, range_end_year + 1)}


async def validate_file_path(file_path_str: str, base_path: Optional[Union[Path, str]] = None) -> Dict[str, Any]:
    """
    Validates a file path for safety and optional inclusion within a base directory. (Asynchronous version)
    This is primarily for paths constructed internally, not for direct user input paths
    which should be handled with extreme care (e.g., never directly used from user input).

    Args:
        file_path_str (str): The file path string to validate.
        base_path (Optional[Union[Path, str]]): If provided, the file path must resolve
                                                 to be within this base directory.

    Returns:
        Dict[str, Any]: A dictionary containing:
            - 'valid' (bool): True if the path is considered safe and valid, False otherwise.
            - 'message' (str): A message indicating the validation status or error.
            - 'resolved_path' (str, optional): The resolved absolute path if valid and base_path is used.
    """
    try:
        if not file_path_str:
            return {'valid': False, 'message': 'File path string is empty.'}

        # Basic path traversal check using os.path.normpath
        # This helps catch simple ".." traversals.
        normalized_path_str = os.path.normpath(file_path_str)
        if ".." in normalized_path_str.split(os.sep) and not base_path: # More risky if no base path defined
             logger.warning(f"Potential path traversal detected in '{file_path_str}' (normalized: '{normalized_path_str}') without a base path.")
             # Allow if base_path is set, as it will be checked against resolved base.

        # If a base_path is provided, ensure the final path is within it.
        if base_path:
            base_path_abs = await asyncio.to_thread(Path(base_path).resolve)

            # Path() constructor is safer for potentially absolute inputs.
            path_obj_file_path_str = Path(file_path_str) # Create Path object once
            is_abs_input = await asyncio.to_thread(path_obj_file_path_str.is_absolute)

            if is_abs_input:
                # If file_path_str is absolute, it must be *equal to or under* base_path_abs
                abs_file_path = await asyncio.to_thread(path_obj_file_path_str.resolve)
                if not str(abs_file_path).startswith(str(base_path_abs)):
                    return {'valid': False, 'message': 'Absolute file path is outside the allowed base directory.'}
            else:
                # If relative, join with base_path and resolve
                abs_file_path = await asyncio.to_thread((base_path_abs / path_obj_file_path_str).resolve)
                # Check if abs_file_path is truly under base_path_abs
                # This is a common way to check for path traversal after resolving.
                # Note: .parents is synchronous, but operates on already resolved Path objects.
                if base_path_abs != abs_file_path and base_path_abs not in abs_file_path.parents:
                    return {'valid': False, 'message': 'File path resolves outside the allowed base directory (path traversal attempt).'}

            return {'valid': True, 'message': 'File path is valid and within the base directory.', 'resolved_path': str(abs_file_path)}
        else:
            # No base path, just attempt to resolve. This doesn't make it "safe" from accessing
            # arbitrary system files if the input `file_path_str` is user-controlled.
            # This validation is more about path well-formedness in this case.
            await asyncio.to_thread(Path(file_path_str).resolve) # Will raise error if path is malformed for OS
            return {'valid': True, 'message': 'File path format appears valid (no base path check).'}

    except Exception as e_path:
        logger.error(f"Error validating file path '{file_path_str}': {e_path}", exc_info=True)
        return {'valid': False, 'message': f'Path validation error: {str(e_path)}'}


async def get_file_info(file_path: Union[Path, str]) -> Dict[str, Any]:
    """
    Retrieves comprehensive information about a file or directory. (Asynchronous version)

    Args:
        file_path (Union[Path, str]): The path to the file or directory.

    Returns:
        Dict[str, Any]: A dictionary containing file information:
            - 'exists' (bool): True if the path exists.
            - 'path' (str): The string representation of the input path.
            - 'name' (str, optional): Filename or directory name.
            - 'size_bytes' (int, optional): Size in bytes.
            - 'size_mb' (float, optional): Size in megabytes, rounded to 2 decimal places.
            - 'created_iso' (str, optional): ISO formatted creation timestamp.
            - 'modified_iso' (str, optional): ISO formatted modification timestamp.
            - 'is_file' (bool, optional): True if it's a file.
            - 'is_directory' (bool, optional): True if it's a directory.
            - 'extension' (str, optional): File extension (lowercase, including dot).
            - 'message' (str, optional): Message if path does not exist.
            - 'error' (str, optional): Error message if an exception occurred.
    """
    file_path_obj = Path(file_path)
    import asyncio # Required for asyncio.to_thread
    try:
        exists = await asyncio.to_thread(file_path_obj.exists)
        if not exists:
            return {'exists': False, 'path': str(file_path_obj), 'message': 'Path does not exist.'}

        stat_info = await asyncio.to_thread(file_path_obj.stat)
        is_file = await asyncio.to_thread(file_path_obj.is_file)
        is_directory = await asyncio.to_thread(file_path_obj.is_dir)

        return {
            'exists': True,
            'path': str(file_path_obj),
            'name': file_path_obj.name,
            'size_bytes': stat_info.st_size,
            'size_mb': round(stat_info.st_size / (1024 * 1024), 2),
            'created_iso': datetime.fromtimestamp(stat_info.st_ctime).isoformat(),
            'modified_iso': datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
            'is_file': is_file,
            'is_directory': is_directory,
            'extension': file_path_obj.suffix.lower() if is_file else None
        }
    except Exception as e_info:
        logger.error(f"Error getting file info for {file_path_obj}: {e_info}", exc_info=True)
        return {'exists': False, 'path': str(file_path_obj), 'error': str(e_info)}


async def cleanup_old_files(directory: Union[Path, str], max_age_days: int = 30, file_patterns: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Cleans up old files in a specified directory based on their modification time. (Asynchronous version)

    Args:
        directory (Union[Path, str]): The directory to clean.
        max_age_days (int): Maximum age of files (in days) to keep. Files older than this will be deleted.
        file_patterns (Optional[List[str]]): A list of glob patterns (e.g., ['*.log', '*.tmp'])
                                             to match files for cleanup. If None, all files are considered.

    Returns:
        Dict[str, Any]: A dictionary summarizing the cleanup operation:
            - 'success' (bool): True if the operation completed (even if no files were deleted).
            - 'cleaned_files' (List[str]): List of filenames that were successfully deleted.
            - 'failed_to_delete' (List[Dict[str, str]]): List of files that could not be deleted, with error messages.
            - 'message' (str): A summary message of the cleanup.
            - 'error' (str, optional): General error message if the operation failed catastrophically.
    """
    directory_path = Path(directory)
    if not (directory_path.exists() and directory_path.is_dir()):
        return {'success': False, 'cleaned_files': [], 'failed_to_delete': [], 'message': 'Directory does not exist or is not a directory.'}

    import time # Local import for this function
    import asyncio # For asyncio.to_thread

    cutoff_timestamp = time.time() - (max_age_days * 24 * 60 * 60)
    cleaned_files_list, failed_files_list = [], []

    glob_patterns_to_check = file_patterns if file_patterns else ["*"]

    # Helper function to process a single file path asynchronously
    async def process_file(item_path_to_check: Path):
        try:
            # Run synchronous stat() in a thread
            stat_info = await asyncio.to_thread(item_path_to_check.stat)
            if stat_info.st_mtime < cutoff_timestamp:
                # Run synchronous unlink() in a thread
                await asyncio.to_thread(item_path_to_check.unlink)
                cleaned_files_list.append(item_path_to_check.name)
                logger.info(f"Cleaned up old file: {item_path_to_check}")
        except Exception as e_clean:
            failed_files_list.append({'file': item_path_to_check.name, 'error': str(e_clean)})
            logger.error(f"Failed to clean up file {item_path_to_check.name}: {e_clean}")

    # Collect all file processing tasks
    tasks = []
    for pattern in glob_patterns_to_check:
        # directory_path.glob() is an iterator, convert to list for async processing
        # or wrap the glob iteration itself if it's very large.
        # For simplicity, let's assume the number of files per pattern isn't astronomically large
        # such that converting glob result to list becomes a memory issue itself.
        # If it is, a more complex async generator approach for glob would be needed.
        try:
            items_to_check = await asyncio.to_thread(list, directory_path.glob(pattern))
            for item_path in items_to_check:
                is_file = await asyncio.to_thread(item_path.is_file)
                if is_file:
                    tasks.append(process_file(item_path))
        except Exception as e_glob:
            logger.error(f"Error during globbing pattern {pattern} in {directory_path}: {e_glob}")
            # Potentially add to failed_files_list or handle as a broader error

    if tasks:
        await asyncio.gather(*tasks)

    return {
        'success': True, # Operation itself completed
        'cleaned_files': cleaned_files_list,
        'failed_to_delete': failed_files_list,
        'message': f'Cleanup process completed. Cleaned {len(cleaned_files_list)} files. Failed to delete {len(failed_files_list)} files.'
    }


def validate_data_types(data_dict: Dict[str, Any], schema: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validates data types and presence of required fields in a dictionary against a schema.
    Attempts type conversion for basic types (int, float, str, bool).

    Args:
        data_dict (Dict[str, Any]): The dictionary containing data to validate.
        schema (Dict[str, Dict[str, Any]]): A schema dictionary where keys are field names.
            Each field's value is a dictionary specifying requirements like:
            - 'type' (type): Expected Python type (e.g., int, float, str, bool, list, dict).
            - 'required' (bool): True if the field is mandatory.
            - 'min_value' (numeric): Minimum allowed value for numeric types.
            - 'max_value' (numeric): Maximum allowed value for numeric types.
            - 'choices' (List): List of allowed values.
            - 'min_length' (int): Minimum length for strings or lists.
            - 'max_length' (int): Maximum length for strings or lists.

    Returns:
        Dict[str, Any]: A dictionary containing:
            - 'is_valid' (bool): True if all validations pass, False otherwise.
            - 'errors' (List[str]): List of validation error messages.
            - 'warnings' (List[str]): List of non-critical validation warnings.
            - 'validated_data' (Dict[str, Any]): The input data, potentially with type conversions applied.
                                                 This might differ from input `data_dict` if conversions occurred.
    """
    validation_errors: List[str] = []
    validation_warnings: List[str] = [] # Currently not used, but good for future
    processed_data = data_dict.copy() # Work on a copy to store converted values

    try:
        for field_name, rules in schema.items():
            is_field_required = rules.get('required', False)
            current_value = data_dict.get(field_name) # Original value

            if field_name not in data_dict:
                if is_field_required:
                    validation_errors.append(f"Required field '{field_name}' is missing.")
                continue # Skip further checks for this missing field

            expected_py_type = rules.get('type')
            if expected_py_type:
                if not isinstance(current_value, expected_py_type):
                    # Attempt type conversion
                    try:
                        if expected_py_type == int:
                            processed_data[field_name] = int(float(current_value)) # float first for "1.0"
                        elif expected_py_type == float:
                            processed_data[field_name] = float(current_value)
                        elif expected_py_type == str:
                            processed_data[field_name] = str(current_value)
                        elif expected_py_type == bool:
                            if isinstance(current_value, str):
                                if current_value.lower() in ['true', '1', 'yes', 'on']: processed_data[field_name] = True
                                elif current_value.lower() in ['false', '0', 'no', 'off']: processed_data[field_name] = False
                                else: validation_errors.append(f"Field '{field_name}' ('{current_value}') is not a valid boolean string.")
                            else: # Try direct bool conversion
                                processed_data[field_name] = bool(current_value)
                        # For list/dict, usually we check type but don't convert complex structures this simply.
                        # If specific list/dict content validation is needed, schema should be more detailed.
                        elif expected_py_type in [list, dict] and not isinstance(current_value, expected_py_type):
                             validation_errors.append(f"Field '{field_name}' has type {type(current_value).__name__}, expected {expected_py_type.__name__}. Automatic conversion not attempted for complex types.")

                        # Check if conversion was successful for simple types
                        if field_name in processed_data and not isinstance(processed_data[field_name], expected_py_type) and expected_py_type not in [list, dict]:
                             validation_errors.append(f"Field '{field_name}' ('{current_value}') could not be reliably converted to {expected_py_type.__name__}.")

                    except (ValueError, TypeError) as e_conv:
                        validation_errors.append(f"Field '{field_name}' ('{current_value}') could not be converted to {expected_py_type.__name__}: {e_conv}")

            # Use the (potentially converted) value from processed_data for constraint checks
            value_for_constraints = processed_data.get(field_name)
            if value_for_constraints is not None: # Only if value exists and is not None
                if 'min_value' in rules and isinstance(value_for_constraints, (int, float)) and value_for_constraints < rules['min_value']:
                    validation_errors.append(f"Field '{field_name}' value {value_for_constraints} is below minimum {rules['min_value']}.")
                if 'max_value' in rules and isinstance(value_for_constraints, (int, float)) and value_for_constraints > rules['max_value']:
                    validation_errors.append(f"Field '{field_name}' value {value_for_constraints} is above maximum {rules['max_value']}.")
                if 'choices' in rules and value_for_constraints not in rules['choices']:
                    validation_errors.append(f"Field '{field_name}' value '{value_for_constraints}' not in allowed choices: {rules['choices']}.")
                if 'min_length' in rules and hasattr(value_for_constraints, '__len__') and len(value_for_constraints) < rules['min_length']:
                     validation_errors.append(f"Field '{field_name}' length is below minimum {rules['min_length']}.")
                if 'max_length' in rules and hasattr(value_for_constraints, '__len__') and len(value_for_constraints) > rules['max_length']:
                     validation_errors.append(f"Field '{field_name}' length is above maximum {rules['max_length']}.")

        return {'is_valid': not validation_errors, 'errors': validation_errors, 'warnings': validation_warnings, 'validated_data': processed_data}

    except Exception as e_validate:
        logger.exception(f"Critical error during data type validation: {e_validate}")
        return {'is_valid': False, 'errors': [f"Internal validation error: {str(e_validate)}"], 'warnings': [], 'validated_data': data_dict}

print("Defining helper functions... (merged from old_helpers.py and adapted for FastAPI)")
