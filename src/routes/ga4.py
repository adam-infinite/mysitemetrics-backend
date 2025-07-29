from flask import Blueprint, request, jsonify, redirect, session
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.user import db, User, GA4Account, GA4Property
from src.services.ga4_oauth import GA4OAuthService
from src.services.ga4_data import GA4DataService
from datetime import datetime
import secrets

ga4_bp = Blueprint('ga4', __name__)
oauth_service = GA4OAuthService()
data_service = GA4DataService()

@ga4_bp.route('/auth/google/start', methods=['POST'])
@jwt_required()
def start_google_auth():
    """Start Google OAuth flow"""
    user_id = get_jwt_identity()
    
    # Generate state parameter for security
    state = secrets.token_urlsafe(32)
    
    # Store state in session (you might want to use Redis for production)
    session[f'oauth_state_{user_id}'] = state
    
    authorization_url, _ = oauth_service.get_authorization_url(state=state)
    
    return jsonify({
        'authorization_url': authorization_url,
        'state': state
    })

@ga4_bp.route('/auth/google/callback', methods=['GET'])
def google_auth_callback():
    """Handle Google OAuth callback"""
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')
    
    if error:
        return redirect(f"https://app.mysitemetrics.io/ga4-connect?error={error}")
    
    if not code or not state:
        return redirect("https://app.mysitemetrics.io/ga4-connect?error=missing_parameters")
    
    try:
        # Exchange code for tokens
        token_data = oauth_service.exchange_code_for_tokens(code, state)
        
        # Get user info
        user_info = token_data['user_info']
        google_account_id = user_info['id']
        email = user_info['email']
        
        # Store the tokens temporarily in session for the frontend to process
        # In production, you'd want to associate this with the authenticated user
        session['temp_ga4_tokens'] = {
            'access_token': token_data['access_token'],
            'refresh_token': token_data['refresh_token'],
            'expires_at': token_data['expires_at'].isoformat() if token_data['expires_at'] else None,
            'google_account_id': google_account_id,
            'email': email
        }
        
        return redirect(f"https://app.mysitemetrics.io/ga4-connect?success=true&email={email}")
        
    except Exception as e:
        print(f"OAuth callback error: {str(e)}")
        return redirect(f"https://app.mysitemetrics.io/ga4-connect?error=oauth_failed")

@ga4_bp.route('/auth/google/complete', methods=['POST'])
@jwt_required()
def complete_google_auth():
    """Complete the GA4 account connection process"""
    user_id = get_jwt_identity()
    
    # Get tokens from session
    temp_tokens = session.get('temp_ga4_tokens')
    if not temp_tokens:
        return jsonify({'error': 'No authentication data found'}), 400
    
    try:
        # Check if account already exists
        existing_account = GA4Account.query.filter_by(
            user_id=user_id,
            google_account_id=temp_tokens['google_account_id']
        ).first()
        
        if existing_account:
            # Update existing account
            existing_account.access_token = temp_tokens['access_token']
            existing_account.refresh_token = temp_tokens['refresh_token']
            existing_account.token_expires_at = datetime.fromisoformat(temp_tokens['expires_at']) if temp_tokens['expires_at'] else None
            existing_account.is_active = True
            existing_account.updated_at = datetime.utcnow()
            
            account = existing_account
        else:
            # Create new account
            account = GA4Account(
                user_id=user_id,
                google_account_id=temp_tokens['google_account_id'],
                email=temp_tokens['email'],
                access_token=temp_tokens['access_token'],
                refresh_token=temp_tokens['refresh_token'],
                token_expires_at=datetime.fromisoformat(temp_tokens['expires_at']) if temp_tokens['expires_at'] else None
            )
            db.session.add(account)
        
        db.session.commit()
        
        # Fetch and store GA4 properties
        properties = oauth_service.get_analytics_properties(temp_tokens['access_token'])
        
        for prop_data in properties:
            existing_property = GA4Property.query.filter_by(
                account_id=account.id,
                property_id=prop_data['property_id']
            ).first()
            
            if existing_property:
                # Update existing property
                existing_property.property_name = prop_data['property_name']
                existing_property.website_url = prop_data['website_url']
                existing_property.is_active = True
                existing_property.updated_at = datetime.utcnow()
            else:
                # Create new property
                new_property = GA4Property(
                    account_id=account.id,
                    property_id=prop_data['property_id'],
                    property_name=prop_data['property_name'],
                    website_url=prop_data['website_url']
                )
                db.session.add(new_property)
        
        db.session.commit()
        
        # Clear temporary tokens
        session.pop('temp_ga4_tokens', None)
        
        return jsonify({
            'success': True,
            'account': account.to_dict(),
            'properties_count': len(properties)
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Complete auth error: {str(e)}")
        return jsonify({'error': 'Failed to complete authentication'}), 500

@ga4_bp.route('/accounts', methods=['GET'])
@jwt_required()
def get_ga4_accounts():
    """Get user's connected GA4 accounts"""
    user_id = get_jwt_identity()
    
    accounts = GA4Account.query.filter_by(user_id=user_id, is_active=True).all()
    
    accounts_data = []
    for account in accounts:
        account_dict = account.to_dict()
        account_dict['properties_count'] = len(account.properties)
        accounts_data.append(account_dict)
    
    return jsonify({
        'accounts': accounts_data
    })

@ga4_bp.route('/accounts/<int:account_id>/properties', methods=['GET'])
@jwt_required()
def get_account_properties(account_id):
    """Get properties for a specific GA4 account"""
    user_id = get_jwt_identity()
    
    # Verify account belongs to user
    account = GA4Account.query.filter_by(
        id=account_id, 
        user_id=user_id, 
        is_active=True
    ).first()
    
    if not account:
        return jsonify({'error': 'Account not found'}), 404
    
    properties = GA4Property.query.filter_by(
        account_id=account_id, 
        is_active=True
    ).all()
    
    return jsonify({
        'account': account.to_dict(),
        'properties': [prop.to_dict() for prop in properties]
    })

@ga4_bp.route('/properties/<property_id>/analytics', methods=['GET'])
@jwt_required()
def get_property_analytics(property_id):
    """Get analytics data for a specific property"""
    user_id = get_jwt_identity()
    
    # Find the property and verify user access
    property_obj = db.session.query(GA4Property).join(GA4Account).filter(
        GA4Property.property_id == property_id,
        GA4Account.user_id == user_id,
        GA4Property.is_active == True,
        GA4Account.is_active == True
    ).first()
    
    if not property_obj:
        return jsonify({'error': 'Property not found or access denied'}), 404
    
    # Get date range from query parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    try:
        # Get fresh access token (implement token refresh logic)
        account = property_obj.account
        access_token = account.access_token  # You'll need to implement token refresh
        
        # Fetch analytics data
        analytics_data = data_service.get_analytics_data(
            access_token, 
            property_id, 
            start_date, 
            end_date
        )
        
        return jsonify(analytics_data)
        
    except Exception as e:
        print(f"Analytics data error: {str(e)}")
        return jsonify({'error': 'Failed to fetch analytics data'}), 500

@ga4_bp.route('/properties/<property_id>/realtime', methods=['GET'])
@jwt_required()
def get_property_realtime(property_id):
    """Get real-time data for a specific property"""
    user_id = get_jwt_identity()
    
    # Find the property and verify user access
    property_obj = db.session.query(GA4Property).join(GA4Account).filter(
        GA4Property.property_id == property_id,
        GA4Account.user_id == user_id,
        GA4Property.is_active == True,
        GA4Account.is_active == True
    ).first()
    
    if not property_obj:
        return jsonify({'error': 'Property not found or access denied'}), 404
    
    try:
        # Get fresh access token
        account = property_obj.account
        access_token = account.access_token
        
        # Fetch real-time data
        realtime_data = data_service.get_real_time_data(access_token, property_id)
        
        return jsonify(realtime_data)
        
    except Exception as e:
        print(f"Real-time data error: {str(e)}")
        return jsonify({'error': 'Failed to fetch real-time data'}), 500

@ga4_bp.route('/properties/<property_id>/pages', methods=['GET'])
@jwt_required()
def get_property_pages(property_id):
    """Get top pages for a specific property"""
    user_id = get_jwt_identity()
    
    # Find the property and verify user access
    property_obj = db.session.query(GA4Property).join(GA4Account).filter(
        GA4Property.property_id == property_id,
        GA4Account.user_id == user_id,
        GA4Property.is_active == True,
        GA4Account.is_active == True
    ).first()
    
    if not property_obj:
        return jsonify({'error': 'Property not found or access denied'}), 404
    
    # Get date range from query parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    try:
        # Get fresh access token
        account = property_obj.account
        access_token = account.access_token
        
        # Fetch pages data
        pages_data = data_service.get_top_pages(
            access_token, 
            property_id, 
            start_date, 
            end_date
        )
        
        return jsonify({'pages': pages_data})
        
    except Exception as e:
        print(f"Pages data error: {str(e)}")
        return jsonify({'error': 'Failed to fetch pages data'}), 500

@ga4_bp.route('/properties/<property_id>/traffic-sources', methods=['GET'])
@jwt_required()
def get_property_traffic_sources(property_id):
    """Get traffic sources for a specific property"""
    user_id = get_jwt_identity()
    
    # Find the property and verify user access
    property_obj = db.session.query(GA4Property).join(GA4Account).filter(
        GA4Property.property_id == property_id,
        GA4Account.user_id == user_id,
        GA4Property.is_active == True,
        GA4Account.is_active == True
    ).first()
    
    if not property_obj:
        return jsonify({'error': 'Property not found or access denied'}), 404
    
    # Get date range from query parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    try:
        # Get fresh access token
        account = property_obj.account
        access_token = account.access_token
        
        # Fetch traffic sources data
        sources_data = data_service.get_traffic_sources(
            access_token, 
            property_id, 
            start_date, 
            end_date
        )
        
        return jsonify({'sources': sources_data})
        
    except Exception as e:
        print(f"Traffic sources data error: {str(e)}")
        return jsonify({'error': 'Failed to fetch traffic sources data'}), 500

@ga4_bp.route('/accounts/<int:account_id>/disconnect', methods=['DELETE'])
@jwt_required()
def disconnect_ga4_account(account_id):
    """Disconnect a GA4 account"""
    user_id = get_jwt_identity()
    
    # Verify account belongs to user
    account = GA4Account.query.filter_by(
        id=account_id, 
        user_id=user_id, 
        is_active=True
    ).first()
    
    if not account:
        return jsonify({'error': 'Account not found'}), 404
    
    try:
        # Deactivate account and properties
        account.is_active = False
        for property_obj in account.properties:
            property_obj.is_active = False
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Account disconnected successfully'})
        
    except Exception as e:
        db.session.rollback()
        print(f"Disconnect error: {str(e)}")
        return jsonify({'error': 'Failed to disconnect account'}), 500

