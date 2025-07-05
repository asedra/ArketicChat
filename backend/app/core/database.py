"""
Database configuration and session management for ATTILA AI Enhanced Function Management System
"""
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool
from .config import settings


class Base(DeclarativeBase):
    """Base class for all database models"""
    pass


class DatabaseManager:
    """Centralized database management"""
    
    def __init__(self):
        self.engine = None
        self.async_engine = None
        self.SessionLocal = None
        self.AsyncSessionLocal = None
        self._initialized = False
        
    def initialize(self):
        """Initialize database engines and sessions"""
        if self._initialized:
            return
            
        # Create engines
        if settings.DATABASE_URL.startswith("sqlite"):
            # SQLite configuration
            self.engine = create_engine(
                settings.DATABASE_URL,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=settings.DEBUG
            )
            # For async SQLite, we need to handle it differently
            self.async_engine = create_async_engine(
                settings.DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///"),
                echo=settings.DEBUG
            )
        else:
            # PostgreSQL or other databases
            self.engine = create_engine(
                settings.database_url_sync,
                pool_size=settings.DATABASE_POOL_SIZE,
                max_overflow=settings.DATABASE_MAX_OVERFLOW,
                echo=settings.DEBUG
            )
            self.async_engine = create_async_engine(
                settings.DATABASE_URL,
                pool_size=settings.DATABASE_POOL_SIZE,
                max_overflow=settings.DATABASE_MAX_OVERFLOW,
                echo=settings.DEBUG
            )
            
        # Create session makers
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False
        )
        
        self.AsyncSessionLocal = async_sessionmaker(
            bind=self.async_engine,
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False
        )
        
        # SQLite-specific optimizations
        if settings.DATABASE_URL.startswith("sqlite"):
            self._setup_sqlite_optimizations()
            
        self._initialized = True
        
    def _setup_sqlite_optimizations(self):
        """Setup SQLite-specific optimizations"""
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            # Enable foreign key constraints
            cursor.execute("PRAGMA foreign_keys=ON")
            # Set WAL mode for better concurrency
            cursor.execute("PRAGMA journal_mode=WAL")
            # Set synchronous mode for better performance
            cursor.execute("PRAGMA synchronous=NORMAL")
            # Set cache size (in KB)
            cursor.execute("PRAGMA cache_size=10000")
            # Set temp store to memory
            cursor.execute("PRAGMA temp_store=memory")
            # Set mmap size for better performance
            cursor.execute("PRAGMA mmap_size=268435456")  # 256MB
            cursor.close()
            
    async def create_tables(self):
        """Create all database tables"""
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
    async def drop_tables(self):
        """Drop all database tables"""
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            
    async def close(self):
        """Close database connections"""
        if self.async_engine:
            await self.async_engine.dispose()
        if self.engine:
            self.engine.dispose()
            
    def get_session(self):
        """Get synchronous database session"""
        return self.SessionLocal()
        
    async def get_async_session(self) -> AsyncSession:
        """Get asynchronous database session"""
        return self.AsyncSessionLocal()


# Global database manager instance
db_manager = DatabaseManager()


def get_db():
    """Dependency to get database session"""
    db = db_manager.get_session()
    try:
        yield db
    finally:
        db.close()


@asynccontextmanager
async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager for database sessions"""
    async with db_manager.AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_async_db_dependency() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for async database sessions"""
    async with get_async_db() as session:
        yield session


async def init_db():
    """Initialize database with tables and initial data"""
    db_manager.initialize()
    await db_manager.create_tables()
    await create_initial_data()


async def create_initial_data():
    """Create initial database data"""
    from ..services.system_prompt_service import SystemPromptService
    
    async with get_async_db() as session:
        try:
            # Create default function router
            from ..models.function_router import FunctionRouter
            
            # Check if default router exists
            existing_router = await session.execute(
                select(FunctionRouter).where(FunctionRouter.is_default == True)
            )
            if not existing_router.scalar_one_or_none():
                default_router = FunctionRouter(
                    name="Default Function Router",
                    description="Default AI-powered function router with standard routing rules",
                    routing_rules={
                        "intent_analysis": {
                            "enabled": True,
                            "confidence_threshold": 0.7,
                            "max_functions": 5
                        },
                        "dependency_resolution": {
                            "enabled": True,
                            "auto_resolve": True
                        },
                        "performance_optimization": {
                            "enabled": True,
                            "parallel_execution": True,
                            "timeout": 30.0
                        }
                    },
                    is_default=True,
                    is_active=True
                )
                session.add(default_router)
                
            # Create system functions
            await _create_system_functions(session)
            
            await session.commit()
            
        except Exception as e:
            await session.rollback()
            raise e


async def _create_system_functions(session: AsyncSession):
    """Create system-level functions"""
    from ..models.function import Function
    
    system_functions = [
        {
            "name": "help",
            "description": "Provide help and information about available functions",
            "function_type": "basic",
            "category": "system",
            "parameters": [
                {
                    "name": "topic",
                    "type": "string",
                    "description": "Help topic to get information about",
                    "required": False
                }
            ],
            "is_system": True,
            "is_enabled": True
        },
        {
            "name": "health_check",
            "description": "Check system health and status",
            "function_type": "basic",
            "category": "system",
            "parameters": [],
            "is_system": True,
            "is_enabled": True
        },
        {
            "name": "list_functions",
            "description": "List available functions and their descriptions",
            "function_type": "basic",
            "category": "system",
            "parameters": [
                {
                    "name": "category",
                    "type": "string",
                    "description": "Filter functions by category",
                    "required": False
                }
            ],
            "is_system": True,
            "is_enabled": True
        }
    ]
    
    for func_data in system_functions:
        # Check if function already exists
        existing_func = await session.execute(
            select(Function).where(Function.name == func_data["name"])
        )
        if not existing_func.scalar_one_or_none():
            function = Function(**func_data)
            session.add(function)


# Database health check
async def check_database_health() -> dict:
    """Check database connection and health"""
    try:
        async with get_async_db() as session:
            result = await session.execute(select(1))
            result.scalar_one()
            
            # Additional health checks
            health_info = {
                "status": "healthy",
                "database_url": settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else settings.DATABASE_URL,
                "connection_pool": {
                    "size": settings.DATABASE_POOL_SIZE,
                    "max_overflow": settings.DATABASE_MAX_OVERFLOW
                }
            }
            
            return health_info
            
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "database_url": settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else settings.DATABASE_URL
        }


# Import fix
try:
    from sqlalchemy import select
except ImportError:
    from sqlalchemy.future import select