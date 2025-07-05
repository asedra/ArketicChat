# Database Schema Guide
## ATTILA AI Enhanced Function Management System

### 🎯 Overview
Enhanced SQLite schema to support multi-function conversations, intelligent routing, and advanced function types (MCP, API, Prompt, Document).

## 📊 Core Tables

### 1. Enhanced Functions Table
```sql
-- Update existing functions table
ALTER TABLE functions ADD COLUMN function_type VARCHAR(50) DEFAULT 'basic';
ALTER TABLE functions ADD COLUMN prompt_template TEXT;
ALTER TABLE functions ADD COLUMN api_config JSON;
ALTER TABLE functions ADD COLUMN mcp_config JSON;
ALTER TABLE functions ADD COLUMN document_content TEXT;
ALTER TABLE functions ADD COLUMN execution_order INTEGER DEFAULT 0;
ALTER TABLE functions ADD COLUMN dependencies JSON DEFAULT '[]';
ALTER TABLE functions ADD COLUMN success_criteria TEXT;
ALTER TABLE functions ADD COLUMN error_handling JSON DEFAULT '{}';
ALTER TABLE functions ADD COLUMN is_system BOOLEAN DEFAULT FALSE;

-- Add indexes for performance
CREATE INDEX idx_functions_type ON functions(function_type);
CREATE INDEX idx_functions_category ON functions(category);
CREATE INDEX idx_functions_enabled ON functions(is_enabled);
CREATE INDEX idx_functions_system ON functions(is_system);
```

### 2. Function Executions Table
```sql
CREATE TABLE function_executions (
    id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
    session_id TEXT NOT NULL,
    function_id TEXT NOT NULL,
    execution_order INTEGER,
    
    -- Input/Output data
    input_data JSON,
    output_data JSON,
    
    -- Performance metrics
    execution_time REAL,
    memory_used INTEGER,
    cpu_time REAL,
    
    -- Status tracking
    status VARCHAR(20) CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    -- Timestamps
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign keys
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (function_id) REFERENCES functions(id) ON DELETE CASCADE
);

-- Performance indexes
CREATE INDEX idx_executions_session ON function_executions(session_id);
CREATE INDEX idx_executions_function ON function_executions(function_id);
CREATE INDEX idx_executions_status ON function_executions(status);
CREATE INDEX idx_executions_created ON function_executions(created_at DESC);
CREATE INDEX idx_executions_performance ON function_executions(execution_time, memory_used);
```

### 3. Function Router Configuration
```sql
CREATE TABLE function_router (
    id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Routing configuration
    routing_rules JSON NOT NULL,
    priority INTEGER DEFAULT 0,
    
    -- Confidence thresholds
    min_confidence REAL DEFAULT 0.7,
    auto_execute_threshold REAL DEFAULT 0.95,
    
    -- Performance constraints
    max_functions INTEGER DEFAULT 5,
    max_execution_time REAL DEFAULT 30.0,
    
    -- Status
    is_default BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Ensure only one default router
CREATE UNIQUE INDEX idx_router_default ON function_router(is_default) WHERE is_default = TRUE;
CREATE INDEX idx_router_active ON function_router(is_active, priority);
```

### 4. Session Function Context
```sql
CREATE TABLE session_function_context (
    id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
    session_id TEXT NOT NULL UNIQUE,
    
    -- Active configuration
    active_functions JSON DEFAULT '[]',
    function_router_id TEXT,
    
    -- Context data
    context_data JSON DEFAULT '{}',
    user_preferences JSON DEFAULT '{}',
    
    -- Performance tracking
    total_executions INTEGER DEFAULT 0,
    successful_executions INTEGER DEFAULT 0,
    average_execution_time REAL DEFAULT 0,
    
    -- Learning data
    function_usage_patterns JSON DEFAULT '{}',
    error_patterns JSON DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign keys
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (function_router_id) REFERENCES function_router(id) ON DELETE SET NULL
);

CREATE INDEX idx_context_session ON session_function_context(session_id);
CREATE INDEX idx_context_router ON session_function_context(function_router_id);
CREATE INDEX idx_context_activity ON session_function_context(last_activity);
```

### 5. Function Performance Metrics
```sql
CREATE TABLE function_performance_metrics (
    id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
    function_id TEXT NOT NULL,
    
    -- Time period
    date DATE NOT NULL,
    hour INTEGER CHECK (hour >= 0 AND hour <= 23),
    
    -- Execution metrics
    execution_count INTEGER DEFAULT 0,
    successful_executions INTEGER DEFAULT 0,
    failed_executions INTEGER DEFAULT 0,
    
    -- Performance metrics
    total_execution_time REAL DEFAULT 0,
    avg_execution_time REAL DEFAULT 0,
    min_execution_time REAL DEFAULT 0,
    max_execution_time REAL DEFAULT 0,
    
    -- Resource metrics
    total_memory_used INTEGER DEFAULT 0,
    avg_memory_used INTEGER DEFAULT 0,
    max_memory_used INTEGER DEFAULT 0,
    
    -- Error analysis
    timeout_count INTEGER DEFAULT 0,
    error_types JSON DEFAULT '{}',
    
    -- Calculated fields
    success_rate REAL GENERATED ALWAYS AS (
        CASE 
            WHEN execution_count > 0 THEN CAST(successful_executions AS REAL) / execution_count
            ELSE 0 
        END
    ) STORED,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign keys
    FOREIGN KEY (function_id) REFERENCES functions(id) ON DELETE CASCADE,
    
    -- Unique constraint
    UNIQUE(function_id, date, hour)
);

-- Performance analysis indexes
CREATE INDEX idx_perf_function_date ON function_performance_metrics(function_id, date);
CREATE INDEX idx_perf_success_rate ON function_performance_metrics(success_rate);
CREATE INDEX idx_perf_avg_time ON function_performance_metrics(avg_execution_time);
```

### 6. Router Decision Log
```sql
CREATE TABLE router_decision_log (
    id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
    session_id TEXT NOT NULL,
    router_id TEXT NOT NULL,
    
    -- Input data
    user_message TEXT NOT NULL,
    available_functions JSON NOT NULL,
    context_data JSON,
    
    -- Analysis results
    intent_analysis JSON NOT NULL,
    suggested_functions JSON NOT NULL,
    confidence_score REAL NOT NULL,
    execution_strategy VARCHAR(20),
    
    -- Applied rules
    routing_rules_applied JSON,
    dependencies_resolved JSON,
    
    -- Outcome
    final_functions JSON NOT NULL,
    user_accepted BOOLEAN,
    execution_success BOOLEAN,
    
    -- Performance
    analysis_time REAL,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign keys
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (router_id) REFERENCES function_router(id) ON DELETE CASCADE
);

-- Analytics indexes
CREATE INDEX idx_router_log_session ON router_decision_log(session_id);
CREATE INDEX idx_router_log_confidence ON router_decision_log(confidence_score);
CREATE INDEX idx_router_log_success ON router_decision_log(execution_success);
CREATE INDEX idx_router_log_created ON router_decision_log(created_at DESC);
```

## 🔧 Function Type Configurations

### API Function Configuration
```json
{
    "method": "POST|GET|PUT|DELETE",
    "endpoint": "https://api.example.com/v1/resource",
    "headers": {
        "Authorization": "Bearer ${API_KEY}",
        "Content-Type": "application/json"
    },
    "request_transform": {
        "template": "{\"key\": \"${parameter_name}\"}",
        "variables": ["parameter_name"]
    },
    "response_transform": {
        "path": "$.result.data",
        "format": "json|text|xml"
    },
    "authentication": {
        "type": "bearer|basic|api_key",
        "token_key": "API_KEY",
        "header_name": "Authorization"
    },
    "timeout": 30,
    "retry": {
        "max_attempts": 3,
        "backoff": "exponential|linear",
        "initial_delay": 1
    }
}
```

### MCP Function Configuration
```json
{
    "protocol_version": "1.0",
    "endpoint": "wss://mcp.example.com/ws",
    "authentication": {
        "type": "bearer|api_key",
        "token": "${MCP_TOKEN}"
    },
    "message_format": "json|msgpack",
    "timeout": 30,
    "reconnect": {
        "enabled": true,
        "max_attempts": 5,
        "backoff": 2
    },
    "compression": "gzip"
}
```

### Prompt Function Configuration
```json
{
    "model": "gpt-4|claude-3|gemini-pro",
    "temperature": 0.7,
    "max_tokens": 1000,
    "top_p": 1.0,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0,
    "response_format": "text|json",
    "system_prompt": "Additional system instructions",
    "tools": ["function_calling", "code_interpreter"],
    "stream": false
}
```

### Document Function Configuration
```json
{
    "processing_config": {
        "chunk_size": 1000,
        "overlap": 200,
        "format": "markdown|text|pdf"
    },
    "search_config": {
        "method": "semantic|keyword|hybrid",
        "embedding_model": "text-embedding-ada-002",
        "similarity_threshold": 0.8,
        "max_results": 5
    },
    "indexing": {
        "enabled": true,
        "update_frequency": "realtime|hourly|daily"
    }
}
```

## 📈 Performance Optimization

### Database Indexes Strategy
```sql
-- Composite indexes for common queries
CREATE INDEX idx_executions_session_status_time ON function_executions(session_id, status, created_at DESC);
CREATE INDEX idx_functions_type_enabled_category ON functions(function_type, is_enabled, category);
CREATE INDEX idx_perf_function_success_time ON function_performance_metrics(function_id, success_rate DESC, avg_execution_time);

-- Partial indexes for active data
CREATE INDEX idx_active_functions ON functions(id, name) WHERE is_enabled = TRUE;
CREATE INDEX idx_recent_executions ON function_executions(id, function_id, execution_time) 
    WHERE created_at > datetime('now', '-7 days');
```

### Database Maintenance
```sql
-- Cleanup old execution records (keep last 30 days)
DELETE FROM function_executions 
WHERE created_at < datetime('now', '-30 days');

-- Cleanup old performance metrics (keep last 90 days)
DELETE FROM function_performance_metrics 
WHERE date < date('now', '-90 days');

-- Cleanup old router logs (keep last 30 days)
DELETE FROM router_decision_log 
WHERE created_at < datetime('now', '-30 days');

-- Update statistics
ANALYZE;

-- Vacuum database
VACUUM;
```

## 🔄 Migration Scripts

### Migration 001: Add Function Types
```sql
-- 001_add_function_types.sql
BEGIN TRANSACTION;

ALTER TABLE functions ADD COLUMN function_type VARCHAR(50) DEFAULT 'basic';
ALTER TABLE functions ADD COLUMN prompt_template TEXT;
ALTER TABLE functions ADD COLUMN api_config JSON;
ALTER TABLE functions ADD COLUMN mcp_config JSON;
ALTER TABLE functions ADD COLUMN document_content TEXT;
ALTER TABLE functions ADD COLUMN execution_order INTEGER DEFAULT 0;
ALTER TABLE functions ADD COLUMN dependencies JSON DEFAULT '[]';

-- Create indexes
CREATE INDEX idx_functions_type ON functions(function_type);

-- Update existing functions to 'basic' type
UPDATE functions SET function_type = 'basic' WHERE function_type IS NULL;

COMMIT;
```

### Migration 002: Create Execution Tables
```sql
-- 002_create_execution_tables.sql
BEGIN TRANSACTION;

CREATE TABLE function_executions (
    id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
    session_id TEXT NOT NULL,
    function_id TEXT NOT NULL,
    execution_order INTEGER,
    input_data JSON,
    output_data JSON,
    execution_time REAL,
    memory_used INTEGER,
    status VARCHAR(20) CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (function_id) REFERENCES functions(id) ON DELETE CASCADE
);

CREATE INDEX idx_executions_session ON function_executions(session_id);
CREATE INDEX idx_executions_function ON function_executions(function_id);
CREATE INDEX idx_executions_status ON function_executions(status);

COMMIT;
```

## 🧪 Data Validation

### Function Validation Rules
```sql
-- Check function type consistency
SELECT f.id, f.name, f.function_type
FROM functions f
WHERE (f.function_type = 'api' AND f.api_config IS NULL)
   OR (f.function_type = 'mcp' AND f.mcp_config IS NULL)
   OR (f.function_type = 'prompt' AND f.prompt_template IS NULL)
   OR (f.function_type = 'document' AND f.document_content IS NULL);

-- Check dependency validity
SELECT f.id, f.name, f.dependencies
FROM functions f
WHERE json_array_length(f.dependencies) > 0
AND EXISTS (
    SELECT 1 FROM json_each(f.dependencies) dep
    WHERE dep.value NOT IN (SELECT name FROM functions WHERE is_enabled = TRUE)
);
```

### Performance Monitoring Queries
```sql
-- Function performance summary
SELECT 
    f.name,
    f.function_type,
    COUNT(fe.id) as execution_count,
    AVG(fe.execution_time) as avg_execution_time,
    SUM(CASE WHEN fe.status = 'completed' THEN 1 ELSE 0 END) * 100.0 / COUNT(fe.id) as success_rate
FROM functions f
LEFT JOIN function_executions fe ON f.id = fe.function_id
WHERE fe.created_at > datetime('now', '-7 days')
GROUP BY f.id, f.name, f.function_type
ORDER BY execution_count DESC;

-- Slowest functions
SELECT 
    f.name,
    AVG(fe.execution_time) as avg_time,
    MAX(fe.execution_time) as max_time,
    COUNT(fe.id) as executions
FROM functions f
JOIN function_executions fe ON f.id = fe.function_id
WHERE fe.created_at > datetime('now', '-24 hours')
GROUP BY f.id, f.name
HAVING AVG(fe.execution_time) > 2.0
ORDER BY avg_time DESC;
```

---

**Version**: 1.0  
**Created**: January 15, 2025  
**Last Updated**: January 15, 2025 