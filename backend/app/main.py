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


# Import necessary modules for datetime
from datetime import datetime
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