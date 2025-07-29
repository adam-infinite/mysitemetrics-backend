import os
import json
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from flask import current_app

class GA4OAuthService:
    def __init__(self):
        self.client_config = {
            "web": {
                "client_id": os.getenv('GOOGLE_CLIENT_ID'),
                "client_secret": os.getenv('GOOGLE_CLIENT_SECRET'),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [
                    f"https://api.mysitemetrics.io/api/auth/google/callback",
                    f"https://app.mysitemetrics.io/auth/google/callback"
                ]
            }
        }
        self.scopes = [
            'https://www.googleapis.com/auth/analytics.readonly',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile'
        ]

    def get_authorization_url(self, state=None):
        """Generate Google OAuth authorization URL"""
        flow = Flow.from_client_config(
            self.client_config,
            scopes=self.scopes,
            state=state
        )
        flow.redirect_uri = f"https://api.mysitemetrics.io/api/auth/google/callback"
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        return authorization_url, state

    def exchange_code_for_tokens(self, code, state=None):
        """Exchange authorization code for access and refresh tokens"""
        flow = Flow.from_client_config(
            self.client_config,
            scopes=self.scopes,
            state=state
        )
        flow.redirect_uri = f"https://api.mysitemetrics.io/api/auth/google/callback"
        
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Get user info
        user_info_service = build('oauth2', 'v2', credentials=credentials)
        user_info = user_info_service.userinfo().get().execute()
        
        return {
            'access_token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'expires_at': credentials.expiry,
            'user_info': user_info
        }

    def refresh_access_token(self, refresh_token):
        """Refresh access token using refresh token"""
        credentials = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri=self.client_config['web']['token_uri'],
            client_id=self.client_config['web']['client_id'],
            client_secret=self.client_config['web']['client_secret']
        )
        
        credentials.refresh(Request())
        
        return {
            'access_token': credentials.token,
            'expires_at': credentials.expiry
        }

    def get_analytics_properties(self, access_token):
        """Get GA4 properties for the authenticated user"""
        credentials = Credentials(token=access_token)
        
        # Build Analytics Admin API service
        admin_service = build('analyticsadmin', 'v1beta', credentials=credentials)
        
        # List all accounts
        accounts_response = admin_service.accounts().list().execute()
        
        properties = []
        for account in accounts_response.get('accounts', []):
            account_name = account['name']
            
            # List properties for this account
            properties_response = admin_service.accounts().properties().list(
                parent=account_name
            ).execute()
            
            for property_data in properties_response.get('properties', []):
                properties.append({
                    'property_id': property_data['name'].split('/')[-1],
                    'property_name': property_data.get('displayName', 'Unknown Property'),
                    'website_url': property_data.get('websiteUrl', ''),
                    'account_name': account.get('displayName', 'Unknown Account')
                })
        
        return properties

