from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.user import db, User, Client, Website
from datetime import datetime, timedelta
from functools import wraps

admin_users_bp = Blueprint('admin_users', __name__)

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

@admin_users_bp.route('/admin/users', methods=['GET'])
@admin_required
def get_all_users():
    """Get all users with detailed information for admin panel."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        search = request.args.get('search', '')
        status_filter = request.args.get('status', 'all')
        
        query = User.query.outerjoin(Client)
        
        # Search filter
        if search:
            query = query.filter(
                db.or_(
                    User.email.ilike(f'%{search}%'),
                    User.full_name.ilike(f'%{search}%'),
                    Client.company_name.ilike(f'%{search}%')
                )
            )
        
        # Status filter
        if status_filter != 'all':
            if status_filter == 'active':
                query = query.filter(User.is_active == True)
            elif status_filter == 'trial':
                query = query.filter(User.subscription_status == 'trial')
            elif status_filter == 'suspended':
                query = query.filter(User.is_active == False)
            elif status_filter == 'expired':
                query = query.filter(User.subscription_status == 'expired')
        
        users = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        users_data = []
        for user in users.items:
            user_dict = user.to_dict()
            
            # Add client information if exists
            if user.client:
                user_dict['company'] = user.client.company_name
                user_dict['subscription_plan'] = user.client.subscription_plan
                user_dict['websiteCount'] = len(user.client.websites)
            else:
                user_dict['company'] = None
                user_dict['subscription_plan'] = 'free'
                user_dict['websiteCount'] = 0
            
            # Add computed fields
            user_dict['status'] = get_user_status(user)
            user_dict['plan'] = get_user_plan(user)
            user_dict['customBilling'] = getattr(user, 'custom_billing', False)
            user_dict['lastLogin'] = user.last_login_at.isoformat() if user.last_login_at else None
            
            users_data.append(user_dict)
        
        return jsonify({
            'users': users_data,
            'pagination': {
                'page': users.page,
                'pages': users.pages,
                'per_page': users.per_page,
                'total': users.total,
                'has_next': users.has_next,
                'has_prev': users.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to get users: {str(e)}'}), 500

@admin_users_bp.route('/admin/users/<int:user_id>/status', methods=['PUT'])
@admin_required
def update_user_status(user_id):
    """Update user account status (active, suspended, etc.)."""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        data = request.get_json()
        status = data.get('status')
        
        if status not in ['active', 'trial', 'suspended', 'expired']:
            return jsonify({'message': 'Invalid status'}), 400
        
        # Update user status
        if status == 'active':
            user.is_active = True
            user.subscription_status = 'active'
        elif status == 'trial':
            user.is_active = True
            user.subscription_status = 'trial'
            # Set trial expiration if not set
            if not user.trial_ends_at:
                user.trial_ends_at = datetime.utcnow() + timedelta(days=14)
        elif status == 'suspended':
            user.is_active = False
            user.subscription_status = 'suspended'
        elif status == 'expired':
            user.is_active = False
            user.subscription_status = 'expired'
        
        user.updated_at = datetime.utcnow()
        
        # Update client if exists
        if user.client:
            user.client.is_active = user.is_active
            user.client.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'message': 'User status updated successfully',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to update user status: {str(e)}'}), 500

@admin_users_bp.route('/admin/users/<int:user_id>/plan', methods=['PUT'])
@admin_required
def update_user_plan(user_id):
    """Update user subscription plan and billing settings."""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        data = request.get_json()
        plan = data.get('plan')
        custom_billing = data.get('customBilling', False)
        
        if plan not in ['free', 'starter', 'professional', 'agency']:
            return jsonify({'message': 'Invalid plan'}), 400
        
        # Update user plan
        user.subscription_plan = plan
        user.custom_billing = custom_billing
        user.updated_at = datetime.utcnow()
        
        # Update client if exists
        if user.client:
            user.client.subscription_plan = plan
            user.client.updated_at = datetime.utcnow()
        else:
            # Create client record if doesn't exist
            client = Client(
                user_id=user.id,
                company_name=user.full_name or 'Individual',
                contact_email=user.email,
                subscription_plan=plan
            )
            db.session.add(client)
        
        # Set appropriate status based on plan
        if plan == 'free':
            user.subscription_status = 'trial'
            if not user.trial_ends_at:
                user.trial_ends_at = datetime.utcnow() + timedelta(days=14)
        else:
            user.subscription_status = 'active'
            user.is_active = True
        
        db.session.commit()
        
        return jsonify({
            'message': 'User plan updated successfully',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to update user plan: {str(e)}'}), 500

@admin_users_bp.route('/admin/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    """Update user details including personal info and settings."""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        data = request.get_json()
        
        # Update basic user fields
        if 'name' in data:
            user.full_name = data['name']
        if 'email' in data:
            # Check if email is already taken
            existing_user = User.query.filter(
                User.email == data['email'], 
                User.id != user_id
            ).first()
            if existing_user:
                return jsonify({'message': 'Email already in use'}), 409
            user.email = data['email']
        
        # Update subscription settings
        if 'status' in data:
            status = data['status']
            if status == 'active':
                user.is_active = True
                user.subscription_status = 'active'
            elif status == 'trial':
                user.is_active = True
                user.subscription_status = 'trial'
            elif status == 'suspended':
                user.is_active = False
                user.subscription_status = 'suspended'
            elif status == 'expired':
                user.is_active = False
                user.subscription_status = 'expired'
        
        if 'plan' in data:
            user.subscription_plan = data['plan']
        
        if 'customBilling' in data:
            user.custom_billing = data['customBilling']
        
        if 'websiteLimit' in data:
            user.website_limit = data['websiteLimit']
        
        if 'expirationDate' in data and data['expirationDate']:
            user.subscription_ends_at = datetime.fromisoformat(data['expirationDate'])
        
        if 'notes' in data:
            user.admin_notes = data['notes']
        
        user.updated_at = datetime.utcnow()
        
        # Update client record if exists
        if user.client:
            if 'company' in data:
                user.client.company_name = data['company']
            if 'plan' in data:
                user.client.subscription_plan = data['plan']
            user.client.updated_at = datetime.utcnow()
        elif 'company' in data:
            # Create client record if company is provided
            client = Client(
                user_id=user.id,
                company_name=data['company'],
                contact_email=user.email,
                subscription_plan=user.subscription_plan
            )
            db.session.add(client)
        
        db.session.commit()
        
        return jsonify({
            'message': 'User updated successfully',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to update user: {str(e)}'}), 500

@admin_users_bp.route('/admin/stats', methods=['GET'])
@admin_required
def get_admin_stats():
    """Get comprehensive admin dashboard statistics."""
    try:
        # Basic counts
        total_users = User.query.count()
        active_users = User.query.filter_by(is_active=True).count()
        trial_users = User.query.filter_by(subscription_status='trial').count()
        custom_billing_users = User.query.filter_by(custom_billing=True).count()
        
        # Revenue calculation (simplified)
        plan_prices = {
            'starter': 49,
            'professional': 99,
            'agency': 199
        }
        
        monthly_revenue = 0
        for plan, price in plan_prices.items():
            count = User.query.filter(
                User.subscription_plan == plan,
                User.is_active == True,
                User.custom_billing == False
            ).count()
            monthly_revenue += count * price
        
        # Recent activity (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_signups = User.query.filter(
            User.created_at >= thirty_days_ago
        ).count()
        
        stats = {
            'totalUsers': total_users,
            'activeUsers': active_users,
            'trialUsers': trial_users,
            'customBilling': custom_billing_users,
            'monthlyRevenue': monthly_revenue,
            'recentSignups': recent_signups
        }
        
        return jsonify({'stats': stats}), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to get admin stats: {str(e)}'}), 500

@admin_users_bp.route('/admin/users/<int:user_id>/impersonate', methods=['POST'])
@admin_required
def impersonate_user(user_id):
    """Impersonate a user for support purposes."""
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        if not user.is_active:
            return jsonify({'message': 'Cannot impersonate inactive user'}), 400
        
        # Create tokens for the target user
        from flask_jwt_extended import create_access_token, create_refresh_token
        
        access_token = create_access_token(identity=user.id)
        refresh_token = create_refresh_token(identity=user.id)
        
        return jsonify({
            'message': f'Impersonating user: {user.full_name or user.email}',
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to impersonate user: {str(e)}'}), 500

def get_user_status(user):
    """Determine user status based on various factors."""
    if not user.is_active:
        return 'suspended'
    elif user.subscription_status == 'trial':
        return 'trial'
    elif user.subscription_status == 'expired':
        return 'expired'
    elif user.subscription_status == 'active':
        return 'active'
    else:
        return 'trial'

def get_user_plan(user):
    """Get user's current plan."""
    if hasattr(user, 'subscription_plan') and user.subscription_plan:
        return user.subscription_plan
    elif user.client and user.client.subscription_plan:
        return user.client.subscription_plan
    else:
        return 'free'

