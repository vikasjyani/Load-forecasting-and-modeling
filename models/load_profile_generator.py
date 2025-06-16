# # models/load_profile_generator.py
# """
# Load Profile Generator with Base Profile Scaling and STL methods
# Handles financial year calculations and constraint applications
# """
# import pandas as pd
# import numpy as np
# import os
# import json
# import logging
# from datetime import datetime, timedelta
# from pathlib import Path
# import holidays

# # Optional: STL decomposition (install statsmodels if using STL method)
# try:
#     from statsmodels.tsa.seasonal import STL
#     STL_AVAILABLE = True
# except ImportError:
#     STL_AVAILABLE = False
#     logging.warning("STL not available. Install statsmodels for STL decomposition: pip install statsmodels")

# from utils.helpers import ensure_directory, get_file_info
# from utils.constants import UNIT_FACTORS, VALIDATION_RULES
# from utils.response_utils import success_response, error_response

# logger = logging.getLogger(__name__)

# class LoadProfileGenerator:
#     """
#     Load Profile Generator supporting multiple methods and constraints
#     """
    
#     def __init__(self, project_path):
#         self.project_path = Path(project_path)
#         self.inputs_path = self.project_path / 'inputs'
#         self.results_path = self.project_path / 'results' / 'load_profiles'
#         self.config_path = self.project_path / 'config'
        
#         ensure_directory(str(self.results_path))
#         ensure_directory(str(self.config_path))
        
#         # Initialize holidays for Kerala (can be configured)
#         self.holidays_data = self._initialize_holidays()
        
#         logger.info(f"LoadProfileGenerator initialized for project: {project_path}")
    
#     def _initialize_holidays(self, years_range=(2017, 2040), region='IN', subdiv='KL'):
#         """Initialize holiday data for the specified region"""
#         try:
#             years = range(years_range[0], years_range[1])
#             holiday_calendar = holidays.country_holidays(region, subdiv=subdiv, years=years)
            
#             holidays_df = pd.DataFrame(
#                 [(date, name) for date, name in holiday_calendar.items()],
#                 columns=['Date', 'Holiday']
#             )
#             holidays_df['Date'] = pd.to_datetime(holidays_df['Date'])
            
#             logger.info(f"Loaded {len(holidays_df)} holidays for {region}-{subdiv}")
#             return holidays_df
            
#         except Exception as e:
#             logger.warning(f"Could not load holidays: {e}")
#             return pd.DataFrame(columns=['Date', 'Holiday'])
    
#     # def load_template_data(self, template_file=None):
#     #     """
#     #     Load data from the load curve template Excel file
        
#     #     Returns:
#     #         dict: Contains historical_demand, total_demand, monthly_peaks, monthly_load_factors
#     #     """
#     #     if not template_file:
#     #         template_file = self.inputs_path / 'load_curve_template.xlsx'
        
#     #     if not os.path.exists(template_file):
#     #         raise FileNotFoundError(f"Template file not found: {template_file}")
        
#     #     try:
#     #         # Load required sheets
#     #         historical_demand = pd.read_excel(template_file, sheet_name='Past_Hourly_Demand')
#     #         total_demand = pd.read_excel(template_file, sheet_name='Total_Demand')
            
#     #         # Optional sheets
#     #         monthly_peaks = None
#     #         monthly_load_factors = None
            
#     #         try:
#     #             monthly_peaks = pd.read_excel(template_file, sheet_name='Monthly_Peak_Demand')
#     #         except:
#     #             logger.info("Monthly_Peak_Demand sheet not found, skipping monthly peak constraints")
            
#     #         try:
#     #             monthly_load_factors = pd.read_excel(template_file, sheet_name='Monthly_Load_Factors')
#     #         except:
#     #             logger.info("Monthly_Load_Factors sheet not found, skipping load factor constraints")
            
#     #         # Process historical demand
#     #         historical_demand = self._process_historical_demand(historical_demand)
            
#     #         # Process total demand to financial years
#     #         total_demand = self._process_total_demand(total_demand)
            
#     #         logger.info(f"Template data loaded successfully from {template_file}")
            
#     #         return {
#     #             'historical_demand': historical_demand,
#     #             'total_demand': total_demand,
#     #             'monthly_peaks': monthly_peaks,
#     #             'monthly_load_factors': monthly_load_factors,
#     #             'template_info': get_file_info(str(template_file))
#     #         }
            
#     #     except Exception as e:
#     #         logger.error(f"Error loading template data: {e}")
#     #         raise ValueError(f"Failed to load template data: {str(e)}")
    


#     def load_template_data(self, template_file=None):
#         """
#         Load data from the load curve template Excel file
        
#         Returns:
#             dict: Contains historical_demand, total_demand, monthly_peaks, monthly_load_factors
#         """
#         if not template_file:
#             template_file = self.inputs_path / 'load_curve_template.xlsx'
        
#         if not os.path.exists(template_file):
#             raise FileNotFoundError(f"Template file not found: {template_file}")
        
#         try:
#             # Load required sheets
#             historical_demand = pd.read_excel(template_file, sheet_name='Past_Hourly_Demand')
            
#             # --- FIX: Try alternative sheet name for Total Demand ---
#             try:
#                 total_demand = pd.read_excel(template_file, sheet_name='Total_Demand')
#             except Exception:
#                 logger.info("Could not find 'Total_Demand' sheet, trying 'Total Demand' instead.")
#                 total_demand = pd.read_excel(template_file, sheet_name='Total Demand')
            
#             # Optional sheets
#             monthly_peaks = None
#             monthly_load_factors = None
            
#             try:
#                 monthly_peaks = pd.read_excel(template_file, sheet_name='Monthly_Peak_Demand')
#             except:
#                 logger.info("Monthly_Peak_Demand sheet not found, skipping monthly peak constraints")
            
#             try:
#                 monthly_load_factors = pd.read_excel(template_file, sheet_name='Monthly_Load_Factors')
#             except:
#                 logger.info("Monthly_Load_Factors sheet not found, skipping load factor constraints")
            
#             # Process historical demand
#             historical_demand = self._process_historical_demand(historical_demand)
            
#             # Process total demand to financial years
#             total_demand = self._process_total_demand(total_demand)
            
#             logger.info(f"Template data loaded successfully from {template_file}")
            
#             return {
#                 'historical_demand': historical_demand,
#                 'total_demand': total_demand,
#                 'monthly_peaks': monthly_peaks,
#                 'monthly_load_factors': monthly_load_factors,
#                 'template_info': get_file_info(str(template_file))
#             }
            
#         except Exception as e:
#             logger.error(f"Error loading template data: {e}")
#             raise ValueError(f"Failed to load template data: {str(e)}")


#     def _process_historical_demand(self, df):
#         """Process historical demand data with datetime and feature engineering"""
#         try:
#             # Create datetime column
#             if 'date' in df.columns and 'time' in df.columns:
#                 df['ds'] = pd.to_datetime(df['date'].astype(str) + ' ' + df['time'].astype(str))
#             elif 'datetime' in df.columns:
#                 df['ds'] = pd.to_datetime(df['datetime'])
#             else:
#                 raise ValueError("Historical demand must have 'date'+'time' or 'datetime' columns")
            
#             # Handle demand column
#             demand_col = 'demand'
#             if demand_col not in df.columns:
#                 # Try common alternatives
#                 alt_cols = ['Demand', 'load', 'Load', 'power', 'Power']
#                 for col in alt_cols:
#                     if col in df.columns:
#                         demand_col = col
#                         break
#                 else:
#                     raise ValueError("Could not find demand column in historical data")
            
#             # Clean data
#             df = df[['ds', demand_col]].rename(columns={demand_col: 'demand'})
#             df = df.dropna()
            
#             # Handle duplicates by taking mean
#             if df['ds'].duplicated().sum() > 0:
#                 logger.warning(f"Found {df['ds'].duplicated().sum()} duplicate timestamps, taking mean")
#                 df = df.groupby('ds', as_index=False)['demand'].mean()
            
#             # Sort by datetime
#             df = df.sort_values('ds').reset_index(drop=True)
            
#             # Add features
#             df = self._add_time_features(df)
            
#             logger.info(f"Processed {len(df)} historical demand records")
#             return df
            
#         except Exception as e:
#             logger.error(f"Error processing historical demand: {e}")
#             raise
    
#     def _process_total_demand(self, df):
#         """Process total demand data ensuring financial year format"""
#         try:
#             # Check if we have Financial_Year column
#             if 'Financial_Year' not in df.columns:
#                 if 'Year' in df.columns:
#                     # Convert calendar year to financial year (assuming April start)
#                     df['Financial_Year'] = df['Year'] + 1
#                     logger.info("Converted calendar years to financial years")
#                 else:
#                     raise ValueError("Total demand must have 'Financial_Year' or 'Year' column")
            
#             # Check for demand column
#             demand_col = None
#             for col in ['Total_Demand', 'Total demand', 'Demand', 'Total_On_Grid_Demand']:
#                 if col in df.columns:
#                     demand_col = col
#                     break
            
#             if not demand_col:
#                 raise ValueError("Could not find total demand column")
            
#             # Clean and standardize
#             result = df[['Financial_Year', demand_col]].copy()
#             result = result.rename(columns={demand_col: 'Total_Demand'})
#             result = result.dropna()
#             result = result.sort_values('Financial_Year').reset_index(drop=True)
            
#             logger.info(f"Processed total demand for {len(result)} financial years")
#             return result
            
#         except Exception as e:
#             logger.error(f"Error processing total demand: {e}")
#             raise
    
#     def _add_time_features(self, df):
#         """Add comprehensive time-based features"""
#         df = df.copy()
        
#         # Basic time features
#         df['hour'] = df['ds'].dt.hour
#         df['dayofweek'] = df['ds'].dt.dayofweek
#         df['month'] = df['ds'].dt.month
#         df['year'] = df['ds'].dt.year
#         df['day'] = df['ds'].dt.day
        
#         # Financial year (April to March)
#         df['financial_year'] = np.where(df['month'] >= 4, df['year'] + 1, df['year'])
        
#         # Financial month (April = 1, May = 2, ..., March = 12)
#         df['financial_month'] = np.where(df['month'] >= 4, df['month'] - 3, df['month'] + 9)
        
#         # Weekend flag
#         df['is_weekend'] = df['dayofweek'].isin([5, 6]).astype(int)
        
#         # Holiday flag
#         if not self.holidays_data.empty:
#             df['is_holiday'] = df['ds'].dt.date.isin(self.holidays_data['Date'].dt.date).astype(int)
#         else:
#             df['is_holiday'] = 0
        
#         # Special day flag (weekend or holiday)
#         df['is_special_day'] = (df['is_weekend'] | df['is_holiday']).astype(int)
        
#         return df
    
#     def load_scenario_data(self, scenario_path):
#         """
#         Load demand scenario data from CSV file
        
#         Args:
#             scenario_path (str): Path to scenario CSV file
            
#         Returns:
#             pd.DataFrame: Processed scenario data with financial years
#         """
#         try:
#             scenario_df = pd.read_csv(scenario_path)
            
#             # Find year and demand columns
#             year_col = None
#             demand_col = None
            
#             for col in ['Year', 'Financial_Year', 'year']:
#                 if col in scenario_df.columns:
#                     year_col = col
#                     break
            
#             for col in ['Total_On_Grid_Demand', 'Total', 'Total_Demand', 'Demand']:
#                 if col in scenario_df.columns:
#                     demand_col = col
#                     break
            
#             if not year_col or not demand_col:
#                 raise ValueError("Scenario file must have year and demand columns")
            
#             # Process data
#             result = scenario_df[[year_col, demand_col]].copy()
#             result = result.rename(columns={year_col: 'Year', demand_col: 'Total_Demand'})
            
#             # Convert to financial year if needed
#             if year_col != 'Financial_Year':
#                 result['Financial_Year'] = result['Year'] + 1
#             else:
#                 result['Financial_Year'] = result['Year']
            
#             result = result[['Financial_Year', 'Total_Demand']].dropna()
#             result = result.sort_values('Financial_Year').reset_index(drop=True)
            
#             logger.info(f"Loaded scenario data for {len(result)} financial years")
#             return result
            
#         except Exception as e:
#             logger.error(f"Error loading scenario data: {e}")
#             raise
    
#     def get_available_base_years(self, historical_data):
#         """Get available financial years from historical data for base year selection"""
#         if historical_data.empty:
#             return []
        
#         # Get complete financial years only
#         year_counts = historical_data.groupby('financial_year').size()
        
#         # A complete financial year should have close to 8760 hours (365*24) or 8784 (366*24)
#         complete_years = year_counts[year_counts >= 8000].index.tolist()
        
#         return sorted(complete_years)
    
#     def extract_base_profiles(self, historical_data, base_year):
#         """
#         Extract load profiles from a specific base year
        
#         Args:
#             historical_data (pd.DataFrame): Historical demand data
#             base_year (int): Financial year to use as base
            
#         Returns:
#             pd.DataFrame: Load profiles by financial_month, is_special_day, hour
#         """
#         try:
#             # Filter data for base year
#             base_data = historical_data[historical_data['financial_year'] == base_year].copy()
            
#             if base_data.empty:
#                 raise ValueError(f"No data available for base year {base_year}")
            
#             # Calculate daily totals
#             daily_totals = base_data.groupby(['financial_year', 'financial_month', 'day'])['demand'].sum().reset_index()
#             daily_totals.rename(columns={'demand': 'daily_total'}, inplace=True)
            
#             # Merge daily totals back
#             base_data = base_data.merge(daily_totals, on=['financial_year', 'financial_month', 'day'])
            
#             # Calculate hourly fractions
#             base_data['fraction'] = base_data['demand'] / base_data['daily_total']
#             base_data['fraction'] = base_data['fraction'].fillna(0)
            
#             # Extract profiles by financial_month, special day flag, and hour
#             profiles = base_data.groupby(['financial_month', 'is_special_day', 'hour'])['fraction'].mean().reset_index()
            
#             # Validate profiles
#             profiles['fraction'] = profiles['fraction'].clip(lower=0, upper=1)
            
#             logger.info(f"Extracted {len(profiles)} load profile patterns from base year {base_year}")
#             return profiles
            
#         except Exception as e:
#             logger.error(f"Error extracting base profiles: {e}")
#             raise
    
#     def generate_base_profile_forecast(self, historical_data, demand_scenarios, base_year, 
#                                      start_fy, end_fy, frequency='hourly', constraints=None):
#         """
#         Generate load profile forecast using base year scaling method
        
#         Args:
#             historical_data (pd.DataFrame): Historical demand data
#             demand_scenarios (pd.DataFrame): Future demand scenarios
#             base_year (int): Base financial year for profile extraction
#             start_fy (int): Start financial year for forecast
#             end_fy (int): End financial year for forecast
#             frequency (str): Output frequency ('hourly', '15min', etc.)
#             constraints (dict): Optional constraints
            
#         Returns:
#             dict: Forecast results and metadata
#         """
#         try:
#             # Extract base profiles
#             profiles = self.extract_base_profiles(historical_data, base_year)
            
#             # Generate future dates
#             future_dates = self._generate_future_dates(start_fy, end_fy, frequency)
            
#             # Create forecast dataframe
#             forecast_df = pd.DataFrame({'ds': future_dates})
#             forecast_df = self._add_time_features(forecast_df)
            
#             # Apply base profiles
#             forecast_df = self._apply_base_profiles(forecast_df, profiles, demand_scenarios)
            
#             # Apply constraints if provided
#             if constraints:
#                 forecast_df = self._apply_constraints(forecast_df, constraints, demand_scenarios)
            
#             # Final processing
#             forecast_df['demand'] = forecast_df['demand'].clip(lower=0)
#             forecast_df['demand'] = forecast_df['demand'].round(2)
            
#             # Validation
#             validation_results = self._validate_forecast(forecast_df, demand_scenarios, constraints)
            
#             # Prepare results
#             results = {
#                 'method': 'base_profile_scaling',
#                 'base_year': base_year,
#                 'start_fy': start_fy,
#                 'end_fy': end_fy,
#                 'frequency': frequency,
#                 'forecast': forecast_df[['ds', 'demand', 'financial_year', 'financial_month', 'hour']],
#                 'validation': validation_results,
#                 'metadata': {
#                     'generated_at': datetime.now().isoformat(),
#                     'total_hours': len(forecast_df),
#                     'method_config': {
#                         'base_year': base_year,
#                         'profiles_count': len(profiles)
#                     }
#                 }
#             }
            
#             logger.info(f"Generated base profile forecast: {len(forecast_df)} records")
#             return success_response("Base profile forecast generated successfully", results)
            
#         except Exception as e:
#             logger.error(f"Error generating base profile forecast: {e}")
#             return error_response(f"Failed to generate forecast: {str(e)}")
    
#     def generate_stl_forecast(self, historical_data, demand_scenarios, start_fy, end_fy, 
#                             frequency='hourly', stl_params=None, constraints=None):
#         """
#         Generate load profile forecast using STL decomposition method
        
#         Args:
#             historical_data (pd.DataFrame): Historical demand data
#             demand_scenarios (pd.DataFrame): Future demand scenarios
#             start_fy (int): Start financial year for forecast
#             end_fy (int): End financial year for forecast
#             frequency (str): Output frequency
#             stl_params (dict): STL parameters
#             constraints (dict): Optional constraints
            
#         Returns:
#             dict: Forecast results and metadata
#         """
#         if not STL_AVAILABLE:
#             return error_response("STL decomposition not available. Install statsmodels package.")
        
#         try:
#             # Validate historical data length
#             if len(historical_data) < 24 * 365:
#                 raise ValueError("Need at least one year of hourly data for STL decomposition")
            
#             # Set default STL parameters
#             if not stl_params:
#                 stl_params = {
#                     'period': 24 * 365,  # Annual seasonality
#                     'seasonal': 13,      # Seasonal smoother
#                     'trend': None,       # Auto trend smoother
#                     'robust': True       # Robust to outliers
#                 }
            
#             # Perform STL decomposition
#             stl_result = self._perform_stl_decomposition(historical_data, stl_params)
            
#             # Generate future dates
#             future_dates = self._generate_future_dates(start_fy, end_fy, frequency)
            
#             # Create forecast using STL components
#             forecast_df = self._create_stl_forecast(future_dates, stl_result, demand_scenarios)
            
#             # Apply constraints if provided
#             if constraints:
#                 forecast_df = self._apply_constraints(forecast_df, constraints, demand_scenarios)
            
#             # Final processing
#             forecast_df['demand'] = forecast_df['demand'].clip(lower=0)
#             forecast_df['demand'] = forecast_df['demand'].round(2)
            
#             # Validation
#             validation_results = self._validate_forecast(forecast_df, demand_scenarios, constraints)
            
#             # Prepare results
#             results = {
#                 'method': 'stl_decomposition',
#                 'start_fy': start_fy,
#                 'end_fy': end_fy,
#                 'frequency': frequency,
#                 'forecast': forecast_df[['ds', 'demand', 'financial_year', 'financial_month', 'hour']],
#                 'validation': validation_results,
#                 'stl_components': {
#                     'trend_growth_rate': stl_result.get('trend_growth_rate', 0),
#                     'seasonal_strength': stl_result.get('seasonal_strength', 0)
#                 },
#                 'metadata': {
#                     'generated_at': datetime.now().isoformat(),
#                     'total_hours': len(forecast_df),
#                     'method_config': stl_params
#                 }
#             }
            
#             logger.info(f"Generated STL forecast: {len(forecast_df)} records")
#             return success_response("STL forecast generated successfully", results)
            
#         except Exception as e:
#             logger.error(f"Error generating STL forecast: {e}")
#             return error_response(f"Failed to generate STL forecast: {str(e)}")
    
#     def _perform_stl_decomposition(self, historical_data, stl_params):
#         """Perform STL decomposition on historical data"""
#         try:
#             # Ensure data is sorted and complete
#             data = historical_data.sort_values('ds').copy()
            
#             # Create time series
#             demand_series = data.set_index('ds')['demand']
            
#             # Fill missing timestamps if needed (hourly frequency)
#             full_index = pd.date_range(start=demand_series.index.min(), 
#                                      end=demand_series.index.max(), 
#                                      freq='H')
#             demand_series = demand_series.reindex(full_index)
#             demand_series = demand_series.interpolate(method='linear')
            
#             # Perform STL decomposition
#             stl = STL(demand_series, 
#                      period=stl_params.get('period', 24*365),
#                      seasonal=stl_params.get('seasonal', 13),
#                      trend=stl_params.get('trend'),
#                      robust=stl_params.get('robust', True))
            
#             result = stl.fit()
            
#             # Calculate trend growth rate
#             trend_values = result.trend.dropna()
#             if len(trend_values) >= 2:
#                 # Simple linear trend calculation
#                 x = np.arange(len(trend_values))
#                 trend_slope = np.polyfit(x, trend_values, 1)[0]
#                 trend_growth_rate = trend_slope * 24 * 365  # Annual growth
#             else:
#                 trend_growth_rate = 0
            
#             # Calculate seasonal strength
#             seasonal_var = result.seasonal.var()
#             remainder_var = result.resid.var()
#             seasonal_strength = seasonal_var / (seasonal_var + remainder_var) if (seasonal_var + remainder_var) > 0 else 0
            
#             return {
#                 'trend': result.trend,
#                 'seasonal': result.seasonal,
#                 'resid': result.resid,
#                 'trend_growth_rate': trend_growth_rate,
#                 'seasonal_strength': seasonal_strength,
#                 'original_index': demand_series.index
#             }
            
#         except Exception as e:
#             logger.error(f"Error in STL decomposition: {e}")
#             raise
    
#     def _create_stl_forecast(self, future_dates, stl_result, demand_scenarios):
#         """Create forecast using STL components and demand scenarios"""
#         try:
#             forecast_df = pd.DataFrame({'ds': future_dates})
#             forecast_df = self._add_time_features(forecast_df)
            
#             # Extract last trend value and growth rate
#             last_trend = stl_result['trend'].dropna().iloc[-1]
#             trend_growth = stl_result['trend_growth_rate']
            
#             # Project trend forward
#             hours_from_last = (forecast_df['ds'] - stl_result['original_index'][-1]).dt.total_seconds() / 3600
#             forecast_df['trend'] = last_trend + (trend_growth * hours_from_last / (24 * 365))
            
#             # Add seasonal component (repeat last year's pattern)
#             seasonal_data = stl_result['seasonal'].iloc[-24*365:].values  # Last year
#             seasonal_cycles = len(forecast_df) // len(seasonal_data) + 1
#             extended_seasonal = np.tile(seasonal_data, seasonal_cycles)[:len(forecast_df)]
#             forecast_df['seasonal'] = extended_seasonal
            
#             # Combine components for base forecast
#             forecast_df['demand'] = forecast_df['trend'] + forecast_df['seasonal']
            
#             # Scale to match demand scenarios
#             if not demand_scenarios.empty:
#                 forecast_df = self._scale_to_annual_targets(forecast_df, demand_scenarios)
            
#             return forecast_df
            
#         except Exception as e:
#             logger.error(f"Error creating STL forecast: {e}")
#             raise
    
#     def _apply_base_profiles(self, forecast_df, profiles, demand_scenarios):
#         """Apply base year profiles to forecast with annual scaling"""
#         try:
#             # Merge profiles
#             forecast_df = forecast_df.merge(
#                 profiles, 
#                 on=['financial_month', 'is_special_day', 'hour'], 
#                 how='left'
#             )
            
#             # Fill missing fractions with average
#             avg_fraction = profiles['fraction'].mean()
#             forecast_df['fraction'] = forecast_df['fraction'].fillna(avg_fraction)
            
#             # Calculate daily totals for each financial year
#             daily_totals = forecast_df.groupby(['financial_year', 'financial_month', 'day']).size().reset_index()
#             daily_totals.rename(columns={0: 'hours_in_day'}, inplace=True)
            
#             # Initialize demand with profiles
#             forecast_df['demand'] = forecast_df['fraction'] * avg_fraction * 1000  # Base scaling
            
#             # Scale to annual targets
#             if not demand_scenarios.empty:
#                 forecast_df = self._scale_to_annual_targets(forecast_df, demand_scenarios)
            
#             return forecast_df
            
#         except Exception as e:
#             logger.error(f"Error applying base profiles: {e}")
#             raise
    
#     def _scale_to_annual_targets(self, forecast_df, demand_scenarios):
#         """Scale forecast to match annual demand targets"""
#         try:
#             for _, scenario_row in demand_scenarios.iterrows():
#                 fy = scenario_row['Financial_Year']
#                 target_annual = scenario_row['Total_Demand']
                
#                 # Filter forecast for this financial year
#                 fy_mask = forecast_df['financial_year'] == fy
                
#                 if fy_mask.sum() == 0:
#                     continue
                
#                 # Calculate current annual total
#                 current_annual = forecast_df.loc[fy_mask, 'demand'].sum()
                
#                 if current_annual > 0:
#                     # Scale to target
#                     scale_factor = target_annual / current_annual
#                     forecast_df.loc[fy_mask, 'demand'] *= scale_factor
            
#             return forecast_df
            
#         except Exception as e:
#             logger.error(f"Error scaling to annual targets: {e}")
#             raise
    
#     def _generate_future_dates(self, start_fy, end_fy, frequency='hourly'):
#         """Generate future datetime range for financial years"""
#         try:
#             # Convert financial years to calendar dates
#             start_date = f"{start_fy-1}-04-01"  # April 1st of previous calendar year
#             end_date = f"{end_fy}-03-31 23:00"  # March 31st 23:00 of end calendar year
            
#             # Set frequency
#             freq_map = {
#                 'hourly': 'H',
#                 '15min': '15T',
#                 '30min': '30T',
#                 'daily': 'D'
#             }
            
#             freq = freq_map.get(frequency, 'H')
            
#             # Generate date range
#             dates = pd.date_range(start=start_date, end=end_date, freq=freq)
            
#             logger.info(f"Generated {len(dates)} timestamps from FY{start_fy} to FY{end_fy}")
#             return dates
            
#         except Exception as e:
#             logger.error(f"Error generating future dates: {e}")
#             raise
    
#     def _apply_constraints(self, forecast_df, constraints, demand_scenarios):
#         """Apply monthly peak and load factor constraints"""
#         try:
#             modified_df = forecast_df.copy()
            
#             # Apply monthly peak constraints
#             if 'monthly_peaks' in constraints and constraints['monthly_peaks'] is not None:
#                 modified_df = self._apply_monthly_peak_constraints(
#                     modified_df, constraints['monthly_peaks']
#                 )
            
#             # Apply monthly load factor constraints
#             if 'monthly_load_factors' in constraints and constraints['monthly_load_factors'] is not None:
#                 modified_df = self._apply_load_factor_constraints(
#                     modified_df, constraints['monthly_load_factors']
#                 )
            
#             # Re-scale to annual targets after constraint application
#             if not demand_scenarios.empty:
#                 modified_df = self._scale_to_annual_targets(modified_df, demand_scenarios)
            
#             return modified_df
            
#         except Exception as e:
#             logger.error(f"Error applying constraints: {e}")
#             return forecast_df  # Return original if constraints fail
    
#     def _apply_monthly_peak_constraints(self, forecast_df, monthly_peaks):
#         """Apply monthly peak demand constraints"""
#         try:
#             # Month name to number mapping for financial year
#             month_map = {
#                 'Apr': 1, 'May': 2, 'Jun': 3, 'Jul': 4, 'Aug': 5, 'Sep': 6,
#                 'Oct': 7, 'Nov': 8, 'Dec': 9, 'Jan': 10, 'Feb': 11, 'Mar': 12
#             }
            
#             # Melt monthly peaks data
#             peak_cols = [col for col in monthly_peaks.columns if col in month_map.keys()]
#             if not peak_cols:
#                 logger.warning("No valid month columns found in monthly peaks data")
#                 return forecast_df
            
#             peaks_melted = monthly_peaks.melt(
#                 id_vars=['Financial_Year'], 
#                 value_vars=peak_cols,
#                 var_name='month_name', 
#                 value_name='target_peak'
#             )
#             peaks_melted['financial_month'] = peaks_melted['month_name'].map(month_map)
#             peaks_melted = peaks_melted.dropna()
            
#             # Apply constraints
#             for _, peak_row in peaks_melted.iterrows():
#                 fy = peak_row['Financial_Year']
#                 fm = peak_row['financial_month']
#                 target_peak = peak_row['target_peak']
                
#                 if pd.isna(target_peak) or target_peak <= 0:
#                     continue
                
#                 # Filter for this month and year
#                 mask = (forecast_df['financial_year'] == fy) & (forecast_df['financial_month'] == fm)
                
#                 if mask.sum() == 0:
#                     continue
                
#                 # Current peak
#                 current_peak = forecast_df.loc[mask, 'demand'].max()
                
#                 if current_peak > 0 and current_peak < target_peak:
#                     # Scale up to meet peak constraint
#                     scale_factor = target_peak / current_peak
#                     forecast_df.loc[mask, 'demand'] *= scale_factor
            
#             return forecast_df
            
#         except Exception as e:
#             logger.error(f"Error applying monthly peak constraints: {e}")
#             return forecast_df
    
#     def _apply_load_factor_constraints(self, forecast_df, load_factors):
#         """Apply monthly load factor constraints"""
#         try:
#             for _, lf_row in load_factors.iterrows():
#                 fy = lf_row.get('Financial_Year')
#                 month = lf_row.get('Month')  # Could be month number or name
#                 target_lf = lf_row.get('Load_Factor')
                
#                 if pd.isna(target_lf) or target_lf <= 0 or target_lf > 1:
#                     continue
                
#                 # Convert month to financial month if needed
#                 if isinstance(month, str):
#                     month_map = {
#                         'Apr': 1, 'May': 2, 'Jun': 3, 'Jul': 4, 'Aug': 5, 'Sep': 6,
#                         'Oct': 7, 'Nov': 8, 'Dec': 9, 'Jan': 10, 'Feb': 11, 'Mar': 12
#                     }
#                     financial_month = month_map.get(month)
#                 else:
#                     financial_month = month
                
#                 if not financial_month:
#                     continue
                
#                 # Filter data
#                 mask = (forecast_df['financial_year'] == fy) & (forecast_df['financial_month'] == financial_month)
                
#                 if mask.sum() == 0:
#                     continue
                
#                 # Calculate current load factor
#                 month_data = forecast_df.loc[mask, 'demand']
#                 current_avg = month_data.mean()
#                 current_peak = month_data.max()
#                 current_lf = current_avg / current_peak if current_peak > 0 else 0
                
#                 # Adjust if needed
#                 if current_lf != target_lf and current_peak > 0:
#                     target_avg = target_lf * current_peak
#                     scale_factor = target_avg / current_avg if current_avg > 0 else 1
#                     forecast_df.loc[mask, 'demand'] *= scale_factor
            
#             return forecast_df
            
#         except Exception as e:
#             logger.error(f"Error applying load factor constraints: {e}")
#             return forecast_df
    
#     def _validate_forecast(self, forecast_df, demand_scenarios, constraints=None):
#         """Validate forecast against targets and constraints"""
#         validation = {
#             'annual_totals': {},
#             'monthly_peaks': {},
#             'load_factors': {},
#             'general_stats': {}
#         }
        
#         try:
#             # Annual totals validation
#             annual_totals = forecast_df.groupby('financial_year')['demand'].sum()
            
#             for _, scenario_row in demand_scenarios.iterrows():
#                 fy = scenario_row['Financial_Year']
#                 target = scenario_row['Total_Demand']
                
#                 if fy in annual_totals.index:
#                     actual = annual_totals[fy]
#                     diff_percent = abs(target - actual) / target * 100 if target > 0 else 0
#                     validation['annual_totals'][f'FY{fy}'] = {
#                         'target': target,
#                         'actual': actual,
#                         'difference_percent': diff_percent
#                     }
            
#             # General statistics
#             validation['general_stats'] = {
#                 'total_hours': len(forecast_df),
#                 'peak_demand': forecast_df['demand'].max(),
#                 'min_demand': forecast_df['demand'].min(),
#                 'avg_demand': forecast_df['demand'].mean(),
#                 'overall_load_factor': forecast_df['demand'].mean() / forecast_df['demand'].max() if forecast_df['demand'].max() > 0 else 0
#             }
            
#             # Monthly peaks validation if constraints provided
#             if constraints and 'monthly_peaks' in constraints:
#                 # Add monthly peak validation
#                 pass
            
#         except Exception as e:
#             logger.error(f"Error in forecast validation: {e}")
#             validation['error'] = str(e)
        
#         return validation
    
#     def save_forecast(self, forecast_results, profile_id=None):
#         """Save forecast results to CSV file"""
#         try:
#             if not profile_id:
#                 timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
#                 method = forecast_results.get('method', 'unknown')
#                 profile_id = f"{method}_{timestamp}"
            
#             # Save forecast data
#             forecast_df = forecast_results['forecast']
#             csv_path = self.results_path / f"{profile_id}.csv"
#             forecast_df.to_csv(csv_path, index=False)
            
#             # Save metadata
#             metadata = {
#                 'profile_id': profile_id,
#                 'method': forecast_results.get('method'),
#                 'generated_at': forecast_results.get('metadata', {}).get('generated_at'),
#                 'validation': forecast_results.get('validation'),
#                 'file_info': get_file_info(str(csv_path))
#             }
            
#             metadata_path = self.config_path / f"{profile_id}_metadata.json"
#             with open(metadata_path, 'w') as f:
#                 json.dump(metadata, f, indent=2, default=str)
            
#             logger.info(f"Saved forecast to {csv_path}")
            
#             return {
#                 'profile_id': profile_id,
#                 'csv_path': str(csv_path),
#                 'metadata_path': str(metadata_path),
#                 'file_size': metadata['file_info']['size_mb']
#             }
            
#         except Exception as e:
#             logger.error(f"Error saving forecast: {e}")
#             raise
    
#     def get_saved_profiles(self):
#         """Get list of saved load profiles"""
#         try:
#             profiles = []
            
#             if not self.results_path.exists():
#                 return profiles
            
#             for csv_file in self.results_path.glob("*.csv"):
#                 profile_id = csv_file.stem
#                 metadata_file = self.config_path / f"{profile_id}_metadata.json"
                
#                 profile_info = {
#                     'profile_id': profile_id,
#                     'csv_path': str(csv_file),
#                     'file_info': get_file_info(str(csv_file))
#                 }
                
#                 # Load metadata if available
#                 if metadata_file.exists():
#                     try:
#                         with open(metadata_file, 'r') as f:
#                             metadata = json.load(f)
#                         profile_info.update(metadata)
#                     except:
#                         pass
                
#                 profiles.append(profile_info)
            
#             # Sort by creation time (newest first)
#             profiles.sort(key=lambda x: x.get('generated_at', ''), reverse=True)
            
#             return profiles
            
#         except Exception as e:
#             logger.error(f"Error getting saved profiles: {e}")
#             return []
# models/load_profile_generator.py
"""
Load Profile Generator with Base Profile Scaling and STL methods
Handles financial year calculations and constraint applications
Now includes dynamic calculation of monthly peaks and load factors when not in template
"""
import pandas as pd
import numpy as np
import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
import holidays

# Optional: STL decomposition (install statsmodels if using STL method)
try:
    from statsmodels.tsa.seasonal import STL
    STL_AVAILABLE = True
except ImportError:
    STL_AVAILABLE = False
    logging.warning("STL not available. Install statsmodels for STL decomposition: pip install statsmodels")

from utils.helpers import ensure_directory, get_file_info
from utils.constants import UNIT_FACTORS, VALIDATION_RULES
from utils.response_utils import success_response, error_response

logger = logging.getLogger(__name__)

class LoadProfileGenerator:
    """
    Load Profile Generator supporting multiple methods and constraints
    """
    
    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.inputs_path = self.project_path / 'inputs'
        self.results_path = self.project_path / 'results' / 'load_profiles'
        self.config_path = self.project_path / 'config'
        
        ensure_directory(str(self.results_path))
        ensure_directory(str(self.config_path))
        
        # Initialize holidays for Kerala (can be configured)
        self.holidays_data = self._initialize_holidays()
        
        logger.info(f"LoadProfileGenerator initialized for project: {project_path}")
    
    def _initialize_holidays(self, years_range=(2017, 2040), region='IN', subdiv='KL'):
        """Initialize holiday data for the specified region"""
        try:
            years = range(years_range[0], years_range[1])
            holiday_calendar = holidays.country_holidays(region, subdiv=subdiv, years=years)
            
            holidays_df = pd.DataFrame(
                [(date, name) for date, name in holiday_calendar.items()],
                columns=['Date', 'Holiday']
            )
            holidays_df['Date'] = pd.to_datetime(holidays_df['Date'])
            
            logger.info(f"Loaded {len(holidays_df)} holidays for {region}-{subdiv}")
            return holidays_df
            
        except Exception as e:
            logger.warning(f"Could not load holidays: {e}")
            return pd.DataFrame(columns=['Date', 'Holiday'])

    def load_template_data(self, template_file=None):
        """
        Load data from the load curve template Excel file
        
        Returns:
            dict: Contains historical_demand, total_demand, monthly_peaks, monthly_load_factors
        """
        if not template_file:
            template_file = self.inputs_path / 'load_curve_template.xlsx'
        
        if not os.path.exists(template_file):
            raise FileNotFoundError(f"Template file not found: {template_file}")
        
        try:
            # Load required sheets
            historical_demand = pd.read_excel(template_file, sheet_name='Past_Hourly_Demand')
            
            # Try alternative sheet name for Total Demand
            try:
                total_demand = pd.read_excel(template_file, sheet_name='Total_Demand')
            except Exception:
                logger.info("Could not find 'Total_Demand' sheet, trying 'Total Demand' instead.")
                total_demand = pd.read_excel(template_file, sheet_name='Total Demand')
            
            # Optional sheets
            monthly_peaks = None
            monthly_load_factors = None
            
            try:
                monthly_peaks = pd.read_excel(template_file, sheet_name='Monthly_Peak_Demand')
                logger.info("Monthly_Peak_Demand sheet loaded from template")
            except:
                logger.info("Monthly_Peak_Demand sheet not found, will calculate dynamically")
            
            try:
                monthly_load_factors = pd.read_excel(template_file, sheet_name='Monthly_Load_Factors')
                logger.info("Monthly_Load_Factors sheet loaded from template")
            except:
                logger.info("Monthly_Load_Factors sheet not found, will calculate dynamically")
            
            # Process historical demand
            historical_demand = self._process_historical_demand(historical_demand)
            
            # Process total demand to financial years
            total_demand = self._process_total_demand(total_demand)
            
            # Calculate dynamic constraints if not available in template
            calculated_monthly_peaks = None
            calculated_load_factors = None
            
            if monthly_peaks is None:
                calculated_monthly_peaks = self._calculate_monthly_peaks(historical_demand)
                logger.info("Calculated monthly peaks from historical data")
            
            if monthly_load_factors is None:
                calculated_load_factors = self._calculate_monthly_load_factors(historical_demand)
                logger.info("Calculated monthly load factors from historical data")
            
            logger.info(f"Template data loaded successfully from {template_file}")
            
            return {
                'historical_demand': historical_demand,
                'total_demand': total_demand,
                'monthly_peaks': monthly_peaks,
                'monthly_load_factors': monthly_load_factors,
                'calculated_monthly_peaks': calculated_monthly_peaks,
                'calculated_load_factors': calculated_load_factors,
                'template_info': get_file_info(str(template_file))
            }
            
        except Exception as e:
            logger.error(f"Error loading template data: {e}")
            raise ValueError(f"Failed to load template data: {str(e)}")

    def _calculate_monthly_peaks(self, historical_data):
        """
        Calculate monthly peak fractions from historical data
        
        Args:
            historical_data (pd.DataFrame): Historical demand data with time features
            
        Returns:
            pd.DataFrame: Monthly peaks by financial year
        """
        try:
            if historical_data.empty:
                return None
            
            # Calculate monthly totals and peaks for each financial year
            monthly_stats = []
            
            for fy in historical_data['financial_year'].unique():
                fy_data = historical_data[historical_data['financial_year'] == fy]
                
                if len(fy_data) < 8000:  # Skip incomplete years
                    continue
                
                # Calculate annual total
                annual_total = fy_data['demand'].sum()
                
                if annual_total <= 0:
                    continue
                
                # Calculate monthly shares and peaks
                monthly_row = {'Financial_Year': fy}
                
                for month in range(1, 13):
                    month_data = fy_data[fy_data['financial_month'] == month]
                    
                    if not month_data.empty:
                        monthly_total = month_data['demand'].sum()
                        monthly_peak = month_data['demand'].max()
                        
                        # Calculate monthly share
                        monthly_share = monthly_total / annual_total if annual_total > 0 else 0
                        
                        # Store monthly share (this will be used for future scaling)
                        month_names = ['Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep',
                                     'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar']
                        month_col = month_names[month - 1]
                        monthly_row[month_col] = monthly_share
                
                monthly_stats.append(monthly_row)
            
            if not monthly_stats:
                return None
            
            # Create DataFrame and average across years
            monthly_peaks_df = pd.DataFrame(monthly_stats)
            
            # Calculate average monthly shares across all years
            month_cols = ['Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep',
                         'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar']
            
            avg_shares = {}
            for col in month_cols:
                if col in monthly_peaks_df.columns:
                    avg_shares[col] = monthly_peaks_df[col].mean()
            
            # Create final dataframe with average values
            final_peaks = pd.DataFrame([avg_shares])
            final_peaks['Financial_Year'] = 'Average'
            
            logger.info(f"Calculated monthly peaks for {len(monthly_stats)} years")
            return final_peaks
            
        except Exception as e:
            logger.error(f"Error calculating monthly peaks: {e}")
            return None

    def _calculate_monthly_load_factors(self, historical_data):
        """
        Calculate monthly load factors from historical data
        
        Args:
            historical_data (pd.DataFrame): Historical demand data with time features
            
        Returns:
            pd.DataFrame: Monthly load factors by financial year
        """
        try:
            if historical_data.empty:
                return None
            
            monthly_lf_stats = []
            
            for fy in historical_data['financial_year'].unique():
                fy_data = historical_data[historical_data['financial_year'] == fy]
                
                if len(fy_data) < 8000:  # Skip incomplete years
                    continue
                
                monthly_row = {'Financial_Year': fy}
                
                for month in range(1, 13):
                    month_data = fy_data[fy_data['financial_month'] == month]
                    
                    if not month_data.empty:
                        avg_demand = month_data['demand'].mean()
                        max_demand = month_data['demand'].max()
                        
                        # Calculate load factor
                        load_factor = avg_demand / max_demand if max_demand > 0 else 0
                        
                        month_names = ['Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep',
                                     'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar']
                        month_col = month_names[month - 1]
                        monthly_row[month_col] = load_factor
                
                monthly_lf_stats.append(monthly_row)
            
            if not monthly_lf_stats:
                return None
            
            # Create DataFrame and average across years
            monthly_lf_df = pd.DataFrame(monthly_lf_stats)
            
            # Calculate average load factors across all years
            month_cols = ['Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep',
                         'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar']
            
            avg_lf = {}
            for col in month_cols:
                if col in monthly_lf_df.columns:
                    avg_lf[col] = monthly_lf_df[col].mean()
            
            # Create final dataframe with average values
            final_lf = pd.DataFrame([avg_lf])
            final_lf['Financial_Year'] = 'Average'
            
            logger.info(f"Calculated monthly load factors for {len(monthly_lf_stats)} years")
            return final_lf
            
        except Exception as e:
            logger.error(f"Error calculating monthly load factors: {e}")
            return None

    def _process_historical_demand(self, df):
        """Process historical demand data with datetime and feature engineering"""
        try:
            # Create datetime column
            if 'date' in df.columns and 'time' in df.columns:
                df['ds'] = pd.to_datetime(df['date'].astype(str) + ' ' + df['time'].astype(str))
            elif 'datetime' in df.columns:
                df['ds'] = pd.to_datetime(df['datetime'])
            else:
                raise ValueError("Historical demand must have 'date'+'time' or 'datetime' columns")
            
            # Handle demand column
            demand_col = 'demand'
            if demand_col not in df.columns:
                # Try common alternatives
                alt_cols = ['Demand', 'load', 'Load', 'power', 'Power']
                for col in alt_cols:
                    if col in df.columns:
                        demand_col = col
                        break
                else:
                    raise ValueError("Could not find demand column in historical data")
            
            # Clean data
            df = df[['ds', demand_col]].rename(columns={demand_col: 'demand'})
            df = df.dropna()
            
            # Handle duplicates by taking mean
            if df['ds'].duplicated().sum() > 0:
                logger.warning(f"Found {df['ds'].duplicated().sum()} duplicate timestamps, taking mean")
                df = df.groupby('ds', as_index=False)['demand'].mean()
            
            # Sort by datetime
            df = df.sort_values('ds').reset_index(drop=True)
            
            # Add features
            df = self._add_time_features(df)
            
            logger.info(f"Processed {len(df)} historical demand records")
            return df
            
        except Exception as e:
            logger.error(f"Error processing historical demand: {e}")
            raise
    
    def _process_total_demand(self, df):
        """Process total demand data ensuring financial year format"""
        try:
            # Check if we have Financial_Year column
            if 'Financial_Year' not in df.columns:
                if 'Year' in df.columns:
                    # Convert calendar year to financial year (assuming April start)
                    df['Financial_Year'] = df['Year'] + 1
                    logger.info("Converted calendar years to financial years")
                else:
                    raise ValueError("Total demand must have 'Financial_Year' or 'Year' column")
            
            # Check for demand column
            demand_col = None
            for col in ['Total_Demand', 'Total demand', 'Demand', 'Total_On_Grid_Demand']:
                if col in df.columns:
                    demand_col = col
                    break
            
            if not demand_col:
                raise ValueError("Could not find total demand column")
            
            # Clean and standardize
            result = df[['Financial_Year', demand_col]].copy()
            result = result.rename(columns={demand_col: 'Total_Demand'})
            result = result.dropna()
            result = result.sort_values('Financial_Year').reset_index(drop=True)
            
            logger.info(f"Processed total demand for {len(result)} financial years")
            return result
            
        except Exception as e:
            logger.error(f"Error processing total demand: {e}")
            raise
    
    def _add_time_features(self, df):
        """Add comprehensive time-based features"""
        df = df.copy()
        
        # Basic time features
        df['hour'] = df['ds'].dt.hour
        df['dayofweek'] = df['ds'].dt.dayofweek
        df['month'] = df['ds'].dt.month
        df['year'] = df['ds'].dt.year
        df['day'] = df['ds'].dt.day
        
        # Financial year (April to March)
        df['financial_year'] = np.where(df['month'] >= 4, df['year'] + 1, df['year'])
        
        # Financial month (April = 1, May = 2, ..., March = 12)
        df['financial_month'] = np.where(df['month'] >= 4, df['month'] - 3, df['month'] + 9)
        
        # Weekend flag
        df['is_weekend'] = df['dayofweek'].isin([5, 6]).astype(int)
        
        # Holiday flag
        if not self.holidays_data.empty:
            df['is_holiday'] = df['ds'].dt.date.isin(self.holidays_data['Date'].dt.date).astype(int)
        else:
            df['is_holiday'] = 0
        
        # Special day flag (weekend or holiday)
        df['is_special_day'] = (df['is_weekend'] | df['is_holiday']).astype(int)
        
        return df
    
    def load_scenario_data(self, scenario_path):
        """
        Load demand scenario data from CSV file
        
        Args:
            scenario_path (str): Path to scenario CSV file
            
        Returns:
            pd.DataFrame: Processed scenario data with financial years
        """
        try:
            scenario_df = pd.read_csv(scenario_path)
            
            # Find year and demand columns
            year_col = None
            demand_col = None
            
            for col in ['Year', 'Financial_Year', 'year']:
                if col in scenario_df.columns:
                    year_col = col
                    break
            
            for col in ['Total_On_Grid_Demand', 'Total', 'Total_Demand', 'Demand']:
                if col in scenario_df.columns:
                    demand_col = col
                    break
            
            if not year_col or not demand_col:
                raise ValueError("Scenario file must have year and demand columns")
            
            # Process data
            result = scenario_df[[year_col, demand_col]].copy()
            result = result.rename(columns={year_col: 'Year', demand_col: 'Total_Demand'})
            
            # Convert to financial year if needed
            if year_col != 'Financial_Year':
                result['Financial_Year'] = result['Year'] + 1
            else:
                result['Financial_Year'] = result['Year']
            
            result = result[['Financial_Year', 'Total_Demand']].dropna()
            result = result.sort_values('Financial_Year').reset_index(drop=True)
            
            logger.info(f"Loaded scenario data for {len(result)} financial years")
            return result
            
        except Exception as e:
            logger.error(f"Error loading scenario data: {e}")
            raise
    
    def get_available_base_years(self, historical_data):
        """Get available financial years from historical data for base year selection"""
        if historical_data.empty:
            return []
        
        # Get complete financial years only
        year_counts = historical_data.groupby('financial_year').size()
        
        # A complete financial year should have close to 8760 hours (365*24) or 8784 (366*24)
        complete_years = year_counts[year_counts >= 8000].index.tolist()
        
        return sorted(complete_years)
    
    def extract_base_profiles(self, historical_data, base_year):
        """
        Extract load profiles from a specific base year
        
        Args:
            historical_data (pd.DataFrame): Historical demand data
            base_year (int): Financial year to use as base
            
        Returns:
            pd.DataFrame: Load profiles by financial_month, is_special_day, hour
        """
        try:
            # Filter data for base year
            base_data = historical_data[historical_data['financial_year'] == base_year].copy()
            
            if base_data.empty:
                raise ValueError(f"No data available for base year {base_year}")
            
            # Calculate daily totals
            daily_totals = base_data.groupby(['financial_year', 'financial_month', 'day'])['demand'].sum().reset_index()
            daily_totals.rename(columns={'demand': 'daily_total'}, inplace=True)
            
            # Merge daily totals back
            base_data = base_data.merge(daily_totals, on=['financial_year', 'financial_month', 'day'])
            
            # Calculate hourly fractions
            base_data['fraction'] = base_data['demand'] / base_data['daily_total']
            base_data['fraction'] = base_data['fraction'].fillna(0)
            
            # Extract profiles by financial_month, special day flag, and hour
            profiles = base_data.groupby(['financial_month', 'is_special_day', 'hour'])['fraction'].mean().reset_index()
            
            # Validate profiles
            profiles['fraction'] = profiles['fraction'].clip(lower=0, upper=1)
            
            logger.info(f"Extracted {len(profiles)} load profile patterns from base year {base_year}")
            return profiles
            
        except Exception as e:
            logger.error(f"Error extracting base profiles: {e}")
            raise
    
    def generate_base_profile_forecast(self, historical_data, demand_scenarios, base_year, 
                                     start_fy, end_fy, frequency='hourly', constraints=None):
        """
        Generate load profile forecast using base year scaling method
        
        Args:
            historical_data (pd.DataFrame): Historical demand data
            demand_scenarios (pd.DataFrame): Future demand scenarios
            base_year (int): Base financial year for profile extraction
            start_fy (int): Start financial year for forecast
            end_fy (int): End financial year for forecast
            frequency (str): Output frequency ('hourly', '15min', etc.)
            constraints (dict): Optional constraints
            
        Returns:
            dict: Forecast results and metadata
        """
        try:
            # Extract base profiles
            profiles = self.extract_base_profiles(historical_data, base_year)
            
            # Generate future dates
            future_dates = self._generate_future_dates(start_fy, end_fy, frequency)
            
            # Create forecast dataframe
            forecast_df = pd.DataFrame({'ds': future_dates})
            forecast_df = self._add_time_features(forecast_df)
            
            # Apply base profiles
            forecast_df = self._apply_base_profiles(forecast_df, profiles, demand_scenarios)
            
            # Apply constraints if provided
            if constraints:
                forecast_df = self._apply_constraints(forecast_df, constraints, demand_scenarios, historical_data)
            
            # Final processing
            forecast_df['demand'] = forecast_df['demand'].clip(lower=0)
            forecast_df['demand'] = forecast_df['demand'].round(2)
            
            # Validation
            validation_results = self._validate_forecast(forecast_df, demand_scenarios, constraints)
            
            # Prepare results
            results = {
                'method': 'base_profile_scaling',
                'base_year': base_year,
                'start_fy': start_fy,
                'end_fy': end_fy,
                'frequency': frequency,
                'forecast': forecast_df[['ds', 'demand', 'financial_year', 'financial_month', 'hour']],
                'validation': validation_results,
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'total_hours': len(forecast_df),
                    'method_config': {
                        'base_year': base_year,
                        'profiles_count': len(profiles)
                    }
                }
            }
            
            logger.info(f"Generated base profile forecast: {len(forecast_df)} records")
            return success_response("Base profile forecast generated successfully", results)
            
        except Exception as e:
            logger.error(f"Error generating base profile forecast: {e}")
            return error_response(f"Failed to generate forecast: {str(e)}")
    
    def generate_stl_forecast(self, historical_data, demand_scenarios, start_fy, end_fy, 
                            frequency='hourly', stl_params=None, constraints=None):
        """
        Generate load profile forecast using STL decomposition method
        
        Args:
            historical_data (pd.DataFrame): Historical demand data
            demand_scenarios (pd.DataFrame): Future demand scenarios
            start_fy (int): Start financial year for forecast
            end_fy (int): End financial year for forecast
            frequency (str): Output frequency
            stl_params (dict): STL parameters
            constraints (dict): Optional constraints
            
        Returns:
            dict: Forecast results and metadata
        """
        if not STL_AVAILABLE:
            return error_response("STL decomposition not available. Install statsmodels package.")
        
        try:
            # Validate historical data length
            if len(historical_data) < 24 * 365:
                raise ValueError("Need at least one year of hourly data for STL decomposition")
            
            # Set default STL parameters
            if not stl_params:
                stl_params = {
                    'period': 24 * 365,  # Annual seasonality
                    'seasonal': 13,      # Seasonal smoother
                    'trend': None,       # Auto trend smoother
                    'robust': True       # Robust to outliers
                }
            
            # Perform STL decomposition
            stl_result = self._perform_stl_decomposition(historical_data, stl_params)
            
            # Generate future dates
            future_dates = self._generate_future_dates(start_fy, end_fy, frequency)
            
            # Create forecast using STL components
            forecast_df = self._create_stl_forecast(future_dates, stl_result, demand_scenarios)
            
            # Apply constraints if provided
            if constraints:
                forecast_df = self._apply_constraints(forecast_df, constraints, demand_scenarios, historical_data)
            
            # Final processing
            forecast_df['demand'] = forecast_df['demand'].clip(lower=0)
            forecast_df['demand'] = forecast_df['demand'].round(2)
            
            # Validation
            validation_results = self._validate_forecast(forecast_df, demand_scenarios, constraints)
            
            # Prepare results
            results = {
                'method': 'stl_decomposition',
                'start_fy': start_fy,
                'end_fy': end_fy,
                'frequency': frequency,
                'forecast': forecast_df[['ds', 'demand', 'financial_year', 'financial_month', 'hour']],
                'validation': validation_results,
                'stl_components': {
                    'trend_growth_rate': stl_result.get('trend_growth_rate', 0),
                    'seasonal_strength': stl_result.get('seasonal_strength', 0)
                },
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'total_hours': len(forecast_df),
                    'method_config': stl_params
                }
            }
            
            logger.info(f"Generated STL forecast: {len(forecast_df)} records")
            return success_response("STL forecast generated successfully", results)
            
        except Exception as e:
            logger.error(f"Error generating STL forecast: {e}")
            return error_response(f"Failed to generate STL forecast: {str(e)}")
    
    def _perform_stl_decomposition(self, historical_data, stl_params):
        """Perform STL decomposition on historical data"""
        try:
            # Ensure data is sorted and complete
            data = historical_data.sort_values('ds').copy()
            
            # Create time series
            demand_series = data.set_index('ds')['demand']
            
            # Fill missing timestamps if needed (hourly frequency)
            full_index = pd.date_range(start=demand_series.index.min(), 
                                     end=demand_series.index.max(), 
                                     freq='h')
            demand_series = demand_series.reindex(full_index)
            demand_series = demand_series.interpolate(method='linear')
            
            # Perform STL decomposition
            stl = STL(demand_series, 
                     period=stl_params.get('period', 24*365),
                     seasonal=stl_params.get('seasonal', 13),
                     trend=stl_params.get('trend'),
                     robust=stl_params.get('robust', True))
            
            result = stl.fit()
            
            # Calculate trend growth rate
            trend_values = result.trend.dropna()
            if len(trend_values) >= 2:
                # Simple linear trend calculation
                x = np.arange(len(trend_values))
                trend_slope = np.polyfit(x, trend_values, 1)[0]
                trend_growth_rate = trend_slope * 24 * 365  # Annual growth
            else:
                trend_growth_rate = 0
            
            # Calculate seasonal strength
            seasonal_var = result.seasonal.var()
            remainder_var = result.resid.var()
            seasonal_strength = seasonal_var / (seasonal_var + remainder_var) if (seasonal_var + remainder_var) > 0 else 0
            
            return {
                'trend': result.trend,
                'seasonal': result.seasonal,
                'resid': result.resid,
                'trend_growth_rate': trend_growth_rate,
                'seasonal_strength': seasonal_strength,
                'original_index': demand_series.index
            }
            
        except Exception as e:
            logger.error(f"Error in STL decomposition: {e}")
            raise
    
    def _create_stl_forecast(self, future_dates, stl_result, demand_scenarios):
        """Create forecast using STL components and demand scenarios"""
        try:
            forecast_df = pd.DataFrame({'ds': future_dates})
            forecast_df = self._add_time_features(forecast_df)
            
            # Extract last trend value and growth rate
            last_trend = stl_result['trend'].dropna().iloc[-1]
            trend_growth = stl_result['trend_growth_rate']
            
            # Project trend forward
            hours_from_last = (forecast_df['ds'] - stl_result['original_index'][-1]).dt.total_seconds() / 3600
            forecast_df['trend'] = last_trend + (trend_growth * hours_from_last / (24 * 365))
            
            # Add seasonal component (repeat last year's pattern)
            seasonal_data = stl_result['seasonal'].iloc[-24*365:].values  # Last year
            seasonal_cycles = len(forecast_df) // len(seasonal_data) + 1
            extended_seasonal = np.tile(seasonal_data, seasonal_cycles)[:len(forecast_df)]
            forecast_df['seasonal'] = extended_seasonal
            
            # Combine components for base forecast
            forecast_df['demand'] = forecast_df['trend'] + forecast_df['seasonal']
            
            # Scale to match demand scenarios
            if not demand_scenarios.empty:
                forecast_df = self._scale_to_annual_targets(forecast_df, demand_scenarios)
            
            return forecast_df
            
        except Exception as e:
            logger.error(f"Error creating STL forecast: {e}")
            raise
    
    def _apply_base_profiles(self, forecast_df, profiles, demand_scenarios):
        """Apply base year profiles to forecast with annual scaling"""
        try:
            # Merge profiles
            forecast_df = forecast_df.merge(
                profiles, 
                on=['financial_month', 'is_special_day', 'hour'], 
                how='left'
            )
            
            # Fill missing fractions with average
            avg_fraction = profiles['fraction'].mean()
            forecast_df['fraction'] = forecast_df['fraction'].fillna(avg_fraction)
            
            # Initialize demand with profiles
            forecast_df['demand'] = forecast_df['fraction'] * avg_fraction * 1000  # Base scaling
            
            # Scale to annual targets
            if not demand_scenarios.empty:
                forecast_df = self._scale_to_annual_targets(forecast_df, demand_scenarios)
            
            return forecast_df
            
        except Exception as e:
            logger.error(f"Error applying base profiles: {e}")
            raise
    
    def _scale_to_annual_targets(self, forecast_df, demand_scenarios):
        """Scale forecast to match annual demand targets"""
        try:
            for _, scenario_row in demand_scenarios.iterrows():
                fy = scenario_row['Financial_Year']
                target_annual = scenario_row['Total_Demand']
                
                # Filter forecast for this financial year
                fy_mask = forecast_df['financial_year'] == fy
                
                if fy_mask.sum() == 0:
                    continue
                
                # Calculate current annual total
                current_annual = forecast_df.loc[fy_mask, 'demand'].sum()
                
                if current_annual > 0:
                    # Scale to target
                    scale_factor = target_annual / current_annual
                    forecast_df.loc[fy_mask, 'demand'] *= scale_factor
            
            return forecast_df
            
        except Exception as e:
            logger.error(f"Error scaling to annual targets: {e}")
            raise
    
    def _generate_future_dates(self, start_fy, end_fy, frequency='hourly'):
        """Generate future datetime range for financial years"""
        try:
            # Convert financial years to calendar dates
            start_date = f"{start_fy-1}-04-01"  # April 1st of previous calendar year
            end_date = f"{end_fy}-03-31 23:00"  # March 31st 23:00 of end calendar year
            
            # Set frequency
            freq_map = {
                'hourly': 'H',
                '15min': '15T',
                '30min': '30T',
                'daily': 'D'
            }
            
            freq = freq_map.get(frequency, 'H')
            
            # Generate date range
            dates = pd.date_range(start=start_date, end=end_date, freq=freq)
            
            logger.info(f"Generated {len(dates)} timestamps from FY{start_fy} to FY{end_fy}")
            return dates
            
        except Exception as e:
            logger.error(f"Error generating future dates: {e}")
            raise
    
    def _apply_constraints(self, forecast_df, constraints, demand_scenarios, historical_data):
        """Apply constraints including calculated ones"""
        try:
            modified_df = forecast_df.copy()
            
            # Determine which constraints to use
            monthly_peaks_data = constraints.get('monthly_peaks')
            monthly_lf_data = constraints.get('monthly_load_factors')
            calculated_peaks = constraints.get('calculated_monthly_peaks')
            calculated_lf = constraints.get('calculated_load_factors')
            
            # Use calculated constraints if template constraints are not available
            if monthly_peaks_data is None and calculated_peaks is not None:
                monthly_peaks_data = calculated_peaks
                logger.info("Using calculated monthly peaks for constraints")
            
            if monthly_lf_data is None and calculated_lf is not None:
                monthly_lf_data = calculated_lf
                logger.info("Using calculated load factors for constraints")
            
            # Apply monthly share constraints (dynamic monthly peaks)
            if calculated_peaks is not None:
                modified_df = self._apply_monthly_share_constraints(
                    modified_df, calculated_peaks, demand_scenarios
                )
            
            # Apply load factor constraints
            if monthly_lf_data is not None:
                modified_df = self._apply_load_factor_constraints(
                    modified_df, monthly_lf_data
                )
            
            # Re-scale to annual targets after constraint application
            if not demand_scenarios.empty:
                modified_df = self._scale_to_annual_targets(modified_df, demand_scenarios)
            
            return modified_df
            
        except Exception as e:
            logger.error(f"Error applying constraints: {e}")
            return forecast_df  # Return original if constraints fail
    
    def _apply_monthly_share_constraints(self, forecast_df, monthly_shares_data, demand_scenarios):
        """Apply monthly share constraints based on calculated historical patterns"""
        try:
            # Month name to number mapping for financial year
            month_map = {
                'Apr': 1, 'May': 2, 'Jun': 3, 'Jul': 4, 'Aug': 5, 'Sep': 6,
                'Oct': 7, 'Nov': 8, 'Dec': 9, 'Jan': 10, 'Feb': 11, 'Mar': 12
            }
            
            # Get monthly shares
            if monthly_shares_data.empty:
                return forecast_df
            
            shares_row = monthly_shares_data.iloc[0]  # Use first (average) row
            
            # Apply constraints for each financial year and month
            for _, scenario_row in demand_scenarios.iterrows():
                fy = scenario_row['Financial_Year']
                annual_target = scenario_row['Total_Demand']
                
                for month_name, financial_month in month_map.items():
                    if month_name not in shares_row:
                        continue
                    
                    monthly_share = shares_row[month_name]
                    if pd.isna(monthly_share) or monthly_share <= 0:
                        continue
                    
                    # Calculate target monthly total
                    target_monthly_total = annual_target * monthly_share
                    
                    # Filter forecast for this month and year
                    mask = (forecast_df['financial_year'] == fy) & (forecast_df['financial_month'] == financial_month)
                    
                    if mask.sum() == 0:
                        continue
                    
                    # Current monthly total
                    current_monthly_total = forecast_df.loc[mask, 'demand'].sum()
                    
                    if current_monthly_total > 0:
                        # Scale to target monthly total
                        scale_factor = target_monthly_total / current_monthly_total
                        forecast_df.loc[mask, 'demand'] *= scale_factor
            
            return forecast_df
            
        except Exception as e:
            logger.error(f"Error applying monthly share constraints: {e}")
            return forecast_df
    
    def _apply_load_factor_constraints(self, forecast_df, load_factors_data):
        """Apply monthly load factor constraints"""
        try:
            # Month name to number mapping
            month_map = {
                'Apr': 1, 'May': 2, 'Jun': 3, 'Jul': 4, 'Aug': 5, 'Sep': 6,
                'Oct': 7, 'Nov': 8, 'Dec': 9, 'Jan': 10, 'Feb': 11, 'Mar': 12
            }
            
            if load_factors_data.empty:
                return forecast_df
            
            lf_row = load_factors_data.iloc[0]  # Use first (average) row
            
            # Apply load factor constraints for each financial year
            for fy in forecast_df['financial_year'].unique():
                for month_name, financial_month in month_map.items():
                    if month_name not in lf_row:
                        continue
                    
                    target_lf = lf_row[month_name]
                    if pd.isna(target_lf) or target_lf <= 0 or target_lf > 1:
                        continue
                    
                    # Filter data for this month and year
                    mask = (forecast_df['financial_year'] == fy) & (forecast_df['financial_month'] == financial_month)
                    
                    if mask.sum() == 0:
                        continue
                    
                    month_data = forecast_df.loc[mask, 'demand']
                    if month_data.empty:
                        continue
                    
                    # Calculate current load factor
                    current_avg = month_data.mean()
                    current_peak = month_data.max()
                    
                    if current_peak <= 0:
                        continue
                    
                    current_lf = current_avg / current_peak
                    
                    # Adjust if needed (only if significantly different)
                    if abs(current_lf - target_lf) > 0.05:  # 5% tolerance
                        # Calculate required average to achieve target load factor
                        target_avg = target_lf * current_peak
                        
                        # Scale demands to achieve target average
                        if current_avg > 0:
                            scale_factor = target_avg / current_avg
                            forecast_df.loc[mask, 'demand'] *= scale_factor
            
            return forecast_df
            
        except Exception as e:
            logger.error(f"Error applying load factor constraints: {e}")
            return forecast_df
    
    def _validate_forecast(self, forecast_df, demand_scenarios, constraints=None):
        """Validate forecast against targets and constraints"""
        validation = {
            'annual_totals': {},
            'monthly_validation': {},
            'general_stats': {}
        }
        
        try:
            # Annual totals validation
            annual_totals = forecast_df.groupby('financial_year')['demand'].sum()
            
            for _, scenario_row in demand_scenarios.iterrows():
                fy = scenario_row['Financial_Year']
                target = scenario_row['Total_Demand']
                
                if fy in annual_totals.index:
                    actual = annual_totals[fy]
                    diff_percent = abs(target - actual) / target * 100 if target > 0 else 0
                    validation['annual_totals'][f'FY{fy}'] = {
                        'target': target,
                        'actual': actual,
                        'difference_percent': diff_percent
                    }
            
            # Monthly validation
            monthly_stats = forecast_df.groupby(['financial_year', 'financial_month']).agg({
                'demand': ['sum', 'max', 'mean']
            }).round(2)
            
            # General statistics
            validation['general_stats'] = {
                'total_hours': len(forecast_df),
                'peak_demand': forecast_df['demand'].max(),
                'min_demand': forecast_df['demand'].min(),
                'avg_demand': forecast_df['demand'].mean(),
                'overall_load_factor': forecast_df['demand'].mean() / forecast_df['demand'].max() if forecast_df['demand'].max() > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error in forecast validation: {e}")
            validation['error'] = str(e)
        
        return validation
        
    def save_forecast(self, forecast_results, profile_id=None):
        """
        Save forecast results to CSV file with format
        Output columns: datetime, Demand (kW), Date, Time, Fiscal_Year, Year
        """
        try:
            if not profile_id:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                method = forecast_results.get('method', 'unknown')
                profile_id = f"{method}_{timestamp}"
            
            # Get forecast data
            forecast_df = forecast_results['forecast'].copy()
            
            # Ensure we have the required columns
            if 'ds' not in forecast_df.columns or 'demand' not in forecast_df.columns:
                raise ValueError("Forecast data must contain 'ds' and 'demand' columns")
            
            # Create output dataframe with required format
            output_df = pd.DataFrame()
            
            # Convert demand to kW (assuming input is in kW, but ensure consistency)
            # If demand is in MW, multiply by 1000; if in GW, multiply by 1,000,000
            demand_values = forecast_df['demand'].copy()
            
            # Check the magnitude to guess the unit and convert to kW
            # avg_demand = demand_values.mean()
            # if avg_demand > 1000000:  # Likely GW
            #     demand_values = demand_values * 1000000  # GW to kW
            #     logger.info("Converted demand from GW to kW")
            # elif avg_demand > 1000:  # Likely MW
            #     demand_values = demand_values * 1000  # MW to kW
            #     logger.info("Converted demand from MW to kW")
            # Otherwise assume already in kW
            
            # Create output columns in the specified order
            output_df['datetime'] = pd.to_datetime(forecast_df['ds'])
            output_df['Demand (kW)'] = demand_values.round(2)
            
            # Extract date and time components
            output_df['Date'] = output_df['datetime'].dt.date
            output_df['Time'] = output_df['datetime'].dt.time
            
            # Add financial year and calendar year
            if 'financial_year' in forecast_df.columns:
                output_df['Fiscal_Year'] = forecast_df['financial_year']
            else:
                # Calculate financial year from datetime (April to March)
                output_df['Fiscal_Year'] = np.where(
                    output_df['datetime'].dt.month >= 4,
                    output_df['datetime'].dt.year + 1,
                    output_df['datetime'].dt.year
                )
            
            output_df['Year'] = output_df['datetime'].dt.year
            
            # Add hour column for reference (useful for analysis)
            if 'hour' in forecast_df.columns:
                output_df['Hour'] = forecast_df['hour']
            else:
                output_df['Hour'] = output_df['datetime'].dt.hour
            
            # Sort by datetime to ensure chronological order
            output_df = output_df.sort_values('datetime').reset_index(drop=True)
            
            # Save to CSV with the specified column order
            csv_path = self.results_path / f"{profile_id}.csv"
            output_df.to_csv(csv_path, index=False)
            
            # Create summary statistics for metadata
            summary_stats = {
                'total_records': len(output_df),
                'date_range': {
                    'start': output_df['datetime'].min().isoformat(),
                    'end': output_df['datetime'].max().isoformat()
                },
                'demand_stats_kW': {
                    'min': float(output_df['Demand (kW)'].min()),
                    'max': float(output_df['Demand (kW)'].max()),
                    'mean': float(output_df['Demand (kW)'].mean()),
                    'std': float(output_df['Demand (kW)'].std())
                },
                'fiscal_years': {
                    'start': int(output_df['Fiscal_Year'].min()),
                    'end': int(output_df['Fiscal_Year'].max()),
                    'count': len(output_df['Fiscal_Year'].unique())
                },
                'load_factor': float(output_df['Demand (kW)'].mean() / output_df['Demand (kW)'].max()) if output_df['Demand (kW)'].max() > 0 else 0
            }
            
            # Save metadata
            metadata = {
                'profile_id': profile_id,
                'method': forecast_results.get('method'),
                'generated_at': forecast_results.get('metadata', {}).get('generated_at'),
                'start_fy': int(output_df['Fiscal_Year'].min()),
                'end_fy': int(output_df['Fiscal_Year'].max()),
                'output_format': {
                    'columns': list(output_df.columns),
                    'demand_unit': 'kW',
                    'timestamp_format': 'datetime',
                    'total_hours': len(output_df)
                },
                'summary_statistics': summary_stats,
                'validation': forecast_results.get('validation'),
                'file_info': get_file_info(str(csv_path))
            }
            
            metadata_path = self.config_path / f"{profile_id}_metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
            
            logger.info(f"Saved forecast to {csv_path} with {len(output_df)} records")
            logger.info(f"Output format: {list(output_df.columns)}")
            logger.info(f"Demand range: {summary_stats['demand_stats_kW']['min']:.1f} - {summary_stats['demand_stats_kW']['max']:.1f} kW")
            
            return {
                'profile_id': profile_id,
                'csv_path': str(csv_path),
                'metadata_path': str(metadata_path),
                'file_size': metadata['file_info']['size_mb'],
                'summary_stats': summary_stats
            }
            
        except Exception as e:
            logger.error(f"Error saving forecast: {e}")
            raise


    def get_saved_profiles(self):
        """Get list of saved load profiles"""
        try:
            profiles = []
            
            if not self.results_path.exists():
                return profiles
            
            for csv_file in self.results_path.glob("*.csv"):
                profile_id = csv_file.stem
                metadata_file = self.config_path / f"{profile_id}_metadata.json"
                
                profile_info = {
                    'profile_id': profile_id,
                    'csv_path': str(csv_file),
                    'file_info': get_file_info(str(csv_file))
                }
                
                # Load metadata if available
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                        profile_info.update(metadata)
                    except:
                        pass
                
                profiles.append(profile_info)
            
            # Sort by creation time (newest first)
            profiles.sort(key=lambda x: x.get('generated_at', ''), reverse=True)
            
            return profiles
            
        except Exception as e:
            logger.error(f"Error getting saved profiles: {e}")
            return []

    def get_profile_data(self, profile_id):
        """
        method to get profile data with proper column handling
        """
        try:
            # Find profile file
            csv_path = self.results_path / f"{profile_id}.csv"
            
            if not csv_path.exists():
                raise FileNotFoundError(f"Profile not found: {profile_id}")
            
            # Load profile data
            profile_df = pd.read_csv(csv_path)
            
            # Load metadata if available
            metadata_path = self.config_path / f"{profile_id}_metadata.json"
            metadata = {}
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
            
            # Determine demand column (handle both old and new formats)
            demand_col = None
            if 'Demand (kW)' in profile_df.columns:
                demand_col = 'Demand (kW)'
            elif 'demand' in profile_df.columns:
                demand_col = 'demand'
            else:
                # Look for any column with 'demand' in the name
                demand_cols = [col for col in profile_df.columns if 'demand' in col.lower()]
                if demand_cols:
                    demand_col = demand_cols[0]
            
            if not demand_col:
                raise ValueError(f"No demand column found in profile {profile_id}")
            
            # Prepare response data
            profile_data = {
                'profile_id': profile_id,
                'file_info': get_file_info(str(csv_path)),
                'data_summary': {
                    'total_records': len(profile_df),
                    'columns': list(profile_df.columns),
                    'demand_column': demand_col
                },
                'metadata': metadata
            }
            
            # Add date range if datetime column exists
            datetime_col = None
            if 'datetime' in profile_df.columns:
                datetime_col = 'datetime'
            elif 'ds' in profile_df.columns:
                datetime_col = 'ds'
            
            if datetime_col:
                profile_data['data_summary']['date_range'] = {
                    'start': profile_df[datetime_col].min(),
                    'end': profile_df[datetime_col].max()
                }
            
            # Add demand statistics
            if demand_col:
                profile_data['data_summary']['demand_stats'] = {
                    'min': float(profile_df[demand_col].min()),
                    'max': float(profile_df[demand_col].max()),
                    'mean': float(profile_df[demand_col].mean()),
                    'std': float(profile_df[demand_col].std())
                }
            
            # Optional: Include sample data (first 100 records)
            sample_size = min(100, len(profile_df))
            profile_data['sample_data'] = profile_df.head(sample_size).to_dict('records')
            
            return profile_data
            
        except Exception as e:
            logger.error(f"Error getting profile data for {profile_id}: {e}")
            raise