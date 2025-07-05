"""
Enhanced Function model for ATTILA AI Enhanced Function Management System
Supports: basic, api, prompt, document, mcp function types
"""
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from uuid import uuid4

from sqlalchemy import Column, String, Text, Boolean, Integer, Float, DateTime, JSON, CheckConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import validates
from pydantic import BaseModel, validator, Field

from ..core.database import Base


class Function(Base):
    """Enhanced Function model supporting multiple function types"""
    __tablename__ = "functions"
    
    # Core fields
    id = Column(String, primary_key=True, default=lambda: uuid4().hex)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text)
    
    # Function type and configuration
    function_type = Column(String(50), nullable=False, default="basic")
    icon = Column(String(50), default="gear")
    category = Column(String(100), nullable=False)
    parameters = Column(JSON, default=list)
    
    # Type-specific configurations
    prompt_template = Column(Text)  # For prompt functions
    api_config = Column(JSON)  # For API functions
    mcp_config = Column(JSON)  # For MCP functions
    document_content = Column(Text)  # For document functions
    
    # Execution configuration
    execution_order = Column(Integer, default=0)
    dependencies = Column(JSON, default=list)
    success_criteria = Column(Text)
    error_handling = Column(JSON, default=dict)
    
    # Meta information
    is_enabled = Column(Boolean, default=True)
    is_system = Column(Boolean, default=False)
    implementation = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Extra data for extensibility
    extra_data = Column(JSON, default=dict)
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "function_type IN ('basic', 'api', 'prompt', 'document', 'mcp')",
            name="check_function_type"
        ),
    )
    
    @validates('function_type')
    def validate_function_type(self, key, value):
        """Validate function type"""
        allowed_types = ['basic', 'api', 'prompt', 'document', 'mcp']
        if value not in allowed_types:
            raise ValueError(f"Function type must be one of: {allowed_types}")
        return value
    
    @validates('parameters')
    def validate_parameters(self, key, value):
        """Validate parameters format"""
        if not isinstance(value, list):
            raise ValueError("Parameters must be a list")
        
        for param in value:
            if not isinstance(param, dict):
                raise ValueError("Each parameter must be a dictionary")
            
            required_fields = ['name', 'type', 'description']
            for field in required_fields:
                if field not in param:
                    raise ValueError(f"Parameter must have '{field}' field")
        
        return value
    
    @validates('dependencies')
    def validate_dependencies(self, key, value):
        """Validate dependencies format"""
        if not isinstance(value, list):
            raise ValueError("Dependencies must be a list")
        
        for dep in value:
            if not isinstance(dep, str):
                raise ValueError("Each dependency must be a string (function name)")
        
        return value
    
    def get_type_config(self) -> Dict[str, Any]:
        """Get type-specific configuration"""
        if self.function_type == "api":
            return self.api_config or {}
        elif self.function_type == "mcp":
            return self.mcp_config or {}
        elif self.function_type == "prompt":
            return {"template": self.prompt_template}
        elif self.function_type == "document":
            return {"content": self.document_content}
        else:
            return {}
    
    def get_parameter_schema(self) -> Dict[str, Any]:
        """Get parameter schema for validation"""
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }
        
        for param in self.parameters:
            schema["properties"][param["name"]] = {
                "type": param["type"],
                "description": param["description"]
            }
            
            if param.get("required", False):
                schema["required"].append(param["name"])
        
        return schema
    
    def validate_execution_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate execution parameters against schema"""
        from jsonschema import validate, ValidationError
        
        try:
            validate(params, self.get_parameter_schema())
            return params
        except ValidationError as e:
            raise ValueError(f"Parameter validation failed: {e.message}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "function_type": self.function_type,
            "icon": self.icon,
            "category": self.category,
            "parameters": self.parameters,
            "type_config": self.get_type_config(),
            "execution_order": self.execution_order,
            "dependencies": self.dependencies,
            "success_criteria": self.success_criteria,
            "error_handling": self.error_handling,
            "is_enabled": self.is_enabled,
            "is_system": self.is_system,
            "implementation": self.implementation,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "extra_data": self.extra_data
        }
    
    def __repr__(self):
        return f"<Function(name='{self.name}', type='{self.function_type}', enabled={self.is_enabled})>"


# Pydantic models for API serialization
class FunctionParameter(BaseModel):
    """Function parameter schema"""
    name: str
    type: str
    description: str
    required: bool = False
    default: Optional[Any] = None
    
    @validator('type')
    def validate_type(cls, v):
        allowed_types = ['string', 'integer', 'number', 'boolean', 'array', 'object']
        if v not in allowed_types:
            raise ValueError(f"Type must be one of: {allowed_types}")
        return v


class APIConfig(BaseModel):
    """API function configuration"""
    method: str = "POST"
    endpoint: str
    headers: Dict[str, str] = Field(default_factory=dict)
    request_transform: Optional[Dict[str, Any]] = None
    response_transform: Optional[Dict[str, Any]] = None
    authentication: Optional[Dict[str, Any]] = None
    timeout: int = 30
    retry: Optional[Dict[str, Any]] = None
    
    @validator('method')
    def validate_method(cls, v):
        allowed_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
        if v.upper() not in allowed_methods:
            raise ValueError(f"Method must be one of: {allowed_methods}")
        return v.upper()


class MCPConfig(BaseModel):
    """MCP function configuration"""
    protocol_version: str = "1.0"
    endpoint: str
    authentication: Optional[Dict[str, Any]] = None
    message_format: str = "json"
    timeout: int = 30
    reconnect: Optional[Dict[str, Any]] = None
    compression: Optional[str] = None
    
    @validator('message_format')
    def validate_message_format(cls, v):
        allowed_formats = ['json', 'msgpack']
        if v not in allowed_formats:
            raise ValueError(f"Message format must be one of: {allowed_formats}")
        return v


class PromptConfig(BaseModel):
    """Prompt function configuration"""
    model: str = "gpt-4"
    temperature: float = 0.7
    max_tokens: int = 1000
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    response_format: str = "text"
    system_prompt: Optional[str] = None
    tools: Optional[List[str]] = None
    stream: bool = False
    
    @validator('temperature')
    def validate_temperature(cls, v):
        if not 0 <= v <= 2:
            raise ValueError("Temperature must be between 0 and 2")
        return v
    
    @validator('response_format')
    def validate_response_format(cls, v):
        allowed_formats = ['text', 'json']
        if v not in allowed_formats:
            raise ValueError(f"Response format must be one of: {allowed_formats}")
        return v


class DocumentConfig(BaseModel):
    """Document function configuration"""
    processing_config: Dict[str, Any] = Field(default_factory=lambda: {
        "chunk_size": 1000,
        "overlap": 200,
        "format": "markdown"
    })
    search_config: Dict[str, Any] = Field(default_factory=lambda: {
        "method": "semantic",
        "embedding_model": "text-embedding-ada-002",
        "similarity_threshold": 0.8,
        "max_results": 5
    })
    indexing: Dict[str, Any] = Field(default_factory=lambda: {
        "enabled": True,
        "update_frequency": "realtime"
    })


class FunctionCreate(BaseModel):
    """Function creation schema"""
    name: str
    description: Optional[str] = None
    function_type: str = "basic"
    icon: str = "gear"
    category: str
    parameters: List[FunctionParameter] = Field(default_factory=list)
    
    # Type-specific configurations
    prompt_template: Optional[str] = None
    api_config: Optional[APIConfig] = None
    mcp_config: Optional[MCPConfig] = None
    document_content: Optional[str] = None
    
    # Execution configuration
    execution_order: int = 0
    dependencies: List[str] = Field(default_factory=list)
    success_criteria: Optional[str] = None
    error_handling: Dict[str, Any] = Field(default_factory=dict)
    
    # Meta information
    is_enabled: bool = True
    implementation: Optional[str] = None
    extra_data: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('function_type')
    def validate_function_type(cls, v):
        allowed_types = ['basic', 'api', 'prompt', 'document', 'mcp']
        if v not in allowed_types:
            raise ValueError(f"Function type must be one of: {allowed_types}")
        return v
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Function name cannot be empty")
        if len(v) > 255:
            raise ValueError("Function name cannot exceed 255 characters")
        return v.strip()


class FunctionUpdate(BaseModel):
    """Function update schema"""
    name: Optional[str] = None
    description: Optional[str] = None
    function_type: Optional[str] = None
    icon: Optional[str] = None
    category: Optional[str] = None
    parameters: Optional[List[FunctionParameter]] = None
    
    # Type-specific configurations
    prompt_template: Optional[str] = None
    api_config: Optional[APIConfig] = None
    mcp_config: Optional[MCPConfig] = None
    document_content: Optional[str] = None
    
    # Execution configuration
    execution_order: Optional[int] = None
    dependencies: Optional[List[str]] = None
    success_criteria: Optional[str] = None
    error_handling: Optional[Dict[str, Any]] = None
    
    # Meta information
    is_enabled: Optional[bool] = None
    implementation: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None


class FunctionResponse(BaseModel):
    """Function response schema"""
    id: str
    name: str
    description: Optional[str]
    function_type: str
    icon: str
    category: str
    parameters: List[Dict[str, Any]]
    type_config: Dict[str, Any]
    execution_order: int
    dependencies: List[str]
    success_criteria: Optional[str]
    error_handling: Dict[str, Any]
    is_enabled: bool
    is_system: bool
    implementation: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    extra_data: Dict[str, Any]
    
    class Config:
        from_attributes = True