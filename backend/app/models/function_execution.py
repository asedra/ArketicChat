"""
Function Execution model for tracking execution history and performance metrics
"""
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4

from sqlalchemy import Column, String, Text, Boolean, Integer, Float, DateTime, JSON, CheckConstraint, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, validates
from pydantic import BaseModel, Field

from ..core.database import Base


class FunctionExecution(Base):
    """Function execution tracking model"""
    __tablename__ = "function_executions"
    
    # Core fields
    id = Column(String, primary_key=True, default=lambda: uuid4().hex)
    session_id = Column(String, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    function_id = Column(String, ForeignKey("functions.id", ondelete="CASCADE"), nullable=False)
    execution_order = Column(Integer)
    
    # Input/Output data
    input_data = Column(JSON)
    output_data = Column(JSON)
    
    # Performance metrics
    execution_time = Column(Float)  # in seconds
    memory_used = Column(Integer)  # in MB
    cpu_time = Column(Float)  # CPU time in seconds
    
    # Status tracking
    status = Column(String(20), nullable=False, default="pending")
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    
    # Timestamps
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', 'cancelled')",
            name="check_execution_status"
        ),
    )
    
    # Relationships
    function = relationship("Function", back_populates="executions")
    
    @validates('status')
    def validate_status(self, key, value):
        """Validate execution status"""
        allowed_statuses = ['pending', 'running', 'completed', 'failed', 'cancelled']
        if value not in allowed_statuses:
            raise ValueError(f"Status must be one of: {allowed_statuses}")
        return value
    
    def start_execution(self):
        """Mark execution as started"""
        self.status = "running"
        self.started_at = datetime.utcnow()
    
    def complete_execution(self, output_data: Dict[str, Any] = None):
        """Mark execution as completed"""
        self.status = "completed"
        self.completed_at = datetime.utcnow()
        if output_data:
            self.output_data = output_data
        self._calculate_performance_metrics()
    
    def fail_execution(self, error_message: str):
        """Mark execution as failed"""
        self.status = "failed"
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
        self._calculate_performance_metrics()
    
    def cancel_execution(self):
        """Mark execution as cancelled"""
        self.status = "cancelled"
        self.completed_at = datetime.utcnow()
        self._calculate_performance_metrics()
    
    def _calculate_performance_metrics(self):
        """Calculate performance metrics"""
        if self.started_at and self.completed_at:
            self.execution_time = (self.completed_at - self.started_at).total_seconds()
    
    def get_duration(self) -> Optional[float]:
        """Get execution duration in seconds"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        elif self.started_at:
            return (datetime.utcnow() - self.started_at).total_seconds()
        return None
    
    def is_running(self) -> bool:
        """Check if execution is currently running"""
        return self.status == "running"
    
    def is_completed(self) -> bool:
        """Check if execution is completed"""
        return self.status == "completed"
    
    def is_failed(self) -> bool:
        """Check if execution failed"""
        return self.status == "failed"
    
    def is_successful(self) -> bool:
        """Check if execution was successful"""
        return self.status == "completed" and not self.error_message
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "function_id": self.function_id,
            "execution_order": self.execution_order,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "execution_time": self.execution_time,
            "memory_used": self.memory_used,
            "cpu_time": self.cpu_time,
            "status": self.status,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "duration": self.get_duration()
        }
    
    def __repr__(self):
        return f"<FunctionExecution(id='{self.id}', function='{self.function_id}', status='{self.status}')>"


# Pydantic models for API serialization
class FunctionExecutionCreate(BaseModel):
    """Function execution creation schema"""
    session_id: str
    function_id: str
    execution_order: Optional[int] = None
    input_data: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class FunctionExecutionUpdate(BaseModel):
    """Function execution update schema"""
    status: Optional[str] = None
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    execution_time: Optional[float] = None
    memory_used: Optional[int] = None
    cpu_time: Optional[float] = None
    
    class Config:
        from_attributes = True


class FunctionExecutionResponse(BaseModel):
    """Function execution response schema"""
    id: str
    session_id: str
    function_id: str
    execution_order: Optional[int]
    input_data: Optional[Dict[str, Any]]
    output_data: Optional[Dict[str, Any]]
    execution_time: Optional[float]
    memory_used: Optional[int]
    cpu_time: Optional[float]
    status: str
    error_message: Optional[str]
    retry_count: int
    started_at: Optional[str]
    completed_at: Optional[str]
    created_at: Optional[str]
    duration: Optional[float]
    
    class Config:
        from_attributes = True


class ExecutionPerformanceMetrics(BaseModel):
    """Execution performance metrics"""
    total_executions: int
    successful_executions: int
    failed_executions: int
    average_execution_time: float
    min_execution_time: float
    max_execution_time: float
    success_rate: float
    
    class Config:
        from_attributes = True