# ATTILA AI - API Documentation
## Enhanced Function Management System

### 🎯 Base URLs
- **Development**: `http://localhost:8000/api/v1`
- **Production**: `https://attila-ai.com/api/v1`

### 🔐 Authentication
```http
Authorization: Bearer <your_api_token>
Content-Type: application/json
```

## 📋 Function Management API

### Create Function
```http
POST /functions
```

**Request Body:**
```json
{
    "name": "Jira Ticket Creator",
    "description": "Creates Jira tickets with AI assistance",
    "function_type": "api",
    "category": "productivity",
    "icon": "ticket",
    "parameters": [
        {
            "name": "summary",
            "type": "string",
            "description": "Ticket summary",
            "required": true
        },
        {
            "name": "description",
            "type": "string", 
            "description": "Detailed description",
            "required": false
        }
    ],
    "api_config": {
        "method": "POST",
        "endpoint": "https://company.atlassian.net/rest/api/3/issue",
        "headers": {
            "Authorization": "Basic ${JIRA_TOKEN}",
            "Content-Type": "application/json"
        },
        "request_transform": {
            "template": "{\"fields\": {\"project\": {\"key\": \"PROJ\"}, \"summary\": \"${summary}\", \"description\": \"${description}\", \"issuetype\": {\"name\": \"Task\"}}}"
        },
        "timeout": 30
    },
    "dependencies": [],
    "is_enabled": true
}
```

**Response:**
```json
{
    "id": "func_123456789",
    "name": "Jira Ticket Creator",
    "function_type": "api",
    "status": "created",
    "created_at": "2025-01-15T10:00:00Z"
}
```

### List Functions
```http
GET /functions?type={function_type}&category={category}&enabled={true|false}
```

**Response:**
```json
{
    "functions": [
        {
            "id": "func_123456789",
            "name": "Jira Ticket Creator", 
            "function_type": "api",
            "category": "productivity",
            "is_enabled": true,
            "execution_count": 156,
            "avg_execution_time": 1.2,
            "success_rate": 0.98
        }
    ],
    "total": 25,
    "page": 1,
    "per_page": 20
}
```

### Update Function
```http
PUT /functions/{function_id}
```

### Delete Function
```http
DELETE /functions/{function_id}
```

## 🧠 Function Router API

### Analyze Message Intent
```http
POST /router/analyze
```

**Request:**
```json
{
    "message": "Create a Jira ticket for the login bug and search for related documentation",
    "session_id": "session_123",
    "available_functions": ["jira_create", "doc_search", "web_search"],
    "context": {
        "user_preferences": {"preferred_functions": ["jira_create"]},
        "recent_failures": []
    }
}
```

**Response:**
```json
{
    "intent": "Create task and gather information",
    "intent_category": "task_creation",
    "suggested_functions": ["jira_create", "doc_search"],
    "confidence": 0.92,
    "reasoning": "User wants to create a Jira ticket (high confidence) and search for documentation (medium confidence)",
    "execution_strategy": "sequential",
    "estimated_execution_time": 2.5,
    "dependencies_resolved": true
}
```

### Route Functions
```http
POST /router/route
```

**Request:**
```json
{
    "message": "Generate a summary of our API docs and save to Confluence",
    "session_id": "session_123",
    "routing_config": {
        "max_functions": 5,
        "min_confidence": 0.7,
        "enable_auto_dependencies": true
    }
}
```

**Response:**
```json
{
    "selected_functions": ["doc_summarize", "confluence_save"],
    "execution_plan": {
        "phases": [
            {
                "functions": ["doc_summarize"],
                "execution_type": "sequential",
                "estimated_time": 3.0
            },
            {
                "functions": ["confluence_save"],
                "execution_type": "sequential", 
                "estimated_time": 1.5
            }
        ]
    },
    "total_estimated_time": 4.5,
    "confidence": 0.89
}
```

## 🚀 Function Execution API

### Execute Functions
```http
POST /execute
```

**Request:**
```json
{
    "functions": [
        {
            "function_id": "func_123456789",
            "parameters": {
                "summary": "Login page throws 500 error",
                "description": "Users cannot log in due to server error"
            }
        }
    ],
    "session_id": "session_123",
    "execution_config": {
        "timeout": 30,
        "enable_recovery": true,
        "max_retries": 3
    }
}
```

**Response:**
```json
{
    "execution_id": "exec_987654321",
    "status": "completed",
    "results": {
        "func_123456789": {
            "status": "completed",
            "result": {
                "ticket_id": "PROJ-123",
                "ticket_url": "https://company.atlassian.net/browse/PROJ-123"
            },
            "execution_time": 1.4,
            "memory_used": 45
        }
    },
    "total_execution_time": 1.4,
    "performance": {
        "success_rate": 1.0,
        "avg_memory_usage": 45
    }
}
```

### Get Execution Status
```http
GET /execute/{execution_id}
```

### Stream Execution Progress
```http
GET /execute/{execution_id}/stream
```
WebSocket endpoint for real-time execution updates.

## 💬 Chat API

### Send Message with Functions
```http
POST /chat/message
```

**Request:**
```json
{
    "message": "Create a ticket for the bug and find similar issues",
    "session_id": "session_123",
    "functions": {
        "auto_select": true,
        "max_functions": 3,
        "preferred_types": ["api", "prompt"]
    }
}
```

**Response:**
```json
{
    "message_id": "msg_456789",
    "response": "I'll create a Jira ticket for the bug and search for similar issues. Let me execute these functions for you.",
    "functions_executed": [
        {
            "function_name": "jira_create",
            "result": {"ticket_id": "PROJ-123"},
            "execution_time": 1.2
        },
        {
            "function_name": "issue_search", 
            "result": {"similar_issues": 3},
            "execution_time": 0.8
        }
    ],
    "total_execution_time": 2.0,
    "generated_response": "Created ticket PROJ-123 for the bug. Found 3 similar issues that might be related."
}
```

## 📊 Analytics API

### Function Performance
```http
GET /analytics/functions/{function_id}/performance?period=7d
```

**Response:**
```json
{
    "function_id": "func_123456789",
    "period": "7d",
    "metrics": {
        "execution_count": 156,
        "success_rate": 0.98,
        "avg_execution_time": 1.24,
        "avg_memory_usage": 42,
        "error_rate": 0.02
    },
    "trends": {
        "execution_time_trend": "stable",
        "success_rate_trend": "improving"
    }
}
```

### System Health
```http
GET /analytics/system/health
```

**Response:**
```json
{
    "status": "healthy",
    "metrics": {
        "active_executions": 12,
        "cpu_usage": 0.45,
        "memory_usage": 0.67,
        "response_time_p95": 1.8
    },
    "alerts": []
}
```

## 🔧 WebSocket Events

### Connect to Real-time Updates
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/{session_id}');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    switch(data.type) {
        case 'function_started':
            console.log(`Function ${data.function_name} started`);
            break;
        case 'function_completed':
            console.log(`Function completed:`, data.result);
            break;
        case 'function_failed':
            console.log(`Function failed:`, data.error);
            break;
        case 'execution_progress':
            console.log(`Progress: ${data.progress}%`);
            break;
    }
};
```

## 🚨 Error Responses

### Standard Error Format
```json
{
    "error": {
        "code": "FUNCTION_EXECUTION_FAILED",
        "message": "Function execution failed due to timeout",
        "details": {
            "function_id": "func_123456789",
            "execution_time": 30.0,
            "error_type": "timeout"
        },
        "retry_possible": true,
        "suggested_action": "Increase timeout or check function configuration"
    }
}
```

### Error Codes
- `INVALID_FUNCTION_TYPE` - Unsupported function type
- `FUNCTION_NOT_FOUND` - Function ID doesn't exist
- `EXECUTION_TIMEOUT` - Function execution exceeded timeout
- `DEPENDENCY_ERROR` - Function dependency issue
- `RESOURCE_EXHAUSTED` - System resource limits exceeded
- `AUTHENTICATION_FAILED` - Invalid API credentials
- `RATE_LIMIT_EXCEEDED` - Too many requests

## 📈 Rate Limits
- **Function Creation**: 10 per minute
- **Function Execution**: 100 per minute  
- **Router Analysis**: 200 per minute
- **Chat Messages**: 60 per minute

## 🔄 Pagination
Standard pagination for list endpoints:
```http
GET /functions?page=2&per_page=20&sort=created_at&order=desc
```

---

**Version**: 1.0  
**Last Updated**: January 15, 2025 