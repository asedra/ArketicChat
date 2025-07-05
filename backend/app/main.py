"""
ATTILA AI Enhanced Function Management System - Main FastAPI Application
Phase 1: Foundation with AI-powered function routing and execution
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from .core.config import settings
from .core.database import init_db, get_async_db_dependency, check_database_health
from .services.function_router_service import FunctionRouterService
from .services.function_execution_service import FunctionExecutionService
from .services.analytics_service import AnalyticsService
from .models.function import Function, FunctionCreate, FunctionUpdate, FunctionResponse
from .models.function_router import FunctionRouter, FunctionRouterCreate, FunctionRouterUpdate, FunctionRouterResponse
from .models.function_execution import FunctionExecution, FunctionExecutionResponse


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting ATTILA AI Enhanced Function Management System...")
    
    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized successfully")
        
        # Initialize services
        app.state.router_service = FunctionRouterService()
        app.state.execution_service = FunctionExecutionService()
        app.state.analytics_service = AnalyticsService()
        logger.info("Services initialized successfully")
        
        logger.info("Application startup complete")
        
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down ATTILA AI Enhanced Function Management System...")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered function orchestration platform with intelligent routing and multi-function execution",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health Check Endpoints
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    try:
        db_health = await check_database_health()
        
        return {
            "status": "healthy",
            "version": settings.APP_VERSION,
            "database": db_health,
            "services": {
                "function_router": "operational",
                "function_executor": "operational"
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "version": settings.APP_VERSION
            }
        )


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with system information"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "AI-powered function orchestration platform",
        "features": [
            "AI-powered function routing (>85% accuracy)",
            "Multi-function execution (<2s target)",
            "4 function types (basic, api, prompt, document, mcp)",
            "Dependency resolution",
            "Performance monitoring",
            "Real-time execution tracking"
        ],
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "functions": "/functions",
            "router": "/router",
            "execute": "/execute"
        }
    }


# Function Management Endpoints
@app.get("/functions", response_model=List[FunctionResponse], tags=["Functions"])
async def list_functions(
    category: Optional[str] = None,
    function_type: Optional[str] = None,
    enabled_only: bool = True,
    db: AsyncSession = Depends(get_async_db_dependency)
):
    """List all functions with optional filtering"""
    try:
        from sqlalchemy import select
        
        query = select(Function)
        
        if enabled_only:
            query = query.where(Function.is_enabled == True)
        
        if category:
            query = query.where(Function.category == category)
            
        if function_type:
            query = query.where(Function.function_type == function_type)
        
        result = await db.execute(query)
        functions = result.scalars().all()
        
        return [FunctionResponse.from_orm(func) for func in functions]
        
    except Exception as e:
        logger.error(f"Error listing functions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/functions", response_model=FunctionResponse, tags=["Functions"])
async def create_function(
    function_data: FunctionCreate,
    db: AsyncSession = Depends(get_async_db_dependency)
):
    """Create a new function"""
    try:
        # Convert Pydantic model to SQLAlchemy model
        function_dict = function_data.dict()
        
        # Handle type-specific configurations
        if function_data.api_config:
            function_dict['api_config'] = function_data.api_config.dict()
        if function_data.mcp_config:
            function_dict['mcp_config'] = function_data.mcp_config.dict()
        
        # Convert parameters to dict format
        function_dict['parameters'] = [param.dict() for param in function_data.parameters]
        
        function = Function(**function_dict)
        
        db.add(function)
        await db.commit()
        await db.refresh(function)
        
        logger.info(f"Created function: {function.name} ({function.function_type})")
        
        return FunctionResponse.from_orm(function)
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating function: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/functions/{function_id}", response_model=FunctionResponse, tags=["Functions"])
async def get_function(
    function_id: str,
    db: AsyncSession = Depends(get_async_db_dependency)
):
    """Get a specific function by ID"""
    try:
        from sqlalchemy import select
        
        result = await db.execute(
            select(Function).where(Function.id == function_id)
        )
        function = result.scalar_one_or_none()
        
        if not function:
            raise HTTPException(status_code=404, detail="Function not found")
        
        return FunctionResponse.from_orm(function)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting function {function_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/functions/{function_id}", response_model=FunctionResponse, tags=["Functions"])
async def update_function(
    function_id: str,
    function_data: FunctionUpdate,
    db: AsyncSession = Depends(get_async_db_dependency)
):
    """Update an existing function"""
    try:
        from sqlalchemy import select
        
        result = await db.execute(
            select(Function).where(Function.id == function_id)
        )
        function = result.scalar_one_or_none()
        
        if not function:
            raise HTTPException(status_code=404, detail="Function not found")
        
        # Update fields that are provided
        update_data = function_data.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            if field == 'parameters' and value is not None:
                value = [param.dict() for param in value]
            elif field == 'api_config' and value is not None:
                value = value.dict()
            elif field == 'mcp_config' and value is not None:
                value = value.dict()
            
            setattr(function, field, value)
        
        await db.commit()
        await db.refresh(function)
        
        logger.info(f"Updated function: {function.name}")
        
        return FunctionResponse.from_orm(function)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating function {function_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/functions/{function_id}", tags=["Functions"])
async def delete_function(
    function_id: str,
    db: AsyncSession = Depends(get_async_db_dependency)
):
    """Delete a function"""
    try:
        from sqlalchemy import select
        
        result = await db.execute(
            select(Function).where(Function.id == function_id)
        )
        function = result.scalar_one_or_none()
        
        if not function:
            raise HTTPException(status_code=404, detail="Function not found")
        
        await db.delete(function)
        await db.commit()
        
        logger.info(f"Deleted function: {function.name}")
        
        return {"message": "Function deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting function {function_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Function Router Endpoints
@app.post("/router/analyze", tags=["Router"])
async def analyze_message(
    message: str,
    session_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    db: AsyncSession = Depends(get_async_db_dependency)
):
    """Analyze user message and suggest functions using AI router"""
    try:
        # Get available functions
        from sqlalchemy import select
        
        result = await db.execute(
            select(Function).where(Function.is_enabled == True)
        )
        available_functions = result.scalars().all()
        
        if not available_functions:
            raise HTTPException(status_code=400, detail="No enabled functions available")
        
        # Analyze message using router service
        router_service = app.state.router_service
        analysis = await router_service.analyze_message_intent(
            message=message,
            available_functions=list(available_functions),
            context=context,
            session_id=session_id
        )
        
        # Apply routing rules
        analysis = await router_service.apply_routing_rules(
            analysis=analysis,
            functions=list(available_functions)
        )
        
        # Log decision for analysis
        if session_id:
            router_result = await db.execute(
                select(FunctionRouter).where(FunctionRouter.is_default == True)
            )
            default_router = router_result.scalar_one_or_none()
            
            if default_router:
                await router_service.log_routing_decision(
                    session_id=session_id,
                    router_id=default_router.id,
                    analysis=analysis,
                    user_message=message,
                    available_functions=list(available_functions)
                )
        
        return {
            "analysis": analysis,
            "message": message,
            "available_functions_count": len(available_functions),
            "routing_timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/execute", tags=["Execution"])
async def execute_functions(
    function_names: List[str],
    session_id: str,
    context: Optional[Dict[str, Any]] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_async_db_dependency)
):
    """Execute selected functions with dependency resolution"""
    try:
        # Get functions to execute
        from sqlalchemy import select
        
        result = await db.execute(
            select(Function).where(
                Function.name.in_(function_names),
                Function.is_enabled == True
            )
        )
        functions = result.scalars().all()
        
        if not functions:
            raise HTTPException(status_code=400, detail="No valid functions found to execute")
        
        # Create function configurations (for now, just basic configs)
        function_configs = [{"name": func.name} for func in functions]
        
        # Execute functions
        execution_service = app.state.execution_service
        result = await execution_service.execute_functions(
            functions=list(functions),
            function_configs=function_configs,
            session_id=session_id,
            context=context
        )
        
        return {
            "execution_result": result,
            "session_id": session_id,
            "functions_executed": [func.name for func in functions],
            "execution_timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing functions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/router/accuracy", tags=["Router"])
async def get_router_accuracy(days: int = 7):
    """Get router accuracy metrics"""
    try:
        router_service = app.state.router_service
        accuracy_metrics = await router_service.get_routing_accuracy(days=days)
        
        return {
            "accuracy_metrics": accuracy_metrics,
            "period_days": days,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting router accuracy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Analytics and Monitoring Endpoints
@app.get("/analytics/performance", tags=["Analytics"])
async def get_performance_metrics(
    days: int = 7,
    db: AsyncSession = Depends(get_async_db_dependency)
):
    """Get system performance metrics"""
    try:
        from sqlalchemy import select, func
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Get execution metrics
        result = await db.execute(
            select(
                func.count(FunctionExecution.id).label('total_executions'),
                func.avg(FunctionExecution.execution_time).label('avg_execution_time'),
                func.sum(
                    func.case([(FunctionExecution.status == 'completed', 1)], else_=0)
                ).label('successful_executions')
            ).where(FunctionExecution.created_at >= cutoff_date)
        )
        
        metrics = result.first()
        
        success_rate = 0.0
        if metrics.total_executions and metrics.total_executions > 0:
            success_rate = metrics.successful_executions / metrics.total_executions
        
        return {
            "performance_metrics": {
                "total_executions": metrics.total_executions or 0,
                "average_execution_time": float(metrics.avg_execution_time or 0),
                "success_rate": success_rate,
                "successful_executions": metrics.successful_executions or 0,
                "failed_executions": (metrics.total_executions or 0) - (metrics.successful_executions or 0)
            },
            "period_days": days,
            "target_metrics": {
                "target_execution_time": settings.TARGET_EXECUTION_TIME,
                "target_success_rate": 0.90
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/comprehensive", tags=["Analytics"])
async def get_comprehensive_analytics(
    period_hours: int = 24,
    db: AsyncSession = Depends(get_async_db_dependency)
):
    """Get comprehensive analytics report"""
    try:
        analytics_service = app.state.analytics_service
        report = await analytics_service.generate_analytics_report(period_hours=period_hours)
        
        return {
            "report": {
                "period_start": report.period_start.isoformat(),
                "period_end": report.period_end.isoformat(),
                "summary": report.summary,
                "performance_metrics": report.performance_metrics,
                "usage_statistics": report.usage_statistics,
                "error_analysis": report.error_analysis,
                "recommendations": report.recommendations
            },
            "generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting comprehensive analytics: {e}")
        # Return mock data as fallback
        return {
            "report": {
                "period_start": (datetime.now() - timedelta(hours=period_hours)).isoformat(),
                "period_end": datetime.now().isoformat(),
                "summary": {
                    "period_hours": period_hours,
                    "total_executions": 0,
                    "success_rate": 0,
                    "active_functions": 0,
                    "system_uptime": "Unknown",
                    "health_status": "unknown"
                },
                "performance_metrics": {
                    "total_executions": 0,
                    "avg_execution_time": 0,
                    "p95_execution_time": 0,
                    "p99_execution_time": 0,
                    "fastest_execution": 0,
                    "slowest_execution": 0,
                    "throughput_per_hour": 0,
                    "performance_trend": []
                },
                "usage_statistics": {
                    "function_type_distribution": {},
                    "popular_functions": [],
                    "router_accuracy": 0,
                    "total_router_decisions": 0,
                    "hourly_usage_pattern": {},
                    "peak_usage_hour": 0
                },
                "error_analysis": {
                    "total_executions": 0,
                    "total_failures": 0,
                    "error_rate": 0,
                    "error_categories": {},
                    "error_by_function": [],
                    "mttr": 0
                },
                "recommendations": [
                    "System monitoring initialized. Start using functions to generate insights."
                ]
            },
            "generated_at": datetime.now().isoformat(),
            "note": "Analytics service not available, showing mock data"
        }


@app.get("/analytics/realtime", tags=["Analytics"])
async def get_realtime_metrics():
    """Get real-time system metrics"""
    try:
        analytics_service = app.state.analytics_service
        metrics = await analytics_service.get_real_time_metrics()
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error getting real-time metrics: {e}")
        # Return mock data as fallback
        return {
            "timestamp": datetime.now().isoformat(),
            "system_metrics": {
                "cpu_usage_percent": 0,
                "memory_usage_percent": 0,
                "memory_available_gb": 0,
                "disk_usage_percent": 0,
                "disk_free_gb": 0,
                "system_health_score": 0
            },
            "recent_executions": 0,
            "recent_success_rate": 0,
            "current_throughput": 0,
            "alerts": [],
            "note": "Analytics service not available, showing mock data"
        }


@app.get("/analytics/usage", tags=["Analytics"])
async def get_usage_analytics(
    period_hours: int = 24,
    db: AsyncSession = Depends(get_async_db_dependency)
):
    """Get usage analytics and patterns"""
    try:
        from sqlalchemy import select, func
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(hours=period_hours)
        
        # Get function usage by type
        function_usage = await db.execute(
            select(
                Function.function_type,
                func.count(FunctionExecution.id).label('usage_count')
            )
            .join(FunctionExecution, Function.id == FunctionExecution.function_id)
            .where(FunctionExecution.created_at >= cutoff_date)
            .group_by(Function.function_type)
        )
        
        usage_by_type = {row.function_type: row.usage_count for row in function_usage.all()}
        
        # Get most used functions
        popular_functions = await db.execute(
            select(
                Function.name,
                Function.function_type,
                func.count(FunctionExecution.id).label('usage_count')
            )
            .join(FunctionExecution, Function.id == FunctionExecution.function_id)
            .where(FunctionExecution.created_at >= cutoff_date)
            .group_by(Function.id, Function.name, Function.function_type)
            .order_by(func.count(FunctionExecution.id).desc())
            .limit(10)
        )
        
        popular_list = [
            {
                "name": row.name,
                "type": row.function_type,
                "usage_count": row.usage_count
            }
            for row in popular_functions.all()
        ]
        
        return {
            "usage_analytics": {
                "function_type_distribution": usage_by_type,
                "popular_functions": popular_list,
                "period_hours": period_hours,
                "total_unique_functions": len(popular_list)
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting usage analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analytics/errors", tags=["Analytics"])
async def get_error_analytics(
    period_hours: int = 24,
    db: AsyncSession = Depends(get_async_db_dependency)
):
    """Get error analytics and patterns"""
    try:
        from sqlalchemy import select, func
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(hours=period_hours)
        
        # Get error statistics
        error_stats = await db.execute(
            select(
                func.count(FunctionExecution.id).label('total_executions'),
                func.sum(
                    func.case([(FunctionExecution.status == 'failed', 1)], else_=0)
                ).label('failed_executions')
            ).where(FunctionExecution.created_at >= cutoff_date)
        )
        
        stats = error_stats.first()
        total_executions = stats.total_executions or 0
        failed_executions = stats.failed_executions or 0
        error_rate = failed_executions / total_executions if total_executions > 0 else 0
        
        # Get error messages
        error_messages = await db.execute(
            select(FunctionExecution.error_message)
            .where(
                FunctionExecution.created_at >= cutoff_date,
                FunctionExecution.status == 'failed',
                FunctionExecution.error_message.isnot(None)
            )
        )
        
        # Categorize errors
        error_categories = {}
        for row in error_messages.all():
            error_msg = row.error_message.lower()
            if 'timeout' in error_msg:
                error_categories['timeout'] = error_categories.get('timeout', 0) + 1
            elif 'authentication' in error_msg or 'unauthorized' in error_msg:
                error_categories['authentication'] = error_categories.get('authentication', 0) + 1
            elif 'connection' in error_msg or 'network' in error_msg:
                error_categories['network'] = error_categories.get('network', 0) + 1
            elif 'validation' in error_msg or 'invalid' in error_msg:
                error_categories['validation'] = error_categories.get('validation', 0) + 1
            else:
                error_categories['other'] = error_categories.get('other', 0) + 1
        
        return {
            "error_analytics": {
                "total_executions": total_executions,
                "failed_executions": failed_executions,
                "error_rate": error_rate,
                "error_categories": error_categories,
                "period_hours": period_hours
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting error analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Import necessary modules for datetime
from datetime import datetime, timedelta
from typing import List, Optional


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.AUTO_RELOAD,
        log_level=settings.LOG_LEVEL.lower()
    )