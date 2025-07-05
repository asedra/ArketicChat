"""
Function Executors Package for ATTILA AI Enhanced Function Management System
Contains specialized executors for different function types
"""

from .api_executor import APIExecutor
from .prompt_executor import PromptExecutor
from .document_executor import DocumentExecutor
from .mcp_executor import MCPExecutor

__all__ = [
    'APIExecutor',
    'PromptExecutor', 
    'DocumentExecutor',
    'MCPExecutor'
]

# Executor type mapping
EXECUTOR_MAPPING = {
    'api': APIExecutor,
    'prompt': PromptExecutor,
    'document': DocumentExecutor,
    'mcp': MCPExecutor
}

def get_executor(function_type: str):
    """Get executor class for function type"""
    if function_type not in EXECUTOR_MAPPING:
        raise ValueError(f"No executor available for function type: {function_type}")
    
    return EXECUTOR_MAPPING[function_type]