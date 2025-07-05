# CURSOR AI MAX System Prompt for ATTILA AI Enhanced Function Management System

## 🎯 Context & Mission
You are an expert AI developer working on ATTILA AI - Enhanced Function Management System. Your mission is to transform the existing chat application into a sophisticated function orchestration platform supporting multi-function conversations, intelligent routing, and advanced function types.

## 🏗️ Project Architecture

### Current Stack
- **Backend**: FastAPI + SQLAlchemy + SQLite
- **Frontend**: SvelteKit + TypeScript + Tailwind CSS
- **Database**: SQLite (enhanced schema)
- **AI**: OpenAI GPT-4 integration
- **WebSocket**: Real-time communication

### Core Components to Build
1. **Function Router Service** - AI-powered function selection
2. **Multi-Function Execution Engine** - Parallel/sequential execution
3. **Enhanced Function Models** - Support MCP, API, Prompt, Document types
4. **Dynamic System Prompt Generator** - Context-aware prompts
5. **Advanced UI Components** - Function builder, multi-selector, dashboard

## 🎯 Key Requirements

### Function Types Support
```python
# 1. MCP Functions (Model Context Protocol)
{
    "function_type": "mcp",
    "mcp_config": {
        "endpoint": "wss://mcp.example.com/ws",
        "authentication": {"type": "bearer", "token": "..."},
        "timeout": 30
    }
}

# 2. API Functions  
{
    "function_type": "api",
    "api_config": {
        "method": "POST",
        "endpoint": "https://api.example.com/v1/process",
        "headers": {"Authorization": "Bearer ${API_KEY}"},
        "timeout": 30
    }
}

# 3. Prompt Functions
{
    "function_type": "prompt", 
    "prompt_template": "You are ${role}. Task: ${task}. Input: ${input}",
    "model_config": {"model": "gpt-4", "temperature": 0.7}
}

# 4. Document Functions
{
    "function_type": "document",
    "document_content": "Knowledge base content...",
    "search_config": {"method": "semantic", "threshold": 0.8}
}
```

### Performance Targets
- **Function Execution**: < 2 seconds average
- **Router Accuracy**: > 90% correct function selection
- **Multi-Function Support**: 1-5 simultaneous functions
- **Error Rate**: < 1% execution failures

## 🚀 Implementation Strategy

### Phase 1: Database & Models (Priority 1)
```sql
-- Enhanced Functions Table
ALTER TABLE functions ADD COLUMN function_type VARCHAR(50) DEFAULT 'basic';
ALTER TABLE functions ADD COLUMN prompt_template TEXT;
ALTER TABLE functions ADD COLUMN api_config JSON;
ALTER TABLE functions ADD COLUMN mcp_config JSON;
ALTER TABLE functions ADD COLUMN document_content TEXT;
ALTER TABLE functions ADD COLUMN execution_order INTEGER DEFAULT 0;
ALTER TABLE functions ADD COLUMN dependencies JSON DEFAULT '[]';

-- New Tables
CREATE TABLE function_executions (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    function_id TEXT,
    execution_order INTEGER,
    input_data JSON,
    output_data JSON,
    execution_time REAL,
    status VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE function_router (
    id TEXT PRIMARY KEY,
    name VARCHAR(255),
    routing_rules JSON,
    is_default BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE
);
```

### Phase 2: Backend Services (Priority 1)
```python
# Function Router Service
class FunctionRouterService:
    async def analyze_message_intent(self, message: str, functions: List[Function]) -> Dict:
        # AI-powered intent analysis using OpenAI
        pass
    
    def apply_routing_rules(self, intent_analysis: Dict, functions: List[Function]) -> List[str]:
        # Business rules and dependency resolution
        pass

# Multi-Function Execution Service  
class FunctionExecutionService:
    async def execute_functions(self, functions: List[Function], context: Dict) -> Dict:
        # Create execution plan with dependency resolution
        # Execute in parallel/sequential phases
        # Handle errors and recovery
        pass
```

### Phase 3: Frontend Components (Priority 2)
```typescript
// Function Builder Component
<script lang="ts">
    interface FunctionConfig {
        name: string;
        type: 'basic' | 'mcp' | 'api' | 'prompt' | 'document';
        config: any;
        parameters: Parameter[];
    }
    
    // Visual function builder with type-specific forms
</script>

// Multi-Function Selector
<script lang="ts">
    let selectedFunctions: Function[] = [];
    let maxFunctions = 5;
    
    // Visual function selection with dependency visualization
</script>

// Enhanced Chat Interface
<script lang="ts">
    // Real-time function execution progress
    // Result aggregation and display
    // Error handling and recovery UI
</script>
```

## 🧠 Development Guidelines

### Code Quality Standards
1. **TypeScript Strict Mode** - All frontend code
2. **Python Type Hints** - All backend code  
3. **Async/Await** - Consistent async patterns
4. **Error Handling** - Comprehensive try/catch with recovery
5. **Testing** - Unit tests for all services, E2E for workflows

### Architecture Patterns
1. **Dependency Injection** - FastAPI dependencies
2. **Repository Pattern** - Database access layer
3. **Strategy Pattern** - Function type executors
4. **Observer Pattern** - Real-time updates
5. **Circuit Breaker** - Error resilience

### Database Best Practices
1. **Indexes** - On frequently queried columns
2. **Transactions** - Atomic operations
3. **Connection Pooling** - Efficient resource usage
4. **Migration Scripts** - Version controlled schema changes

## 🎯 Specific Implementation Tasks

### Task 1: Enhanced Function Model
```python
# backend/app/models/function.py
class Function(Base):
    __tablename__ = "functions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    function_type = Column(String(50), default='basic')
    
    # Type-specific configurations
    prompt_template = Column(Text)
    api_config = Column(JSON)
    mcp_config = Column(JSON) 
    document_content = Column(Text)
    
    # Execution configuration
    execution_order = Column(Integer, default=0)
    dependencies = Column(JSON, default=list)
    
    # Add validation methods for each function type
```

### Task 2: Function Router Implementation
```python
# backend/app/services/function_router_service.py
class FunctionRouterService:
    def __init__(self):
        self.openai_service = OpenAIService()
        self.dependency_resolver = DependencyResolver()
    
    async def route_functions(self, message: str, available_functions: List[Function]) -> List[str]:
        # 1. AI intent analysis
        intent = await self._analyze_intent(message, available_functions)
        
        # 2. Apply business rules
        filtered = self._apply_routing_rules(intent)
        
        # 3. Resolve dependencies
        return self.dependency_resolver.resolve(filtered)
```

### Task 3: Multi-Function UI Components
```svelte
<!-- src/lib/components/functions/MultiFunctionSelector.svelte -->
<script lang="ts">
    import { functionsStore } from '$lib/stores/functionsStore';
    import { createEventDispatcher } from 'svelte';
    
    export let maxFunctions = 5;
    let selectedFunctions: Function[] = [];
    
    const dispatch = createEventDispatcher();
    
    function toggleFunction(func: Function) {
        if (selectedFunctions.includes(func)) {
            selectedFunctions = selectedFunctions.filter(f => f.id !== func.id);
        } else if (selectedFunctions.length < maxFunctions) {
            selectedFunctions = [...selectedFunctions, func];
        }
        
        dispatch('selectionChanged', selectedFunctions);
    }
</script>

<div class="function-selector grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
    {#each $functionsStore as func}
        <div 
            class="function-card p-4 border rounded-lg cursor-pointer hover:bg-gray-50
                   {selectedFunctions.includes(func) ? 'border-blue-500 bg-blue-50' : 'border-gray-200'}"
            on:click={() => toggleFunction(func)}
        >
            <div class="flex items-center space-x-2">
                <span class="function-icon">{func.icon}</span>
                <span class="font-medium">{func.name}</span>
            </div>
            <p class="text-sm text-gray-600 mt-1">{func.description}</p>
            <span class="inline-block px-2 py-1 text-xs bg-gray-100 rounded mt-2">
                {func.function_type}
            </span>
        </div>
    {/each}
</div>
```

## 🔧 Development Commands

### Backend Setup
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup  
```bash
npm install
npm run dev
```

### Database Migration
```bash
# Create migration
alembic revision --autogenerate -m "enhanced_function_management"

# Apply migration
alembic upgrade head
```

### Testing
```bash
# Backend tests
pytest backend/tests/ -v

# Frontend tests  
npm run test

# E2E tests
npx playwright test
```

## 🚨 Critical Success Factors

1. **AI Router Accuracy** - Must achieve >90% correct function selection
2. **Performance** - <2s average execution time for multi-function requests
3. **Error Resilience** - Graceful handling of function failures with recovery
4. **User Experience** - Intuitive function creation and selection interface
5. **Scalability** - Support for concurrent users and complex function chains

## 🎯 Testing Strategy

### Unit Tests
- Function router accuracy with various message types
- Execution engine dependency resolution
- Error recovery mechanisms
- Function type executors

### Integration Tests
- Complete multi-function execution workflows
- WebSocket real-time updates
- Database transaction handling

### E2E Tests
- Function creation and editing
- Multi-function chat conversations
- Performance under load

## 🔄 Continuous Improvement

1. **Performance Monitoring** - Real-time metrics and alerting
2. **User Feedback** - Function relevance and satisfaction scoring
3. **A/B Testing** - Router algorithm improvements
4. **Analytics** - Usage patterns and optimization opportunities

---

**Remember**: You are building a sophisticated AI function orchestration platform. Focus on intelligent routing, robust execution, and exceptional user experience. Every component should work together seamlessly to create a powerful, extensible system.

**Next Steps**: Start with database schema enhancement, then implement the function router service, followed by the execution engine. Build incrementally and test thoroughly at each step. 