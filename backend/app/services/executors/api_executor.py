"""
API Function Executor for HTTP API calls with authentication and retry logic
Supports GET, POST, PUT, DELETE methods with request/response transformation
"""
import asyncio
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlparse

import httpx
from jinja2 import Template

from ...core.config import settings
from ...models.function import Function


class APIExecutor:
    """
    HTTP API function executor with authentication, retry logic, and transformation
    """
    
    def __init__(self):
        self.client = None
        self.timeout = httpx.Timeout(settings.HTTP_TIMEOUT)
        
    async def execute(self, function: Function, parameters: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute an API function with full HTTP client support
        
        Args:
            function: Function object with API configuration
            parameters: Function parameters from user input
            context: Execution context
            
        Returns:
            Dict containing API response and metadata
        """
        if not function.api_config:
            raise ValueError("API configuration is required for API functions")
        
        api_config = function.api_config
        start_time = time.time()
        
        # Initialize HTTP client if needed
        if not self.client:
            await self._initialize_client()
        
        try:
            # Validate API configuration
            self._validate_api_config(api_config)
            
            # Build request
            request_data = await self._build_request(api_config, parameters, context)
            
            # Execute request with retry logic
            response_data = await self._execute_with_retry(
                method=api_config['method'],
                url=request_data['url'],
                headers=request_data['headers'],
                data=request_data.get('data'),
                params=request_data.get('params'),
                max_retries=api_config.get('retry', {}).get('max_attempts', 3)
            )
            
            # Transform response
            transformed_response = self._transform_response(response_data, api_config)
            
            execution_time = time.time() - start_time
            
            return {
                "success": True,
                "result": transformed_response,
                "metadata": {
                    "execution_time": execution_time,
                    "status_code": response_data.get('status_code'),
                    "method": api_config['method'],
                    "endpoint": api_config['endpoint'],
                    "response_size": len(str(transformed_response))
                }
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                "success": False,
                "error": str(e),
                "metadata": {
                    "execution_time": execution_time,
                    "method": api_config.get('method', 'UNKNOWN'),
                    "endpoint": api_config.get('endpoint', 'UNKNOWN')
                }
            }
    
    async def _initialize_client(self):
        """Initialize HTTP client with configuration"""
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            verify=True
        )
    
    def _validate_api_config(self, api_config: Dict[str, Any]):
        """Validate API configuration"""
        required_fields = ['method', 'endpoint']
        for field in required_fields:
            if field not in api_config:
                raise ValueError(f"Missing required API config field: {field}")
        
        # Validate method
        allowed_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
        if api_config['method'].upper() not in allowed_methods:
            raise ValueError(f"Unsupported HTTP method: {api_config['method']}")
        
        # Validate endpoint URL
        try:
            parsed_url = urlparse(api_config['endpoint'])
            if not parsed_url.scheme or not parsed_url.netloc:
                raise ValueError(f"Invalid endpoint URL: {api_config['endpoint']}")
        except Exception as e:
            raise ValueError(f"Invalid endpoint URL: {e}")
        
        # Security check - block localhost and private IPs in production
        if settings.is_production:
            if any(blocked in api_config['endpoint'].lower() for blocked in 
                   ['localhost', '127.0.0.1', '192.168.', '10.', '172.16.', '172.17.']):
                raise ValueError("Private/localhost endpoints not allowed in production")
    
    async def _build_request(self, api_config: Dict[str, Any], parameters: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Build HTTP request from configuration and parameters"""
        
        # Start with the base endpoint
        url = api_config['endpoint']
        
        # Prepare headers
        headers = api_config.get('headers', {}).copy()
        
        # Add authentication headers
        auth_config = api_config.get('authentication', {})
        if auth_config:
            headers.update(self._build_auth_headers(auth_config))
        
        # Prepare request data and parameters
        request_data = {
            'url': url,
            'headers': headers
        }
        
        # Handle request transformation
        transform_config = api_config.get('request_transform', {})
        if transform_config:
            transformed_data = self._transform_request(transform_config, parameters, context)
            
            if api_config['method'].upper() in ['POST', 'PUT', 'PATCH']:
                if headers.get('Content-Type', '').startswith('application/json'):
                    request_data['data'] = json.dumps(transformed_data)
                else:
                    request_data['data'] = transformed_data
            else:
                request_data['params'] = transformed_data
        else:
            # Use parameters directly
            if api_config['method'].upper() in ['POST', 'PUT', 'PATCH']:
                request_data['data'] = json.dumps(parameters)
                headers['Content-Type'] = 'application/json'
            else:
                request_data['params'] = parameters
        
        return request_data
    
    def _build_auth_headers(self, auth_config: Dict[str, Any]) -> Dict[str, str]:
        """Build authentication headers"""
        headers = {}
        
        auth_type = auth_config.get('type', '').lower()
        
        if auth_type == 'bearer':
            token = auth_config.get('token') or auth_config.get('token_key', '')
            if token:
                # Support environment variable references
                if token.startswith('${') and token.endswith('}'):
                    import os
                    env_var = token[2:-1]
                    token = os.getenv(env_var, '')
                headers['Authorization'] = f'Bearer {token}'
        
        elif auth_type == 'api_key':
            api_key = auth_config.get('api_key') or auth_config.get('token', '')
            header_name = auth_config.get('header_name', 'X-API-Key')
            if api_key:
                # Support environment variable references
                if api_key.startswith('${') and api_key.endswith('}'):
                    import os
                    env_var = api_key[2:-1]
                    api_key = os.getenv(env_var, '')
                headers[header_name] = api_key
        
        elif auth_type == 'basic':
            username = auth_config.get('username', '')
            password = auth_config.get('password', '')
            if username and password:
                import base64
                credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
                headers['Authorization'] = f'Basic {credentials}'
        
        return headers
    
    def _transform_request(self, transform_config: Dict[str, Any], parameters: Dict[str, Any], context: Dict[str, Any] = None) -> Any:
        """Transform request data using configuration"""
        
        template_str = transform_config.get('template', '')
        variables = transform_config.get('variables', [])
        
        if template_str:
            # Use Jinja2 for template processing
            template = Template(template_str)
            
            # Prepare template variables
            template_vars = {}
            template_vars.update(parameters)
            if context:
                template_vars.update(context)
            
            # Render template
            rendered = template.render(**template_vars)
            
            # Try to parse as JSON, fall back to string
            try:
                return json.loads(rendered)
            except json.JSONDecodeError:
                return rendered
        
        else:
            # Simple variable mapping
            result = {}
            for var in variables:
                if var in parameters:
                    result[var] = parameters[var]
            return result if result else parameters
    
    async def _execute_with_retry(self, method: str, url: str, headers: Dict[str, str], 
                                data: Any = None, params: Dict = None, max_retries: int = 3) -> Dict[str, Any]:
        """Execute HTTP request with retry logic"""
        
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                # Execute request
                response = await self.client.request(
                    method=method.upper(),
                    url=url,
                    headers=headers,
                    content=data if isinstance(data, (str, bytes)) else None,
                    json=data if not isinstance(data, (str, bytes)) and data is not None else None,
                    params=params
                )
                
                # Handle response
                response_data = {
                    'status_code': response.status_code,
                    'headers': dict(response.headers),
                    'content': response.text
                }
                
                # Try to parse JSON response
                try:
                    response_data['json'] = response.json()
                except:
                    response_data['json'] = None
                
                # Check if request was successful
                if 200 <= response.status_code < 300:
                    return response_data
                elif response.status_code >= 500 and attempt < max_retries:
                    # Retry on server errors
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    raise httpx.HTTPStatusError(
                        f"HTTP {response.status_code}: {response.text}",
                        request=response.request,
                        response=response
                    )
                
            except httpx.TimeoutException as e:
                last_exception = e
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    raise e
            
            except httpx.RequestError as e:
                last_exception = e
                if attempt < max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    raise e
        
        if last_exception:
            raise last_exception
    
    def _transform_response(self, response_data: Dict[str, Any], api_config: Dict[str, Any]) -> Any:
        """Transform response data using configuration"""
        
        response_config = api_config.get('response_transform', {})
        if not response_config:
            # Return JSON if available, otherwise text
            return response_data.get('json') or response_data.get('content', '')
        
        # Extract data using JSONPath-like syntax
        path = response_config.get('path', '')
        format_type = response_config.get('format', 'auto')
        
        # Start with the appropriate data source
        if response_data.get('json'):
            data = response_data['json']
        else:
            data = response_data.get('content', '')
        
        # Apply path extraction
        if path and isinstance(data, dict):
            try:
                # Simple JSONPath implementation
                if path.startswith('$.'):
                    path = path[2:]  # Remove $.
                
                keys = path.split('.')
                for key in keys:
                    if key:
                        data = data[key]
            except (KeyError, TypeError):
                # If path extraction fails, return original data
                pass
        
        # Apply format transformation
        if format_type == 'json' and isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                pass
        elif format_type == 'text':
            data = str(data)
        
        return data
    
    async def close(self):
        """Close HTTP client"""
        if self.client:
            await self.client.aclose()
            self.client = None
    
    def __del__(self):
        """Cleanup on destruction"""
        if self.client:
            try:
                asyncio.create_task(self.close())
            except:
                pass


# Test configuration examples
EXAMPLE_API_CONFIGS = {
    "rest_api_example": {
        "method": "POST",
        "endpoint": "https://api.example.com/v1/data",
        "headers": {
            "Content-Type": "application/json",
            "User-Agent": "ATTILA-AI/1.0"
        },
        "authentication": {
            "type": "bearer",
            "token": "${API_TOKEN}"
        },
        "request_transform": {
            "template": '{"query": "{{ search_term }}", "limit": {{ limit | default(10) }}}',
            "variables": ["search_term", "limit"]
        },
        "response_transform": {
            "path": "$.data.results",
            "format": "json"
        },
        "retry": {
            "max_attempts": 3,
            "backoff": "exponential"
        }
    },
    
    "webhook_example": {
        "method": "POST",
        "endpoint": "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX",
        "headers": {
            "Content-Type": "application/json"
        },
        "request_transform": {
            "template": '{"text": "{{ message }}", "channel": "#{{ channel | default(\"general\") }}"}',
            "variables": ["message", "channel"]
        },
        "response_transform": {
            "format": "text"
        }
    }
}