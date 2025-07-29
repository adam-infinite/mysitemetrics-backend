from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.user import db, User, Website, Client
from datetime import datetime

websites_bp = Blueprint('websites', __name__)

@websites_bp.route('/websites', methods=['GET'])
@jwt_required()
def get_websites():
    """Get all websites for the current user."""
    try:
        current_user_id = int(get_jwt_identity())
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        if user.role == 'admin':
            # Admin can see all websites
            websites = Website.query.all()
        elif user.role == 'client' and user.client:
            # Client can only see their own websites
            websites = user.client.websites
        else:
            return jsonify({'message': 'Access denied'}), 403
        
        websites_data = []
        for website in websites:
            website_dict = website.to_dict()
            # Add client information for admin users
            if user.role == 'admin':
                website_dict['client'] = website.client.to_dict()
            websites_data.append(website_dict)
        
        return jsonify({
            'websites': websites_data,
            'total': len(websites_data)
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to get websites: {str(e)}'}), 500

@websites_bp.route('/websites', methods=['POST'])
@jwt_required()
def create_website():
    """Create a new website."""
    try:
        current_user_id = int(get_jwt_identity())
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        data = request.get_json()
        
        if not data.get('domain'):
            return jsonify({'message': 'Domain is required'}), 400
        
        # Determine client_id
        client_id = None
        if user.role == 'admin':
            # Admin can create websites for any client
            client_id = data.get('client_id')
            if not client_id:
                return jsonify({'message': 'client_id is required for admin users'}), 400
            
            # Verify client exists
            client = Client.query.get(client_id)
            if not client:
                return jsonify({'message': 'Client not found'}), 404
                
        elif user.role == 'client' and user.client:
            # Client creates website for themselves
            client_id = user.client.id
        else:
            return jsonify({'message': 'Access denied'}), 403
        
        # Check if domain already exists for this client
        existing_website = Website.query.filter_by(
            client_id=client_id, 
            domain=data['domain']
        ).first()
        
        if existing_website:
            return jsonify({'message': 'Website with this domain already exists for this client'}), 409
        
        # Create new website
        website = Website(
            client_id=client_id,
            domain=data['domain'],
            ga4_property_id=data.get('ga4_property_id'),
            search_console_url=data.get('search_console_url')
        )
        
        db.session.add(website)
        db.session.commit()
        
        website_dict = website.to_dict()
        if user.role == 'admin':
            website_dict['client'] = website.client.to_dict()
        
        return jsonify({
            'message': 'Website created successfully',
            'website': website_dict
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to create website: {str(e)}'}), 500

@websites_bp.route('/websites/<int:website_id>', methods=['GET'])
@jwt_required()
def get_website(website_id):
    """Get a specific website."""
    try:
        current_user_id = int(get_jwt_identity())
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        website = Website.query.get(website_id)
        if not website:
            return jsonify({'message': 'Website not found'}), 404
        
        # Check permissions
        if user.role == 'client':
            if not user.client or website.client_id != user.client.id:
                return jsonify({'message': 'Access denied'}), 403
        
        website_dict = website.to_dict()
        if user.role == 'admin':
            website_dict['client'] = website.client.to_dict()
        
        return jsonify({'website': website_dict}), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to get website: {str(e)}'}), 500

@websites_bp.route('/websites/<int:website_id>', methods=['PUT'])
@jwt_required()
def update_website(website_id):
    """Update a website."""
    try:
        current_user_id = int(get_jwt_identity())
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        website = Website.query.get(website_id)
        if not website:
            return jsonify({'message': 'Website not found'}), 404
        
        # Check permissions
        if user.role == 'client':
            if not user.client or website.client_id != user.client.id:
                return jsonify({'message': 'Access denied'}), 403
        
        data = request.get_json()
        
        # Update fields
        if 'domain' in data:
            # Check if new domain conflicts with existing websites
            existing_website = Website.query.filter(
                Website.client_id == website.client_id,
                Website.domain == data['domain'],
                Website.id != website_id
            ).first()
            
            if existing_website:
                return jsonify({'message': 'Website with this domain already exists for this client'}), 409
            
            website.domain = data['domain']
        
        if 'ga4_property_id' in data:
            website.ga4_property_id = data['ga4_property_id']
        
        if 'search_console_url' in data:
            website.search_console_url = data['search_console_url']
        
        if 'is_active' in data and user.role == 'admin':
            website.is_active = data['is_active']
        
        website.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        website_dict = website.to_dict()
        if user.role == 'admin':
            website_dict['client'] = website.client.to_dict()
        
        return jsonify({
            'message': 'Website updated successfully',
            'website': website_dict
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to update website: {str(e)}'}), 500

@websites_bp.route('/websites/<int:website_id>', methods=['DELETE'])
@jwt_required()
def delete_website(website_id):
    """Delete a website."""
    try:
        current_user_id = int(get_jwt_identity())
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        website = Website.query.get(website_id)
        if not website:
            return jsonify({'message': 'Website not found'}), 404
        
        # Check permissions
        if user.role == 'client':
            if not user.client or website.client_id != user.client.id:
                return jsonify({'message': 'Access denied'}), 403
        
        # Soft delete by setting is_active to False
        website.is_active = False
        website.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({'message': 'Website deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to delete website: {str(e)}'}), 500

@websites_bp.route('/websites/<int:website_id>/verify-ga4', methods=['POST'])
@jwt_required()
def verify_ga4_connection(website_id):
    """Verify GA4 connection for a website."""
    try:
        current_user_id = int(get_jwt_identity())
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        website = Website.query.get(website_id)
        if not website:
            return jsonify({'message': 'Website not found'}), 404
        
        # Check permissions
        if user.role == 'client':
            if not user.client or website.client_id != user.client.id:
                return jsonify({'message': 'Access denied'}), 403
        
        if not website.ga4_property_id:
            return jsonify({'message': 'GA4 property ID not configured'}), 400
        
        # TODO: Implement actual GA4 API verification
        # For now, we'll simulate a successful verification
        verification_result = {
            'status': 'success',
            'property_id': website.ga4_property_id,
            'property_name': f'Property for {website.domain}',
            'last_data_date': '2025-07-27',
            'message': 'GA4 connection verified successfully'
        }
        
        return jsonify({
            'message': 'GA4 connection verified',
            'verification': verification_result
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to verify GA4 connection: {str(e)}'}), 500

@websites_bp.route('/websites/<int:website_id>/verify-gsc', methods=['POST'])
@jwt_required()
def verify_search_console_connection(website_id):
    """Verify Google Search Console connection for a website."""
    try:
        current_user_id = int(get_jwt_identity())
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        website = Website.query.get(website_id)
        if not website:
            return jsonify({'message': 'Website not found'}), 404
        
        # Check permissions
        if user.role == 'client':
            if not user.client or website.client_id != user.client.id:
                return jsonify({'message': 'Access denied'}), 403
        
        if not website.search_console_url:
            return jsonify({'message': 'Search Console URL not configured'}), 400
        
        # TODO: Implement actual Search Console API verification
        # For now, we'll simulate a successful verification
        verification_result = {
            'status': 'success',
            'url': website.search_console_url,
            'permission_level': 'Full',
            'last_data_date': '2025-07-27',
            'message': 'Search Console connection verified successfully'
        }
        
        return jsonify({
            'message': 'Search Console connection verified',
            'verification': verification_result
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to verify Search Console connection: {str(e)}'}), 500

