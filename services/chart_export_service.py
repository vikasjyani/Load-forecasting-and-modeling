#!/usr/bin/env python3
"""
Chart Export Service
Comprehensive chart export functionality for various formats
"""

import json
import csv
import io
import base64
from typing import Dict, List, Optional, Union, Any
import logging
from pathlib import Path
import sys
from datetime import datetime

# Add utils to path
sys.path.append(str(Path(__file__).parent.parent / 'utils'))
from color_manager import ColorManager

logger = logging.getLogger(__name__)

class ChartExportService:
    """
    Service for exporting chart data in various formats
    Supports JSON, CSV, Excel, and image exports
    """
    
    def __init__(self):
        self.color_manager = ColorManager()
        
    def export_to_json(self, chart_data: Dict, 
                      filename: Optional[str] = None,
                      pretty_print: bool = True) -> Dict:
        """
        Export chart data to JSON format
        """
        try:
            if filename is None:
                filename = f"chart_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            # Ensure filename has .json extension
            if not filename.endswith('.json'):
                filename += '.json'
            
            # Convert to JSON string
            if pretty_print:
                json_str = json.dumps(chart_data, indent=2, ensure_ascii=False)
            else:
                json_str = json.dumps(chart_data, ensure_ascii=False)
            
            return {
                'success': True,
                'format': 'json',
                'filename': filename,
                'data': json_str,
                'size': len(json_str),
                'download_url': f'/api/download/{filename}'
            }
            
        except Exception as e:
            logger.error(f"Error exporting to JSON: {e}")
            return {
                'success': False,
                'error': str(e),
                'format': 'json'
            }
    
    def export_to_csv(self, chart_data: Dict, 
                     filename: Optional[str] = None) -> Dict:
        """
        Export chart data to CSV format
        """
        try:
            if filename is None:
                filename = f"chart_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            # Ensure filename has .csv extension
            if not filename.endswith('.csv'):
                filename += '.csv'
            
            # Extract data from chart structure
            csv_data = self._extract_tabular_data(chart_data)
            
            # Create CSV string
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write headers
            if csv_data and len(csv_data) > 0:
                headers = list(csv_data[0].keys())
                writer.writerow(headers)
                
                # Write data rows
                for row in csv_data:
                    writer.writerow([row.get(header, '') for header in headers])
            
            csv_str = output.getvalue()
            output.close()
            
            return {
                'success': True,
                'format': 'csv',
                'filename': filename,
                'data': csv_str,
                'size': len(csv_str),
                'download_url': f'/api/download/{filename}'
            }
            
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            return {
                'success': False,
                'error': str(e),
                'format': 'csv'
            }
    
    def export_to_excel(self, chart_data: Dict, 
                       filename: Optional[str] = None) -> Dict:
        """
        Export chart data to Excel format
        """
        try:
            import pandas as pd
            
            if filename is None:
                filename = f"chart_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
            # Ensure filename has .xlsx extension
            if not filename.endswith('.xlsx'):
                filename += '.xlsx'
            
            # Extract data from chart structure
            csv_data = self._extract_tabular_data(chart_data)
            
            if csv_data:
                # Create DataFrame
                df = pd.DataFrame(csv_data)
                
                # Create Excel file in memory
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Chart Data', index=False)
                    
                    # Add metadata sheet
                    metadata = {
                        'Chart Type': [chart_data.get('type', 'Unknown')],
                        'Title': [chart_data.get('options', {}).get('plugins', {}).get('title', {}).get('text', 'Untitled')],
                        'Export Date': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
                        'Data Points': [len(csv_data)]
                    }
                    pd.DataFrame(metadata).to_excel(writer, sheet_name='Metadata', index=False)
                
                excel_data = output.getvalue()
                output.close()
                
                # Convert to base64 for transfer
                excel_b64 = base64.b64encode(excel_data).decode('utf-8')
                
                return {
                    'success': True,
                    'format': 'excel',
                    'filename': filename,
                    'data': excel_b64,
                    'size': len(excel_data),
                    'download_url': f'/api/download/{filename}'
                }
            else:
                return {
                    'success': False,
                    'error': 'No data to export',
                    'format': 'excel'
                }
                
        except ImportError:
            return {
                'success': False,
                'error': 'pandas and openpyxl required for Excel export',
                'format': 'excel'
            }
        except Exception as e:
            logger.error(f"Error exporting to Excel: {e}")
            return {
                'success': False,
                'error': str(e),
                'format': 'excel'
            }
    
    def export_chart_config(self, chart_data: Dict, 
                          filename: Optional[str] = None) -> Dict:
        """
        Export chart configuration for recreation
        """
        try:
            if filename is None:
                filename = f"chart_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            # Ensure filename has .json extension
            if not filename.endswith('.json'):
                filename += '.json'
            
            # Create configuration object
            config = {
                'chart_type': chart_data.get('type', 'line'),
                'title': chart_data.get('options', {}).get('plugins', {}).get('title', {}).get('text', ''),
                'data_structure': self._analyze_data_structure(chart_data),
                'color_scheme': self._extract_color_scheme(chart_data),
                'options': chart_data.get('options', {}),
                'export_metadata': {
                    'export_date': datetime.now().isoformat(),
                    'version': '1.0',
                    'source': 'KSEB Load Forecasting Platform'
                }
            }
            
            config_str = json.dumps(config, indent=2, ensure_ascii=False)
            
            return {
                'success': True,
                'format': 'config',
                'filename': filename,
                'data': config_str,
                'size': len(config_str),
                'download_url': f'/api/download/{filename}'
            }
            
        except Exception as e:
            logger.error(f"Error exporting chart config: {e}")
            return {
                'success': False,
                'error': str(e),
                'format': 'config'
            }
    
    def export_multiple_formats(self, chart_data: Dict,
                              formats: List[str] = None,
                              base_filename: str = None) -> Dict:
        """
        Export chart data in multiple formats
        """
        if formats is None:
            formats = ['json', 'csv']
        
        if base_filename is None:
            base_filename = f"chart_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        results = {}
        
        for format_type in formats:
            if format_type == 'json':
                results['json'] = self.export_to_json(chart_data, f"{base_filename}.json")
            elif format_type == 'csv':
                results['csv'] = self.export_to_csv(chart_data, f"{base_filename}.csv")
            elif format_type == 'excel':
                results['excel'] = self.export_to_excel(chart_data, f"{base_filename}.xlsx")
            elif format_type == 'config':
                results['config'] = self.export_chart_config(chart_data, f"{base_filename}_config.json")
        
        # Summary
        successful_exports = [fmt for fmt, result in results.items() if result.get('success', False)]
        
        return {
            'success': len(successful_exports) > 0,
            'formats': successful_exports,
            'results': results,
            'total_exports': len(successful_exports)
        }
    
    def _extract_tabular_data(self, chart_data: Dict) -> List[Dict]:
        """
        Extract tabular data from chart structure
        """
        try:
            data_section = chart_data.get('data', {})
            labels = data_section.get('labels', [])
            datasets = data_section.get('datasets', [])
            
            if not labels or not datasets:
                return []
            
            # Create rows
            rows = []
            for i, label in enumerate(labels):
                row = {'label': label}
                
                for dataset in datasets:
                    dataset_label = dataset.get('label', 'Value')
                    dataset_data = dataset.get('data', [])
                    
                    if i < len(dataset_data):
                        row[dataset_label] = dataset_data[i]
                    else:
                        row[dataset_label] = None
                
                rows.append(row)
            
            return rows
            
        except Exception as e:
            logger.error(f"Error extracting tabular data: {e}")
            return []
    
    def _analyze_data_structure(self, chart_data: Dict) -> Dict:
        """
        Analyze the structure of chart data
        """
        try:
            data_section = chart_data.get('data', {})
            datasets = data_section.get('datasets', [])
            
            structure = {
                'labels_count': len(data_section.get('labels', [])),
                'datasets_count': len(datasets),
                'dataset_info': []
            }
            
            for i, dataset in enumerate(datasets):
                dataset_info = {
                    'index': i,
                    'label': dataset.get('label', f'Dataset {i+1}'),
                    'data_points': len(dataset.get('data', [])),
                    'chart_type': dataset.get('type', chart_data.get('type', 'line')),
                    'has_colors': 'backgroundColor' in dataset or 'borderColor' in dataset
                }
                structure['dataset_info'].append(dataset_info)
            
            return structure
            
        except Exception as e:
            logger.error(f"Error analyzing data structure: {e}")
            return {}
    
    def _extract_color_scheme(self, chart_data: Dict) -> Dict:
        """
        Extract color scheme from chart data
        """
        try:
            datasets = chart_data.get('data', {}).get('datasets', [])
            colors = {
                'background_colors': [],
                'border_colors': [],
                'theme': self.color_manager.get_current_theme()
            }
            
            for dataset in datasets:
                if 'backgroundColor' in dataset:
                    bg_color = dataset['backgroundColor']
                    if isinstance(bg_color, list):
                        colors['background_colors'].extend(bg_color)
                    else:
                        colors['background_colors'].append(bg_color)
                
                if 'borderColor' in dataset:
                    border_color = dataset['borderColor']
                    if isinstance(border_color, list):
                        colors['border_colors'].extend(border_color)
                    else:
                        colors['border_colors'].append(border_color)
            
            return colors
            
        except Exception as e:
            logger.error(f"Error extracting color scheme: {e}")
            return {}
    
    def create_export_summary(self, chart_data: Dict) -> Dict:
        """
        Create a summary of exportable data
        """
        try:
            tabular_data = self._extract_tabular_data(chart_data)
            data_structure = self._analyze_data_structure(chart_data)
            
            summary = {
                'chart_info': {
                    'type': chart_data.get('type', 'Unknown'),
                    'title': chart_data.get('options', {}).get('plugins', {}).get('title', {}).get('text', 'Untitled'),
                    'has_data': len(tabular_data) > 0
                },
                'data_summary': {
                    'total_rows': len(tabular_data),
                    'total_columns': len(tabular_data[0].keys()) if tabular_data else 0,
                    'datasets': data_structure.get('datasets_count', 0),
                    'data_points': data_structure.get('labels_count', 0)
                },
                'export_options': {
                    'available_formats': ['json', 'csv', 'excel', 'config'],
                    'recommended_formats': self._get_recommended_formats(chart_data),
                    'estimated_sizes': self._estimate_export_sizes(chart_data)
                }
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error creating export summary: {e}")
            return {
                'error': str(e),
                'chart_info': {'has_data': False}
            }
    
    def _get_recommended_formats(self, chart_data: Dict) -> List[str]:
        """
        Get recommended export formats based on chart type and data
        """
        chart_type = chart_data.get('type', 'line')
        data_size = len(self._extract_tabular_data(chart_data))
        
        recommended = ['json']  # Always recommend JSON
        
        if data_size > 0:
            recommended.append('csv')
            
        if data_size > 100:
            recommended.append('excel')
            
        if chart_type in ['heatmap', 'complex']:
            recommended.append('config')
            
        return recommended
    
    def _estimate_export_sizes(self, chart_data: Dict) -> Dict:
        """
        Estimate export file sizes
        """
        try:
            json_size = len(json.dumps(chart_data))
            tabular_data = self._extract_tabular_data(chart_data)
            
            # Rough estimates
            csv_size = len(tabular_data) * 50 if tabular_data else 0  # ~50 chars per row
            excel_size = csv_size * 2 if csv_size > 0 else 0  # Excel is roughly 2x CSV
            
            return {
                'json': f"{json_size / 1024:.1f} KB",
                'csv': f"{csv_size / 1024:.1f} KB" if csv_size > 0 else "N/A",
                'excel': f"{excel_size / 1024:.1f} KB" if excel_size > 0 else "N/A"
            }
            
        except Exception:
            return {
                'json': "Unknown",
                'csv': "Unknown",
                'excel': "Unknown"
            }

# Global instance
chart_export_service = ChartExportService()

# Utility functions for direct use
def export_to_json(chart_data: Dict, 
                  filename: Optional[str] = None,
                  pretty_print: bool = True) -> Dict:
    """Direct function to export to JSON"""
    return chart_export_service.export_to_json(chart_data, filename, pretty_print)

def export_to_csv(chart_data: Dict, 
                 filename: Optional[str] = None) -> Dict:
    """Direct function to export to CSV"""
    return chart_export_service.export_to_csv(chart_data, filename)

def export_to_excel(chart_data: Dict, 
                   filename: Optional[str] = None) -> Dict:
    """Direct function to export to Excel"""
    return chart_export_service.export_to_excel(chart_data, filename)

def export_chart_config(chart_data: Dict, 
                       filename: Optional[str] = None) -> Dict:
    """Direct function to export chart config"""
    return chart_export_service.export_chart_config(chart_data, filename)

def export_multiple_formats(chart_data: Dict,
                          formats: List[str] = None,
                          base_filename: str = None) -> Dict:
    """Direct function to export in multiple formats"""
    return chart_export_service.export_multiple_formats(chart_data, formats, base_filename)

def create_export_summary(chart_data: Dict) -> Dict:
    """Direct function to create export summary"""
    return chart_export_service.create_export_summary(chart_data)