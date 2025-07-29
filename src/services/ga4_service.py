import os
import json
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
    RunRealtimeReportRequest
)
from google.auth.exceptions import DefaultCredentialsError
from src.models.user import db, GA4DataCache

class GA4Service:
    """Service for interacting with Google Analytics 4 Data API."""
    
    def __init__(self):
        self.client = None
        self.credentials_available = False
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the GA4 client with credentials."""
        try:
            # Check if credentials are available
            credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            if credentials_path and os.path.exists(credentials_path):
                self.client = BetaAnalyticsDataClient()
                self.credentials_available = True
                print("GA4 client initialized successfully")
            else:
                print("GA4 credentials not found, using mock data")
                self.credentials_available = False
        except Exception as e:
            print(f"Failed to initialize GA4 client: {str(e)}")
            self.credentials_available = False
    
    def _get_mock_data(self, metric_names: List[str], dimension_names: List[str] = None) -> Dict[str, Any]:
        """Generate mock data for testing when real credentials aren't available."""
        import random
        
        mock_data = {
            'dimension_headers': [],
            'metric_headers': [],
            'rows': []
        }
        
        # Add dimension headers
        if dimension_names:
            for dim in dimension_names:
                mock_data['dimension_headers'].append({'name': dim})
        
        # Add metric headers
        for metric in metric_names:
            mock_data['metric_headers'].append({
                'name': metric,
                'type': 'TYPE_INTEGER' if metric in ['activeUsers', 'sessions'] else 'TYPE_FLOAT'
            })
        
        # Generate mock rows
        if dimension_names and 'country' in dimension_names:
            countries = ['United States', 'Canada', 'United Kingdom', 'Germany', 'France']
            for country in countries:
                row = {
                    'dimension_values': [{'value': country}],
                    'metric_values': []
                }
                for metric in metric_names:
                    if metric == 'activeUsers':
                        value = random.randint(100, 5000)
                    elif metric == 'sessions':
                        value = random.randint(150, 6000)
                    elif metric == 'screenPageViews':
                        value = random.randint(200, 8000)
                    elif metric == 'bounceRate':
                        value = round(random.uniform(0.3, 0.8), 4)
                    elif metric == 'averageSessionDuration':
                        value = random.randint(120, 300)
                    elif metric == 'userEngagementDuration':
                        value = random.randint(60, 200)
                    else:
                        value = random.randint(50, 1000)
                    
                    row['metric_values'].append({'value': str(value)})
                
                mock_data['rows'].append(row)
        else:
            # Single row for overview metrics
            row = {'metric_values': []}
            for metric in metric_names:
                if metric == 'activeUsers':
                    value = random.randint(1000, 10000)
                elif metric == 'sessions':
                    value = random.randint(1500, 12000)
                elif metric == 'screenPageViews':
                    value = random.randint(2000, 15000)
                elif metric == 'bounceRate':
                    value = round(random.uniform(0.4, 0.7), 4)
                elif metric == 'averageSessionDuration':
                    value = random.randint(120, 300)
                elif metric == 'userEngagementDuration':
                    value = random.randint(80, 250)
                else:
                    value = random.randint(100, 5000)
                
                row['metric_values'].append({'value': str(value)})
            
            mock_data['rows'].append(row)
        
        return mock_data
    
    def get_overview_metrics(self, property_id: str, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """Get overview metrics for a GA4 property."""
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        metrics = [
            'activeUsers',
            'sessions', 
            'screenPageViews',  # Changed from 'pageviews' to GA4 standard
            'bounceRate',
            'averageSessionDuration'
        ]
        
        if self.credentials_available and self.client:
            try:
                request = RunReportRequest(
                    property=f"properties/{property_id}",
                    date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
                    metrics=[Metric(name=metric) for metric in metrics]
                )
                
                response = self.client.run_report(request)
                return self._format_response(response)
                
            except Exception as e:
                print(f"Error fetching GA4 data: {str(e)}")
                return self._get_mock_data(metrics)
        else:
            return self._get_mock_data(metrics)
    
    def get_traffic_sources(self, property_id: str, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """Get traffic sources data."""
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        metrics = ['sessions', 'activeUsers']
        dimensions = ['sessionDefaultChannelGrouping']
        
        if self.credentials_available and self.client:
            try:
                request = RunReportRequest(
                    property=f"properties/{property_id}",
                    date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
                    dimensions=[Dimension(name=dim) for dim in dimensions],
                    metrics=[Metric(name=metric) for metric in metrics],
                    limit=10
                )
                
                response = self.client.run_report(request)
                return self._format_response(response)
                
            except Exception as e:
                print(f"Error fetching traffic sources: {str(e)}")
                # Mock traffic sources
                mock_sources = ['Organic Search', 'Direct', 'Social', 'Referral', 'Email']
                return self._get_mock_traffic_sources(mock_sources)
        else:
            mock_sources = ['Organic Search', 'Direct', 'Social', 'Referral', 'Email']
            return self._get_mock_traffic_sources(mock_sources)
    
    def _get_mock_traffic_sources(self, sources: List[str]) -> Dict[str, Any]:
        """Generate mock traffic sources data."""
        import random
        
        mock_data = {
            'dimension_headers': [{'name': 'sessionDefaultChannelGrouping'}],
            'metric_headers': [
                {'name': 'sessions', 'type': 'TYPE_INTEGER'},
                {'name': 'activeUsers', 'type': 'TYPE_INTEGER'}
            ],
            'rows': []
        }
        
        for source in sources:
            sessions = random.randint(100, 2000)
            users = random.randint(80, int(sessions * 0.9))
            
            row = {
                'dimension_values': [{'value': source}],
                'metric_values': [
                    {'value': str(sessions)},
                    {'value': str(users)}
                ]
            }
            mock_data['rows'].append(row)
        
        return mock_data
    
    def get_page_performance(self, property_id: str, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """Get page performance data."""
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        metrics = ['screenPageViews', 'sessions', 'userEngagementDuration', 'bounceRate']
        dimensions = ['pagePath']
        
        if self.credentials_available and self.client:
            try:
                request = RunReportRequest(
                    property=f"properties/{property_id}",
                    date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
                    dimensions=[Dimension(name=dim) for dim in dimensions],
                    metrics=[Metric(name=metric) for metric in metrics],
                    limit=20,
                    order_bys=[{'metric': {'metric_name': 'pageviews'}, 'desc': True}]
                )
                
                response = self.client.run_report(request)
                return self._format_response(response)
                
            except Exception as e:
                print(f"Error fetching page performance: {str(e)}")
                return self._get_mock_page_data()
        else:
            return self._get_mock_page_data()
    
    def _get_mock_page_data(self) -> Dict[str, Any]:
        """Generate mock page performance data."""
        import random
        
        pages = ['/', '/about', '/services', '/contact', '/blog', '/products', '/pricing']
        
        mock_data = {
            'dimension_headers': [{'name': 'pagePath'}],
            'metric_headers': [
                {'name': 'screenPageViews', 'type': 'TYPE_INTEGER'},
                {'name': 'sessions', 'type': 'TYPE_INTEGER'},
                {'name': 'userEngagementDuration', 'type': 'TYPE_FLOAT'},
                {'name': 'bounceRate', 'type': 'TYPE_FLOAT'}
            ],
            'rows': []
        }
        
        for page in pages:
            pageviews = random.randint(50, 1000)
            sessions = random.randint(40, int(pageviews * 0.8))
            engagement_duration = random.randint(30, 300)
            bounce_rate = round(random.uniform(0.2, 0.8), 4)
            
            row = {
                'dimension_values': [{'value': page}],
                'metric_values': [
                    {'value': str(pageviews)},
                    {'value': str(sessions)},
                    {'value': str(engagement_duration)},
                    {'value': str(bounce_rate)}
                ]
            }
            mock_data['rows'].append(row)
        
        return mock_data
    
    def get_realtime_data(self, property_id: str) -> Dict[str, Any]:
        """Get real-time data."""
        metrics = ['activeUsers']
        
        if self.credentials_available and self.client:
            try:
                request = RunRealtimeReportRequest(
                    property=f"properties/{property_id}",
                    metrics=[Metric(name=metric) for metric in metrics]
                )
                
                response = self.client.run_realtime_report(request)
                return self._format_response(response)
                
            except Exception as e:
                print(f"Error fetching realtime data: {str(e)}")
                return self._get_mock_realtime_data()
        else:
            return self._get_mock_realtime_data()
    
    def _get_mock_realtime_data(self) -> Dict[str, Any]:
        """Generate mock real-time data."""
        import random
        
        return {
            'metric_headers': [{'name': 'activeUsers', 'type': 'TYPE_INTEGER'}],
            'rows': [{
                'metric_values': [{'value': str(random.randint(5, 50))}]
            }]
        }
    
    def _format_response(self, response) -> Dict[str, Any]:
        """Format GA4 API response to a consistent structure."""
        formatted_response = {
            'dimension_headers': [],
            'metric_headers': [],
            'rows': []
        }
        
        # Add dimension headers
        if hasattr(response, 'dimension_headers'):
            for header in response.dimension_headers:
                formatted_response['dimension_headers'].append({'name': header.name})
        
        # Add metric headers
        if hasattr(response, 'metric_headers'):
            for header in response.metric_headers:
                formatted_response['metric_headers'].append({
                    'name': header.name,
                    'type': header.type_.name if hasattr(header, 'type_') else 'TYPE_STRING'
                })
        
        # Add rows
        if hasattr(response, 'rows'):
            for row in response.rows:
                formatted_row = {
                    'dimension_values': [],
                    'metric_values': []
                }
                
                # Add dimension values
                if hasattr(row, 'dimension_values'):
                    for dim_value in row.dimension_values:
                        formatted_row['dimension_values'].append({'value': dim_value.value})
                
                # Add metric values
                if hasattr(row, 'metric_values'):
                    for metric_value in row.metric_values:
                        formatted_row['metric_values'].append({'value': metric_value.value})
                
                formatted_response['rows'].append(formatted_row)
        
        return formatted_response
    
    def cache_data(self, website_id: int, metric_name: str, data: Dict[str, Any], 
                   start_date: str, end_date: str, cache_hours: int = 4):
        """Cache GA4 data in the database."""
        try:
            # Clear existing cache for this metric and date range
            GA4DataCache.query.filter(
                GA4DataCache.website_id == website_id,
                GA4DataCache.metric_name == metric_name,
                GA4DataCache.date_range_start == datetime.strptime(start_date, '%Y-%m-%d').date(),
                GA4DataCache.date_range_end == datetime.strptime(end_date, '%Y-%m-%d').date()
            ).delete()
            
            # Cache new data
            expires_at = datetime.utcnow() + timedelta(hours=cache_hours)
            
            for row in data.get('rows', []):
                for i, metric_value in enumerate(row.get('metric_values', [])):
                    # Get dimension value if available
                    dimension_value = None
                    dimension_name = None
                    
                    if row.get('dimension_values') and data.get('dimension_headers'):
                        dimension_value = row['dimension_values'][0]['value']
                        dimension_name = data['dimension_headers'][0]['name']
                    
                    cache_entry = GA4DataCache(
                        website_id=website_id,
                        metric_name=metric_name,
                        dimension_name=dimension_name,
                        dimension_value=dimension_value,
                        metric_value=float(metric_value['value']),
                        date_range_start=datetime.strptime(start_date, '%Y-%m-%d').date(),
                        date_range_end=datetime.strptime(end_date, '%Y-%m-%d').date(),
                        expires_at=expires_at
                    )
                    
                    db.session.add(cache_entry)
            
            db.session.commit()
            print(f"Cached GA4 data for website {website_id}, metric {metric_name}")
            
        except Exception as e:
            db.session.rollback()
            print(f"Failed to cache GA4 data: {str(e)}")
    
    def get_cached_data(self, website_id: int, metric_name: str, 
                       start_date: str, end_date: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached GA4 data."""
        try:
            cached_entries = GA4DataCache.query.filter(
                GA4DataCache.website_id == website_id,
                GA4DataCache.metric_name == metric_name,
                GA4DataCache.date_range_start == datetime.strptime(start_date, '%Y-%m-%d').date(),
                GA4DataCache.date_range_end == datetime.strptime(end_date, '%Y-%m-%d').date(),
                GA4DataCache.expires_at > datetime.utcnow()
            ).all()
            
            if not cached_entries:
                return None
            
            # Reconstruct the data format
            data = {
                'dimension_headers': [],
                'metric_headers': [{'name': metric_name, 'type': 'TYPE_FLOAT'}],
                'rows': []
            }
            
            # Group by dimension value
            dimension_groups = {}
            has_dimensions = False
            
            for entry in cached_entries:
                if entry.dimension_name and entry.dimension_value:
                    has_dimensions = True
                    if entry.dimension_value not in dimension_groups:
                        dimension_groups[entry.dimension_value] = []
                    dimension_groups[entry.dimension_value].append(entry)
                else:
                    # No dimensions, single row
                    data['rows'].append({
                        'metric_values': [{'value': str(entry.metric_value)}]
                    })
            
            if has_dimensions:
                # Add dimension header
                first_entry = cached_entries[0]
                data['dimension_headers'].append({'name': first_entry.dimension_name})
                
                # Add rows for each dimension value
                for dim_value, entries in dimension_groups.items():
                    row = {
                        'dimension_values': [{'value': dim_value}],
                        'metric_values': [{'value': str(entries[0].metric_value)}]
                    }
                    data['rows'].append(row)
            
            print(f"Retrieved cached GA4 data for website {website_id}, metric {metric_name}")
            return data
            
        except Exception as e:
            print(f"Failed to retrieve cached data: {str(e)}")
            return None

# Global instance
ga4_service = GA4Service()

