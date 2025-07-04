# services/demand_visualization_service.py
"""
Demand Visualization Service
Dynamic data processing with proper filtering and chart generation using plot_utils
"""
import os
import json
import pandas as pd
import numpy as np
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from pathlib import Path

# Import plot utilities
from utils.plot_utils import PlotUtils
from utils.color_manager import color_manager

logger = logging.getLogger(__name__)

@dataclass
class ScenarioInfo:
    name: str
    path: str
    sectors_count: int
    year_range: Dict[str, int]
    has_data: bool
    file_count: int = 0
    last_modified: str = None
    available_sectors: List[str] = None
    available_models: List[str] = None

@dataclass
class SectorData:
    name: str
    years: List[int]
    models: List[str]
    data: Dict[str, List[float]]
    metadata: Dict[str, Any] = None

@dataclass
class FilterConfig:
    unit: str = 'TWh'
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    selected_sectors: List[str] = None
    selected_models: List[str] = None

class DemandVisualizationService:
    """
    service with dynamic data handling and plot_utils integration
    """
    
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.results_path = os.path.join(project_path, 'results', 'demand_projection')
        self.config_path = os.path.join(project_path, 'config')
        
        # Initialize plot utilities
        self.plot_utils = PlotUtils()
        
        # Unit conversion factors (base: kWh)
        self.unit_factors = {
            'kWh': 1,
            'MWh': 1000,
            'GWh': 1000000,
            'TWh': 1000000000
        }
        
        # Ensure config directory exists
        os.makedirs(self.config_path, exist_ok=True)
        
        logger.info(f"service initialized: {self.results_path}")
    
    def get_available_scenarios(self) -> List[ScenarioInfo]:
        """Get comprehensive list of available scenarios with metadata"""
        try:
            if not os.path.exists(self.results_path):
                logger.warning(f"Results path does not exist: {self.results_path}")
                return []
            
            scenarios = []
            for item in os.listdir(self.results_path):
                item_path = os.path.join(self.results_path, item)
                
                if not os.path.isdir(item_path):
                    continue
                
                try:
                    scenario_info = self._analyze_scenario_directory(item, item_path)
                    if scenario_info.has_data:
                        scenarios.append(scenario_info)
                except Exception as e:
                    logger.warning(f"Error analyzing scenario {item}: {e}")
                    continue
            
            # Sort by last modified (newest first)
            scenarios.sort(key=lambda x: x.last_modified or '', reverse=True)
            logger.info(f"Found {len(scenarios)} valid scenarios")
            return scenarios
            
        except Exception as e:
            logger.exception(f"Error getting available scenarios: {e}")
            return []
    
    def _analyze_scenario_directory(self, scenario_name: str, scenario_path: str) -> ScenarioInfo:
        """Comprehensive analysis of scenario directory"""
        try:
            excel_files = [
                f for f in os.listdir(scenario_path)
                if f.endswith('.xlsx') and not f.startswith('_') and not f.startswith('~')
            ]
            
            year_range = {'min': 2025, 'max': 2037}
            last_modified = None
            available_sectors = []
            available_models = set()
            
            for excel_file in excel_files:
                file_path = os.path.join(scenario_path, excel_file)
                sector_name = os.path.splitext(excel_file)[0]
                available_sectors.append(sector_name)
                
                try:
                    file_mtime = os.path.getmtime(file_path)
                    if last_modified is None or file_mtime > last_modified:
                        last_modified = file_mtime
                    
                    # Quick analysis for year range and models
                    sector_info = self._quick_analyze_sector_file(file_path)
                    if sector_info:
                        if sector_info['year_range']:
                            year_range['min'] = min(year_range['min'], sector_info['year_range']['min'])
                            year_range['max'] = max(year_range['max'], sector_info['year_range']['max'])
                        
                        available_models.update(sector_info.get('models', []))
                        
                except Exception as e:
                    logger.debug(f"Could not analyze file {excel_file}: {e}")
                    continue
            
            return ScenarioInfo(
                name=scenario_name,
                path=scenario_path,
                sectors_count=len(excel_files),
                year_range=year_range,
                has_data=len(excel_files) > 0,
                file_count=len(excel_files),
                last_modified=datetime.fromtimestamp(last_modified).isoformat() if last_modified else None,
                available_sectors=available_sectors,
                available_models=list(available_models)
            )
            
        except Exception as e:
            logger.warning(f"Error analyzing scenario directory {scenario_name}: {e}")
            return ScenarioInfo(
                name=scenario_name,
                path=scenario_path,
                sectors_count=0,
                year_range={'min': 2025, 'max': 2037},
                has_data=False,
                available_sectors=[],
                available_models=[]
            )
    
    def _quick_analyze_sector_file(self, file_path: str) -> Dict[str, Any]:
        """Quick analysis of sector file for metadata"""
        try:
            # Determine sheet name
            with pd.ExcelFile(file_path) as xls:
                sheet_names = xls.sheet_names
                target_sheet = 'Results' if 'Results' in sheet_names else sheet_names[0]
            
            # Read only first few rows for quick analysis
            df = pd.read_excel(file_path, sheet_name=target_sheet, nrows=50)
            
            info = {
                'year_range': None,
                'models': []
            }
            
            # Find year column and range
            year_column = None
            for col in df.columns:
                if 'year' in str(col).lower():
                    year_column = col
                    break
            
            if year_column:
                years = pd.to_numeric(df[year_column], errors='coerce').dropna()
                if not years.empty:
                    info['year_range'] = {
                        'min': int(years.min()),
                        'max': int(years.max())
                    }
            
            # Identify model columns
            exclude_patterns = ['year', 'years', 'unnamed', 'index', 'id', 'date', 'time']
            models = []
            
            for col in df.columns:
                if col == year_column:
                    continue
                
                col_str = str(col).lower().strip()
                if any(pattern in col_str for pattern in exclude_patterns):
                    continue
                
                if col_str.startswith('unnamed') or col_str == '' or col_str.isdigit():
                    continue
                
                # Check if column has numeric data
                try:
                    col_data = pd.to_numeric(df[col], errors='coerce')
                    if not col_data.isna().all():
                        models.append(str(col))
                except:
                    continue
            
            info['models'] = models
            return info
            
        except Exception as e:
            logger.debug(f"Quick analysis failed for {file_path}: {e}")
            return {'year_range': None, 'models': []}
    
    def get_scenario_data(self, scenario_name: str, filters: FilterConfig = None) -> Dict[str, Any]:
        """Get comprehensive scenario data with dynamic filtering"""
        try:
            scenario_path = os.path.join(self.results_path, scenario_name)
            if not os.path.exists(scenario_path):
                return {'error': f"Scenario '{scenario_name}' not found"}
            
            # Initialize filters
            if filters is None:
                filters = FilterConfig()
            
            logger.info(f"Loading scenario {scenario_name} with filters: {filters}")
            
            # Get all Excel files in scenario directory
            excel_files = [
                f for f in os.listdir(scenario_path)
                if f.endswith('.xlsx') and not f.startswith('_') and not f.startswith('~')
            ]
            
            if not excel_files:
                return {'error': f"No data files found in scenario '{scenario_name}'"}
            
            sectors_data = {}
            all_years = set()
            all_models = set()
            
            # Process each sector file
            for excel_file in excel_files:
                sector_name = os.path.splitext(excel_file)[0]
                
                # Apply sector filtering if specified
                if filters.selected_sectors and sector_name not in filters.selected_sectors:
                    continue
                
                file_path = os.path.join(scenario_path, excel_file)
                sector_data = self._load_and_process_sector_data(
                    file_path, 
                    sector_name, 
                    filters
                )
                
                if sector_data:
                    sectors_data[sector_name] = sector_data
                    all_years.update(sector_data.years)
                    all_models.update(sector_data.models)
            
            if not sectors_data:
                return {'error': 'No valid sector data found with applied filters'}
            
            # Determine comprehensive year range
            year_range = {
                'min': min(all_years) if all_years else 2025,
                'max': max(all_years) if all_years else 2037
            }
            
            # Convert to response format
            response_data = {
                'scenario_name': scenario_name,
                'sectors': {},
                'sector_list': list(sectors_data.keys()),
                'year_range': year_range,
                'available_models': list(all_models),
                'unit': filters.unit,
                'filters_applied': {
                    'unit': filters.unit,
                    'start_year': filters.start_year,
                    'end_year': filters.end_year,
                    'selected_sectors': filters.selected_sectors,
                    'selected_models': filters.selected_models
                },
                'total_sectors': len(sectors_data),
                'has_data': True
            }
            
            # Convert sector data to response format
            for sector_name, sector_data in sectors_data.items():
                response_data['sectors'][sector_name] = {
                    'sector': sector_data.name,
                    'years': sector_data.years,
                    'models': sector_data.models,
                    **sector_data.data
                }
            
            logger.info(f"Successfully loaded {len(sectors_data)} sectors for scenario {scenario_name}")
            return response_data
            
        except Exception as e:
            logger.exception(f"Error getting scenario data for {scenario_name}: {e}")
            return {'error': str(e)}
    
    def _load_and_process_sector_data(self, file_path: str, sector_name: str, 
                                    filters: FilterConfig) -> Optional[SectorData]:
        """Load and process individual sector data with comprehensive filtering"""
        try:
            # Determine sheet name
            with pd.ExcelFile(file_path) as xls:
                sheet_names = xls.sheet_names
                target_sheet = 'Results' if 'Results' in sheet_names else sheet_names[0]
            
            df = pd.read_excel(file_path, sheet_name=target_sheet)
            
            # Find year column
            year_column = None
            for col in df.columns:
                if 'year' in str(col).lower():
                    year_column = col
                    break
            
            if not year_column:
                logger.warning(f"No year column found in {file_path}")
                return None
            
            # Clean and validate years
            df[year_column] = pd.to_numeric(df[year_column], errors='coerce')
            df = df.dropna(subset=[year_column])
            df[year_column] = df[year_column].astype(int)
            
            # Apply year filtering
            if filters.start_year and filters.end_year:
                df = df[(df[year_column] >= filters.start_year) & (df[year_column] <= filters.end_year)]
            elif filters.start_year:
                df = df[df[year_column] >= filters.start_year]
            elif filters.end_year:
                df = df[df[year_column] <= filters.end_year]
            
            if df.empty:
                logger.warning(f"No data after year filtering for {sector_name}")
                return None
            
            df = df.sort_values(year_column)
            years = df[year_column].tolist()
            
            # Identify model columns dynamically
            model_columns = self._identify_model_columns(df, year_column)
            
            # Apply model filtering if specified
            if filters.selected_models:
                model_columns = [m for m in model_columns if m in filters.selected_models]
            
            if not model_columns:
                logger.warning(f"No valid model columns found for {sector_name}")
                return None
            
            # Process data with unit conversion
            unit_factor = self.unit_factors.get(filters.unit, self.unit_factors['TWh'])
            processed_data = {}
            
            for model in model_columns:
                model_values = []
                for value in df[model]:
                    try:
                        # Convert from base unit (assumed to be in file) to target unit
                        num_value = float(value) if pd.notnull(value) else 0
                        # Assuming data in file is in TWh, convert to target unit
                        source_factor = self.unit_factors['TWh']
                        converted_value = (num_value * source_factor) / unit_factor
                        model_values.append(round(converted_value, 6))
                    except:
                        model_values.append(0)
                
                processed_data[model] = model_values
            
            return SectorData(
                name=sector_name,
                years=years,
                models=model_columns,
                data=processed_data,
                metadata={
                    'file_path': file_path,
                    'original_unit': 'TWh',  # Assumption
                    'converted_unit': filters.unit,
                    'data_points': len(years)
                }
            )
            
        except Exception as e:
            logger.warning(f"Error loading sector data from {file_path}: {e}")
            return None
    
    def _identify_model_columns(self, df: pd.DataFrame, year_column: str) -> List[str]:
        """Dynamically identify model columns in the DataFrame"""
        exclude_patterns = ['year', 'years', 'unnamed', 'index', 'id', 'date', 'time', 'total', 'sum']
        model_columns = []
        
        for col in df.columns:
            if col == year_column:
                continue
            
            col_str = str(col).lower().strip()
            
            # Skip excluded patterns
            if any(pattern in col_str for pattern in exclude_patterns):
                continue
            
            # Skip unnamed or empty columns
            if col_str.startswith('unnamed') or col_str == '' or col_str.isdigit():
                continue
            
            # Check if column has numeric data
            try:
                col_data = pd.to_numeric(df[col], errors='coerce')
                non_null_data = col_data.dropna()
                
                # Require at least some numeric data
                if len(non_null_data) > 0:
                    model_columns.append(str(col).strip())
            except:
                continue
        
        return model_columns
    
    # ========== CHART GENERATION METHODS ==========
    
    def generate_sector_chart_data(self, scenario_name: str, sector_name: str, 
                                 chart_type: str = "line", filters: FilterConfig = None) -> Dict[str, Any]:
        """Generate chart data for sector analysis using plot_utils"""
        try:
            if filters is None:
                filters = FilterConfig()
            
            # Get scenario data
            scenario_data = self.get_scenario_data(scenario_name, filters)
            if 'error' in scenario_data:
                return scenario_data
            
            if sector_name not in scenario_data['sectors']:
                return {'error': f'Sector {sector_name} not found in scenario'}
            
            sector_data = scenario_data['sectors'][sector_name]
            
            # Apply year range filtering
            year_range = None
            if filters.start_year or filters.end_year:
                year_range = (filters.start_year, filters.end_year)
            
            # Generate chart using plot utils
            result = self.plot_utils.create_sector_chart_data(
                scenario_name=scenario_name,
                sector_name=sector_name,
                sector_data=sector_data,
                chart_type=chart_type,
                unit=filters.unit,
                year_range=year_range
            )
            
            return result
            
        except Exception as e:
            logger.exception(f"Error generating sector chart data: {e}")
            return {'error': str(e)}
    
    def generate_sector_comparison_chart_data(self, scenario_name: str, sectors: List[str], 
                                            selected_models: Dict[str, str] = None,
                                            chart_type: str = "line", 
                                            filters: FilterConfig = None) -> Dict[str, Any]:
        """Generate chart data for sector comparison using plot_utils"""
        try:
            if filters is None:
                filters = FilterConfig()
            
            # Get scenario data
            scenario_data = self.get_scenario_data(scenario_name, filters)
            if 'error' in scenario_data:
                return scenario_data
            
            # Extract sectors data
            sectors_data = {}
            for sector in sectors:
                if sector in scenario_data['sectors']:
                    sectors_data[sector] = scenario_data['sectors'][sector]
            
            if not sectors_data:
                return {'error': 'No valid sectors found for comparison'}
            
            # Use provided model selection or default to first model
            if not selected_models:
                selected_models = {}
                for sector, sector_data in sectors_data.items():
                    if sector_data['models']:
                        selected_models[sector] = sector_data['models'][0]
            
            # Apply year range filtering
            year_range = None
            if filters.start_year or filters.end_year:
                year_range = (filters.start_year, filters.end_year)
            
            # Generate chart using plot utils
            result = self.plot_utils.create_sector_comparison_chart_data(
                scenario_name=scenario_name,
                sectors_data=sectors_data,
                selected_models=selected_models,
                chart_type=chart_type,
                unit=filters.unit,
                year_range=year_range
            )
            
            return result
            
        except Exception as e:
            logger.exception(f"Error generating sector comparison chart: {e}")
            return {'error': str(e)}
    
    def generate_consolidated_chart_data(self, scenario_name: str, 
                                       chart_type: str = "stacked_bar",
                                       filters: FilterConfig = None) -> Dict[str, Any]:
        """Generate consolidated chart data using plot_utils"""
        try:
            if filters is None:
                filters = FilterConfig()
            
            # Get consolidated results
            consolidated_data = self._get_cached_consolidated_results(scenario_name)
            
            if not consolidated_data:
                return {'error': 'No consolidated results found. Please generate consolidated results first.'}
            
            # Generate chart using plot utils
            result = self.plot_utils.create_consolidated_electricity_chart_data(
                consolidated_data=consolidated_data,
                chart_type=chart_type,
                unit=filters.unit
            )
            
            return result
            
        except Exception as e:
            logger.exception(f"Error generating consolidated chart: {e}")
            return {'error': str(e)}
    
    def generate_td_losses_chart_data(self, scenario_name: str) -> Dict[str, Any]:
        """Generate T&D losses chart data using plot_utils"""
        try:
            # Get T&D losses configuration
            td_config = self.get_td_losses_configuration(scenario_name)
            
            if 'error' in td_config:
                return td_config
            
            td_losses_data = td_config.get('td_losses', [])
            
            if not td_losses_data:
                return {'error': 'No T&D losses configuration found'}
            
            # Generate chart using plot utils
            result = self.plot_utils.create_td_losses_configuration_chart_data(td_losses_data)
            
            return result
            
        except Exception as e:
            logger.exception(f"Error generating T&D losses chart: {e}")
            return {'error': str(e)}
    
    # ========== CONFIGURATION MANAGEMENT ==========
    
    def save_model_selection(self, scenario_name: str, model_config: Dict[str, str]) -> Dict[str, Any]:
        """Save model selection configuration"""
        try:
            config_file = os.path.join(self.config_path, f"{scenario_name}_model_selection.json")
            
            config_data = {
                'scenario_name': scenario_name,
                'model_selection': model_config,
                'saved_at': datetime.now().isoformat(),
                'saved_by': 'demand_visualization_service'
            }
            
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            logger.info(f"Saved model selection for scenario {scenario_name}: {len(model_config)} sectors")
            return {'success': True, 'message': 'Model selection saved successfully'}
            
        except Exception as e:
            logger.exception(f"Error saving model selection: {e}")
            return {'error': str(e)}
    
    def get_model_selection(self, scenario_name: str) -> Dict[str, Any]:
        """Get saved model selection configuration"""
        try:
            config_file = os.path.join(self.config_path, f"{scenario_name}_model_selection.json")
            
            if not os.path.exists(config_file):
                return {'model_selection': {}, 'message': 'No saved configuration found'}
            
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            return {
                'model_selection': config.get('model_selection', {}),
                'saved_at': config.get('saved_at'),
                'success': True
            }
            
        except Exception as e:
            logger.exception(f"Error getting model selection: {e}")
            return {'error': str(e)}
    
    def save_td_losses_configuration(self, scenario_name: str, td_losses: List[Dict]) -> Dict[str, Any]:
        """Save T&D losses configuration with validation"""
        try:
            # Validate T&D losses data
            validated_losses = []
            for loss in td_losses:
                try:
                    year = int(loss.get('year', 0))
                    loss_pct = float(loss.get('loss_percentage', 0))
                    
                    if year > 0 and 0 <= loss_pct <= 100:
                        validated_losses.append({
                            'year': year,
                            'loss_percentage': round(loss_pct, 2)
                        })
                except ValueError:
                    continue
            
            if not validated_losses:
                return {'error': 'No valid T&D losses data provided'}
            
            # Sort by year
            validated_losses.sort(key=lambda x: x['year'])
            
            config_file = os.path.join(self.config_path, f"{scenario_name}_td_losses.json")
            
            config_data = {
                'scenario_name': scenario_name,
                'td_losses': validated_losses,
                'saved_at': datetime.now().isoformat()
            }
            
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            logger.info(f"Saved T&D losses for scenario {scenario_name}: {len(validated_losses)} points")
            return {'success': True, 'message': 'T&D losses saved successfully'}
            
        except Exception as e:
            logger.exception(f"Error saving T&D losses: {e}")
            return {'error': str(e)}
    
    def get_td_losses_configuration(self, scenario_name: str) -> Dict[str, Any]:
        """Get saved T&D losses configuration"""
        try:
            config_file = os.path.join(self.config_path, f"{scenario_name}_td_losses.json")
            
            if not os.path.exists(config_file):
                return {'td_losses': [], 'message': 'No saved T&D losses found'}
            
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            return {
                'td_losses': config.get('td_losses', []),
                'saved_at': config.get('saved_at'),
                'success': True
            }
            
        except Exception as e:
            logger.exception(f"Error getting T&D losses: {e}")
            return {'error': str(e)}
    
    # ========== CONSOLIDATED RESULTS GENERATION ==========
    
    def generate_consolidated_results(self, scenario_name: str, model_selection: Dict[str, str], 
                                    td_losses: List[Dict], filters: FilterConfig = None) -> Dict[str, Any]:
        """Generate comprehensive consolidated electricity demand results"""
        try:
            if filters is None:
                filters = FilterConfig()
            
            logger.info(f"Generating consolidated results for {scenario_name}")
            
            # Validate inputs
            if not model_selection:
                return {'error': 'Model selection configuration required'}
            
            if not td_losses:
                return {'error': 'T&D losses configuration required'}
            
            # Get scenario data
            scenario_data = self.get_scenario_data(scenario_name, filters)
            if 'error' in scenario_data:
                return scenario_data
            
            # Check if all selected sectors have data
            missing_sectors = []
            for sector in model_selection.keys():
                if sector not in scenario_data['sectors']:
                    missing_sectors.append(sector)
            
            if missing_sectors:
                return {'error': f'Missing data for sectors: {", ".join(missing_sectors)}'}
            
            # Determine year range
            start_year = filters.start_year or scenario_data['year_range']['min']
            end_year = filters.end_year or scenario_data['year_range']['max']
            years = list(range(start_year, end_year + 1))
            
            # Generate consolidated data
            consolidated_data = self._generate_consolidated_electricity_data(
                scenario_data['sectors'],
                model_selection,
                td_losses,
                years,
                filters.unit
            )
            
            # Calculate summary statistics
            summary_stats = self._calculate_summary_statistics(consolidated_data, filters.unit)
            
            # Save results for future reference
            self._save_consolidated_results(scenario_name, consolidated_data, {
                'model_selection': model_selection,
                'td_losses': td_losses,
                'filters': {
                    'unit': filters.unit,
                    'start_year': start_year,
                    'end_year': end_year
                },
                'summary_statistics': summary_stats,
                'generation_timestamp': datetime.now().isoformat()
            })
            
            return {
                'success': True,
                'consolidated_data': consolidated_data,
                'metadata': {
                    'scenario_name': scenario_name,
                    'unit': filters.unit,
                    'year_range': {'start': start_year, 'end': end_year},
                    'total_years': len(years),
                    'total_sectors': len(model_selection),
                    'summary_statistics': summary_stats
                }
            }
            
        except Exception as e:
            logger.exception(f"Error generating consolidated results: {e}")
            return {'error': str(e)}
    
    def _generate_consolidated_electricity_data(self, sectors_data: Dict, 
                                              model_selection: Dict[str, str],
                                              td_losses: List[Dict], 
                                              years: List[int], 
                                              unit: str) -> List[Dict]:
        """Generate consolidated electricity data with proper T&D losses calculation"""
        try:
            # Interpolate T&D losses for all years
            td_losses_interpolated = self._interpolate_td_losses(td_losses, years)
            
            # Unit conversion factor
            unit_factor = self.unit_factors.get(unit, self.unit_factors['TWh'])
            
            consolidated_data = []
            
            for year in years:
                year_data = {'Year': year}
                total_gross_demand = 0
                
                # Process each sector with selected model
                for sector, selected_model in model_selection.items():
                    if sector not in sectors_data:
                        continue
                    
                    sector_data = sectors_data[sector]
                    demand_value = 0
                    
                    # Get demand value for this year
                    if year in sector_data['years']:
                        year_index = sector_data['years'].index(year)
                        if (selected_model in sector_data and 
                            year_index < len(sector_data[selected_model])):
                            demand_value = sector_data[selected_model][year_index]
                    
                    # Store sector demand with clean name
                    clean_sector_name = self._format_sector_name_for_table(sector)
                    year_data[clean_sector_name] = round(demand_value, 3)
                    total_gross_demand += demand_value
                
                # Calculate T&D losses for electricity
                loss_percentage = td_losses_interpolated.get(year, 0)
                loss_fraction = loss_percentage / 100
                
                # Electricity T&D calculation: Net = Gross / (1 - loss_fraction)
                if loss_fraction < 1:
                    total_net_demand = total_gross_demand / (1 - loss_fraction)
                    td_loss_amount = total_net_demand - total_gross_demand
                else:
                    total_net_demand = total_gross_demand
                    td_loss_amount = 0
                
                # Add totals and losses
                year_data.update({
                    'Total_Gross_Demand': round(total_gross_demand, 3),
                    'TD_Losses': round(max(0, td_loss_amount), 3),
                    'Total_Net_Demand': round(max(0, total_net_demand), 3),
                    'Loss_Percentage': round(loss_percentage, 2)
                })
                
                consolidated_data.append(year_data)
            
            return consolidated_data
            
        except Exception as e:
            logger.error(f"Error generating consolidated electricity data: {e}")
            raise
    
    def _interpolate_td_losses(self, td_losses: List[Dict], target_years: List[int]) -> Dict[int, float]:
        """Interpolate T&D losses for target years"""
        if not td_losses:
            return {year: 0 for year in target_years}
        
        # Sort by year
        sorted_losses = sorted(td_losses, key=lambda x: x['year'])
        interpolated = {}
        
        for year in target_years:
            if year <= sorted_losses[0]['year']:
                interpolated[year] = sorted_losses[0]['loss_percentage']
            elif year >= sorted_losses[-1]['year']:
                interpolated[year] = sorted_losses[-1]['loss_percentage']
            else:
                # Linear interpolation
                for i in range(len(sorted_losses) - 1):
                    if sorted_losses[i]['year'] <= year <= sorted_losses[i + 1]['year']:
                        x1, y1 = sorted_losses[i]['year'], sorted_losses[i]['loss_percentage']
                        x2, y2 = sorted_losses[i + 1]['year'], sorted_losses[i + 1]['loss_percentage']
                        
                        slope = (y2 - y1) / (x2 - x1)
                        interpolated[year] = y1 + slope * (year - x1)
                        break
        
        return interpolated
    
    def _format_sector_name_for_table(self, sector_name: str) -> str:
        """Format sector name for table display"""
        return (sector_name.replace('_', ' ')
                          .replace('-', ' ')
                          .replace('  ', ' ')
                          .strip()
                          .title())
    
    def _calculate_summary_statistics(self, consolidated_data: List[Dict], unit: str) -> Dict[str, Any]:
        """Calculate summary statistics for consolidated data"""
        try:
            if not consolidated_data:
                return {}
            
            df = pd.DataFrame(consolidated_data)
            
            # Basic statistics
            total_years = len(consolidated_data)
            start_year = consolidated_data[0]['Year']
            end_year = consolidated_data[-1]['Year']
            
            # Demand statistics
            gross_demands = df['Total_Gross_Demand'].tolist()
            net_demands = df['Total_Net_Demand'].tolist()
            td_losses = df['TD_Losses'].tolist()
            
            # Growth calculations
            gross_growth = ((gross_demands[-1] - gross_demands[0]) / gross_demands[0] * 100) if gross_demands[0] > 0 else 0
            net_growth = ((net_demands[-1] - net_demands[0]) / net_demands[0] * 100) if net_demands[0] > 0 else 0
            
            # Average loss percentage
            loss_percentages = []
            for row in consolidated_data:
                loss_pct = row['Loss_Percentage']
                if isinstance(loss_pct, (int, float)):
                    loss_percentages.append(loss_pct)
            
            avg_loss_percentage = sum(loss_percentages) / len(loss_percentages) if loss_percentages else 0
            
            return {
                'total_years': total_years,
                'year_range': {'start': start_year, 'end': end_year},
                'gross_demand': {
                    'min': round(min(gross_demands), 3),
                    'max': round(max(gross_demands), 3),
                    'avg': round(sum(gross_demands) / len(gross_demands), 3),
                    'growth_percent': round(gross_growth, 2)
                },
                'net_demand': {
                    'min': round(min(net_demands), 3),
                    'max': round(max(net_demands), 3),
                    'avg': round(sum(net_demands) / len(net_demands), 3),
                    'growth_percent': round(net_growth, 2)
                },
                'td_losses': {
                    'min': round(min(td_losses), 3),
                    'max': round(max(td_losses), 3),
                    'avg': round(sum(td_losses) / len(td_losses), 3),
                    'avg_percentage': round(avg_loss_percentage, 2)
                },
                'unit': unit
            }
            
        except Exception as e:
            logger.warning(f"Error calculating summary statistics: {e}")
            return {}
    
    def _save_consolidated_results(self, scenario_name: str, 
                                 consolidated_data: List[Dict], 
                                 metadata: Dict) -> None:
        """Save consolidated results for future reference"""
        try:
            results_file = os.path.join(self.config_path, f"{scenario_name}_consolidated_results.json")
            
            results_data = {
                'scenario_name': scenario_name,
                'consolidated_data': consolidated_data,
                'metadata': metadata,
                'saved_at': datetime.now().isoformat()
            }
            
            with open(results_file, 'w') as f:
                json.dump(results_data, f, indent=2)
            
            # Also save as CSV for easy access
            csv_file = os.path.join(self.config_path, f"{scenario_name}_consolidated_results.csv")
            df = pd.DataFrame(consolidated_data)
            df.to_csv(csv_file, index=False)
            
            logger.info(f"Saved consolidated results for {scenario_name}")
            
        except Exception as e:
            logger.warning(f"Error saving consolidated results: {e}")
    
    def _get_cached_consolidated_results(self, scenario_name: str) -> Optional[List[Dict]]:
        """Get cached consolidated results if available"""
        try:
            results_file = os.path.join(self.config_path, f"{scenario_name}_consolidated_results.json")
            
            if not os.path.exists(results_file):
                return None
            
            with open(results_file, 'r') as f:
                results_data = json.load(f)
            
            return results_data.get('consolidated_data', [])
            
        except Exception as e:
            logger.warning(f"Error loading cached consolidated results: {e}")
            return None
    
    # ========== EXPORT FUNCTIONS ==========
    
    def export_scenario_data(self, scenario_name: str, filters: FilterConfig = None) -> str:
        """Export scenario data to CSV"""
        try:
            if filters is None:
                filters = FilterConfig()
            
            scenario_data = self.get_scenario_data(scenario_name, filters)
            if 'error' in scenario_data:
                raise ValueError(scenario_data['error'])
            
            # Create export DataFrame
            export_data = []
            for sector, data in scenario_data['sectors'].items():
                for i, year in enumerate(data['years']):
                    row = {'Sector': sector, 'Year': year}
                    for model in data['models']:
                        if model in data and i < len(data[model]):
                            row[model] = data[model][i]
                    export_data.append(row)
            
            df = pd.DataFrame(export_data)
            
            # Save export file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{scenario_name}_scenario_export_{timestamp}.csv"
            export_path = os.path.join(self.config_path, filename)
            df.to_csv(export_path, index=False)
            
            return export_path
            
        except Exception as e:
            logger.exception(f"Error exporting scenario data: {e}")
            raise
    
    def export_consolidated_data(self, scenario_name: str) -> str:
        """Export consolidated data to CSV"""
        try:
            consolidated_data = self._get_cached_consolidated_results(scenario_name)
            
            if not consolidated_data:
                raise ValueError("No consolidated results found. Please generate first.")
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{scenario_name}_consolidated_export_{timestamp}.csv"
            export_path = os.path.join(self.config_path, filename)
            
            df = pd.DataFrame(consolidated_data)
            df.to_csv(export_path, index=False)
            
            return export_path
            
        except Exception as e:
            logger.exception(f"Error exporting consolidated data: {e}")
            raise
    
    # ========== ANALYSIS FUNCTIONS ==========
    
    def get_analysis_summary(self, scenario_name: str, filters: FilterConfig = None) -> Dict[str, Any]:
        """Get comprehensive analysis summary"""
        try:
            if filters is None:
                filters = FilterConfig()
            
            scenario_data = self.get_scenario_data(scenario_name, filters)
            if 'error' in scenario_data:
                return scenario_data
            
            summary = {
                'scenario_name': scenario_name,
                'total_sectors': len(scenario_data['sectors']),
                'year_range': scenario_data['year_range'],
                'available_models': scenario_data['available_models'],
                'unit': scenario_data['unit'],
                'sector_analysis': {},
                'model_analysis': {},
                'overall_trends': {}
            }
            
            # Analyze each sector
            for sector, data in scenario_data['sectors'].items():
                sector_summary = {
                    'models_count': len(data['models']),
                    'years_count': len(data['years']),
                    'model_ranges': {},
                    'data_quality': {}
                }
                
                # Calculate ranges and quality metrics for each model
                for model in data['models']:
                    if model in data:
                        values = [v for v in data[model] if v > 0]
                        if values:
                            sector_summary['model_ranges'][model] = {
                                'min': round(min(values), 3),
                                'max': round(max(values), 3),
                                'avg': round(sum(values) / len(values), 3),
                                'growth_rate': self._calculate_growth_rate(data[model])
                            }
                            
                            # Data quality metrics
                            total_points = len(data[model])
                            non_zero_points = len(values)
                            sector_summary['data_quality'][model] = {
                                'completeness': round(non_zero_points / total_points * 100, 1),
                                'consistency': self._calculate_consistency_score(data[model])
                            }
                
                summary['sector_analysis'][sector] = sector_summary
            
            # Model performance analysis across sectors
            model_performance = {}
            for model in scenario_data['available_models']:
                appearances = 0
                total_growth_rates = []
                
                for sector_data in scenario_data['sectors'].values():
                    if model in sector_data['models'] and model in sector_data:
                        appearances += 1
                        growth_rate = self._calculate_growth_rate(sector_data[model])
                        if growth_rate is not None:
                            total_growth_rates.append(growth_rate)
                
                if appearances > 0:
                    model_performance[model] = {
                        'sector_appearances': appearances,
                        'avg_growth_rate': round(sum(total_growth_rates) / len(total_growth_rates), 2) if total_growth_rates else 0,
                        'coverage': round(appearances / len(scenario_data['sectors']) * 100, 1)
                    }
            
            summary['model_analysis'] = model_performance
            
            # Overall trends
            all_values = []
            all_growth_rates = []
            
            for sector_data in scenario_data['sectors'].values():
                for model in sector_data['models']:
                    if model in sector_data:
                        values = [v for v in sector_data[model] if v > 0]
                        all_values.extend(values)
                        
                        growth_rate = self._calculate_growth_rate(sector_data[model])
                        if growth_rate is not None:
                            all_growth_rates.append(growth_rate)
            
            if all_values:
                summary['overall_trends'] = {
                    'total_data_points': len(all_values),
                    'overall_min': round(min(all_values), 3),
                    'overall_max': round(max(all_values), 3),
                    'overall_avg': round(sum(all_values) / len(all_values), 3),
                    'avg_growth_rate': round(sum(all_growth_rates) / len(all_growth_rates), 2) if all_growth_rates else 0,
                    'data_spread': round(max(all_values) - min(all_values), 3)
                }
            
            return summary
            
        except Exception as e:
            logger.exception(f"Error getting analysis summary: {e}")
            return {'error': str(e)}
    
    def _calculate_growth_rate(self, values: List[float]) -> Optional[float]:
        """Calculate annual growth rate for a series of values"""
        try:
            clean_values = [v for v in values if v > 0]
            if len(clean_values) < 2:
                return None
            
            first_value = clean_values[0]
            last_value = clean_values[-1]
            years = len(clean_values) - 1
            
            if first_value == 0:
                return None
            
            # Compound annual growth rate (CAGR)
            growth_rate = ((last_value / first_value) ** (1 / years) - 1) * 100
            return round(growth_rate, 2)
            
        except Exception:
            return None
    
    def _calculate_consistency_score(self, values: List[float]) -> float:
        """Calculate consistency score based on data smoothness"""
        try:
            if len(values) < 3:
                return 100.0
            
            # Calculate coefficient of variation of differences
            differences = []
            for i in range(1, len(values)):
                if values[i] > 0 and values[i-1] > 0:
                    diff = abs(values[i] - values[i-1]) / values[i-1]
                    differences.append(diff)
            
            if not differences:
                return 100.0
            
            mean_diff = sum(differences) / len(differences)
            if mean_diff == 0:
                return 100.0
            
            variance = sum([(d - mean_diff) ** 2 for d in differences]) / len(differences)
            cv = (variance ** 0.5) / mean_diff
            
            # Convert to consistency score (lower CV = higher consistency)
            consistency = max(0, 100 - (cv * 100))
            return round(consistency, 1)
            
        except Exception:
            return 50.0  # Default medium consistency

# Utility function to create FilterConfig from request args
def create_filter_config_from_args(args: Dict) -> FilterConfig:
    """Create FilterConfig from request arguments"""
    return FilterConfig(
        unit=args.get('unit', 'TWh'),
        start_year=args.get('start_year', type=int),
        end_year=args.get('end_year', type=int),
        selected_sectors=args.getlist('sectors') if hasattr(args, 'getlist') else args.get('sectors', []),
        selected_models=args.getlist('models') if hasattr(args, 'getlist') else args.get('models', [])
    )