import os
import sys
import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from src.models.user import db, User, Client, Website, Keyword, KeywordRanking, GA4DataCache
from src.routes.user import user_bp
from src.routes.auth import auth_bp
from src.routes.websites import websites_bp
from src.routes.analytics import analytics_bp
from src.routes.admin import admin_bp
from src.routes.admin_users import admin_users_bp

def create_app():
    app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)
    app.config['JWT_CSRF_IN_COOKIES'] = False  # Disable CSRF protection
    
    # Database configuration
    database_url = os.getenv('DATABASE_URL', f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}")
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    CORS(app, origins="*", allow_headers=["Content-Type", "Authorization"])
    jwt = JWTManager(app)
    db.init_app(app)
    
    # Configure JWT to allow integer subjects
    app.config['JWT_IDENTITY_CLAIM'] = 'sub'
    
    # JWT error handlers
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        print(f"JWT expired: {jwt_payload}")
        return jsonify({'message': 'Token has expired'}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        print(f"JWT invalid: {error}")
        return jsonify({'message': 'Invalid token'}), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        print(f"JWT missing: {error}")
        return jsonify({'message': 'Authorization token is required'}), 401
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(admin_bp, url_prefix='/api')
    app.register_blueprint(admin_users_bp, url_prefix='/api')
    app.register_blueprint(analytics_bp, url_prefix='/api')
    app.register_blueprint(websites_bp, url_prefix='/api')
    app.register_blueprint(user_bp, url_prefix='/api')
    
    # Create database tables
    with app.app_context():
        # Create database directory if it doesn't exist
        db_dir = os.path.dirname(database_url.replace('sqlite:///', ''))
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
        
        db.create_all()
        
        # Create default admin user if it doesn't exist
        admin_user = User.query.filter_by(email='adam@infinitedesigns.io').first()
        if not admin_user:
            admin_user = User(
                email='adam@infinitedesigns.io',
                full_name='Adam - Infinite Designs',
                role='admin'
            )
            admin_user.set_password('cJttMY6JKhu_zKY')
            db.session.add(admin_user)
            db.session.commit()
            print("Created admin user: adam@infinitedesigns.io")
    
    # Health check endpoint
    @app.route('/api/health')
    def health_check():
        return jsonify({'status': 'healthy', 'message': 'Analytics Dashboard API is running'})
    
    # Serve frontend
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        static_folder_path = app.static_folder
        if static_folder_path is None:
            return "Static folder not configured", 404

        if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
            return send_from_directory(static_folder_path, path)
        else:
            index_path = os.path.join(static_folder_path, 'index.html')
            if os.path.exists(index_path):
                return send_from_directory(static_folder_path, 'index.html')
            else:
                return jsonify({
                    'message': 'Analytics Dashboard API',
                    'version': '1.0.0',
                    'endpoints': {
                        'health': '/api/health',
                        'auth': '/api/auth/*',
                        'users': '/api/users/*'
                    }
                })
    
    return app

app = create_app()

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5002))
    app.run(host='0.0.0.0', port=port, debug=False)