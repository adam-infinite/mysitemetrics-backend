from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.user import db, User, Website
from src.services.ga4_service_simple import ga4_service
from datetime import datetime, timedelta

analytics_bp = Blueprint('analytics', __name__)

def check_website_access(user, website_id):
    """Check if user has access to the website."""
    website = Website.query.get(website_id)
    if not website:
        return None, {'message': 'Website not found'}, 404
    
    # Check permissions
    if user.role == 'client':
        if not user.client or website.client_id != user.client.id:
            return None, {'message': 'Access denied'}, 403
    
    return website, None, None

@analytics_bp.route('/analytics/<int:website_id>/overview', methods=['GET'])
@jwt_required()
def get_overview(website_id):
    """Get overview analytics data for a website."""
    try:
        current_user_id = int(get_jwt_identity())
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        website, error_response, status_code = check_website_access(user, website_id)
        if error_response:
            return jsonify(error_response), status_code
        
        # Get date range from query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        # Check cache first
        cached_data = ga4_service.get_cached_data(
            website_id, 'overview', start_date, end_date
        )
        
        if cached_data:
            return jsonify({
                'website_id': website_id,
                'domain': website.domain,
                'date_range': {'start': start_date, 'end': end_date},
                'data': cached_data,
                'cached': True
            }), 200
        
        # Fetch fresh data
        if not website.ga4_property_id:
            return jsonify({'message': 'GA4 property ID not configured for this website'}), 400
        
        data = ga4_service.get_overview_metrics(
            website.ga4_property_id, start_date, end_date
        )
        
        # Cache the data
        ga4_service.cache_data(website_id, 'overview', data, start_date, end_date)
        
        return jsonify({
            'website_id': website_id,
            'domain': website.domain,
            'date_range': {'start': start_date, 'end': end_date},
            'data': data,
            'cached': False
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to get overview data: {str(e)}'}), 500

@analytics_bp.route('/analytics/<int:website_id>/traffic', methods=['GET'])
@jwt_required()
def get_traffic_data(website_id):
    """Get traffic analytics data for a website."""
    try:
        current_user_id = int(get_jwt_identity())
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        website, error_response, status_code = check_website_access(user, website_id)
        if error_response:
            return jsonify(error_response), status_code
        
        # Get date range from query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        # Check cache first
        cached_data = ga4_service.get_cached_data(
            website_id, 'traffic_sources', start_date, end_date
        )
        
        if cached_data:
            return jsonify({
                'website_id': website_id,
                'domain': website.domain,
                'date_range': {'start': start_date, 'end': end_date},
                'data': cached_data,
                'cached': True
            }), 200
        
        # Fetch fresh data
        if not website.ga4_property_id:
            return jsonify({'message': 'GA4 property ID not configured for this website'}), 400
        
        data = ga4_service.get_traffic_sources(
            website.ga4_property_id, start_date, end_date
        )
        
        # Cache the data
        ga4_service.cache_data(website_id, 'traffic_sources', data, start_date, end_date)
        
        return jsonify({
            'website_id': website_id,
            'domain': website.domain,
            'date_range': {'start': start_date, 'end': end_date},
            'data': data,
            'cached': False
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to get traffic data: {str(e)}'}), 500

@analytics_bp.route('/analytics/<int:website_id>/pages', methods=['GET'])
@jwt_required()
def get_page_performance(website_id):
    """Get page performance data for a website."""
    try:
        current_user_id = int(get_jwt_identity())
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        website, error_response, status_code = check_website_access(user, website_id)
        if error_response:
            return jsonify(error_response), status_code
        
        # Get date range from query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        # Check cache first
        cached_data = ga4_service.get_cached_data(
            website_id, 'page_performance', start_date, end_date
        )
        
        if cached_data:
            return jsonify({
                'website_id': website_id,
                'domain': website.domain,
                'date_range': {'start': start_date, 'end': end_date},
                'data': cached_data,
                'cached': True
            }), 200
        
        # Fetch fresh data
        if not website.ga4_property_id:
            return jsonify({'message': 'GA4 property ID not configured for this website'}), 400
        
        data = ga4_service.get_page_performance(
            website.ga4_property_id, start_date, end_date
        )
        
        # Cache the data
        ga4_service.cache_data(website_id, 'page_performance', data, start_date, end_date)
        
        return jsonify({
            'website_id': website_id,
            'domain': website.domain,
            'date_range': {'start': start_date, 'end': end_date},
            'data': data,
            'cached': False
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to get page performance data: {str(e)}'}), 500

@analytics_bp.route('/analytics/<int:website_id>/realtime', methods=['GET'])
@jwt_required()
def get_realtime_data(website_id):
    """Get real-time analytics data for a website."""
    try:
        current_user_id = int(get_jwt_identity())
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        website, error_response, status_code = check_website_access(user, website_id)
        if error_response:
            return jsonify(error_response), status_code
        
        # Real-time data is never cached
        if not website.ga4_property_id:
            return jsonify({'message': 'GA4 property ID not configured for this website'}), 400
        
        data = ga4_service.get_realtime_data(website.ga4_property_id)
        
        return jsonify({
            'website_id': website_id,
            'domain': website.domain,
            'timestamp': datetime.utcnow().isoformat(),
            'data': data
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to get real-time data: {str(e)}'}), 500

@analytics_bp.route('/analytics/<int:website_id>/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard_data(website_id):
    """Get comprehensive dashboard data for a website."""
    try:
        current_user_id = int(get_jwt_identity())
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        website, error_response, status_code = check_website_access(user, website_id)
        if error_response:
            return jsonify(error_response), status_code
        
        # Get date range from query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        if not website.ga4_property_id:
            return jsonify({'message': 'GA4 property ID not configured for this website'}), 400
        
        # Fetch all dashboard data
        dashboard_data = {
            'website': {
                'id': website_id,
                'domain': website.domain,
                'ga4_property_id': website.ga4_property_id
            },
            'date_range': {'start': start_date, 'end': end_date},
            'overview': None,
            'traffic_sources': None,
            'page_performance': None,
            'realtime': None
        }
        
        # Get overview data
        cached_overview = ga4_service.get_cached_data(website_id, 'overview', start_date, end_date)
        if cached_overview:
            dashboard_data['overview'] = cached_overview
        else:
            overview_data = ga4_service.get_overview_metrics(website.ga4_property_id, start_date, end_date)
            ga4_service.cache_data(website_id, 'overview', overview_data, start_date, end_date)
            dashboard_data['overview'] = overview_data
        
        # Get traffic sources
        cached_traffic = ga4_service.get_cached_data(website_id, 'traffic_sources', start_date, end_date)
        if cached_traffic:
            dashboard_data['traffic_sources'] = cached_traffic
        else:
            traffic_data = ga4_service.get_traffic_sources(website.ga4_property_id, start_date, end_date)
            ga4_service.cache_data(website_id, 'traffic_sources', traffic_data, start_date, end_date)
            dashboard_data['traffic_sources'] = traffic_data
        
        # Get page performance
        cached_pages = ga4_service.get_cached_data(website_id, 'page_performance', start_date, end_date)
        if cached_pages:
            dashboard_data['page_performance'] = cached_pages
        else:
            pages_data = ga4_service.get_page_performance(website.ga4_property_id, start_date, end_date)
            ga4_service.cache_data(website_id, 'page_performance', pages_data, start_date, end_date)
            dashboard_data['page_performance'] = pages_data
        
        # Get real-time data (never cached)
        dashboard_data['realtime'] = ga4_service.get_realtime_data(website.ga4_property_id)
        
        return jsonify(dashboard_data), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to get dashboard data: {str(e)}'}), 500

@analytics_bp.route('/analytics/<int:website_id>/clear-cache', methods=['POST'])
@jwt_required()
def clear_cache(website_id):
    """Clear cached analytics data for a website."""
    try:
        current_user_id = int(get_jwt_identity())
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        website, error_response, status_code = check_website_access(user, website_id)
        if error_response:
            return jsonify(error_response), status_code
        
        # Clear all cached data for this website
        deleted_count = db.session.query(GA4DataCache).filter(
            GA4DataCache.website_id == website_id
        ).delete()
        
        db.session.commit()
        
        return jsonify({
            'message': f'Cleared {deleted_count} cached entries for website {website.domain}'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to clear cache: {str(e)}'}), 500

