"""
MCP Function Executor for Model Context Protocol integration
Supports WebSocket communication with MCP-compatible services
"""
import asyncio
import json
import time
import uuid
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass

import websockets
import msgpack

from ...core.config import settings
from ...models.function import Function


class MCPMessageType(Enum):
    """MCP message types"""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"


@dataclass
class MCPMessage:
    """MCP protocol message"""
    message_type: MCPMessageType
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


class MCPExecutor:
    """
    MCP (Model Context Protocol) function executor with WebSocket support
    """
    
    def __init__(self):
        self.connections = {}
        self.pending_requests = {}
        
    async def execute(self, function: Function, parameters: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute an MCP function with WebSocket communication
        
        Args:
            function: Function object with MCP configuration
            parameters: Function parameters from user input
            context: Execution context
            
        Returns:
            Dict containing MCP response and metadata
        """
        if not function.mcp_config:
            raise ValueError("MCP configuration is required for MCP functions")
        
        start_time = time.time()
        mcp_config = function.mcp_config
        
        try:
            # Validate MCP configuration
            self._validate_mcp_config(mcp_config)
            
            # Get or create connection
            connection = await self._get_connection(mcp_config)
            
            # Build MCP request message
            request_message = self._build_request_message(
                method=parameters.get('method', 'execute'),
                params=parameters,
                context=context
            )
            
            # Send request and wait for response
            response = await self._send_request(connection, request_message, mcp_config)
            
            execution_time = time.time() - start_time
            
            return {
                "success": True,
                "result": response.result,
                "metadata": {
                    "execution_time": execution_time,
                    "protocol_version": mcp_config.get("protocol_version", "1.0"),
                    "endpoint": mcp_config["endpoint"],
                    "message_format": mcp_config.get("message_format", "json"),
                    "request_id": request_message.id
                }
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                "success": False,
                "error": str(e),
                "metadata": {
                    "execution_time": execution_time,
                    "endpoint": mcp_config.get("endpoint", "unknown")
                }
            }
    
    def _validate_mcp_config(self, mcp_config: Dict[str, Any]):
        """Validate MCP configuration"""
        required_fields = ['endpoint']
        for field in required_fields:
            if field not in mcp_config:
                raise ValueError(f"Missing required MCP config field: {field}")
        
        # Validate endpoint URL
        endpoint = mcp_config['endpoint']
        if not endpoint.startswith(('ws://', 'wss://')):
            raise ValueError(f"MCP endpoint must be a WebSocket URL: {endpoint}")
        
        # Validate protocol version
        protocol_version = mcp_config.get('protocol_version', '1.0')
        supported_versions = ['1.0', '1.1']
        if protocol_version not in supported_versions:
            raise ValueError(f"Unsupported MCP protocol version: {protocol_version}")
        
        # Validate message format
        message_format = mcp_config.get('message_format', 'json')
        if message_format not in ['json', 'msgpack']:
            raise ValueError(f"Unsupported message format: {message_format}")
    
    async def _get_connection(self, mcp_config: Dict[str, Any]):
        """Get or create WebSocket connection to MCP service"""
        
        endpoint = mcp_config['endpoint']
        connection_key = self._get_connection_key(mcp_config)
        
        # Check if we have an existing connection
        if connection_key in self.connections:
            connection = self.connections[connection_key]
            if not connection.closed:
                return connection
            else:
                # Connection is closed, remove from cache
                del self.connections[connection_key]
        
        # Create new connection
        connection = await self._create_connection(mcp_config)
        self.connections[connection_key] = connection
        
        return connection
    
    def _get_connection_key(self, mcp_config: Dict[str, Any]) -> str:
        """Generate unique connection key"""
        endpoint = mcp_config['endpoint']
        auth_key = str(mcp_config.get('authentication', {}))
        return f"{endpoint}:{hash(auth_key)}"
    
    async def _create_connection(self, mcp_config: Dict[str, Any]):
        """Create new WebSocket connection"""
        
        endpoint = mcp_config['endpoint']
        timeout = mcp_config.get('timeout', settings.WS_CONNECTION_TIMEOUT)
        
        # Prepare connection headers
        headers = {}
        
        # Add authentication if configured
        auth_config = mcp_config.get('authentication', {})
        if auth_config:
            headers.update(self._build_auth_headers(auth_config))
        
        try:
            # Create WebSocket connection
            connection = await asyncio.wait_for(
                websockets.connect(
                    endpoint,
                    extra_headers=headers,
                    compression=mcp_config.get('compression'),
                    ping_interval=mcp_config.get('ping_interval', 20),
                    ping_timeout=mcp_config.get('ping_timeout', 10)
                ),
                timeout=timeout
            )
            
            # Send initial handshake if required
            await self._perform_handshake(connection, mcp_config)
            
            return connection
            
        except Exception as e:
            raise ConnectionError(f"Failed to connect to MCP service: {e}")
    
    def _build_auth_headers(self, auth_config: Dict[str, Any]) -> Dict[str, str]:
        """Build authentication headers for WebSocket connection"""
        headers = {}
        
        auth_type = auth_config.get('type', '').lower()
        
        if auth_type == 'bearer':
            token = auth_config.get('token', '')
            if token:
                # Support environment variable references
                if token.startswith('${') and token.endswith('}'):
                    import os
                    env_var = token[2:-1]
                    token = os.getenv(env_var, '')
                headers['Authorization'] = f'Bearer {token}'
        
        elif auth_type == 'api_key':
            api_key = auth_config.get('api_key', '')
            header_name = auth_config.get('header_name', 'X-API-Key')
            if api_key:
                headers[header_name] = api_key
        
        return headers
    
    async def _perform_handshake(self, connection, mcp_config: Dict[str, Any]):
        """Perform MCP protocol handshake"""
        
        protocol_version = mcp_config.get('protocol_version', '1.0')
        
        # Send handshake message
        handshake_message = MCPMessage(
            message_type=MCPMessageType.REQUEST,
            method="initialize",
            params={
                "protocol_version": protocol_version,
                "client_info": {
                    "name": "ATTILA-AI",
                    "version": "1.0.0"
                }
            },
            id=str(uuid.uuid4())
        )
        
        # Send handshake
        await self._send_message(connection, handshake_message, mcp_config)
        
        # Wait for handshake response
        response_message = await self._receive_message(connection, mcp_config)
        
        if response_message.message_type == MCPMessageType.ERROR:
            raise ConnectionError(f"MCP handshake failed: {response_message.error}")
        
        if response_message.result:
            server_info = response_message.result
            print(f"Connected to MCP server: {server_info.get('server_info', {}).get('name', 'unknown')}")
    
    def _build_request_message(self, method: str, params: Dict[str, Any], context: Dict[str, Any] = None) -> MCPMessage:
        """Build MCP request message"""
        
        # Combine parameters and context
        request_params = params.copy()
        if context:
            request_params['context'] = context
        
        return MCPMessage(
            message_type=MCPMessageType.REQUEST,
            method=method,
            params=request_params,
            id=str(uuid.uuid4())
        )
    
    async def _send_request(self, connection, request_message: MCPMessage, mcp_config: Dict[str, Any]) -> MCPMessage:
        """Send request and wait for response"""
        
        request_id = request_message.id
        timeout = mcp_config.get('timeout', 30)
        
        # Store pending request
        response_future = asyncio.Future()
        self.pending_requests[request_id] = response_future
        
        try:
            # Send request
            await self._send_message(connection, request_message, mcp_config)
            
            # Wait for response
            response = await asyncio.wait_for(response_future, timeout=timeout)
            
            return response
            
        except asyncio.TimeoutError:
            raise TimeoutError(f"MCP request timed out after {timeout} seconds")
        
        finally:
            # Clean up pending request
            self.pending_requests.pop(request_id, None)
    
    async def _send_message(self, connection, message: MCPMessage, mcp_config: Dict[str, Any]):
        """Send message over WebSocket connection"""
        
        message_format = mcp_config.get('message_format', 'json')
        
        # Convert message to dict
        message_dict = {
            'type': message.message_type.value,
            'id': message.id
        }
        
        if message.method:
            message_dict['method'] = message.method
        if message.params:
            message_dict['params'] = message.params
        if message.result is not None:
            message_dict['result'] = message.result
        if message.error:
            message_dict['error'] = message.error
        
        # Serialize message
        if message_format == 'json':
            serialized_message = json.dumps(message_dict)
        elif message_format == 'msgpack':
            serialized_message = msgpack.packb(message_dict)
        else:
            raise ValueError(f"Unsupported message format: {message_format}")
        
        # Send message
        await connection.send(serialized_message)
    
    async def _receive_message(self, connection, mcp_config: Dict[str, Any]) -> MCPMessage:
        """Receive message from WebSocket connection"""
        
        message_format = mcp_config.get('message_format', 'json')
        
        # Receive raw message
        raw_message = await connection.recv()
        
        # Deserialize message
        try:
            if message_format == 'json':
                message_dict = json.loads(raw_message)
            elif message_format == 'msgpack':
                message_dict = msgpack.unpackb(raw_message, raw=False)
            else:
                raise ValueError(f"Unsupported message format: {message_format}")
        except Exception as e:
            raise ValueError(f"Failed to deserialize message: {e}")
        
        # Convert to MCPMessage
        message_type = MCPMessageType(message_dict.get('type', 'response'))
        
        message = MCPMessage(
            message_type=message_type,
            method=message_dict.get('method'),
            params=message_dict.get('params'),
            result=message_dict.get('result'),
            error=message_dict.get('error'),
            id=message_dict.get('id')
        )
        
        # Handle response to pending request
        if message.id and message.id in self.pending_requests:
            future = self.pending_requests[message.id]
            if not future.done():
                future.set_result(message)
        
        return message
    
    async def close_connections(self):
        """Close all WebSocket connections"""
        for connection in self.connections.values():
            if not connection.closed:
                await connection.close()
        
        self.connections.clear()
        self.pending_requests.clear()
    
    async def close(self):
        """Close executor and clean up resources"""
        await self.close_connections()


# Example MCP configurations
EXAMPLE_MCP_CONFIGS = {
    "code_analysis_service": {
        "protocol_version": "1.0",
        "endpoint": "wss://mcp.codeanalysis.com/ws",
        "authentication": {
            "type": "bearer",
            "token": "${MCP_CODE_TOKEN}"
        },
        "message_format": "json",
        "timeout": 30,
        "reconnect": {
            "enabled": True,
            "max_attempts": 5,
            "backoff": 2
        }
    },
    
    "data_processing_service": {
        "protocol_version": "1.1",
        "endpoint": "wss://mcp.dataproc.com/ws",
        "authentication": {
            "type": "api_key",
            "api_key": "${MCP_DATA_KEY}",
            "header_name": "X-MCP-Key"
        },
        "message_format": "msgpack",
        "timeout": 60,
        "compression": "deflate"
    },
    
    "ai_assistant_service": {
        "protocol_version": "1.0",
        "endpoint": "wss://mcp.assistant.com/ws",
        "message_format": "json",
        "timeout": 45,
        "ping_interval": 30,
        "ping_timeout": 10
    }
}