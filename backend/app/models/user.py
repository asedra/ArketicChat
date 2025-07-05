"""
User Management Models for ATTILA AI Enhanced Function Management System
Supports authentication, authorization, role-based access control, and multi-tenancy
"""
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from enum import Enum

from sqlalchemy import Column, String, DateTime, Boolean, Text, Integer, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel, EmailStr, validator, Field
import bcrypt
import jwt
from passlib.context import CryptContext

from ..core.database import Base
from ..core.config import settings


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserRole(str, Enum):
    """User roles for role-based access control"""
    SUPER_ADMIN = "super_admin"      # System administrator
    ADMIN = "admin"                  # Organization administrator
    MANAGER = "manager"              # Team manager
    DEVELOPER = "developer"          # Function developer
    USER = "user"                    # Basic user
    VIEWER = "viewer"                # Read-only access


class UserStatus(str, Enum):
    """User account status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class SubscriptionPlan(str, Enum):
    """Subscription plans for multi-tenancy"""
    FREE = "free"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


# Database Models
class Organization(Base):
    """Organization model for multi-tenancy"""
    __tablename__ = "organizations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Subscription and billing
    subscription_plan = Column(String(50), default=SubscriptionPlan.FREE)
    subscription_expires_at = Column(DateTime)
    billing_email = Column(String(255))
    
    # Usage limits
    max_users = Column(Integer, default=5)
    max_functions = Column(Integer, default=50)
    max_executions_per_month = Column(Integer, default=10000)
    
    # Organization settings
    settings = Column(JSON, default=dict)
    allowed_domains = Column(JSON, default=list)  # Email domains for auto-join
    
    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    api_keys = relationship("ApiKey", back_populates="organization", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="organization", cascade="all, delete-orphan")


class User(Base):
    """User model with authentication and authorization"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    
    # Authentication
    hashed_password = Column(String(255), nullable=False)
    is_email_verified = Column(Boolean, default=False)
    email_verification_token = Column(String(255))
    password_reset_token = Column(String(255))
    password_reset_expires = Column(DateTime)
    
    # Authorization
    role = Column(String(50), default=UserRole.USER)
    permissions = Column(JSON, default=list)  # Additional fine-grained permissions
    
    # Multi-tenancy
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    
    # Profile and preferences
    avatar_url = Column(String(500))
    timezone = Column(String(50), default="UTC")
    language = Column(String(10), default="en")
    theme = Column(String(20), default="auto")
    
    # Security and session management
    two_factor_enabled = Column(Boolean, default=False)
    two_factor_secret = Column(String(32))
    last_login_at = Column(DateTime)
    last_login_ip = Column(String(45))
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime)
    
    # Account status
    status = Column(String(20), default=UserStatus.ACTIVE)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization", back_populates="users")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    
    @property
    def full_name(self) -> str:
        """Get user's full name"""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_admin(self) -> bool:
        """Check if user has admin privileges"""
        return self.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]
    
    @property
    def is_locked(self) -> bool:
        """Check if account is locked"""
        return self.locked_until and self.locked_until > datetime.utcnow()
    
    def verify_password(self, password: str) -> bool:
        """Verify password against hash"""
        return pwd_context.verify(password, self.hashed_password)
    
    def set_password(self, password: str):
        """Hash and set password"""
        self.hashed_password = pwd_context.hash(password)
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission"""
        # Super admin has all permissions
        if self.role == UserRole.SUPER_ADMIN:
            return True
        
        # Check role-based permissions
        role_permissions = get_role_permissions(self.role)
        if permission in role_permissions:
            return True
        
        # Check additional permissions
        return permission in (self.permissions or [])
    
    def generate_access_token(self, expires_delta: Optional[timedelta] = None) -> str:
        """Generate JWT access token"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode = {
            "sub": str(self.id),
            "email": self.email,
            "role": self.role,
            "org_id": str(self.organization_id),
            "exp": expire
        }
        
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt


class ApiKey(Base):
    """API Key model for programmatic access"""
    __tablename__ = "api_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Key data
    key_hash = Column(String(255), nullable=False, unique=True, index=True)
    key_prefix = Column(String(10), nullable=False)  # First 8 chars for identification
    
    # Access control
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    scopes = Column(JSON, default=list)  # API scopes/permissions
    
    # Usage tracking
    last_used_at = Column(DateTime)
    usage_count = Column(Integer, default=0)
    rate_limit = Column(Integer, default=1000)  # Requests per hour
    
    # Metadata
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User")
    organization = relationship("Organization", back_populates="api_keys")
    
    @property
    def is_expired(self) -> bool:
        """Check if API key is expired"""
        return self.expires_at and self.expires_at < datetime.utcnow()


class UserSession(Base):
    """User session tracking for security"""
    __tablename__ = "user_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Session data
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    refresh_token = Column(String(255), unique=True, nullable=False, index=True)
    
    # Client information
    ip_address = Column(String(45))
    user_agent = Column(Text)
    device_fingerprint = Column(String(255))
    
    # Session lifecycle
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    @property
    def is_expired(self) -> bool:
        """Check if session is expired"""
        return self.expires_at and self.expires_at < datetime.utcnow()


class AuditLog(Base):
    """Audit log for compliance and security monitoring"""
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Event information
    event_type = Column(String(100), nullable=False, index=True)
    event_category = Column(String(50), nullable=False, index=True)
    event_description = Column(Text)
    
    # Actor information
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    actor_type = Column(String(20), default="user")  # user, system, api_key
    actor_identifier = Column(String(255))  # API key ID, system process, etc.
    
    # Target information
    resource_type = Column(String(100))  # function, execution, user, etc.
    resource_id = Column(String(255))
    resource_name = Column(String(255))
    
    # Request context
    ip_address = Column(String(45))
    user_agent = Column(Text)
    request_id = Column(String(255))
    session_id = Column(String(255))
    
    # Event details
    changes = Column(JSON)  # Before/after values for modifications
    metadata = Column(JSON)  # Additional context
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    organization = relationship("Organization", back_populates="audit_logs")


# Pydantic Models for API
class OrganizationBase(BaseModel):
    """Base organization model"""
    name: str = Field(..., min_length=2, max_length=255)
    display_name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    subscription_plan: SubscriptionPlan = SubscriptionPlan.FREE
    billing_email: Optional[EmailStr] = None
    allowed_domains: List[str] = []


class OrganizationCreate(OrganizationBase):
    """Organization creation model"""
    pass


class OrganizationUpdate(BaseModel):
    """Organization update model"""
    display_name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    subscription_plan: Optional[SubscriptionPlan] = None
    billing_email: Optional[EmailStr] = None
    allowed_domains: Optional[List[str]] = None
    max_users: Optional[int] = Field(None, ge=1)
    max_functions: Optional[int] = Field(None, ge=1)
    max_executions_per_month: Optional[int] = Field(None, ge=1)
    settings: Optional[Dict[str, Any]] = None


class OrganizationResponse(OrganizationBase):
    """Organization response model"""
    id: uuid.UUID
    max_users: int
    max_functions: int
    max_executions_per_month: int
    subscription_expires_at: Optional[datetime]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserBase(BaseModel):
    """Base user model"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    role: UserRole = UserRole.USER
    timezone: str = "UTC"
    language: str = "en"


class UserCreate(UserBase):
    """User creation model"""
    password: str = Field(..., min_length=8)
    organization_id: Optional[uuid.UUID] = None
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserUpdate(BaseModel):
    """User update model"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    role: Optional[UserRole] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    theme: Optional[str] = None
    avatar_url: Optional[str] = None
    permissions: Optional[List[str]] = None
    status: Optional[UserStatus] = None


class UserResponse(UserBase):
    """User response model"""
    id: uuid.UUID
    organization_id: uuid.UUID
    full_name: str
    avatar_url: Optional[str]
    theme: str
    permissions: List[str]
    status: UserStatus
    is_email_verified: bool
    two_factor_enabled: bool
    last_login_at: Optional[datetime]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ApiKeyCreate(BaseModel):
    """API key creation model"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    scopes: List[str] = []
    expires_at: Optional[datetime] = None
    rate_limit: int = Field(1000, ge=1, le=10000)


class ApiKeyResponse(BaseModel):
    """API key response model"""
    id: uuid.UUID
    name: str
    description: Optional[str]
    key_prefix: str
    scopes: List[str]
    last_used_at: Optional[datetime]
    usage_count: int
    rate_limit: int
    expires_at: Optional[datetime]
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    """Login request model"""
    email: EmailStr
    password: str
    remember_me: bool = False


class LoginResponse(BaseModel):
    """Login response model"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class AuditLogResponse(BaseModel):
    """Audit log response model"""
    id: uuid.UUID
    event_type: str
    event_category: str
    event_description: Optional[str]
    actor_type: str
    actor_identifier: Optional[str]
    resource_type: Optional[str]
    resource_id: Optional[str]
    resource_name: Optional[str]
    ip_address: Optional[str]
    success: bool
    error_message: Optional[str]
    timestamp: datetime
    
    class Config:
        from_attributes = True


# Role-based permissions
def get_role_permissions(role: UserRole) -> List[str]:
    """Get permissions for a role"""
    permissions = {
        UserRole.SUPER_ADMIN: [
            "admin:*",  # All admin permissions
            "organization:*",  # All organization permissions
            "user:*",  # All user permissions
            "function:*",  # All function permissions
            "execution:*",  # All execution permissions
            "analytics:*",  # All analytics permissions
            "audit:*"  # All audit permissions
        ],
        UserRole.ADMIN: [
            "organization:read", "organization:update",
            "user:create", "user:read", "user:update", "user:delete",
            "function:*",
            "execution:*",
            "analytics:read",
            "audit:read"
        ],
        UserRole.MANAGER: [
            "user:read",
            "function:create", "function:read", "function:update", "function:delete",
            "execution:create", "execution:read",
            "analytics:read"
        ],
        UserRole.DEVELOPER: [
            "function:create", "function:read", "function:update",
            "execution:create", "execution:read",
            "analytics:read"
        ],
        UserRole.USER: [
            "function:read",
            "execution:create", "execution:read"
        ],
        UserRole.VIEWER: [
            "function:read",
            "execution:read",
            "analytics:read"
        ]
    }
    
    return permissions.get(role, [])