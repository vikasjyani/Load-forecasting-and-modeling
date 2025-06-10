import numpy as np
from flask import current_app # Added current_app

def get_interpolated_td_loss(target_year, td_loss_config_list):
    """
    Calculates the T&D loss for a target year using linear interpolation
    based on a list of configured year-loss_percentage pairs.

    Args:
        target_year (int): The year for which to calculate the T&D loss.
        td_loss_config_list (list): A list of dictionaries, where each dictionary
                                   has 'year' (int) and 'loss_pct' (float, e.g., 5.0 for 5%).
                                   Example: [{'year': 2020, 'loss_pct': 5.0}, {'year': 2030, 'loss_pct': 4.0}]

    Returns:
        float: The interpolated T&D loss as a decimal (e.g., 0.05 for 5%),
               or 0.0 if no configuration is provided or if other errors occur.
               Uses constant extrapolation if target_year is outside the configured range.
    """
    logger = current_app.logger # Get logger instance

    # Validate target_year
    if not isinstance(target_year, (int, float, np.integer, np.floating)): # Added numpy types for safety
        logger.warning(f"T&D Loss Calc: Invalid target_year type: {type(target_year)}. Expected numeric. Returning 0.0 loss.")
        return 0.0

    # Validate td_loss_config_list structure
    if not isinstance(td_loss_config_list, list):
        logger.warning(f"T&D Loss Calc: Configuration is not a list. Target year: {target_year}. Returning 0.0 loss.")
        return 0.0

    if not td_loss_config_list:
        logger.info(f"T&D Loss Calc: Configuration is empty for target year {target_year}. Returning 0.0 loss.")
        return 0.0

    valid_config_points = []
    for i, item in enumerate(td_loss_config_list):
        if not isinstance(item, dict):
            logger.warning(f"T&D Loss Calc: Item {i} in config is not a dictionary. Target year: {target_year}. Skipping: {item}")
            continue
        if 'year' not in item or 'loss_pct' not in item:
            logger.warning(f"T&D Loss Calc: Item {i} in config missing 'year' or 'loss_pct'. Target year: {target_year}. Skipping: {item}")
            continue
        try:
            year = int(item['year'])
            loss_pct_val = float(item['loss_pct'])
            # Basic range check for loss_pct, year range handled by interpolation/extrapolation logic
            if not (0.0 <= loss_pct_val <= 100.0):
                 logger.warning(f"T&D Loss Calc: Item {i} loss_pct {loss_pct_val}% is outside typical range 0-100%. Using it as is. Item: {item}")

            valid_config_points.append({'year': year, 'loss_pct_decimal': loss_pct_val / 100.0}) # Store as decimal
        except (ValueError, TypeError) as e:
            logger.warning(f"T&D Loss Calc: Invalid data types in config item {item} for target year {target_year}. Error: {e}. Skipping.")
            continue

    if not valid_config_points:
        logger.warning(f"T&D Loss Calc: No valid data points in configuration after validation for target year {target_year}. Returning 0.0 loss.")
        return 0.0

    # Sort the validated configuration by year
    sorted_config = sorted(valid_config_points, key=lambda x: x['year'])

    years = np.array([item['year'] for item in sorted_config])
    loss_decimals = np.array([item['loss_pct_decimal'] for item in sorted_config])

    try:
        # Handle cases with single data point for constant extrapolation
        if len(years) == 1:
            interpolated_loss_decimal = loss_decimals[0]
            logger.debug(f"T&D Loss Calc: Target year {target_year}. Single point config ({years[0]}: {interpolated_loss_decimal:.4f}). Using constant loss.")
            return interpolated_loss_decimal

        # np.interp handles extrapolation by default (repeats end values)
        interpolated_loss_decimal = np.interp(target_year, years, loss_decimals)

        if target_year < years[0]:
            logger.debug(f"T&D Loss Calc: Target year {target_year} is before first config year {years[0]}. Extrapolating with loss {interpolated_loss_decimal:.4f} (value from year {years[0]}).")
        elif target_year > years[-1]:
            logger.debug(f"T&D Loss Calc: Target year {target_year} is after last config year {years[-1]}. Extrapolating with loss {interpolated_loss_decimal:.4f} (value from year {years[-1]}).")
        else:
            logger.debug(f"T&D Loss Calc: Target year {target_year}. Interpolated loss {interpol_loss_decimal:.4f}.")

    except IndexError:
        # This should ideally be prevented by checks for empty valid_config_points and len(years)==1
        logger.error(f"T&D Loss Calc: IndexError during interpolation for target year {target_year} (empty years/losses array after validation, which should not happen). Returning 0.0 loss.", exc_info=True)
        return 0.0
    except Exception as e:
        logger.error(f"T&D Loss Calc: Unexpected error during numpy interpolation for target year {target_year}: {e}", exc_info=True)
        return 0.0 # Default to 0 on unexpected error

    return interpolated_loss_decimal


if __name__ == '__main__':
    # Example Usage:
    config1 = [{'year': 2020, 'loss_pct': 5.0}, {'year': 2030, 'loss_pct': 4.0}]
    print(f"Config1, Year 2020: {get_interpolated_td_loss(2020, config1)}") # Expected: 0.05
    print(f"Config1, Year 2025: {get_interpolated_td_loss(2025, config1)}") # Expected: 0.045
    print(f"Config1, Year 2030: {get_interpolated_td_loss(2030, config1)}") # Expected: 0.04
    print(f"Config1, Year 2015 (extrapolation): {get_interpolated_td_loss(2015, config1)}") # Expected: 0.05
    print(f"Config1, Year 2035 (extrapolation): {get_interpolated_td_loss(2035, config1)}") # Expected: 0.04

    config2 = [{'year': 2022, 'loss_pct': 6.0}]
    print(f"Config2, Year 2020 (extrapolation): {get_interpolated_td_loss(2020, config2)}") # Expected: 0.06
    print(f"Config2, Year 2025 (extrapolation): {get_interpolated_td_loss(2025, config2)}") # Expected: 0.06

    config_unsorted = [{'year': 2030, 'loss_pct': 4.0}, {'year': 2020, 'loss_pct': 5.0}]
    print(f"Config Unsorted, Year 2025: {get_interpolated_td_loss(2025, config_unsorted)}") # Expected: 0.045

    print(f"No Config, Year 2025: {get_interpolated_td_loss(2025, [])}") # Expected: 0.0
    print(f"Invalid Config, Year 2025: {get_interpolated_td_loss(2025, [{'y': 2020, 'l': 5}])}") # Expected: 0.0
