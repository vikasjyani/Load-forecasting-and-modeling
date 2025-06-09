import numpy as np

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
    if not td_loss_config_list or not isinstance(td_loss_config_list, list):
        return 0.0  # Default to 0% loss if no configuration or invalid format

    # Ensure all entries are dicts with 'year' and 'loss_pct'
    valid_entries = [
        item for item in td_loss_config_list
        if isinstance(item, dict) and 'year' in item and 'loss_pct' in item
    ]

    if not valid_entries:
        return 0.0 # No valid entries found

    # Sort the configuration by year to ensure np.interp works correctly
    sorted_config = sorted(valid_entries, key=lambda x: x['year'])

    years = np.array([item['year'] for item in sorted_config])
    # Convert loss_pct from percentage (e.g., 5.0) to decimal (e.g., 0.05)
    loss_percentages_decimal = np.array([item['loss_pct'] / 100.0 for item in sorted_config])

    if len(years) == 0: # Should be caught by valid_entries check, but as a safeguard
        return 0.0

    if len(years) == 1:
        return loss_percentages_decimal[0] # Only one point, constant loss

    # np.interp handles extrapolation as constant values from endpoints if target_year is outside range
    interpolated_loss_decimal = np.interp(target_year, years, loss_percentages_decimal)

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
