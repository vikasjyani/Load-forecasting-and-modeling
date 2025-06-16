import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression

def forecast_slr(historical_series, target_years, sector_name, confidence_pct=0.1):
    """
    Forecasts demand using Simple Linear Regression.

    Args:
        historical_series (pd.Series): Series with 'Year' as index and demand as values.
        target_years (list): List of future years to forecast.
        sector_name (str): Name of the sector being forecasted.
        confidence_pct (float): Percentage for simple lower/upper bound calculation (e.g., 0.1 for +/- 10%).

    Returns:
        pd.DataFrame: DataFrame with columns ['Year', 'Sector', 'Model', 'Value', 'Lower_Bound', 'Upper_Bound'].
    """
    if historical_series.empty or len(historical_series) < 2:
        results = []
        for year in target_years:
            results.append({
                'Year': year, 'Sector': sector_name, 'Model': 'SLR',
                'Value': np.nan, 'Lower_Bound': np.nan, 'Upper_Bound': np.nan,
                'Comment': 'Insufficient historical data'
            })
        return pd.DataFrame(results)

    X = historical_series.index.values.reshape(-1, 1)  # Years
    y = historical_series.values  # Demand

    try:
        model = LinearRegression()
        model.fit(X, y)
        forecast_values = model.predict(np.array(target_years).reshape(-1, 1))
    except Exception as e:
        results = []
        for year in target_years:
            results.append({
                'Year': year, 'Sector': sector_name, 'Model': 'SLR',
                'Value': np.nan, 'Lower_Bound': np.nan, 'Upper_Bound': np.nan,
                'Comment': f'Error during model fitting or prediction: {e}'
            })
        return pd.DataFrame(results)

    results = []
    for i, year in enumerate(target_years):
        forecasted_value = forecast_values[i]
        # Ensure forecast is not negative if historical data is non-negative
        if (y >= 0).all() and forecasted_value < 0:
            forecasted_value = 0

        lower_bound = forecasted_value * (1 - confidence_pct)
        upper_bound = forecasted_value * (1 + confidence_pct)
        results.append({
            'Year': year,
            'Sector': sector_name,
            'Model': 'SLR',
            'Value': forecasted_value,
            'Lower_Bound': lower_bound if forecasted_value > 0 else 0, # ensure bounds are also non-negative
            'Upper_Bound': upper_bound if forecasted_value > 0 else 0,
            'Comment': ''
        })
    return pd.DataFrame(results)

def forecast_wam(historical_series, target_years, sector_name, window_size=3, confidence_pct=0.1):
    """
    Forecasts demand using Weighted Average Method (Simple Moving Average).

    Args:
        historical_series (pd.Series): Series with 'Year' as index and demand as values.
        target_years (list): List of future years to forecast.
        sector_name (str): Name of the sector.
        window_size (int): Number of past years to average for the forecast.
        confidence_pct (float): Percentage for simple lower/upper bound.

    Returns:
        pd.DataFrame: DataFrame with forecast results.
    """
    if not isinstance(window_size, int) or window_size <= 0:
        window_size = 3 # Default to 3 if invalid
        comment_ws = f'Invalid window_size, defaulted to {window_size}. '
    else:
        comment_ws = ''

    if historical_series.empty or len(historical_series) < window_size:
        results = []
        for year in target_years:
            results.append({
                'Year': year, 'Sector': sector_name, 'Model': 'WAM',
                'Value': np.nan, 'Lower_Bound': np.nan, 'Upper_Bound': np.nan,
                'Comment': comment_ws + 'Insufficient historical data for given window size.'
            })
        return pd.DataFrame(results)

    last_known_values = historical_series.iloc[-window_size:]
    forecasted_value = last_known_values.mean()

    # Ensure forecast is not negative if historical data is non-negative
    if (historical_series.values >= 0).all() and forecasted_value < 0:
        forecasted_value = 0

    results = []
    for year in target_years:
        lower_bound = forecasted_value * (1 - confidence_pct)
        upper_bound = forecasted_value * (1 + confidence_pct)
        results.append({
            'Year': year,
            'Sector': sector_name,
            'Model': 'WAM',
            'Value': forecasted_value, # Same value for all target years in this simple WAM
            'Lower_Bound': lower_bound if forecasted_value > 0 else 0,
            'Upper_Bound': upper_bound if forecasted_value > 0 else 0,
            'Comment': comment_ws.strip()
        })
    return pd.DataFrame(results)

def forecast_mlr(historical_df, target_years, sector_name, independent_vars, confidence_pct=0.1):
    """
    Placeholder for Multi-Linear Regression forecast.

    Args:
        historical_df (pd.DataFrame): DataFrame with 'Year', sector demand, and independent variable columns.
                                      Assumes 'Year' is a column, not necessarily the index.
        target_years (list): List of future years.
        sector_name (str): The dependent variable column name (e.g., 'Domestic_Demand').
        independent_vars (list): List of column names to be used as independent variables.
                                 These should exist in historical_df.
        confidence_pct (float): Percentage for bounds.

    Returns:
        pd.DataFrame: DataFrame with placeholder results.
    """
    # Actual MLR requires future values for independent_vars, typically from an 'Assumptions' source.
    # This placeholder does not implement the actual regression.

    comment = f"MLR for {sector_name} using {independent_vars} is a placeholder. Requires future assumptions for independent variables."
    print(f"INFO: {comment}")

    results = []
    for year in target_years:
        results.append({
            'Year': year, 'Sector': sector_name, 'Model': 'MLR',
            'Value': np.nan,
            'Lower_Bound': np.nan,
            'Upper_Bound': np.nan,
            'Comment': comment
        })
    return pd.DataFrame(results)

# Example of how you might call these:
if __name__ == '__main__':
    # Sample data
    data = {
        'Year': [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023],
        'Domestic_Demand': [100, 105, 110, 115, 120, 118, 122, 125, 130],
        'Commercial_Demand': [50, 52, 55, 58, 60, 59, 62, 65, 68],
        'GDP': [1000, 1020, 1050, 1080, 1100, 1090, 1120, 1150, 1180], # Example independent var
        'Population': [10, 10.1, 10.2, 10.3, 10.4, 10.35, 10.45, 10.5, 10.6] # Example independent var
    }
    historical_df_full = pd.DataFrame(data)
    target_years_to_forecast = [2024, 2025, 2030]

    # SLR Example for Domestic_Demand
    domestic_series = historical_df_full.set_index('Year')['Domestic_Demand']
    slr_results_domestic = forecast_slr(domestic_series, target_years_to_forecast, 'Domestic_Demand')
    print("SLR Domestic Demand Forecast:\n", slr_results_domestic)

    # WAM Example for Commercial_Demand
    commercial_series = historical_df_full.set_index('Year')['Commercial_Demand']
    wam_results_commercial = forecast_wam(commercial_series, target_years_to_forecast, 'Commercial_Demand', window_size=3)
    print("\nWAM Commercial Demand Forecast:\n", wam_results_commercial)

    # MLR Placeholder Example for Domestic_Demand
    # For MLR, historical_df should contain the sector demand and independent variables.
    # 'Year' could be index or a column. Our placeholder assumes it's a column for now.
    mlr_results_domestic = forecast_mlr(historical_df_full, target_years_to_forecast, 'Domestic_Demand', ['GDP', 'Population'])
    print("\nMLR Domestic Demand Forecast (Placeholder):\n", mlr_results_domestic)
