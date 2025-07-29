from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.user import db, User, Client, Website
from datetime import datetime, timedelta
from functools import wraps

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    """Decorator to require admin role."""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        current_user_id = int(get_jwt_identity())
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        if user.role != 'admin':
            return jsonify({'message': 'Admin access required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/admin/clients', methods=['GET'])
@admin_required
def get_all_clients():
    """Get all clients (admin only)."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '')
        
        query = Client.query.join(User)
        
        if search:
            query = query.filter(
                db.or_(
                    Client.company_name.ilike(f'%{search}%'),
                    User.email.ilike(f'%{search}%'),
                    User.full_name.ilike(f'%{search}%')
                )
            )
        
        clients = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        clients_data = []
        for client in clients.items:
            client_dict = client.to_dict()
            client_dict['user'] = client.user.to_dict()
            client_dict['websites_count'] = len(client.websites)
            clients_data.append(client_dict)
        
        return jsonify({
            'clients': clients_data,
            'pagination': {
                'page': clients.page,
                'pages': clients.pages,
                'per_page': clients.per_page,
                'total': clients.total,
                'has_next': clients.has_next,
                'has_prev': clients.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to get clients: {str(e)}'}), 500

@admin_bp.route('/admin/clients', methods=['POST'])
@admin_required
def create_client():
    """Create a new client (admin only)."""
    try:
        data = request.get_json()
        
        required_fields = ['email', 'password', 'full_name', 'company_name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'message': f'{field} is required'}), 400
        
        email = data.get('email').lower().strip()
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            return jsonify({'message': 'User with this email already exists'}), 409
        
        # Create new user
        user = User(
            email=email,
            full_name=data.get('full_name'),
            role='client'
        )
        user.set_password(data.get('password'))
        
        db.session.add(user)
        db.session.flush()  # Get user ID
        
        # Create client profile
        client = Client(
            user_id=user.id,
            company_name=data.get('company_name'),
            contact_email=data.get('contact_email', email),
            phone=data.get('phone'),
            address=data.get('address'),
            subscription_plan=data.get('subscription_plan', 'basic')
        )
        
        db.session.add(client)
        db.session.commit()
        
        client_dict = client.to_dict()
        client_dict['user'] = user.to_dict()
        
        return jsonify({
            'message': 'Client created successfully',
            'client': client_dict
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to create client: {str(e)}'}), 500

@admin_bp.route('/admin/clients/<int:client_id>', methods=['GET'])
@admin_required
def get_client(client_id):
    """Get a specific client (admin only)."""
    try:
        client = Client.query.get(client_id)
        if not client:
            return jsonify({'message': 'Client not found'}), 404
        
        client_dict = client.to_dict()
        client_dict['user'] = client.user.to_dict()
        client_dict['websites'] = [website.to_dict() for website in client.websites]
        
        return jsonify({'client': client_dict}), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to get client: {str(e)}'}), 500

@admin_bp.route('/admin/clients/<int:client_id>', methods=['PUT'])
@admin_required
def update_client(client_id):
    """Update a client (admin only)."""
    try:
        client = Client.query.get(client_id)
        if not client:
            return jsonify({'message': 'Client not found'}), 404
        
        data = request.get_json()
        
        # Update client fields
        if 'company_name' in data:
            client.company_name = data['company_name']
        if 'contact_email' in data:
            client.contact_email = data['contact_email']
        if 'phone' in data:
            client.phone = data['phone']
        if 'address' in data:
            client.address = data['address']
        if 'subscription_plan' in data:
            client.subscription_plan = data['subscription_plan']
        if 'is_active' in data:
            client.is_active = data['is_active']
        
        client.updated_at = datetime.utcnow()
        
        # Update user fields
        user = client.user
        if 'full_name' in data:
            user.full_name = data['full_name']
        if 'is_active' in data:
            user.is_active = data['is_active']
        if 'password' in data and data['password']:
            user.set_password(data['password'])
        
        user.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        client_dict = client.to_dict()
        client_dict['user'] = user.to_dict()
        
        return jsonify({
            'message': 'Client updated successfully',
            'client': client_dict
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to update client: {str(e)}'}), 500

@admin_bp.route('/admin/clients/<int:client_id>', methods=['DELETE'])
@admin_required
def delete_client(client_id):
    """Delete a client (admin only)."""
    try:
        client = Client.query.get(client_id)
        if not client:
            return jsonify({'message': 'Client not found'}), 404
        
        # Soft delete by setting is_active to False
        client.is_active = False
        client.user.is_active = False
        client.updated_at = datetime.utcnow()
        client.user.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({'message': 'Client deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to delete client: {str(e)}'}), 500

@admin_bp.route('/admin/clients/<int:client_id>/websites', methods=['GET'])
@admin_required
def get_client_websites(client_id):
    """Get all websites for a specific client (admin only)."""
    try:
        client = Client.query.get(client_id)
        if not client:
            return jsonify({'message': 'Client not found'}), 404
        
        websites_data = [website.to_dict() for website in client.websites]
        
        return jsonify({
            'client_id': client_id,
            'company_name': client.company_name,
            'websites': websites_data,
            'total': len(websites_data)
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to get client websites: {str(e)}'}), 500

@admin_bp.route('/admin/stats', methods=['GET'])
@admin_required
def get_admin_stats():
    """Get admin dashboard statistics."""
    try:
        stats = {
            'total_clients': Client.query.filter_by(is_active=True).count(),
            'total_websites': Website.query.filter_by(is_active=True).count(),
            'total_users': User.query.filter_by(is_active=True).count(),
            'clients_by_plan': {}
        }
        
        # Get clients by subscription plan
        plans = db.session.query(
            Client.subscription_plan, 
            db.func.count(Client.id)
        ).filter(Client.is_active == True).group_by(Client.subscription_plan).all()
        
        for plan, count in plans:
            stats['clients_by_plan'][plan] = count
        
        # Recent activity (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        stats['recent_clients'] = Client.query.filter(
            Client.created_at >= thirty_days_ago
        ).count()
        
        stats['recent_websites'] = Website.query.filter(
            Website.created_at >= thirty_days_ago
        ).count()
        
        return jsonify(stats), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to get admin stats: {str(e)}'}), 500

@admin_bp.route('/admin/clients/<int:client_id>/impersonate', methods=['POST'])
@admin_required
def impersonate_client(client_id):
    """Impersonate a client for testing (admin only)."""
    try:
        client = Client.query.get(client_id)
        if not client:
            return jsonify({'message': 'Client not found'}), 404
        
        if not client.is_active or not client.user.is_active:
            return jsonify({'message': 'Client account is inactive'}), 400
        
        # Create tokens for the client user
        from flask_jwt_extended import create_access_token, create_refresh_token
        
        access_token = create_access_token(identity=client.user.id)
        refresh_token = create_refresh_token(identity=client.user.id)
        
        return jsonify({
            'message': f'Impersonating client: {client.company_name}',
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': client.user.to_dict(),
            'client': client.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to impersonate client: {str(e)}'}), 500

