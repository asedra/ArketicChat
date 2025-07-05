"""
Function Router model for AI-powered function routing configuration
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4

from sqlalchemy import Column, String, Text, Boolean, Integer, Float, DateTime, JSON, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import validates
from pydantic import BaseModel, Field, validator

from ..core.database import Base


class FunctionRouter(Base):
    """Function router configuration model"""
    __tablename__ = "function_router"
    
    # Core fields
    id = Column(String, primary_key=True, default=lambda: uuid4().hex)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Routing configuration
    routing_rules = Column(JSON, nullable=False)
    priority = Column(Integer, default=0)
    
    # Confidence thresholds
    min_confidence = Column(Float, default=0.7)
    auto_execute_threshold = Column(Float, default=0.95)
    
    # Performance constraints
    max_functions = Column(Integer, default=5)
    max_execution_time = Column(Float, default=30.0)
    
    # Status
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("is_default", name="unique_default_router"),
    )
    
    @validates('routing_rules')
    def validate_routing_rules(self, key, value):
        """Validate routing rules format"""
        if not isinstance(value, dict):
            raise ValueError("Routing rules must be a dictionary")
        
        # Check for required sections
        required_sections = ['intent_analysis', 'dependency_resolution', 'performance_optimization']
        for section in required_sections:
            if section not in value:
                raise ValueError(f"Routing rules must contain '{section}' section")
        
        return value
    
    @validates('min_confidence')
    def validate_min_confidence(self, key, value):
        """Validate minimum confidence threshold"""
        if not 0 <= value <= 1:
            raise ValueError("Minimum confidence must be between 0 and 1")
        return value
    
    @validates('auto_execute_threshold')
    def validate_auto_execute_threshold(self, key, value):
        """Validate auto-execute threshold"""
        if not 0 <= value <= 1:
            raise ValueError("Auto-execute threshold must be between 0 and 1")
        return value
    
    @validates('max_functions')
    def validate_max_functions(self, key, value):
        """Validate maximum functions"""
        if value < 1:
            raise ValueError("Maximum functions must be at least 1")
        return value
    
    def get_intent_analysis_config(self) -> Dict[str, Any]:
        """Get intent analysis configuration"""
        return self.routing_rules.get('intent_analysis', {})
    
    def get_dependency_resolution_config(self) -> Dict[str, Any]:
        """Get dependency resolution configuration"""
        return self.routing_rules.get('dependency_resolution', {})
    
    def get_performance_optimization_config(self) -> Dict[str, Any]:
        """Get performance optimization configuration"""
        return self.routing_rules.get('performance_optimization', {})
    
    def is_intent_analysis_enabled(self) -> bool:
        """Check if intent analysis is enabled"""
        return self.get_intent_analysis_config().get('enabled', False)
    
    def is_dependency_resolution_enabled(self) -> bool:
        """Check if dependency resolution is enabled"""
        return self.get_dependency_resolution_config().get('enabled', False)
    
    def is_performance_optimization_enabled(self) -> bool:
        """Check if performance optimization is enabled"""
        return self.get_performance_optimization_config().get('enabled', False)
    
    def should_auto_execute(self, confidence: float) -> bool:
        """Check if should auto-execute based on confidence"""
        return confidence >= self.auto_execute_threshold
    
    def meets_confidence_threshold(self, confidence: float) -> bool:
        """Check if confidence meets minimum threshold"""
        return confidence >= self.min_confidence
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "routing_rules": self.routing_rules,
            "priority": self.priority,
            "min_confidence": self.min_confidence,
            "auto_execute_threshold": self.auto_execute_threshold,
            "max_functions": self.max_functions,
            "max_execution_time": self.max_execution_time,
            "is_default": self.is_default,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f"<FunctionRouter(name='{self.name}', active={self.is_active}, default={self.is_default})>"


# Pydantic models for API serialization
class RoutingRulesConfig(BaseModel):
    """Routing rules configuration schema"""
    intent_analysis: Dict[str, Any] = Field(default_factory=lambda: {
        "enabled": True,
        "confidence_threshold": 0.7,
        "max_functions": 5,
        "model": "gpt-4",
        "temperature": 0.3
    })
    dependency_resolution: Dict[str, Any] = Field(default_factory=lambda: {
        "enabled": True,
        "auto_resolve": True,
        "max_depth": 3,
        "circular_detection": True
    })
    performance_optimization: Dict[str, Any] = Field(default_factory=lambda: {
        "enabled": True,
        "parallel_execution": True,
        "timeout": 30.0,
        "memory_limit": 1024,
        "cpu_limit": 70
    })
    
    class Config:
        from_attributes = True


class FunctionRouterCreate(BaseModel):
    """Function router creation schema"""
    name: str
    description: Optional[str] = None
    routing_rules: RoutingRulesConfig
    priority: int = 0
    min_confidence: float = Field(default=0.7, ge=0, le=1)
    auto_execute_threshold: float = Field(default=0.95, ge=0, le=1)
    max_functions: int = Field(default=5, ge=1)
    max_execution_time: float = Field(default=30.0, gt=0)
    is_active: bool = True
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Router name cannot be empty")
        if len(v) > 255:
            raise ValueError("Router name cannot exceed 255 characters")
        return v.strip()
    
    @validator('auto_execute_threshold')
    def validate_auto_execute_threshold_vs_min(cls, v, values):
        if 'min_confidence' in values and v < values['min_confidence']:
            raise ValueError("Auto-execute threshold must be >= min_confidence")
        return v
    
    class Config:
        from_attributes = True


class FunctionRouterUpdate(BaseModel):
    """Function router update schema"""
    name: Optional[str] = None
    description: Optional[str] = None
    routing_rules: Optional[RoutingRulesConfig] = None
    priority: Optional[int] = None
    min_confidence: Optional[float] = Field(default=None, ge=0, le=1)
    auto_execute_threshold: Optional[float] = Field(default=None, ge=0, le=1)
    max_functions: Optional[int] = Field(default=None, ge=1)
    max_execution_time: Optional[float] = Field(default=None, gt=0)
    is_active: Optional[bool] = None
    
    class Config:
        from_attributes = True


class FunctionRouterResponse(BaseModel):
    """Function router response schema"""
    id: str
    name: str
    description: Optional[str]
    routing_rules: Dict[str, Any]
    priority: int
    min_confidence: float
    auto_execute_threshold: float
    max_functions: int
    max_execution_time: float
    is_default: bool
    is_active: bool
    created_at: Optional[str]
    updated_at: Optional[str]
    
    class Config:
        from_attributes = True


class RouterDecisionLog(Base):
    """Router decision log for analysis and improvement"""
    __tablename__ = "router_decision_log"
    
    # Core fields
    id = Column(String, primary_key=True, default=lambda: uuid4().hex)
    session_id = Column(String, nullable=False)
    router_id = Column(String, nullable=False)
    
    # Input data
    user_message = Column(Text, nullable=False)
    available_functions = Column(JSON, nullable=False)
    context_data = Column(JSON)
    
    # Analysis results
    intent_analysis = Column(JSON, nullable=False)
    suggested_functions = Column(JSON, nullable=False)
    confidence_score = Column(Float, nullable=False)
    execution_strategy = Column(String(20))
    
    # Applied rules
    routing_rules_applied = Column(JSON)
    dependencies_resolved = Column(JSON)
    
    # Outcome
    final_functions = Column(JSON, nullable=False)
    user_accepted = Column(Boolean)
    execution_success = Column(Boolean)
    
    # Performance
    analysis_time = Column(Float)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "router_id": self.router_id,
            "user_message": self.user_message,
            "available_functions": self.available_functions,
            "context_data": self.context_data,
            "intent_analysis": self.intent_analysis,
            "suggested_functions": self.suggested_functions,
            "confidence_score": self.confidence_score,
            "execution_strategy": self.execution_strategy,
            "routing_rules_applied": self.routing_rules_applied,
            "dependencies_resolved": self.dependencies_resolved,
            "final_functions": self.final_functions,
            "user_accepted": self.user_accepted,
            "execution_success": self.execution_success,
            "analysis_time": self.analysis_time,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f"<RouterDecisionLog(router='{self.router_id}', confidence={self.confidence_score})>"