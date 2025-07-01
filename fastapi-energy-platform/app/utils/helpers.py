# utils/helpers.py
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
from fastapi import UploadFile
# from werkzeug.utils import secure_filename # secure_filename is good, but FastAPI handles this differently.
                                         # For file uploads, FastAPI's UploadFile.filename is usually safe.
                                         # If storing with original names, ensure proper sanitization.

# Assuming constants are now in fastapi-energy-platform/app/utils/constants.py
# Adjust imports as necessary if constants are moved or restructured.
from app.utils.constants import (
    PROJECT_STRUCTURE, TEMPLATE_FILES, ERROR_MESSAGES,
    VALIDATION_RULES, DEFAULT_PATHS # Review DEFAULT_PATHS for FastAPI context
)

logger = logging.getLogger(__name__)

def slugify(text: str) -> str:
    """
    Convert text to a safe slug for use in IDs and filenames.
    """
    import re
    from unicodedata import normalize

    text = str(text).lower().strip()
    text = normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text

def safe_filename(filename: str) -> str:
    """
    Creates a safe filename.
    FastAPI's UploadFile.filename is generally safe as it doesn't include path components.
    This function can be used for additional sanitization if needed, or if constructing filenames manually.
    """
    if not filename:
        return ""
    # Basic sanitization: remove path components and limit character set.
    # Consider a more robust library if complex sanitization is needed.
    name = Path(filename).name # Removes directory paths
    name = "".join(c if c.isalnum() or c in ('.', '-', '_') else '_' for c in name)
    return name


def ensure_directory(path: Path | str) -> bool:
    """Ensure directory exists, create if it doesn't"""
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Failed to create directory {path}: {e}")
        return False

def create_project_structure(project_path: Path | str, template_root_path: Path | str | None = None):
    """
    Create the standard project folder structure.
    Paths should be Path objects or absolute strings for clarity.

    Args:
        project_path: The root path where the project structure will be created.
        template_root_path: Absolute path to the root of template files.
                            If None, template copying is skipped.
    Returns:
        dict: Result with success status and details.
    """
    project_path = Path(project_path)
    logger.info(f"Creating project structure at: {project_path}")

    if not ensure_directory(project_path):
        return {
            'success': False,
            'message': f'Failed to create project directory: {project_path}'
        }

    created_folders = []
    for folder_name, subfolders_dict in PROJECT_STRUCTURE.items():
        folder_path = project_path / folder_name
        if ensure_directory(folder_path):
            created_folders.append(folder_name)
            if isinstance(subfolders_dict, dict):
                for subfolder_name in subfolders_dict.keys():
                    subfolder_path = folder_path / subfolder_name
                    if ensure_directory(subfolder_path):
                        created_folders.append(f"{folder_name}/{subfolder_name}")

    copied_templates = []
    if template_root_path:
        template_root_path = Path(template_root_path)
        if template_root_path.exists() and template_root_path.is_dir():
            inputs_folder = project_path / 'inputs' # Assuming 'inputs' is a key in PROJECT_STRUCTURE
            ensure_directory(inputs_folder)

            for template_key, dest_filename in TEMPLATE_FILES.items():
                # Assuming template_key is the actual filename in template_root_path
                source_path = template_root_path / template_key
                if source_path.exists() and source_path.is_file():
                    dest_path = inputs_folder / dest_filename
                    try:
                        shutil.copy2(source_path, dest_path)
                        copied_templates.append(dest_filename)
                        logger.debug(f"Copied template: {source_path} -> {dest_path}")
                    except Exception as e:
                        logger.warning(f"Failed to copy template {source_path}: {e}")
                else:
                    logger.warning(f"Template file not found: {source_path}")
        else:
            logger.warning(f"Template root path not found or not a directory: {template_root_path}")


    metadata = {
        'name': project_path.name,
        'created': datetime.now().isoformat(),
        'last_modified': datetime.now().isoformat(),
        'version': '1.0', # Consider making this configurable
        'structure_created': created_folders,
        'templates_copied': copied_templates
    }

    metadata_path = project_path / 'config' / 'project.json' # Assuming 'config' in PROJECT_STRUCTURE
    ensure_directory(metadata_path.parent)
    try:
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to create project metadata at {metadata_path}: {e}")

    logger.info(f"Project structure created successfully at {project_path}")
    return {
        'success': True,
        'message': 'Project structure created successfully',
        'created_folders': created_folders,
        'copied_templates': copied_templates,
        'metadata_path': str(metadata_path)
    }


def validate_project_structure(project_path: Path | str):
    """
    Validate project structure and return detailed status.
    Paths should be Path objects or absolute strings.
    """
    project_path = Path(project_path)
    if not project_path.exists():
        return {
            'status': 'error',
            'message': ERROR_MESSAGES['FILE_NOT_FOUND'].replace('file', f'path "{project_path}"'),
            'valid': False
        }
    if not project_path.is_dir():
        return {
            'status': 'error',
            'message': f'The path "{project_path}" is not a directory',
            'valid': False
        }

    missing_folders, existing_folders = [], []
    for folder_name, subfolders_dict in PROJECT_STRUCTURE.items():
        folder_path = project_path / folder_name
        if not (folder_path.exists() and folder_path.is_dir()):
            missing_folders.append(folder_name)
        else:
            existing_folders.append(folder_name)
            if isinstance(subfolders_dict, dict):
                for subfolder_name in subfolders_dict.keys():
                    subfolder_path = folder_path / subfolder_name
                    if not (subfolder_path.exists() and subfolder_path.is_dir()):
                        missing_folders.append(f"{folder_name}/{subfolder_name}")
                    else:
                        existing_folders.append(f"{folder_name}/{subfolder_name}")

    inputs_folder = project_path / 'inputs'
    missing_templates, existing_templates = [], []
    if inputs_folder.exists() and inputs_folder.is_dir():
        for template_dest_name in TEMPLATE_FILES.values():
            template_path = inputs_folder / template_dest_name
            if not template_path.exists():
                missing_templates.append(template_dest_name)
            else:
                existing_templates.append(template_dest_name)

    valid = not missing_folders
    status = 'success' if valid and not missing_templates else 'warning'
    if not valid: status = 'error'

    message = 'Valid project structure detected'
    if status == 'error': message = f'Invalid project structure: Missing folders: {", ".join(missing_folders)}'
    elif status == 'warning' and missing_templates : message = f'Template files missing: {", ".join(missing_templates)}'
    elif status == 'warning' and missing_folders: message = f'Project structure incomplete: Missing folders: {", ".join(missing_folders)}'


    return {
        'status': status,
        'message': message,
        'valid': valid,
        'can_fix': status != 'success', # Simplification, actual fix capability depends
        'missing_folders': missing_folders,
        'existing_folders': existing_folders,
        'missing_templates': missing_templates,
        'existing_templates': existing_templates
    }

def copy_missing_templates(project_path: Path | str, missing_templates: list, template_root_path: Path | str):
    """Copy missing template files to the project."""
    project_path = Path(project_path)
    template_root_path = Path(template_root_path)

    if not missing_templates:
        return {'success': True, 'copied': [], 'message': 'No templates to copy'}
    if not (template_root_path.exists() and template_root_path.is_dir()):
        return {'success': False, 'message': 'Template root folder not found or not specified', 'copied': []}

    inputs_folder = project_path / 'inputs'
    if not ensure_directory(inputs_folder):
        return {'success': False, 'message': 'Failed to create inputs folder', 'copied': []}

    copied_list, failed_list = [], []
    template_source_map = {v: k for k, v in TEMPLATE_FILES.items()} # dest_filename -> source_filename

    for dest_filename in missing_templates:
        source_filename = template_source_map.get(dest_filename, dest_filename) # Fallback to dest if not in map
        source_path = template_root_path / source_filename
        dest_path = inputs_folder / dest_filename
        try:
            if source_path.exists() and source_path.is_file():
                shutil.copy2(source_path, dest_path)
                copied_list.append(dest_filename)
                logger.info(f"Copied template: {source_path} -> {dest_path}")
            else:
                failed_list.append(dest_filename)
                logger.warning(f"Template source not found: {source_path}")
        except Exception as e:
            failed_list.append(dest_filename)
            logger.error(f"Error copying template {dest_filename} from {source_path}: {e}")

    success = not failed_list
    message = f"Copied {len(copied_list)} templates"
    if failed_list: message += f", failed to copy {len(failed_list)}: {', '.join(failed_list)}"
    return {'success': success, 'copied': copied_list, 'failed': failed_list, 'message': message}


def find_special_symbols(df: pd.DataFrame, marker: str) -> list:
    """Find cells with special marker symbols in DataFrame"""
    markers = []
    try:
        for i, row in df.iterrows():
            for j, value in enumerate(row): # Use enumerate for column index
                if isinstance(value, str) and value.startswith(marker):
                    # Store original row/col index (i, df.columns[j]) if df has headers,
                    # or (i,j) if using default integer column indexing
                    markers.append((i, j, value[len(marker):].strip()))
    except Exception as e:
        logger.error(f"Error finding special symbols ('{marker}'): {e}")
    return markers

def extract_table(df: pd.DataFrame, start_row: int, start_col: int) -> pd.DataFrame:
    """Extract table from DataFrame starting at specified position (0-indexed)."""
    try:
        # Determine end_row: find first row where the start_col is null after start_row
        end_row = start_row + 1 # Header is at start_row, data starts at start_row + 1
        while end_row < len(df) and pd.notnull(df.iloc[end_row, start_col]):
            end_row += 1

        # Determine end_col: find first col where the start_row (header row) is null after start_col
        end_col = start_col + 1
        while end_col < len(df.columns) and pd.notnull(df.iloc[start_row, end_col]):
            end_col += 1

        # Select the table data, excluding the original header row for data part
        table_data = df.iloc[start_row + 1 : end_row, start_col : end_col].copy()
        # Select the header
        header = df.iloc[start_row, start_col : end_col].tolist()

        table_data.columns = header
        table_data.reset_index(drop=True, inplace=True)
        return table_data
    except Exception as e:
        logger.error(f"Error extracting table from ({start_row},{start_col}): {e}")
        return pd.DataFrame()


def extract_tables_by_markers(df: pd.DataFrame, marker: str) -> dict:
    """Extract multiple tables from DataFrame using marker symbols."""
    marker_positions = find_special_symbols(df, marker)
    tables = {}
    for r_idx, c_idx, table_name in marker_positions:
        try:
            # The marker is at (r_idx, c_idx). The actual table header starts below it.
            tables[table_name] = extract_table(df, r_idx + 1, c_idx)
        except Exception as e:
            logger.error(f"Error extracting table '{table_name}' marked at ({r_idx},{c_idx}): {e}")
            tables[table_name] = pd.DataFrame()
    return tables


def interpolate_td_losses_for_range(range_start_year: int, range_end_year: int, points: list[dict]) -> dict:
    """
    Interpolates T&D losses for a given range of years based on specified points.
    Points: [{'year': YYYY, 'losses': X.X}, ...]
    """
    if not points:
        return {year: 0.0 for year in range(range_start_year, range_end_year + 1)}

    try:
        sorted_points = sorted(points, key=lambda p: p['year'])
        point_years = np.array([p['year'] for p in sorted_points])
        point_losses = np.array([p['losses'] for p in sorted_points])

        interpolated_losses = {}
        for year_to_interpolate in range(range_start_year, range_end_year + 1):
            if year_to_interpolate < sorted_points[0]['year']:
                loss_value = sorted_points[0]['losses']
            elif year_to_interpolate > sorted_points[-1]['year']:
                loss_value = sorted_points[-1]['losses']
            else:
                loss_value = np.interp(year_to_interpolate, point_years, point_losses)
            interpolated_losses[year_to_interpolate] = round(float(loss_value), 4)
        return interpolated_losses
    except Exception as e:
        logger.error(f"Error interpolating T&D losses: {e}")
        return {year: 0.0 for year in range(range_start_year, range_end_year + 1)}


def validate_file_path(file_path: str, base_path: Path | str | None = None) -> dict :
    """
    Validate that a file path is safe and optionally within an allowed base directory.
    For FastAPI, file uploads are handled as UploadFile objects, reducing some risks.
    This is more for internally constructed paths.
    """
    try:
        if not file_path:
            return {'valid': False, 'message': 'File path is empty'}

        # Path traversal check (basic)
        normalized_path = os.path.normpath(file_path)
        if ".." in normalized_path.split(os.sep):
             return {'valid': False, 'message': 'Path traversal attempt detected'}


        # Ensure path is relative if base_path is not None
        if base_path and os.path.isabs(file_path):
             return {'valid': False, 'message': 'File path must be relative if base_path is specified.'}


        if base_path:
            base_path = Path(base_path).resolve() # Ensure base_path is absolute and resolved
            # If file_path is already absolute, this check is different.
            # Assuming file_path is relative to base_path for this logic.
            abs_file_path = (base_path / file_path).resolve()
            if base_path not in abs_file_path.parents and base_path != abs_file_path:
                 # This check needs to be robust. A common way:
                 # if os.path.commonprefix([abs_file_path, base_path]) != str(base_path):
                 # A simpler check if we are sure base_path is a prefix of abs_file_path
                if not str(abs_file_path).startswith(str(base_path)):
                    return {'valid': False, 'message': 'File path outside allowed base directory'}
        else:
            # If no base_path, resolve the file_path itself.
            # Depending on context, you might want to restrict to a known root if no base_path.
            Path(file_path).resolve()


        return {'valid': True, 'message': 'Valid file path'}
    except Exception as e: # Catch more specific exceptions if possible
        logger.error(f"Error validating file path '{file_path}': {e}")
        return {'valid': False, 'message': f'Error validating path: {str(e)}'}


def get_file_info(file_path: Path | str) -> dict:
    """Get comprehensive information about a file."""
    file_path = Path(file_path)
    try:
        if not file_path.exists():
            return {'exists': False, 'path': str(file_path), 'message': 'File does not exist'}

        stat = file_path.stat()
        return {
            'exists': True,
            'path': str(file_path),
            'name': file_path.name,
            'size_bytes': stat.st_size,
            'size_mb': round(stat.st_size / (1024 * 1024), 2),
            'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'is_file': file_path.is_file(),
            'is_directory': file_path.is_dir(),
            'extension': file_path.suffix.lower()
        }
    except Exception as e:
        logger.error(f"Error getting file info for {file_path}: {e}")
        return {'exists': False, 'path': str(file_path), 'error': str(e)}


def cleanup_old_files(directory: Path | str, max_age_days: int = 30, file_patterns: list[str] | None = None):
    """
    Clean up old files in a directory.
    `file_patterns` are simple string suffixes (e.g., ['.log', '.tmp']).
    """
    directory = Path(directory)
    if not directory.exists() or not directory.is_dir():
        return {'success': False, 'message': 'Directory does not exist or is not a directory'}

    import time
    cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
    cleaned_files, failed_files = [], []

    for item in directory.iterdir():
        if not item.is_file():
            continue
        if file_patterns and not any(item.name.endswith(pattern) for pattern in file_patterns):
            continue
        try:
            if item.stat().st_mtime < cutoff_time:
                item.unlink() # Remove file
                cleaned_files.append(item.name)
        except Exception as e:
            failed_files.append({'file': item.name, 'error': str(e)})
            logger.error(f"Failed to clean up {item.name}: {e}")

    return {
        'success': True,
        'cleaned_files': cleaned_files,
        'failed_files': failed_files,
        'message': f'Cleaned {len(cleaned_files)} files. Failed to clean {len(failed_files)} files.'
    }


def validate_data_types(data: dict, schema: dict) -> dict:
    """
    Validate data against a schema.
    Schema example: {'field_name': {'type': int, 'required': True, 'min_value': 0}}
    """
    errors, warnings = [], []
    validated_data = data.copy() # To store type-converted values

    try:
        for field, requirements in schema.items():
            is_required = requirements.get('required', False)
            field_value = data.get(field)

            if field not in data:
                if is_required:
                    errors.append(f"Required field '{field}' is missing")
                continue

            expected_type = requirements.get('type')
            if expected_type:
                current_type = type(field_value)
                if not isinstance(field_value, expected_type):
                    try:
                        # Attempt type conversion for common types
                        if expected_type == int and isinstance(field_value, (float, str)):
                            validated_data[field] = int(float(field_value))
                        elif expected_type == float and isinstance(field_value, (int, str)):
                            validated_data[field] = float(field_value)
                        elif expected_type == str and not isinstance(field_value, str):
                             validated_data[field] = str(field_value)
                        # Add more conversions if necessary (bool, datetime, etc.)
                        elif expected_type == bool and isinstance(field_value, str):
                            if field_value.lower() in ['true', '1', 'yes']: validated_data[field] = True
                            elif field_value.lower() in ['false', '0', 'no']: validated_data[field] = False
                            else: errors.append(f"Field '{field}' ('{field_value}') could not be converted to boolean.")
                        elif expected_type == bool and isinstance(field_value, int):
                            validated_data[field] = bool(field_value)

                        else: # If no specific conversion or it failed at isinstance
                            if not isinstance(validated_data[field], expected_type): # Check again after potential conversion
                                errors.append(f"Field '{field}' has type {current_type.__name__}, expected {expected_type.__name__}")
                    except (ValueError, TypeError) as e:
                        errors.append(f"Field '{field}' ('{field_value}') could not be converted to {expected_type.__name__}: {e}")

            # Check constraints on the (potentially type-converted) value
            value_to_check = validated_data.get(field) # Use value from validated_data
            if value_to_check is not None: # Only check constraints if value exists
                if 'min_value' in requirements and value_to_check < requirements['min_value']:
                    errors.append(f"Field '{field}' value {value_to_check} is below minimum {requirements['min_value']}")
                if 'max_value' in requirements and value_to_check > requirements['max_value']:
                    errors.append(f"Field '{field}' value {value_to_check} is above maximum {requirements['max_value']}")
                if 'choices' in requirements and value_to_check not in requirements['choices']:
                    errors.append(f"Field '{field}' value '{value_to_check}' not in allowed choices: {requirements['choices']}")
                if 'min_length' in requirements and hasattr(value_to_check, '__len__') and len(value_to_check) < requirements['min_length']:
                     errors.append(f"Field '{field}' length is below minimum {requirements['min_length']}")
                if 'max_length' in requirements and hasattr(value_to_check, '__len__') and len(value_to_check) > requirements['max_length']:
                     errors.append(f"Field '{field}' length is above maximum {requirements['max_length']}")


        return {'valid': not errors, 'errors': errors, 'warnings': warnings, 'data': validated_data}
    except Exception as e:
        logger.exception(f"Error during data validation: {e}")
        return {'valid': False, 'errors': [f"Validation error: {str(e)}"], 'warnings': warnings, 'data': data}

print("Defining helper functions... (merged from old_helpers.py and adapted for FastAPI)")
