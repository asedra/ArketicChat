"""
Authentication Service for ATTILA AI Enhanced Function Management System
Handles user authentication, authorization, session management, and security
"""
import asyncio
import secrets
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from functools import wraps

import jwt
from sqlalchemy import select, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import pyotp
import qrcode
from io import BytesIO
import base64

from ..core.database import get_async_db
from ..core.config import settings
from ..models.user import (
    User, Organization, ApiKey, UserSession, AuditLog,
    UserRole, UserStatus, UserCreate, LoginRequest,
    pwd_context, get_role_permissions
)


class AuthenticationError(Exception):
    """Authentication-related errors"""
    pass


class AuthorizationError(Exception):
    """Authorization-related errors"""
    pass


class RateLimitError(Exception):
    """Rate limiting errors"""
    pass


security = HTTPBearer()


class AuthService:
    """
    Comprehensive authentication and authorization service
    """
    
    def __init__(self):
        self.failed_login_cache = {}  # In-memory cache for rate limiting
        self.session_cache = {}  # Session cache for performance
        
    async def register_user(
        self, 
        user_data: UserCreate, 
        organization_id: Optional[uuid.UUID] = None,
        session: Optional[AsyncSession] = None
    ) -> User:
        """
        Register a new user with organization support
        
        Args:
            user_data: User creation data
            organization_id: Optional organization ID
            session: Database session
            
        Returns:
            Created user object
        """
        if not session:
            async with get_async_db() as session:
                return await self._register_user_impl(user_data, organization_id, session)
        else:
            return await self._register_user_impl(user_data, organization_id, session)
    
    async def _register_user_impl(
        self, 
        user_data: UserCreate, 
        organization_id: Optional[uuid.UUID],
        session: AsyncSession
    ) -> User:
        """Internal implementation of user registration"""
        
        # Check if user already exists
        existing_user = await session.execute(
            select(User).where(
                or_(User.email == user_data.email, User.username == user_data.username)
            )
        )
        if existing_user.scalar_one_or_none():
            raise AuthenticationError("User with this email or username already exists")
        
        # Handle organization
        if not organization_id:
            # Check if user's domain matches an existing organization
            domain = user_data.email.split('@')[1]
            org_result = await session.execute(
                select(Organization).where(
                    Organization.allowed_domains.contains([domain])
                )
            )
            org = org_result.scalar_one_or_none()
            
            if not org:
                # Create a new organization for the user
                org = Organization(
                    name=domain.replace('.', '_'),
                    display_name=f"{domain.split('.')[0].title()} Organization",
                    description=f"Auto-created organization for {domain}"
                )
                session.add(org)
                await session.flush()
                organization_id = org.id
            else:
                organization_id = org.id
        
        # Create user
        user_dict = user_data.dict(exclude={'password'})
        user_dict['organization_id'] = organization_id
        
        user = User(**user_dict)
        user.set_password(user_data.password)
        user.email_verification_token = secrets.token_urlsafe(32)
        
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        # Log registration
        await self.log_audit_event(
            session=session,
            event_type="user_registered",
            event_category="authentication",
            event_description=f"User {user.email} registered",
            user_id=user.id,
            organization_id=user.organization_id,
            success=True
        )
        
        return user
    
    async def authenticate_user(
        self, 
        email: str, 
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session: Optional[AsyncSession] = None
    ) -> Tuple[User, str, str]:
        """
        Authenticate user and create session
        
        Args:
            email: User email
            password: User password
            ip_address: Client IP address
            user_agent: Client user agent
            session: Database session
            
        Returns:
            Tuple of (user, access_token, refresh_token)
        """
        if not session:
            async with get_async_db() as session:
                return await self._authenticate_user_impl(
                    email, password, ip_address, user_agent, session
                )
        else:
            return await self._authenticate_user_impl(
                email, password, ip_address, user_agent, session
            )
    
    async def _authenticate_user_impl(
        self,
        email: str,
        password: str,
        ip_address: Optional[str],
        user_agent: Optional[str],
        session: AsyncSession
    ) -> Tuple[User, str, str]:
        """Internal implementation of user authentication"""
        
        # Check rate limiting
        await self._check_rate_limit(email, ip_address)
        
        # Get user
        result = await session.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await self._record_failed_login(email, ip_address, "user_not_found")
            raise AuthenticationError("Invalid credentials")
        
        # Check account status
        if not user.is_active:
            await self._record_failed_login(email, ip_address, "account_inactive")
            raise AuthenticationError("Account is inactive")
        
        if user.status != UserStatus.ACTIVE:
            await self._record_failed_login(email, ip_address, "account_suspended")
            raise AuthenticationError("Account is suspended")
        
        if user.is_locked:
            await self._record_failed_login(email, ip_address, "account_locked")
            raise AuthenticationError("Account is temporarily locked")
        
        # Verify password
        if not user.verify_password(password):
            await self._record_failed_login(email, ip_address, "invalid_password")
            user.failed_login_attempts += 1
            
            # Lock account after 5 failed attempts
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.utcnow() + timedelta(minutes=30)
            
            await session.commit()
            raise AuthenticationError("Invalid credentials")
        
        # Reset failed attempts on successful login
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = datetime.utcnow()
        user.last_login_ip = ip_address
        
        # Create session
        access_token = user.generate_access_token()
        refresh_token = secrets.token_urlsafe(32)
        
        user_session = UserSession(
            user_id=user.id,
            session_token=hashlib.sha256(access_token.encode()).hexdigest(),
            refresh_token=hashlib.sha256(refresh_token.encode()).hexdigest(),
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        
        session.add(user_session)
        await session.commit()
        
        # Log successful login
        await self.log_audit_event(
            session=session,
            event_type="user_login",
            event_category="authentication",
            event_description=f"User {user.email} logged in successfully",
            user_id=user.id,
            organization_id=user.organization_id,
            ip_address=ip_address,
            success=True
        )
        
        return user, access_token, refresh_token
    
    async def verify_token(
        self, 
        token: str,
        session: Optional[AsyncSession] = None
    ) -> User:
        """
        Verify JWT token and return user
        
        Args:
            token: JWT access token
            session: Database session
            
        Returns:
            User object if valid
        """
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id: str = payload.get("sub")
            
            if user_id is None:
                raise AuthenticationError("Invalid token")
                
        except jwt.PyJWTError:
            raise AuthenticationError("Invalid token")
        
        if not session:
            async with get_async_db() as session:
                return await self._verify_token_impl(user_id, token, session)
        else:
            return await self._verify_token_impl(user_id, token, session)
    
    async def _verify_token_impl(
        self, 
        user_id: str, 
        token: str, 
        session: AsyncSession
    ) -> User:
        """Internal implementation of token verification"""
        
        # Get user
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise AuthenticationError("User not found")
        
        if not user.is_active:
            raise AuthenticationError("User is inactive")
        
        # Verify session exists
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        session_result = await session.execute(
            select(UserSession).where(
                and_(
                    UserSession.user_id == user.id,
                    UserSession.session_token == token_hash,
                    UserSession.is_active == True
                )
            )
        )
        user_session = session_result.scalar_one_or_none()
        
        if not user_session or user_session.is_expired:
            raise AuthenticationError("Session expired")
        
        # Update last active time
        user_session.last_active_at = datetime.utcnow()
        await session.commit()
        
        return user
    
    async def refresh_token(
        self, 
        refresh_token: str,
        session: Optional[AsyncSession] = None
    ) -> Tuple[str, str]:
        """
        Refresh access token using refresh token
        
        Args:
            refresh_token: Refresh token
            session: Database session
            
        Returns:
            Tuple of (new_access_token, new_refresh_token)
        """
        if not session:
            async with get_async_db() as session:
                return await self._refresh_token_impl(refresh_token, session)
        else:
            return await self._refresh_token_impl(refresh_token, session)
    
    async def _refresh_token_impl(
        self, 
        refresh_token: str, 
        session: AsyncSession
    ) -> Tuple[str, str]:
        """Internal implementation of token refresh"""
        
        refresh_token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        
        # Find session by refresh token
        result = await session.execute(
            select(UserSession).where(
                and_(
                    UserSession.refresh_token == refresh_token_hash,
                    UserSession.is_active == True
                )
            )
        )
        user_session = result.scalar_one_or_none()
        
        if not user_session or user_session.is_expired:
            raise AuthenticationError("Invalid refresh token")
        
        # Get user
        user_result = await session.execute(
            select(User).where(User.id == user_session.user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive")
        
        # Generate new tokens
        new_access_token = user.generate_access_token()
        new_refresh_token = secrets.token_urlsafe(32)
        
        # Update session
        user_session.session_token = hashlib.sha256(new_access_token.encode()).hexdigest()
        user_session.refresh_token = hashlib.sha256(new_refresh_token.encode()).hexdigest()
        user_session.last_active_at = datetime.utcnow()
        user_session.expires_at = datetime.utcnow() + timedelta(hours=24)
        
        await session.commit()
        
        return new_access_token, new_refresh_token
    
    async def logout(
        self, 
        token: str,
        session: Optional[AsyncSession] = None
    ) -> bool:
        """
        Logout user and invalidate session
        
        Args:
            token: Access token
            session: Database session
            
        Returns:
            Success status
        """
        if not session:
            async with get_async_db() as session:
                return await self._logout_impl(token, session)
        else:
            return await self._logout_impl(token, session)
    
    async def _logout_impl(self, token: str, session: AsyncSession) -> bool:
        """Internal implementation of logout"""
        
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Find and deactivate session
        result = await session.execute(
            update(UserSession)
            .where(UserSession.session_token == token_hash)
            .values(is_active=False)
        )
        
        if result.rowcount > 0:
            await session.commit()
            return True
        
        return False
    
    async def create_api_key(
        self,
        user: User,
        name: str,
        description: Optional[str] = None,
        scopes: List[str] = None,
        expires_at: Optional[datetime] = None,
        rate_limit: int = 1000,
        session: Optional[AsyncSession] = None
    ) -> Tuple[ApiKey, str]:
        """
        Create API key for programmatic access
        
        Args:
            user: User creating the API key
            name: API key name
            description: Optional description
            scopes: List of permissions/scopes
            expires_at: Optional expiration date
            rate_limit: Rate limit per hour
            session: Database session
            
        Returns:
            Tuple of (api_key_record, actual_key)
        """
        if not session:
            async with get_async_db() as session:
                return await self._create_api_key_impl(
                    user, name, description, scopes, expires_at, rate_limit, session
                )
        else:
            return await self._create_api_key_impl(
                user, name, description, scopes, expires_at, rate_limit, session
            )
    
    async def _create_api_key_impl(
        self,
        user: User,
        name: str,
        description: Optional[str],
        scopes: List[str],
        expires_at: Optional[datetime],
        rate_limit: int,
        session: AsyncSession
    ) -> Tuple[ApiKey, str]:
        """Internal implementation of API key creation"""
        
        # Generate API key
        api_key = f"attila_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        key_prefix = api_key[:12]
        
                 # Create API key record
        api_key_record = ApiKey(
            name=name,
            description=description,
            key_hash=key_hash,
            key_prefix=key_prefix,
            user_id=user.id,
            organization_id=user.organization_id,
            scopes=scopes if scopes is not None else [],
            expires_at=expires_at,
            rate_limit=rate_limit
        )
        
        session.add(api_key_record)
        await session.commit()
        await session.refresh(api_key_record)
        
        # Log API key creation
        await self.log_audit_event(
            session=session,
            event_type="api_key_created",
            event_category="security",
            event_description=f"API key '{name}' created",
            user_id=user.id,
            organization_id=user.organization_id,
            resource_type="api_key",
            resource_id=str(api_key_record.id),
            resource_name=name,
            success=True
        )
        
        return api_key_record, api_key
    
    async def verify_api_key(
        self, 
        api_key: str,
        session: Optional[AsyncSession] = None
    ) -> Tuple[User, ApiKey]:
        """
        Verify API key and return associated user
        
        Args:
            api_key: API key to verify
            session: Database session
            
        Returns:
            Tuple of (user, api_key_record)
        """
        if not session:
            async with get_async_db() as session:
                return await self._verify_api_key_impl(api_key, session)
        else:
            return await self._verify_api_key_impl(api_key, session)
    
    async def _verify_api_key_impl(
        self, 
        api_key: str, 
        session: AsyncSession
    ) -> Tuple[User, ApiKey]:
        """Internal implementation of API key verification"""
        
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # Find API key
        result = await session.execute(
            select(ApiKey).where(
                and_(
                    ApiKey.key_hash == key_hash,
                    ApiKey.is_active == True
                )
            )
        )
        api_key_record = result.scalar_one_or_none()
        
        if not api_key_record:
            raise AuthenticationError("Invalid API key")
        
        if api_key_record.is_expired:
            raise AuthenticationError("API key expired")
        
        # Get associated user
        user_result = await session.execute(
            select(User).where(User.id == api_key_record.user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive")
        
        # Update usage
        api_key_record.last_used_at = datetime.utcnow()
        api_key_record.usage_count += 1
        await session.commit()
        
        return user, api_key_record
    
    def check_permission(self, user: User, permission: str) -> bool:
        """
        Check if user has specific permission
        
        Args:
            user: User to check
            permission: Permission string (e.g., "function:create")
            
        Returns:
            True if user has permission
        """
        return user.has_permission(permission)
    
    def require_permission(self, permission: str):
        """
        Decorator to require specific permission for endpoint access
        
        Args:
            permission: Required permission
            
        Returns:
            Decorator function
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract user from kwargs (assumes get_current_user dependency)
                user = None
                for value in kwargs.values():
                    if isinstance(value, User):
                        user = value
                        break
                
                if not user:
                    raise AuthorizationError("No user context found")
                
                if not self.check_permission(user, permission):
                    raise AuthorizationError(f"Permission '{permission}' required")
                
                return await func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    async def log_audit_event(
        self,
        session: AsyncSession,
        event_type: str,
        event_category: str,
        organization_id: uuid.UUID,
        event_description: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,
        actor_type: str = "user",
        actor_identifier: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_name: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        session_id: Optional[str] = None,
        changes: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """
        Log audit event for compliance and security monitoring
        
        Args:
            session: Database session
            event_type: Type of event (e.g., "user_login", "function_created")
            event_category: Category (e.g., "authentication", "function_management")
            organization_id: Organization ID
            ... (other parameters for comprehensive audit logging)
        """
        audit_log = AuditLog(
            event_type=event_type,
            event_category=event_category,
            event_description=event_description,
            user_id=user_id,
            organization_id=organization_id,
            actor_type=actor_type,
            actor_identifier=actor_identifier,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            session_id=session_id,
            changes=changes,
            metadata=metadata,
            success=success,
            error_message=error_message
        )
        
        session.add(audit_log)
        # Note: Commit is handled by the calling function
    
    async def _check_rate_limit(self, email: str, ip_address: Optional[str]):
        """Check rate limiting for login attempts"""
        now = datetime.utcnow()
        
        # Clean old entries
        cutoff = now - timedelta(hours=1)
        self.failed_login_cache = {
            k: v for k, v in self.failed_login_cache.items()
            if v['timestamp'] > cutoff
        }
        
        # Check email rate limit
        email_key = f"email:{email}"
        if email_key in self.failed_login_cache:
            attempts = self.failed_login_cache[email_key]['count']
            if attempts >= 10:  # 10 attempts per hour
                raise RateLimitError("Too many failed login attempts for this email")
        
        # Check IP rate limit
        if ip_address:
            ip_key = f"ip:{ip_address}"
            if ip_key in self.failed_login_cache:
                attempts = self.failed_login_cache[ip_key]['count']
                if attempts >= 50:  # 50 attempts per hour per IP
                    raise RateLimitError("Too many failed login attempts from this IP")
    
    async def _record_failed_login(self, email: str, ip_address: Optional[str], reason: str):
        """Record failed login attempt for rate limiting"""
        now = datetime.utcnow()
        
        # Record by email
        email_key = f"email:{email}"
        if email_key in self.failed_login_cache:
            self.failed_login_cache[email_key]['count'] += 1
        else:
            self.failed_login_cache[email_key] = {'count': 1, 'timestamp': now}
        
        # Record by IP
        if ip_address:
            ip_key = f"ip:{ip_address}"
            if ip_key in self.failed_login_cache:
                self.failed_login_cache[ip_key]['count'] += 1
            else:
                self.failed_login_cache[ip_key] = {'count': 1, 'timestamp': now}


# Dependency functions for FastAPI
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_async_db)
) -> User:
    """
    Get current authenticated user from JWT token
    
    Args:
        credentials: HTTP Bearer credentials
        session: Database session
        
    Returns:
        Current user
    """
    auth_service = AuthService()
    
    try:
        user = await auth_service.verify_token(credentials.credentials, session)
        return user
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user (wrapper for additional checks)
    
    Args:
        current_user: Current user from get_current_user
        
    Returns:
        Active user
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


def require_role(required_role: UserRole):
    """
    Dependency to require specific user role
    
    Args:
        required_role: Minimum required role
        
    Returns:
        Dependency function
    """
    async def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        role_hierarchy = [
            UserRole.VIEWER,
            UserRole.USER,
            UserRole.DEVELOPER,
            UserRole.MANAGER,
            UserRole.ADMIN,
            UserRole.SUPER_ADMIN
        ]
        
        if current_user.role not in role_hierarchy:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid user role"
            )
        
        current_role_level = role_hierarchy.index(current_user.role)
        required_role_level = role_hierarchy.index(required_role)
        
        if current_role_level < required_role_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' or higher required"
            )
        
        return current_user
    
    return role_checker


def require_permission(permission: str):
    """
    Dependency to require specific permission
    
    Args:
        permission: Required permission string
        
    Returns:
        Dependency function
    """
    async def permission_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if not current_user.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )
        
        return current_user
    
    return permission_checker