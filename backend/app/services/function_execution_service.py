"""
Function Execution Service for coordinating multi-function execution
Handles dependency resolution, parallel execution, and performance monitoring
"""
import asyncio
import json
import time
import psutil
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.database import get_async_db
from ..models.function import Function
from ..models.function_execution import FunctionExecution
from ..models.function_router import FunctionRouter


class FunctionExecutionService:
    """
    Multi-function execution service with performance monitoring
    Target: <2s average execution time for Phase 1
    """
    
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=5)
        self.performance_monitor = PerformanceMonitor()
        
    async def execute_functions(
        self, 
        functions: List[Function], 
        function_configs: List[Dict[str, Any]], 
        session_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute multiple functions with dependency resolution and optimization
        
        Args:
            functions: List of Function objects to execute
            function_configs: List of function configurations from router
            session_id: Session identifier
            context: Execution context
            
        Returns:
            Dict containing execution results and performance metrics
        """
        start_time = time.time()
        
        # Create execution plan
        execution_plan = self._create_execution_plan(functions, function_configs)
        
        # Initialize tracking
        results = {}
        performance_metrics = {}
        execution_records = []
        
        try:
            # Execute phases
            for phase_index, phase in enumerate(execution_plan):
                phase_start = time.time()
                
                # Execute functions in phase (parallel where possible)
                phase_results = await self._execute_phase(
                    phase, context, session_id, phase_index
                )
                
                # Update results and context
                results.update(phase_results)
                if context:
                    context['previous_results'] = results
                    context['phase_index'] = phase_index
                
                # Track performance
                phase_time = time.time() - phase_start
                performance_metrics[f"phase_{phase_index}"] = {
                    "execution_time": phase_time,
                    "functions": [f.name for f in phase],
                    "memory_usage": self._get_memory_usage()
                }
                
                # Store execution records
                for func in phase:
                    execution_record = phase_results.get(func.name, {})
                    if execution_record:
                        execution_records.append(execution_record)
            
            # Calculate total execution time
            total_time = time.time() - start_time
            
            # Aggregate results
            final_result = {
                "status": "completed",
                "results": results,
                "performance": performance_metrics,
                "total_execution_time": total_time,
                "execution_summary": self._create_execution_summary(results),
                "optimization_suggestions": self._generate_optimization_suggestions(performance_metrics)
            }
            
            return final_result
            
        except Exception as e:
            # Handle execution failure
            error_result = {
                "status": "failed",
                "error": str(e),
                "results": results,
                "performance": performance_metrics,
                "total_execution_time": time.time() - start_time,
                "partial_results": bool(results)
            }
            
            # Log error for analysis
            await self._log_execution_error(session_id, functions, str(e))
            
            return error_result
    
    def _create_execution_plan(
        self, 
        functions: List[Function], 
        function_configs: List[Dict[str, Any]]
    ) -> List[List[Function]]:
        """Create optimized execution plan based on dependencies and resources"""
        
        # Build dependency graph
        dependency_graph = self._build_dependency_graph(functions)
        
        # Topological sort for execution order
        sorted_functions = self._topological_sort(dependency_graph)
        
        # Group into parallel execution phases
        phases = []
        remaining = set(sorted_functions)
        
        while remaining:
            # Find functions that can execute in parallel
            parallel_group = []
            for func in list(remaining):
                if self._can_execute_parallel(func, parallel_group, dependency_graph):
                    parallel_group.append(func)
                    remaining.remove(func)
            
            if parallel_group:
                phases.append(parallel_group)
            elif remaining:
                # Break circular dependencies or handle complex cases
                next_func = remaining.pop()
                phases.append([next_func])
        
        return phases
    
    def _build_dependency_graph(self, functions: List[Function]) -> Dict[str, List[str]]:
        """Build dependency graph from functions"""
        graph = {}
        
        for func in functions:
            graph[func.name] = func.dependencies or []
        
        return graph
    
    def _topological_sort(self, graph: Dict[str, List[str]]) -> List[str]:
        """Perform topological sort on dependency graph"""
        visited = set()
        temp_visited = set()
        result = []
        
        def visit(node):
            if node in temp_visited:
                raise ValueError(f"Circular dependency detected involving {node}")
            if node in visited:
                return
            
            temp_visited.add(node)
            
            for dependency in graph.get(node, []):
                if dependency in graph:
                    visit(dependency)
            
            temp_visited.remove(node)
            visited.add(node)
            result.append(node)
        
        for node in graph:
            if node not in visited:
                visit(node)
        
        return result
    
    def _can_execute_parallel(
        self, 
        func: Function, 
        parallel_group: List[Function], 
        dependency_graph: Dict[str, List[str]]
    ) -> bool:
        """Check if function can execute in parallel with the current group"""
        
        # Check if function has dependencies on any function in the group
        for group_func in parallel_group:
            if group_func.name in dependency_graph.get(func.name, []):
                return False
            if func.name in dependency_graph.get(group_func.name, []):
                return False
        
        return True
    
    async def _execute_phase(
        self, 
        phase: List[Function], 
        context: Optional[Dict[str, Any]], 
        session_id: str, 
        phase_index: int
    ) -> Dict[str, Any]:
        """Execute a phase of functions (parallel or sequential)"""
        
        if len(phase) == 1:
            # Single function execution
            func = phase[0]
            return {func.name: await self._execute_single_function(func, context, session_id)}
        else:
            # Parallel execution
            tasks = []
            for func in phase:
                task = asyncio.create_task(
                    self._execute_single_function(func, context, session_id)
                )
                tasks.append((func.name, task))
            
            # Wait for all tasks to complete
            results = {}
            for func_name, task in tasks:
                try:
                    result = await task
                    results[func_name] = result
                except Exception as e:
                    results[func_name] = {
                        "status": "failed",
                        "error": str(e),
                        "execution_time": 0.0
                    }
            
            return results
    
    async def _execute_single_function(
        self, 
        func: Function, 
        context: Optional[Dict[str, Any]], 
        session_id: str
    ) -> Dict[str, Any]:
        """Execute a single function with performance monitoring"""
        
        start_time = time.time()
        memory_start = self._get_memory_usage()
        
        # Create execution record
        execution_record = FunctionExecution(
            session_id=session_id,
            function_id=func.id,
            status="pending",
            input_data=context or {}
        )
        
        async with get_async_db() as session:
            session.add(execution_record)
            await session.commit()
            await session.refresh(execution_record)
        
        try:
            # Mark as running
            execution_record.start_execution()
            
            # Execute based on function type
            if func.function_type == "basic":
                result = await self._execute_basic_function(func, context)
            elif func.function_type == "api":
                result = await self._execute_api_function(func, context)
            elif func.function_type == "prompt":
                result = await self._execute_prompt_function(func, context)
            elif func.function_type == "document":
                result = await self._execute_document_function(func, context)
            elif func.function_type == "mcp":
                result = await self._execute_mcp_function(func, context)
            else:
                raise ValueError(f"Unsupported function type: {func.function_type}")
            
            # Calculate performance metrics
            execution_time = time.time() - start_time
            memory_used = self._get_memory_usage() - memory_start
            
            # Update execution record
            execution_record.complete_execution(result)
            execution_record.execution_time = execution_time
            execution_record.memory_used = max(0, memory_used)
            
            # Save to database
            async with get_async_db() as session:
                await session.merge(execution_record)
                await session.commit()
            
            return {
                "status": "completed",
                "result": result,
                "execution_time": execution_time,
                "memory_used": memory_used,
                "function_type": func.function_type,
                "execution_id": execution_record.id
            }
            
        except Exception as e:
            # Handle execution failure
            execution_time = time.time() - start_time
            execution_record.fail_execution(str(e))
            execution_record.execution_time = execution_time
            
            # Save to database
            async with get_async_db() as session:
                await session.merge(execution_record)
                await session.commit()
            
            return {
                "status": "failed",
                "error": str(e),
                "execution_time": execution_time,
                "function_type": func.function_type,
                "execution_id": execution_record.id
            }
    
    async def _execute_basic_function(
        self, 
        func: Function, 
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute a basic function"""
        
        # Basic function execution - placeholder for now
        # This would be replaced with actual function implementations
        await asyncio.sleep(0.1)  # Simulate processing time
        
        return {
            "function_name": func.name,
            "result": f"Basic function {func.name} executed successfully",
            "parameters": func.parameters,
            "context": context
        }
    
    async def _execute_api_function(
        self, 
        func: Function, 
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute an API function"""
        
        # API function execution - placeholder for now
        # This would be replaced with actual HTTP client implementation
        await asyncio.sleep(0.2)  # Simulate API call time
        
        api_config = func.api_config or {}
        
        return {
            "function_name": func.name,
            "result": f"API function {func.name} executed successfully",
            "endpoint": api_config.get("endpoint", "N/A"),
            "method": api_config.get("method", "POST"),
            "context": context
        }
    
    async def _execute_prompt_function(
        self, 
        func: Function, 
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute a prompt function"""
        
        # Prompt function execution - placeholder for now
        # This would be replaced with actual OpenAI API integration
        await asyncio.sleep(0.5)  # Simulate AI processing time
        
        return {
            "function_name": func.name,
            "result": f"Prompt function {func.name} executed successfully",
            "template": func.prompt_template,
            "context": context
        }
    
    async def _execute_document_function(
        self, 
        func: Function, 
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute a document function"""
        
        # Document function execution - placeholder for now
        # This would be replaced with actual document processing
        await asyncio.sleep(0.3)  # Simulate document processing time
        
        return {
            "function_name": func.name,
            "result": f"Document function {func.name} executed successfully",
            "document_content": func.document_content[:100] + "..." if func.document_content else "No content",
            "context": context
        }
    
    async def _execute_mcp_function(
        self, 
        func: Function, 
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute an MCP function"""
        
        # MCP function execution - placeholder for now
        # This would be replaced with actual MCP protocol implementation
        await asyncio.sleep(0.4)  # Simulate MCP communication time
        
        mcp_config = func.mcp_config or {}
        
        return {
            "function_name": func.name,
            "result": f"MCP function {func.name} executed successfully",
            "protocol_version": mcp_config.get("protocol_version", "1.0"),
            "endpoint": mcp_config.get("endpoint", "N/A"),
            "context": context
        }
    
    def _get_memory_usage(self) -> int:
        """Get current memory usage in MB"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            return memory_info.rss // 1024 // 1024  # Convert to MB
        except Exception:
            return 0
    
    def _create_execution_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Create execution summary from results"""
        
        total_functions = len(results)
        successful_functions = sum(1 for r in results.values() if r.get('status') == 'completed')
        failed_functions = total_functions - successful_functions
        
        total_time = sum(r.get('execution_time', 0) for r in results.values())
        avg_time = total_time / total_functions if total_functions > 0 else 0
        
        total_memory = sum(r.get('memory_used', 0) for r in results.values())
        
        return {
            "total_functions": total_functions,
            "successful_functions": successful_functions,
            "failed_functions": failed_functions,
            "success_rate": successful_functions / total_functions if total_functions > 0 else 0,
            "total_execution_time": total_time,
            "average_execution_time": avg_time,
            "total_memory_used": total_memory,
            "performance_rating": self._calculate_performance_rating(avg_time, successful_functions / total_functions if total_functions > 0 else 0)
        }
    
    def _calculate_performance_rating(self, avg_time: float, success_rate: float) -> str:
        """Calculate performance rating based on time and success rate"""
        
        if avg_time < 1.0 and success_rate > 0.95:
            return "excellent"
        elif avg_time < 2.0 and success_rate > 0.90:
            return "good"
        elif avg_time < 5.0 and success_rate > 0.80:
            return "fair"
        else:
            return "poor"
    
    def _generate_optimization_suggestions(self, performance_metrics: Dict[str, Any]) -> List[str]:
        """Generate optimization suggestions based on performance metrics"""
        
        suggestions = []
        
        # Analyze execution times
        phase_times = [metrics.get('execution_time', 0) for metrics in performance_metrics.values()]
        if phase_times:
            avg_phase_time = sum(phase_times) / len(phase_times)
            
            if avg_phase_time > 2.0:
                suggestions.append("Consider optimizing slow functions or increasing parallel execution")
            
            if max(phase_times) > 5.0:
                suggestions.append("Some functions are taking too long - consider breaking them down")
        
        # Analyze memory usage
        memory_usage = [metrics.get('memory_usage', 0) for metrics in performance_metrics.values()]
        if memory_usage and max(memory_usage) > 500:  # MB
            suggestions.append("High memory usage detected - consider optimizing memory-intensive functions")
        
        # Analyze parallel execution opportunities
        single_function_phases = sum(1 for metrics in performance_metrics.values() if len(metrics.get('functions', [])) == 1)
        if single_function_phases > 2:
            suggestions.append("Consider increasing parallel execution for better performance")
        
        return suggestions
    
    async def _log_execution_error(self, session_id: str, functions: List[Function], error: str):
        """Log execution error for analysis"""
        
        print(f"Execution error in session {session_id}: {error}")
        print(f"Functions involved: {[f.name for f in functions]}")
        
        # In a real implementation, this would log to a proper logging system
        # or store in a database for analysis


class PerformanceMonitor:
    """Performance monitoring utility"""
    
    def __init__(self):
        self.start_time = None
        self.metrics = {}
    
    def start_monitoring(self):
        """Start performance monitoring"""
        self.start_time = time.time()
        self.metrics = {
            "start_time": self.start_time,
            "start_memory": self._get_memory_usage(),
            "start_cpu": self._get_cpu_usage()
        }
    
    def stop_monitoring(self):
        """Stop performance monitoring and return metrics"""
        if self.start_time is None:
            return {}
        
        end_time = time.time()
        
        return {
            "total_time": end_time - self.start_time,
            "memory_used": self._get_memory_usage() - self.metrics["start_memory"],
            "cpu_used": self._get_cpu_usage() - self.metrics["start_cpu"],
            "efficiency_score": self._calculate_efficiency_score(end_time - self.start_time)
        }
    
    def _get_memory_usage(self) -> int:
        """Get current memory usage in MB"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            return memory_info.rss // 1024 // 1024
        except Exception:
            return 0
    
    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage"""
        try:
            return psutil.cpu_percent(interval=None)
        except Exception:
            return 0.0
    
    def _calculate_efficiency_score(self, execution_time: float) -> float:
        """Calculate efficiency score based on execution time"""
        if execution_time < 1.0:
            return 1.0
        elif execution_time < 2.0:
            return 0.8
        elif execution_time < 5.0:
            return 0.6
        else:
            return 0.4