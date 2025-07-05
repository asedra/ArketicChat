"""
Advanced Analytics Service for ATTILA AI Enhanced Function Management System
Provides comprehensive monitoring, performance insights, and usage analytics
"""
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, Counter
from dataclasses import dataclass
from enum import Enum

import psutil
from sqlalchemy import func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_async_db
from ..models.function import Function
from ..models.function_execution import FunctionExecution
from ..models.function_router import FunctionRouter


class MetricType(Enum):
    """Types of metrics to track"""
    PERFORMANCE = "performance"
    USAGE = "usage"
    ERROR = "error"
    SYSTEM = "system"


@dataclass
class MetricData:
    """Individual metric data point"""
    timestamp: datetime
    metric_type: MetricType
    metric_name: str
    value: float
    metadata: Dict[str, Any]


@dataclass
class AnalyticsReport:
    """Comprehensive analytics report"""
    period_start: datetime
    period_end: datetime
    summary: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    usage_statistics: Dict[str, Any]
    error_analysis: Dict[str, Any]
    recommendations: List[str]


class AnalyticsService:
    """
    Advanced analytics service with real-time monitoring and insights
    """
    
    def __init__(self):
        self.metrics_cache = defaultdict(list)
        self.alert_thresholds = {
            "execution_time": 5.0,  # seconds
            "error_rate": 0.05,     # 5%
            "memory_usage": 0.85,   # 85%
            "cpu_usage": 0.80       # 80%
        }
        
    async def generate_analytics_report(self, period_hours: int = 24) -> AnalyticsReport:
        """
        Generate comprehensive analytics report for specified period
        
        Args:
            period_hours: Number of hours to analyze (default 24)
            
        Returns:
            Complete analytics report with insights and recommendations
        """
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=period_hours)
        
        async with get_async_db() as session:
            # Gather all metrics
            performance_metrics = await self._analyze_performance(session, start_time, end_time)
            usage_statistics = await self._analyze_usage(session, start_time, end_time)
            error_analysis = await self._analyze_errors(session, start_time, end_time)
            system_metrics = await self._analyze_system_metrics()
            
            # Generate summary
            summary = await self._generate_summary(session, start_time, end_time)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                performance_metrics, usage_statistics, error_analysis, system_metrics
            )
            
            return AnalyticsReport(
                period_start=start_time,
                period_end=end_time,
                summary=summary,
                performance_metrics=performance_metrics,
                usage_statistics=usage_statistics,
                error_analysis=error_analysis,
                recommendations=recommendations
            )
    
    async def _analyze_performance(self, session: AsyncSession, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Analyze execution performance metrics"""
        
        # Get all executions in period
        executions = await session.execute(
            session.query(FunctionExecution)
            .filter(and_(
                FunctionExecution.created_at >= start_time,
                FunctionExecution.created_at <= end_time,
                FunctionExecution.status == "completed"
            ))
        )
        executions = executions.scalars().all()
        
        if not executions:
            return {
                "total_executions": 0,
                "avg_execution_time": 0,
                "p95_execution_time": 0,
                "p99_execution_time": 0,
                "fastest_execution": 0,
                "slowest_execution": 0,
                "throughput_per_hour": 0,
                "performance_trend": []
            }
        
        # Calculate basic metrics
        execution_times = [exec.execution_time for exec in executions if exec.execution_time]
        execution_times.sort()
        
        total_executions = len(executions)
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
        
        # Calculate percentiles
        p95_index = int(0.95 * len(execution_times))
        p99_index = int(0.99 * len(execution_times))
        p95_execution_time = execution_times[p95_index] if execution_times else 0
        p99_execution_time = execution_times[p99_index] if execution_times else 0
        
        # Calculate throughput
        period_hours = (end_time - start_time).total_seconds() / 3600
        throughput_per_hour = total_executions / period_hours if period_hours > 0 else 0
        
        # Performance trend analysis (hourly buckets)
        trend_buckets = defaultdict(list)
        for execution in executions:
            hour_bucket = execution.created_at.replace(minute=0, second=0, microsecond=0)
            if execution.execution_time:
                trend_buckets[hour_bucket].append(execution.execution_time)
        
        performance_trend = []
        for hour, times in sorted(trend_buckets.items()):
            avg_time = sum(times) / len(times)
            performance_trend.append({
                "timestamp": hour.isoformat(),
                "avg_execution_time": avg_time,
                "execution_count": len(times)
            })
        
        return {
            "total_executions": total_executions,
            "avg_execution_time": round(avg_execution_time, 3),
            "p95_execution_time": round(p95_execution_time, 3),
            "p99_execution_time": round(p99_execution_time, 3),
            "fastest_execution": round(min(execution_times), 3) if execution_times else 0,
            "slowest_execution": round(max(execution_times), 3) if execution_times else 0,
            "throughput_per_hour": round(throughput_per_hour, 2),
            "performance_trend": performance_trend
        }
    
    async def _analyze_usage(self, session: AsyncSession, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Analyze function usage patterns"""
        
        # Function usage by type
        function_type_usage = await session.execute(
            session.query(Function.function_type, func.count(FunctionExecution.id))
            .join(FunctionExecution, Function.id == FunctionExecution.function_id)
            .filter(and_(
                FunctionExecution.created_at >= start_time,
                FunctionExecution.created_at <= end_time
            ))
            .group_by(Function.function_type)
        )
        function_type_usage = dict(function_type_usage.all())
        
        # Most used functions
        popular_functions = await session.execute(
            session.query(Function.name, Function.function_type, func.count(FunctionExecution.id).label('usage_count'))
            .join(FunctionExecution, Function.id == FunctionExecution.function_id)
            .filter(and_(
                FunctionExecution.created_at >= start_time,
                FunctionExecution.created_at <= end_time
            ))
            .group_by(Function.id, Function.name, Function.function_type)
            .order_by(func.count(FunctionExecution.id).desc())
            .limit(10)
        )
        popular_functions = [
            {
                "name": name,
                "type": func_type,
                "usage_count": count
            }
            for name, func_type, count in popular_functions.all()
        ]
        
        # Router performance analysis
        router_decisions = await session.execute(
            session.query(FunctionRouter)
            .filter(and_(
                FunctionRouter.created_at >= start_time,
                FunctionRouter.created_at <= end_time
            ))
        )
        router_decisions = router_decisions.scalars().all()
        
        # Calculate router accuracy
        total_decisions = len(router_decisions)
        high_confidence_decisions = len([d for d in router_decisions if d.confidence_score >= 0.8])
        router_accuracy = high_confidence_decisions / total_decisions if total_decisions > 0 else 0
        
        # Usage patterns by hour
        hourly_usage = defaultdict(int)
        all_executions = await session.execute(
            session.query(FunctionExecution.created_at)
            .filter(and_(
                FunctionExecution.created_at >= start_time,
                FunctionExecution.created_at <= end_time
            ))
        )
        
        for execution in all_executions.scalars().all():
            hour = execution.hour
            hourly_usage[hour] += 1
        
        return {
            "function_type_distribution": function_type_usage,
            "popular_functions": popular_functions,
            "router_accuracy": round(router_accuracy, 3),
            "total_router_decisions": total_decisions,
            "hourly_usage_pattern": dict(hourly_usage),
            "peak_usage_hour": max(hourly_usage.items(), key=lambda x: x[1])[0] if hourly_usage else 0
        }
    
    async def _analyze_errors(self, session: AsyncSession, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Analyze error patterns and failure rates"""
        
        # Get all executions (including failed ones)
        total_executions = await session.execute(
            session.query(func.count(FunctionExecution.id))
            .filter(and_(
                FunctionExecution.created_at >= start_time,
                FunctionExecution.created_at <= end_time
            ))
        )
        total_executions = total_executions.scalar()
        
        # Get failed executions
        failed_executions = await session.execute(
            session.query(FunctionExecution)
            .filter(and_(
                FunctionExecution.created_at >= start_time,
                FunctionExecution.created_at <= end_time,
                FunctionExecution.status == "failed"
            ))
        )
        failed_executions = failed_executions.scalars().all()
        
        total_failures = len(failed_executions)
        error_rate = total_failures / total_executions if total_executions > 0 else 0
        
        # Analyze error types
        error_categories = defaultdict(int)
        error_functions = defaultdict(int)
        
        for execution in failed_executions:
            if execution.error_message:
                # Categorize errors
                error_msg = execution.error_message.lower()
                if 'timeout' in error_msg:
                    error_categories['timeout'] += 1
                elif 'authentication' in error_msg or 'unauthorized' in error_msg:
                    error_categories['authentication'] += 1
                elif 'connection' in error_msg or 'network' in error_msg:
                    error_categories['network'] += 1
                elif 'validation' in error_msg or 'invalid' in error_msg:
                    error_categories['validation'] += 1
                else:
                    error_categories['other'] += 1
                
                # Track error by function
                error_functions[execution.function_id] += 1
        
        # Get function names for error analysis
        error_by_function = []
        if error_functions:
            function_error_details = await session.execute(
                session.query(Function.name, Function.function_type)
                .filter(Function.id.in_(error_functions.keys()))
            )
            
            for func_name, func_type in function_error_details.all():
                error_by_function.append({
                    "function_name": func_name,
                    "function_type": func_type,
                    "error_count": error_functions.get(func_name, 0)
                })
        
        return {
            "total_executions": total_executions,
            "total_failures": total_failures,
            "error_rate": round(error_rate, 4),
            "error_categories": dict(error_categories),
            "error_by_function": error_by_function,
            "mttr": self._calculate_mttr(failed_executions)  # Mean Time To Recovery
        }
    
    async def _analyze_system_metrics(self) -> Dict[str, Any]:
        """Analyze current system performance metrics"""
        
        # CPU and Memory metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Network metrics (if available)
        try:
            network = psutil.net_io_counters()
            network_metrics = {
                "bytes_sent": network.bytes_sent,
                "bytes_received": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_received": network.packets_recv
            }
        except:
            network_metrics = {}
        
        return {
            "cpu_usage_percent": cpu_percent,
            "memory_usage_percent": memory.percent,
            "memory_available_gb": round(memory.available / (1024**3), 2),
            "disk_usage_percent": disk.percent,
            "disk_free_gb": round(disk.free / (1024**3), 2),
            "network_metrics": network_metrics,
            "system_health_score": self._calculate_health_score(cpu_percent, memory.percent, disk.percent)
        }
    
    async def _generate_summary(self, session: AsyncSession, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Generate executive summary of system performance"""
        
        # Total executions
        total_executions = await session.execute(
            session.query(func.count(FunctionExecution.id))
            .filter(and_(
                FunctionExecution.created_at >= start_time,
                FunctionExecution.created_at <= end_time
            ))
        )
        total_executions = total_executions.scalar()
        
        # Success rate
        successful_executions = await session.execute(
            session.query(func.count(FunctionExecution.id))
            .filter(and_(
                FunctionExecution.created_at >= start_time,
                FunctionExecution.created_at <= end_time,
                FunctionExecution.status == "completed"
            ))
        )
        successful_executions = successful_executions.scalar()
        
        success_rate = successful_executions / total_executions if total_executions > 0 else 0
        
        # Active functions
        active_functions = await session.execute(
            session.query(func.count(Function.id))
            .filter(Function.is_active == True)
        )
        active_functions = active_functions.scalar()
        
        return {
            "period_hours": (end_time - start_time).total_seconds() / 3600,
            "total_executions": total_executions,
            "success_rate": round(success_rate, 4),
            "active_functions": active_functions,
            "system_uptime": self._get_system_uptime(),
            "health_status": "healthy" if success_rate > 0.95 else "degraded" if success_rate > 0.90 else "critical"
        }
    
    def _calculate_mttr(self, failed_executions: List[FunctionExecution]) -> float:
        """Calculate Mean Time To Recovery"""
        if not failed_executions:
            return 0.0
        
        # For simplicity, assume recovery time is based on execution time
        recovery_times = [exec.execution_time for exec in failed_executions if exec.execution_time]
        return sum(recovery_times) / len(recovery_times) if recovery_times else 0.0
    
    def _calculate_health_score(self, cpu_percent: float, memory_percent: float, disk_percent: float) -> float:
        """Calculate overall system health score (0-100)"""
        
        # Normalize metrics (lower is better)
        cpu_score = max(0, 100 - cpu_percent)
        memory_score = max(0, 100 - memory_percent)
        disk_score = max(0, 100 - disk_percent)
        
        # Weighted average (CPU and memory are more important)
        health_score = (cpu_score * 0.4 + memory_score * 0.4 + disk_score * 0.2)
        
        return round(health_score, 1)
    
    def _get_system_uptime(self) -> str:
        """Get system uptime in human-readable format"""
        try:
            uptime_seconds = time.time() - psutil.boot_time()
            uptime_days = int(uptime_seconds // 86400)
            uptime_hours = int((uptime_seconds % 86400) // 3600)
            uptime_minutes = int((uptime_seconds % 3600) // 60)
            
            return f"{uptime_days}d {uptime_hours}h {uptime_minutes}m"
        except:
            return "Unknown"
    
    def _generate_recommendations(self, performance: Dict[str, Any], usage: Dict[str, Any], 
                                errors: Dict[str, Any], system: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on analytics"""
        
        recommendations = []
        
        # Performance recommendations
        if performance.get("avg_execution_time", 0) > 2.0:
            recommendations.append("⚠️ Average execution time exceeds 2s target. Consider optimizing slow functions.")
        
        if performance.get("p95_execution_time", 0) > 5.0:
            recommendations.append("🐌 95th percentile execution time is high. Review and optimize outlier functions.")
        
        # Error rate recommendations
        if errors.get("error_rate", 0) > 0.05:
            recommendations.append("❌ Error rate exceeds 5% threshold. Investigate common failure patterns.")
        
        # System recommendations
        if system.get("cpu_usage_percent", 0) > 80:
            recommendations.append("🔥 High CPU usage detected. Consider scaling or optimizing resource usage.")
        
        if system.get("memory_usage_percent", 0) > 85:
            recommendations.append("💾 High memory usage detected. Monitor for memory leaks or increase capacity.")
        
        # Router recommendations
        if usage.get("router_accuracy", 0) < 0.85:
            recommendations.append("🧠 Router accuracy below target. Review and improve function routing logic.")
        
        # Usage pattern recommendations
        peak_hour = usage.get("peak_usage_hour", 0)
        if peak_hour:
            recommendations.append(f"📈 Peak usage at hour {peak_hour}. Consider load balancing or capacity planning.")
        
        # Function-specific recommendations
        popular_functions = usage.get("popular_functions", [])
        if popular_functions:
            top_function = popular_functions[0]
            recommendations.append(f"⭐ '{top_function['name']}' is most used. Ensure it's well-optimized and monitored.")
        
        if not recommendations:
            recommendations.append("✅ System performing well. Continue monitoring for optimal performance.")
        
        return recommendations
    
    async def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get current real-time system metrics"""
        
        system_metrics = await self._analyze_system_metrics()
        
        # Get recent execution metrics (last hour)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1)
        
        async with get_async_db() as session:
            recent_executions = await session.execute(
                session.query(FunctionExecution)
                .filter(and_(
                    FunctionExecution.created_at >= start_time,
                    FunctionExecution.created_at <= end_time
                ))
            )
            recent_executions = recent_executions.scalars().all()
            
            total_recent = len(recent_executions)
            successful_recent = len([e for e in recent_executions if e.status == "completed"])
            
            return {
                "timestamp": end_time.isoformat(),
                "system_metrics": system_metrics,
                "recent_executions": total_recent,
                "recent_success_rate": successful_recent / total_recent if total_recent > 0 else 0,
                "current_throughput": total_recent,  # executions per hour
                "alerts": self._check_alerts(system_metrics, total_recent, successful_recent / total_recent if total_recent > 0 else 1)
            }
    
    def _check_alerts(self, system_metrics: Dict[str, Any], recent_executions: int, success_rate: float) -> List[Dict[str, Any]]:
        """Check for alert conditions"""
        
        alerts = []
        
        # System alerts
        if system_metrics.get("cpu_usage_percent", 0) > self.alert_thresholds["cpu_usage"] * 100:
            alerts.append({
                "type": "system",
                "severity": "warning",
                "message": f"High CPU usage: {system_metrics['cpu_usage_percent']}%"
            })
        
        if system_metrics.get("memory_usage_percent", 0) > self.alert_thresholds["memory_usage"] * 100:
            alerts.append({
                "type": "system",
                "severity": "warning",
                "message": f"High memory usage: {system_metrics['memory_usage_percent']}%"
            })
        
        # Performance alerts
        error_rate = 1 - success_rate
        if error_rate > self.alert_thresholds["error_rate"]:
            alerts.append({
                "type": "performance",
                "severity": "critical",
                "message": f"High error rate: {error_rate*100:.1f}%"
            })
        
        # Throughput alerts
        if recent_executions == 0:
            alerts.append({
                "type": "usage",
                "severity": "info",
                "message": "No recent executions detected"
            })
        
        return alerts


# Analytics utility functions
def format_duration(seconds: float) -> str:
    """Format duration in human-readable format"""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"


def calculate_trend(values: List[float]) -> str:
    """Calculate trend direction from list of values"""
    if len(values) < 2:
        return "stable"
    
    # Simple linear trend calculation
    n = len(values)
    x_sum = sum(range(n))
    y_sum = sum(values)
    xy_sum = sum(i * values[i] for i in range(n))
    x_squared_sum = sum(i * i for i in range(n))
    
    slope = (n * xy_sum - x_sum * y_sum) / (n * x_squared_sum - x_sum * x_sum)
    
    if slope > 0.1:
        return "increasing"
    elif slope < -0.1:
        return "decreasing"
    else:
        return "stable"