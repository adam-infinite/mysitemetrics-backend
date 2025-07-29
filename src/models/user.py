from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='client')
    is_active = db.Column(db.Boolean, default=True)
    
    # Subscription management fields
    subscription_status = db.Column(db.String(50), default='trial')  # trial, active, expired, suspended
    subscription_plan = db.Column(db.String(50), default='free')     # free, starter, professional, agency
    custom_billing = db.Column(db.Boolean, default=False)            # For manual billing arrangements
    website_limit = db.Column(db.Integer, default=1)                 # Number of websites allowed
    trial_ends_at = db.Column(db.DateTime)                           # Trial expiration date
    subscription_ends_at = db.Column(db.DateTime)                    # Subscription expiration date
    last_login_at = db.Column(db.DateTime)                           # Last login timestamp
    admin_notes = db.Column(db.Text)                                 # Internal admin notes
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    client = db.relationship('Client', backref='user', uselist=False, cascade='all, delete-orphan')

    def set_password(self, password):
        """Set password hash."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check password against hash."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email}>'

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role,
            'is_active': self.is_active,
            'subscription_status': self.subscription_status,
            'subscription_plan': self.subscription_plan,
            'custom_billing': self.custom_billing,
            'website_limit': self.website_limit,
            'trial_ends_at': self.trial_ends_at.isoformat() if self.trial_ends_at else None,
            'subscription_ends_at': self.subscription_ends_at.isoformat() if self.subscription_ends_at else None,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
            'admin_notes': self.admin_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Client(db.Model):
    __tablename__ = 'clients'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    company_name = db.Column(db.String(255), nullable=False)
    contact_email = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    address = db.Column(db.Text)
    subscription_plan = db.Column(db.String(50), default='basic')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    websites = db.relationship('Website', backref='client', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Client {self.company_name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'company_name': self.company_name,
            'contact_email': self.contact_email,
            'phone': self.phone,
            'address': self.address,
            'subscription_plan': self.subscription_plan,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Website(db.Model):
    __tablename__ = 'websites'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    domain = db.Column(db.String(255), nullable=False)
    ga4_property_id = db.Column(db.String(100))
    search_console_url = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    keywords = db.relationship('Keyword', backref='website', cascade='all, delete-orphan')
    ga4_data_cache = db.relationship('GA4DataCache', backref='website', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Website {self.domain}>'

    def to_dict(self):
        return {
            'id': self.id,
            'client_id': self.client_id,
            'domain': self.domain,
            'ga4_property_id': self.ga4_property_id,
            'search_console_url': self.search_console_url,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Keyword(db.Model):
    __tablename__ = 'keywords'
    
    id = db.Column(db.Integer, primary_key=True)
    website_id = db.Column(db.Integer, db.ForeignKey('websites.id'), nullable=False)
    keyword = db.Column(db.String(255), nullable=False)
    target_url = db.Column(db.String(500))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    rankings = db.relationship('KeywordRanking', backref='keyword', cascade='all, delete-orphan')
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('website_id', 'keyword', name='unique_website_keyword'),)

    def __repr__(self):
        return f'<Keyword {self.keyword}>'

    def to_dict(self):
        return {
            'id': self.id,
            'website_id': self.website_id,
            'keyword': self.keyword,
            'target_url': self.target_url,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class KeywordRanking(db.Model):
    __tablename__ = 'keyword_rankings'
    
    id = db.Column(db.Integer, primary_key=True)
    keyword_id = db.Column(db.Integer, db.ForeignKey('keywords.id'), nullable=False)
    position = db.Column(db.Integer)
    search_volume = db.Column(db.Integer)
    clicks = db.Column(db.Integer, default=0)
    impressions = db.Column(db.Integer, default=0)
    ctr = db.Column(db.Numeric(5, 4), default=0)
    tracking_date = db.Column(db.Date, nullable=False)
    data_source = db.Column(db.String(50), nullable=False)  # 'search_console', 'serpapi', etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('keyword_id', 'tracking_date', 'data_source', name='unique_keyword_date_source'),)

    def __repr__(self):
        return f'<KeywordRanking {self.keyword_id} - {self.tracking_date}>'

    def to_dict(self):
        return {
            'id': self.id,
            'keyword_id': self.keyword_id,
            'position': self.position,
            'search_volume': self.search_volume,
            'clicks': self.clicks,
            'impressions': self.impressions,
            'ctr': float(self.ctr) if self.ctr else 0,
            'tracking_date': self.tracking_date.isoformat() if self.tracking_date else None,
            'data_source': self.data_source,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class GA4DataCache(db.Model):
    __tablename__ = 'ga4_data_cache'
    
    id = db.Column(db.Integer, primary_key=True)
    website_id = db.Column(db.Integer, db.ForeignKey('websites.id'), nullable=False)
    metric_name = db.Column(db.String(100), nullable=False)
    dimension_name = db.Column(db.String(100))
    dimension_value = db.Column(db.String(255))
    metric_value = db.Column(db.Numeric(15, 4), nullable=False)
    date_range_start = db.Column(db.Date, nullable=False)
    date_range_end = db.Column(db.Date, nullable=False)
    cached_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f'<GA4DataCache {self.metric_name} - {self.website_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'website_id': self.website_id,
            'metric_name': self.metric_name,
            'dimension_name': self.dimension_name,
            'dimension_value': self.dimension_value,
            'metric_value': float(self.metric_value) if self.metric_value else 0,
            'date_range_start': self.date_range_start.isoformat() if self.date_range_start else None,
            'date_range_end': self.date_range_end.isoformat() if self.date_range_end else None,
            'cached_at': self.cached_at.isoformat() if self.cached_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }

class GA4Account(db.Model):
    __tablename__ = 'ga4_accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    google_account_id = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    access_token = db.Column(db.Text, nullable=False)
    refresh_token = db.Column(db.Text, nullable=False)
    token_expires_at = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    properties = db.relationship('GA4Property', backref='account', cascade='all, delete-orphan')
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('user_id', 'google_account_id', name='unique_user_google_account'),)

    def __repr__(self):
        return f'<GA4Account {self.email}>'

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'google_account_id': self.google_account_id,
            'email': self.email,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class GA4Property(db.Model):
    __tablename__ = 'ga4_properties'
    
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('ga4_accounts.id'), nullable=False)
    property_id = db.Column(db.String(100), nullable=False)
    property_name = db.Column(db.String(255), nullable=False)
    website_url = db.Column(db.String(500))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('account_id', 'property_id', name='unique_account_property'),)

    def __repr__(self):
        return f'<GA4Property {self.property_name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'account_id': self.account_id,
            'property_id': self.property_id,
            'property_name': self.property_name,
            'website_url': self.website_url,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

