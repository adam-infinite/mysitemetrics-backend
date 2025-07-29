from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import json

class GA4DataService:
    def __init__(self):
        pass

    def get_analytics_data(self, access_token, property_id, start_date=None, end_date=None):
        """Fetch analytics data from GA4"""
        credentials = Credentials(token=access_token)
        
        # Build Analytics Data API service
        analytics = build('analyticsdata', 'v1beta', credentials=credentials)
        
        # Default date range (last 30 days)
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        # Basic metrics request
        request = {
            'property': f'properties/{property_id}',
            'dateRanges': [{'startDate': start_date, 'endDate': end_date}],
            'metrics': [
                {'name': 'activeUsers'},
                {'name': 'sessions'},
                {'name': 'screenPageViews'},
                {'name': 'bounceRate'},
                {'name': 'averageSessionDuration'}
            ],
            'dimensions': [
                {'name': 'date'}
            ]
        }
        
        response = analytics.properties().runReport(body=request).execute()
        
        return self._format_analytics_response(response)

    def get_real_time_data(self, access_token, property_id):
        """Fetch real-time analytics data from GA4"""
        credentials = Credentials(token=access_token)
        
        # Build Analytics Data API service
        analytics = build('analyticsdata', 'v1beta', credentials=credentials)
        
        request = {
            'property': f'properties/{property_id}',
            'metrics': [
                {'name': 'activeUsers'}
            ]
        }
        
        response = analytics.properties().runRealtimeReport(body=request).execute()
        
        return self._format_realtime_response(response)

    def get_top_pages(self, access_token, property_id, start_date=None, end_date=None):
        """Get top pages data"""
        credentials = Credentials(token=access_token)
        analytics = build('analyticsdata', 'v1beta', credentials=credentials)
        
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        request = {
            'property': f'properties/{property_id}',
            'dateRanges': [{'startDate': start_date, 'endDate': end_date}],
            'metrics': [
                {'name': 'screenPageViews'},
                {'name': 'activeUsers'}
            ],
            'dimensions': [
                {'name': 'pagePath'},
                {'name': 'pageTitle'}
            ],
            'orderBys': [
                {'metric': {'metricName': 'screenPageViews'}, 'desc': True}
            ],
            'limit': 10
        }
        
        response = analytics.properties().runReport(body=request).execute()
        
        return self._format_pages_response(response)

    def get_traffic_sources(self, access_token, property_id, start_date=None, end_date=None):
        """Get traffic sources data"""
        credentials = Credentials(token=access_token)
        analytics = build('analyticsdata', 'v1beta', credentials=credentials)
        
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        request = {
            'property': f'properties/{property_id}',
            'dateRanges': [{'startDate': start_date, 'endDate': end_date}],
            'metrics': [
                {'name': 'sessions'},
                {'name': 'activeUsers'}
            ],
            'dimensions': [
                {'name': 'sessionDefaultChannelGroup'}
            ],
            'orderBys': [
                {'metric': {'metricName': 'sessions'}, 'desc': True}
            ]
        }
        
        response = analytics.properties().runReport(body=request).execute()
        
        return self._format_traffic_sources_response(response)

    def _format_analytics_response(self, response):
        """Format the analytics API response"""
        formatted_data = {
            'summary': {},
            'daily_data': []
        }
        
        if 'rows' not in response:
            return formatted_data
        
        # Calculate summary metrics
        total_users = 0
        total_sessions = 0
        total_pageviews = 0
        total_bounce_rate = 0
        total_session_duration = 0
        row_count = len(response['rows'])
        
        for row in response['rows']:
            date = row['dimensionValues'][0]['value']
            metrics = row['metricValues']
            
            users = int(metrics[0]['value'])
            sessions = int(metrics[1]['value'])
            pageviews = int(metrics[2]['value'])
            bounce_rate = float(metrics[3]['value'])
            session_duration = float(metrics[4]['value'])
            
            total_users += users
            total_sessions += sessions
            total_pageviews += pageviews
            total_bounce_rate += bounce_rate
            total_session_duration += session_duration
            
            formatted_data['daily_data'].append({
                'date': date,
                'users': users,
                'sessions': sessions,
                'pageviews': pageviews,
                'bounce_rate': bounce_rate,
                'session_duration': session_duration
            })
        
        # Calculate averages
        formatted_data['summary'] = {
            'total_users': total_users,
            'total_sessions': total_sessions,
            'total_pageviews': total_pageviews,
            'avg_bounce_rate': total_bounce_rate / row_count if row_count > 0 else 0,
            'avg_session_duration': total_session_duration / row_count if row_count > 0 else 0
        }
        
        return formatted_data

    def _format_realtime_response(self, response):
        """Format real-time API response"""
        if 'rows' not in response or not response['rows']:
            return {'active_users': 0}
        
        active_users = int(response['rows'][0]['metricValues'][0]['value'])
        return {'active_users': active_users}

    def _format_pages_response(self, response):
        """Format top pages API response"""
        pages = []
        
        if 'rows' not in response:
            return pages
        
        for row in response['rows']:
            page_path = row['dimensionValues'][0]['value']
            page_title = row['dimensionValues'][1]['value']
            pageviews = int(row['metricValues'][0]['value'])
            users = int(row['metricValues'][1]['value'])
            
            pages.append({
                'page_path': page_path,
                'page_title': page_title,
                'pageviews': pageviews,
                'users': users
            })
        
        return pages

    def _format_traffic_sources_response(self, response):
        """Format traffic sources API response"""
        sources = []
        
        if 'rows' not in response:
            return sources
        
        for row in response['rows']:
            channel = row['dimensionValues'][0]['value']
            sessions = int(row['metricValues'][0]['value'])
            users = int(row['metricValues'][1]['value'])
            
            sources.append({
                'channel': channel,
                'sessions': sessions,
                'users': users
            })
        
        return sources

