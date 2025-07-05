# Function Router Service Specification
## Intelligent Function Selection and Routing

### 🎯 Overview

The Function Router Service is the core intelligence layer of ATTILA AI that analyzes user messages and intelligently selects appropriate functions for execution. It uses AI-powered intent analysis combined with configurable business rules to achieve 90%+ accuracy in function selection.

### 🧠 Core Functionality

#### 1. Message Intent Analysis

The router uses OpenAI's GPT-4 model to analyze user messages and understand intent:

```python
class FunctionRouterService:
    def __init__(self):
        self.openai_service = OpenAIService()
        self.routing_rules_engine = RoutingRulesEngine()
        self.dependency_resolver = DependencyResolver()
        self.performance_analyzer = PerformanceAnalyzer()
    
    async def analyze_message_intent(self, message: str, available_functions: List[Function]) -> Dict:
        """
        Analyze user message intent and recommend functions
        
        Args:
            message: User's input message
            available_functions: List of enabled functions
            
        Returns:
            Dict with intent analysis results
        """
        
        # Prepare function context for AI analysis
        function_context = self._prepare_function_context(available_functions)
        
        # Create system prompt for intent analysis
        system_prompt = self._create_intent_analysis_prompt(function_context)
        
        # Get AI analysis
        response = await self.openai_service.generate_response(
            message=message,
            system_prompt=system_prompt,
            response_format="json",
            temperature=0.3,  # Low temperature for consistent analysis
            max_tokens=1000
        )
        
        # Parse and validate response
        intent_data = self._parse_intent_response(response["content"])
        
        # Add confidence scoring
        intent_data["confidence_score"] = self._calculate_confidence_score(
            intent_data, message, available_functions
        )
        
        return intent_data
    
    def _create_intent_analysis_prompt(self, function_context: str) -> str:
        """Create optimized prompt for intent analysis"""
        
        return f"""
You are an expert function router for ATTILA AI. Your task is to analyze user messages and recommend the most appropriate functions.

Available Functions:
{function_context}

Analysis Guidelines:
1. **Intent Recognition**: Understand what the user wants to accomplish
2. **Function Matching**: Match intent to available function capabilities
3. **Combination Logic**: Consider functions that work well together
4. **Performance Impact**: Prefer efficient function combinations
5. **User Context**: Consider conversation history and patterns

Response Format (JSON):
{{
    "intent": "Clear description of user's primary intent",
    "intent_category": "task_creation|information_retrieval|content_generation|analysis|automation",
    "suggested_functions": ["function_name1", "function_name2"],
    "confidence": 0.95,
    "reasoning": "Detailed explanation of function selection logic",
    "execution_strategy": "parallel|sequential|conditional",
    "estimated_execution_time": 2.5,
    "potential_issues": ["concern1", "concern2"],
    "alternative_approaches": ["alternative1", "alternative2"]
}}

Important:
- Only suggest functions that directly address the user's intent
- Consider function dependencies and execution order
- Prioritize functions with higher success rates
- Be conservative with confidence scores
- Always provide clear reasoning
"""
```

#### 2. Routing Rules Engine

Business logic layer that applies configurable rules to refine function selection:

```python
class RoutingRulesEngine:
    def __init__(self):
        self.rules_cache = {}
        self.performance_tracker = PerformanceTracker()
    
    def apply_routing_rules(self, intent_analysis: Dict, functions: List[Function], 
                          session_context: Dict, routing_config: Dict) -> List[str]:
        """
        Apply business rules to refine function selection
        
        Args:
            intent_analysis: AI intent analysis results
            functions: Available functions
            session_context: Current session context
            routing_config: Routing configuration
            
        Returns:
            List of validated function names
        """
        
        suggested_functions = intent_analysis["suggested_functions"]
        confidence = intent_analysis["confidence"]
        
        # Rule 1: Confidence Threshold
        min_confidence = routing_config.get("min_confidence", 0.7)
        if confidence < min_confidence:
            return self._apply_fallback_strategy(intent_analysis, functions)
        
        # Rule 2: Function Limits
        max_functions = routing_config.get("max_functions", 5)
        suggested_functions = suggested_functions[:max_functions]
        
        # Rule 3: Dependency Validation
        validated_functions = self._validate_dependencies(suggested_functions, functions)
        
        # Rule 4: Performance Constraints
        performance_filtered = self._apply_performance_constraints(
            validated_functions, routing_config
        )
        
        # Rule 5: User Preferences
        preference_adjusted = self._apply_user_preferences(
            performance_filtered, session_context
        )
        
        # Rule 6: Resource Availability
        resource_validated = self._check_resource_availability(
            preference_adjusted, functions
        )
        
        # Rule 7: Rate Limiting
        rate_limited = self._apply_rate_limits(
            resource_validated, session_context
        )
        
        return rate_limited
    
    def _validate_dependencies(self, function_names: List[str], 
                             functions: List[Function]) -> List[str]:
        """Validate and resolve function dependencies"""
        
        function_map = {f.name: f for f in functions}
        validated = []
        
        for name in function_names:
            func = function_map.get(name)
            if not func:
                continue
            
            # Check if dependencies are available
            dependencies = func.dependencies or []
            missing_deps = [dep for dep in dependencies if dep not in function_names]
            
            if missing_deps:
                # Auto-include dependencies if available
                for dep in missing_deps:
                    if dep in function_map and dep not in validated:
                        validated.append(dep)
            
            validated.append(name)
        
        return validated
    
    def _apply_performance_constraints(self, function_names: List[str], 
                                     config: Dict) -> List[str]:
        """Apply performance-based filtering"""
        
        max_execution_time = config.get("max_execution_time", 10.0)
        max_memory_usage = config.get("max_memory_usage", 1024)  # MB
        
        filtered = []
        total_estimated_time = 0
        total_estimated_memory = 0
        
        # Get performance estimates for functions
        for name in function_names:
            perf_stats = self.performance_tracker.get_function_stats(name)
            
            estimated_time = perf_stats.get("avg_execution_time", 1.0)
            estimated_memory = perf_stats.get("avg_memory_usage", 100)
            
            # Check if adding this function exceeds limits
            if (total_estimated_time + estimated_time <= max_execution_time and
                total_estimated_memory + estimated_memory <= max_memory_usage):
                
                filtered.append(name)
                total_estimated_time += estimated_time
                total_estimated_memory += estimated_memory
            else:
                # Log performance constraint violation
                logger.warning(
                    f"Function {name} excluded due to performance constraints: "
                    f"time={estimated_time}s, memory={estimated_memory}MB"
                )
        
        return filtered
```

#### 3. Context-Aware Routing

Advanced routing that considers conversation history and user patterns:

```python
class ContextAwareRouter:
    def __init__(self):
        self.session_analyzer = SessionAnalyzer()
        self.pattern_detector = PatternDetector()
        self.preference_engine = PreferenceEngine()
    
    async def route_with_context(self, message: str, session_context: Dict, 
                               available_functions: List[Function]) -> Dict:
        """
        Route functions with full context awareness
        
        Args:
            message: Current user message
            session_context: Session history and context
            available_functions: Available functions
            
        Returns:
            Enhanced routing results with context
        """
        
        # Analyze session patterns
        session_patterns = await self.session_analyzer.analyze_patterns(session_context)
        
        # Detect user preferences
        user_preferences = await self.preference_engine.get_preferences(
            session_context.get("user_id")
        )
        
        # Get base intent analysis
        base_analysis = await self.analyze_message_intent(message, available_functions)
        
        # Apply context-based adjustments
        context_enhanced = self._apply_context_adjustments(
            base_analysis, session_patterns, user_preferences
        )
        
        # Optimize for user workflow
        workflow_optimized = self._optimize_for_workflow(
            context_enhanced, session_context
        )
        
        return workflow_optimized
    
    def _apply_context_adjustments(self, base_analysis: Dict, 
                                 session_patterns: Dict, 
                                 user_preferences: Dict) -> Dict:
        """Apply context-based adjustments to routing decisions"""
        
        adjusted = base_analysis.copy()
        
        # Boost confidence for frequently used function combinations
        if session_patterns.get("frequent_combinations"):
            current_combo = set(adjusted["suggested_functions"])
            for freq_combo in session_patterns["frequent_combinations"]:
                if current_combo.issubset(set(freq_combo["functions"])):
                    adjusted["confidence"] += 0.1  # Boost confidence
                    adjusted["reasoning"] += f" [Context: Frequent pattern detected]"
        
        # Apply user preference weights
        if user_preferences.get("preferred_functions"):
            preferred = set(user_preferences["preferred_functions"])
            current = set(adjusted["suggested_functions"])
            
            # Prioritize preferred functions
            preferred_in_current = list(preferred.intersection(current))
            other_functions = [f for f in adjusted["suggested_functions"] 
                             if f not in preferred_in_current]
            
            adjusted["suggested_functions"] = preferred_in_current + other_functions
        
        # Adjust based on recent failures
        if session_patterns.get("recent_failures"):
            failed_functions = set(session_patterns["recent_failures"])
            adjusted["suggested_functions"] = [
                f for f in adjusted["suggested_functions"] 
                if f not in failed_functions
            ]
            
            if failed_functions.intersection(set(base_analysis["suggested_functions"])):
                adjusted["confidence"] -= 0.15  # Reduce confidence
                adjusted["reasoning"] += f" [Context: Avoiding recently failed functions]"
        
        return adjusted
```

#### 4. Performance Optimization

Intelligent routing decisions based on performance data:

```python
class PerformanceOptimizedRouter:
    def __init__(self):
        self.performance_db = PerformanceDatabase()
        self.load_balancer = LoadBalancer()
        self.resource_monitor = ResourceMonitor()
    
    async def optimize_routing_for_performance(self, function_selection: List[str], 
                                             context: Dict) -> Dict:
        """
        Optimize function routing for best performance
        
        Args:
            function_selection: Selected functions
            context: Execution context
            
        Returns:
            Optimized execution plan
        """
        
        # Get performance data for functions
        perf_data = await self.performance_db.get_function_performance(function_selection)
        
        # Check current system load
        system_load = await self.resource_monitor.get_current_load()
        
        # Create execution plan
        execution_plan = self._create_execution_plan(
            function_selection, perf_data, system_load
        )
        
        # Optimize for parallel execution
        parallel_optimized = self._optimize_parallel_execution(execution_plan)
        
        # Apply load balancing
        load_balanced = self._apply_load_balancing(parallel_optimized, system_load)
        
        return {
            "execution_plan": load_balanced,
            "estimated_total_time": self._calculate_estimated_time(load_balanced),
            "resource_requirements": self._calculate_resource_requirements(load_balanced),
            "optimization_applied": True
        }
    
    def _create_execution_plan(self, functions: List[str], 
                             perf_data: Dict, system_load: Dict) -> List[Dict]:
        """Create optimized execution plan"""
        
        plan = []
        
        for func_name in functions:
            func_perf = perf_data.get(func_name, {})
            
            plan_item = {
                "function": func_name,
                "estimated_time": func_perf.get("avg_execution_time", 1.0),
                "memory_requirement": func_perf.get("avg_memory_usage", 100),
                "cpu_requirement": func_perf.get("avg_cpu_usage", 0.1),
                "success_rate": func_perf.get("success_rate", 0.95),
                "can_parallel": func_perf.get("parallel_safe", True)
            }
            
            # Adjust for current system load
            if system_load.get("cpu_usage", 0) > 0.7:
                plan_item["estimated_time"] *= 1.5  # Slower under high load
            
            if system_load.get("memory_usage", 0) > 0.8:
                plan_item["memory_requirement"] *= 1.2  # More memory needed
            
            plan.append(plan_item)
        
        return plan
    
    def _optimize_parallel_execution(self, execution_plan: List[Dict]) -> List[List[Dict]]:
        """Optimize for parallel execution where possible"""
        
        # Separate parallel-safe and sequential functions
        parallel_safe = [item for item in execution_plan if item["can_parallel"]]
        sequential_only = [item for item in execution_plan if not item["can_parallel"]]
        
        # Group parallel functions by resource requirements
        phases = []
        
        if parallel_safe:
            # Simple grouping by resource requirements
            # More sophisticated algorithms could be implemented
            current_phase = []
            current_memory = 0
            current_cpu = 0
            
            for item in parallel_safe:
                memory_req = item["memory_requirement"]
                cpu_req = item["cpu_requirement"]
                
                # Check if we can add to current phase
                if (current_memory + memory_req < 800 and  # 800MB limit per phase
                    current_cpu + cpu_req < 0.8):  # 80% CPU limit per phase
                    
                    current_phase.append(item)
                    current_memory += memory_req
                    current_cpu += cpu_req
                else:
                    # Start new phase
                    if current_phase:
                        phases.append(current_phase)
                    current_phase = [item]
                    current_memory = memory_req
                    current_cpu = cpu_req
            
            if current_phase:
                phases.append(current_phase)
        
        # Add sequential functions as individual phases
        for item in sequential_only:
            phases.append([item])
        
        return phases
```

#### 5. Error Handling and Fallbacks

Robust error handling with intelligent fallback strategies:

```python
class RouterErrorHandler:
    def __init__(self):
        self.fallback_strategies = FallbackStrategies()
        self.error_analyzer = ErrorAnalyzer()
        self.recovery_engine = RecoveryEngine()
    
    async def handle_routing_error(self, error: Exception, context: Dict) -> Dict:
        """
        Handle routing errors with intelligent fallback
        
        Args:
            error: The error that occurred
            context: Routing context
            
        Returns:
            Recovery strategy and alternative routing
        """
        
        error_type = type(error).__name__
        error_severity = self._assess_error_severity(error)
        
        if error_severity == "critical":
            return await self._critical_error_recovery(error, context)
        elif error_severity == "moderate":
            return await self._moderate_error_recovery(error, context)
        else:
            return await self._minor_error_recovery(error, context)
    
    async def _critical_error_recovery(self, error: Exception, context: Dict) -> Dict:
        """Handle critical errors that prevent any function execution"""
        
        return {
            "strategy": "fallback_to_basic",
            "functions": ["basic-response"],
            "error_handled": True,
            "user_message": "I encountered a technical issue. Using basic response mode.",
            "recovery_time": datetime.now().isoformat(),
            "original_error": str(error)
        }
    
    async def _moderate_error_recovery(self, error: Exception, context: Dict) -> Dict:
        """Handle moderate errors with alternative function selection"""
        
        # Try to find alternative functions
        original_intent = context.get("original_intent", "")
        available_functions = context.get("available_functions", [])
        
        # Use simpler matching for alternative selection
        alternatives = self._find_alternative_functions(original_intent, available_functions)
        
        return {
            "strategy": "alternative_functions",
            "functions": alternatives,
            "error_handled": True,
            "user_message": "I've selected alternative functions to help you.",
            "confidence": 0.6,  # Lower confidence for alternatives
            "original_error": str(error)
        }
    
    def _find_alternative_functions(self, intent: str, functions: List[Function]) -> List[str]:
        """Find alternative functions using keyword matching"""
        
        # Simple keyword-based matching as fallback
        intent_keywords = intent.lower().split()
        
        alternatives = []
        for func in functions:
            func_keywords = (func.name + " " + func.description).lower()
            
            # Check for keyword overlap
            if any(keyword in func_keywords for keyword in intent_keywords):
                alternatives.append(func.name)
        
        return alternatives[:3]  # Limit to top 3 alternatives
```

### 🔧 Configuration and Customization

#### Router Configuration Schema

```python
RouterConfig = {
    "routing_strategy": "ai_powered",  # ai_powered, rule_based, hybrid
    "confidence_thresholds": {
        "minimum": 0.7,
        "high_confidence": 0.9,
        "auto_execute": 0.95
    },
    "function_limits": {
        "max_per_request": 5,
        "max_parallel": 3,
        "timeout_seconds": 30
    },
    "performance_constraints": {
        "max_execution_time": 10.0,
        "max_memory_mb": 1024,
        "max_cpu_usage": 0.8
    },
    "fallback_strategies": {
        "low_confidence": "ask_user",
        "no_functions": "basic_response",
        "error": "retry_with_alternatives"
    },
    "learning_settings": {
        "enable_pattern_learning": True,
        "preference_weight": 0.3,
        "history_window_days": 30
    }
}
```

### 📊 Performance Metrics

#### Key Performance Indicators

- **Routing Accuracy**: 90%+ correct function selection
- **Response Time**: <500ms for intent analysis
- **Confidence Score**: Average >0.8 for successful routes
- **Error Rate**: <5% routing failures
- **User Satisfaction**: >4.5/5 rating for function relevance

#### Monitoring and Analytics

```python
class RouterAnalytics:
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.dashboard = AnalyticsDashboard()
    
    async def track_routing_performance(self, routing_result: Dict, 
                                      user_feedback: Dict = None):
        """Track routing performance metrics"""
        
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "confidence_score": routing_result.get("confidence", 0),
            "functions_selected": len(routing_result.get("suggested_functions", [])),
            "execution_time": routing_result.get("execution_time", 0),
            "success": routing_result.get("success", False),
            "user_satisfaction": user_feedback.get("satisfaction", None) if user_feedback else None
        }
        
        await self.metrics_collector.store_routing_metrics(metrics)
        
        # Update real-time dashboard
        await self.dashboard.update_routing_metrics(metrics)
    
    async def generate_routing_report(self, time_range: str = "24h") -> Dict:
        """Generate comprehensive routing performance report"""
        
        metrics = await self.metrics_collector.get_routing_metrics(time_range)
        
        return {
            "period": time_range,
            "total_requests": len(metrics),
            "average_confidence": np.mean([m["confidence_score"] for m in metrics]),
            "success_rate": len([m for m in metrics if m["success"]]) / len(metrics),
            "average_functions_per_request": np.mean([m["functions_selected"] for m in metrics]),
            "performance_trend": self._calculate_performance_trend(metrics),
            "top_function_combinations": self._get_top_combinations(metrics),
            "error_analysis": self._analyze_errors(metrics)
        }
```

### 🧪 Testing Strategy

#### Unit Testing
```python
@pytest.mark.asyncio
async def test_intent_analysis_accuracy():
    """Test intent analysis accuracy across different message types"""
    
    router = FunctionRouterService()
    
    test_cases = [
        {
            "message": "Create a Jira ticket for the login bug",
            "expected_intent": "task_creation",
            "expected_functions": ["jira-create"],
            "min_confidence": 0.8
        },
        {
            "message": "Search for API documentation and summarize it",
            "expected_intent": "information_retrieval",
            "expected_functions": ["web-search", "document-process"],
            "min_confidence": 0.75
        },
        {
            "message": "Generate a project proposal and save to Confluence",
            "expected_intent": "content_generation",
            "expected_functions": ["content-generate", "confluence-save"],
            "min_confidence": 0.8
        }
    ]
    
    for case in test_cases:
        result = await router.analyze_message_intent(
            case["message"], 
            mock_available_functions
        )
        
        assert result["intent_category"] == case["expected_intent"]
        assert result["confidence"] >= case["min_confidence"]
        assert any(func in result["suggested_functions"] for func in case["expected_functions"])

@pytest.mark.asyncio
async def test_dependency_resolution():
    """Test function dependency resolution"""
    
    rules_engine = RoutingRulesEngine()
    
    # Function A depends on Function B
    functions = [
        Function(name="function_a", dependencies=["function_b"]),
        Function(name="function_b", dependencies=[]),
        Function(name="function_c", dependencies=["function_a"])
    ]
    
    # Test that dependencies are automatically included
    result = rules_engine._validate_dependencies(["function_a"], functions)
    
    assert "function_b" in result  # Dependency should be auto-included
    assert "function_a" in result
    
    # Test complex dependency chain
    result = rules_engine._validate_dependencies(["function_c"], functions)
    
    assert "function_b" in result
    assert "function_a" in result
    assert "function_c" in result
    assert result.index("function_b") < result.index("function_a")  # Correct order
```

### 🔄 Continuous Improvement

#### Machine Learning Integration
```python
class RouterLearningEngine:
    def __init__(self):
        self.pattern_analyzer = PatternAnalyzer()
        self.feedback_processor = FeedbackProcessor()
        self.model_trainer = ModelTrainer()
    
    async def learn_from_interactions(self, interaction_data: List[Dict]):
        """Learn from user interactions to improve routing"""
        
        # Analyze successful routing patterns
        success_patterns = self._extract_success_patterns(interaction_data)
        
        # Update routing confidence algorithms
        await self._update_confidence_models(success_patterns)
        
        # Improve function combination recommendations
        await self._update_combination_models(success_patterns)
        
        # Generate new routing rules
        new_rules = self._generate_learned_rules(success_patterns)
        
        return {
            "patterns_learned": len(success_patterns),
            "confidence_improvement": await self._measure_confidence_improvement(),
            "new_rules_generated": len(new_rules),
            "model_version": self._get_model_version()
        }
```

---

**Document Version**: 1.0  
**Created**: January 15, 2025  
**Last Updated**: January 15, 2025  
**Next Review**: February 1, 2025 