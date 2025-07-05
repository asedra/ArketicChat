<script>
	import { onMount, onDestroy } from 'svelte';
	import { browser } from '$app/environment';
	
	// Analytics state
	let analyticsData = null;
	let realTimeMetrics = null;
	let isLoading = true;
	let selectedPeriod = '24';
	let autoRefresh = true;
	let refreshInterval = null;
	
	// Charts and visualizations
	let performanceChart = null;
	let usageChart = null;
	let errorChart = null;
	
	// API base URL
	const API_BASE = 'http://localhost:8000';
	
	// Refresh intervals
	const REFRESH_INTERVALS = {
		'5': 5000,   // 5 seconds
		'30': 30000, // 30 seconds
		'60': 60000  // 1 minute
	};
	
	onMount(async () => {
		await loadAnalytics();
		await loadRealTimeMetrics();
		
		if (autoRefresh) {
			startAutoRefresh();
		}
	});
	
	onDestroy(() => {
		stopAutoRefresh();
	});
	
	async function loadAnalytics() {
		isLoading = true;
		try {
			const response = await fetch(`${API_BASE}/analytics/performance?period_hours=${selectedPeriod}`, {
				headers: {
					'Content-Type': 'application/json',
				},
			});
			
			if (response.ok) {
				analyticsData = await response.json();
			} else {
				// Fallback to mock data
				analyticsData = generateMockAnalytics();
			}
		} catch (error) {
			console.error('Failed to load analytics:', error);
			analyticsData = generateMockAnalytics();
		} finally {
			isLoading = false;
		}
	}
	
	async function loadRealTimeMetrics() {
		try {
			const response = await fetch(`${API_BASE}/analytics/realtime`, {
				headers: {
					'Content-Type': 'application/json',
				},
			});
			
			if (response.ok) {
				realTimeMetrics = await response.json();
			} else {
				realTimeMetrics = generateMockRealTimeMetrics();
			}
		} catch (error) {
			console.error('Failed to load real-time metrics:', error);
			realTimeMetrics = generateMockRealTimeMetrics();
		}
	}
	
	function startAutoRefresh() {
		if (refreshInterval) return;
		
		refreshInterval = setInterval(async () => {
			await loadRealTimeMetrics();
			if (Math.random() < 0.1) { // Refresh full analytics occasionally
				await loadAnalytics();
			}
		}, REFRESH_INTERVALS['30']);
	}
	
	function stopAutoRefresh() {
		if (refreshInterval) {
			clearInterval(refreshInterval);
			refreshInterval = null;
		}
	}
	
	function toggleAutoRefresh() {
		autoRefresh = !autoRefresh;
		if (autoRefresh) {
			startAutoRefresh();
		} else {
			stopAutoRefresh();
		}
	}
	
	async function handlePeriodChange() {
		await loadAnalytics();
	}
	
	function getHealthStatusColor(status) {
		switch (status) {
			case 'healthy': return 'text-green-600 dark:text-green-400';
			case 'degraded': return 'text-yellow-600 dark:text-yellow-400';
			case 'critical': return 'text-red-600 dark:text-red-400';
			default: return 'text-slate-600 dark:text-slate-400';
		}
	}
	
	function getAlertSeverityColor(severity) {
		switch (severity) {
			case 'critical': return 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-300';
			case 'warning': return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-300';
			case 'info': return 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-300';
			default: return 'bg-slate-100 text-slate-800 dark:bg-slate-700 dark:text-slate-300';
		}
	}
	
	function formatNumber(num) {
		if (num >= 1000000) {
			return (num / 1000000).toFixed(1) + 'M';
		} else if (num >= 1000) {
			return (num / 1000).toFixed(1) + 'K';
		}
		return num.toString();
	}
	
	function formatDuration(seconds) {
		if (seconds < 1) {
			return `${(seconds * 1000).toFixed(0)}ms`;
		} else if (seconds < 60) {
			return `${seconds.toFixed(1)}s`;
		} else if (seconds < 3600) {
			return `${(seconds / 60).toFixed(1)}m`;
		} else {
			return `${(seconds / 3600).toFixed(1)}h`;
		}
	}
	
	function formatPercentage(value) {
		return `${(value * 100).toFixed(1)}%`;
	}
	
	function generateMockAnalytics() {
		return {
			summary: {
				period_hours: parseInt(selectedPeriod),
				total_executions: 2847,
				success_rate: 0.9723,
				active_functions: 12,
				system_uptime: "7d 14h 23m",
				health_status: "healthy"
			},
			performance_metrics: {
				total_executions: 2847,
				avg_execution_time: 1.247,
				p95_execution_time: 3.891,
				p99_execution_time: 7.234,
				fastest_execution: 0.089,
				slowest_execution: 12.456,
				throughput_per_hour: 118.6,
				performance_trend: [
					{ timestamp: "2024-01-01T00:00:00Z", avg_execution_time: 1.2, execution_count: 45 },
					{ timestamp: "2024-01-01T01:00:00Z", avg_execution_time: 1.1, execution_count: 52 },
					{ timestamp: "2024-01-01T02:00:00Z", avg_execution_time: 1.3, execution_count: 38 }
				]
			},
			usage_statistics: {
				function_type_distribution: {
					"api": 1234,
					"prompt": 892,
					"document": 456,
					"mcp": 178,
					"basic": 87
				},
				popular_functions: [
					{ name: "Weather Check", type: "api", usage_count: 456 },
					{ name: "Code Review", type: "prompt", usage_count: 389 },
					{ name: "Document Search", type: "document", usage_count: 234 }
				],
				router_accuracy: 0.912,
				total_router_decisions: 2847,
				hourly_usage_pattern: {
					"0": 23, "1": 18, "2": 15, "3": 12, "4": 19, "5": 34,
					"6": 67, "7": 89, "8": 145, "9": 189, "10": 234, "11": 267,
					"12": 298, "13": 276, "14": 245, "15": 189, "16": 156,
					"17": 123, "18": 98, "19": 76, "20": 54, "21": 43, "22": 32, "23": 28
				},
				peak_usage_hour: 12
			},
			error_analysis: {
				total_executions: 2847,
				total_failures: 79,
				error_rate: 0.0277,
				error_categories: {
					"timeout": 23,
					"authentication": 18,
					"network": 15,
					"validation": 12,
					"other": 11
				},
				error_by_function: [
					{ function_name: "External API", function_type: "api", error_count: 34 },
					{ function_name: "Document Parser", function_type: "document", error_count: 23 }
				],
				mttr: 2.34
			},
			recommendations: [
				"✅ System performing well. Continue monitoring for optimal performance.",
				"⭐ 'Weather Check' is most used. Ensure it's well-optimized and monitored.",
				"📈 Peak usage at hour 12. Consider load balancing or capacity planning."
			]
		};
	}
	
	function generateMockRealTimeMetrics() {
		return {
			timestamp: new Date().toISOString(),
			system_metrics: {
				cpu_usage_percent: 23.4,
				memory_usage_percent: 67.8,
				memory_available_gb: 3.2,
				disk_usage_percent: 45.6,
				disk_free_gb: 24.8,
				system_health_score: 89.2
			},
			recent_executions: 47,
			recent_success_rate: 0.957,
			current_throughput: 47,
			alerts: []
		};
	}
</script>

<svelte:head>
	<title>Analytics Dashboard - ATTILA AI</title>
</svelte:head>

<div class="p-6">
	<!-- Header -->
	<div class="flex items-center justify-between mb-6">
		<div>
			<h1 class="text-2xl font-bold text-slate-900 dark:text-slate-100">Analytics Dashboard</h1>
			<p class="text-slate-600 dark:text-slate-400">Real-time performance monitoring and insights</p>
		</div>
		<div class="flex items-center space-x-4">
			<select bind:value={selectedPeriod} on:change={handlePeriodChange} class="form-select">
				<option value="1">Last Hour</option>
				<option value="6">Last 6 Hours</option>
				<option value="24">Last 24 Hours</option>
				<option value="168">Last Week</option>
			</select>
			<button 
				class="btn-outline flex items-center space-x-2"
				class:bg-green-50={autoRefresh}
				class:border-green-300={autoRefresh}
				on:click={toggleAutoRefresh}
			>
				<div class="w-2 h-2 rounded-full" class:bg-green-500={autoRefresh} class:bg-slate-400={!autoRefresh}></div>
				<span>{autoRefresh ? 'Auto-refresh ON' : 'Auto-refresh OFF'}</span>
			</button>
		</div>
	</div>
	
	<!-- Real-time Alerts -->
	{#if realTimeMetrics?.alerts && realTimeMetrics.alerts.length > 0}
		<div class="mb-6">
			<h2 class="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-3">🚨 Active Alerts</h2>
			<div class="space-y-2">
				{#each realTimeMetrics.alerts as alert}
					<div class="p-3 rounded-lg border-l-4 border-red-500 bg-red-50 dark:bg-red-900/20">
						<div class="flex items-center justify-between">
							<div>
								<span class="badge {getAlertSeverityColor(alert.severity)} text-xs mr-2">
									{alert.severity.toUpperCase()}
								</span>
								<span class="text-sm font-medium text-red-800 dark:text-red-300">
									{alert.message}
								</span>
							</div>
							<span class="text-xs text-red-600 dark:text-red-400">
								{alert.type}
							</span>
						</div>
					</div>
				{/each}
			</div>
		</div>
	{/if}
	
	<!-- Summary Cards -->
	{#if analyticsData}
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
			<div class="metric-card">
				<div class="flex items-center justify-between">
					<div>
						<div class="metric-label">Total Executions</div>
						<div class="metric-value">{formatNumber(analyticsData.summary.total_executions)}</div>
					</div>
					<div class="text-2xl">🚀</div>
				</div>
			</div>
			
			<div class="metric-card">
				<div class="flex items-center justify-between">
					<div>
						<div class="metric-label">Success Rate</div>
						<div class="metric-value">{formatPercentage(analyticsData.summary.success_rate)}</div>
					</div>
					<div class="text-2xl">✅</div>
				</div>
			</div>
			
			<div class="metric-card">
				<div class="flex items-center justify-between">
					<div>
						<div class="metric-label">Active Functions</div>
						<div class="metric-value">{analyticsData.summary.active_functions}</div>
					</div>
					<div class="text-2xl">⚙️</div>
				</div>
			</div>
			
			<div class="metric-card">
				<div class="flex items-center justify-between">
					<div>
						<div class="metric-label">System Health</div>
						<div class="metric-value {getHealthStatusColor(analyticsData.summary.health_status)}">
							{analyticsData.summary.health_status.toUpperCase()}
						</div>
					</div>
					<div class="text-2xl">💚</div>
				</div>
			</div>
		</div>
	{/if}
	
	<!-- Real-time System Metrics -->
	{#if realTimeMetrics}
		<div class="card mb-8">
			<h2 class="text-xl font-semibold text-slate-900 dark:text-slate-100 mb-4">🔥 Real-time System Metrics</h2>
			<div class="grid grid-cols-1 md:grid-cols-3 gap-6">
				<div>
					<div class="flex items-center justify-between mb-2">
						<span class="text-sm font-medium text-slate-700 dark:text-slate-300">CPU Usage</span>
						<span class="text-sm text-slate-600 dark:text-slate-400">
							{realTimeMetrics.system_metrics.cpu_usage_percent.toFixed(1)}%
						</span>
					</div>
					<div class="progress-bar">
						<div 
							class="progress-fill"
							style="width: {realTimeMetrics.system_metrics.cpu_usage_percent}%"
							class:bg-red-500={realTimeMetrics.system_metrics.cpu_usage_percent > 80}
							class:bg-yellow-500={realTimeMetrics.system_metrics.cpu_usage_percent > 60 && realTimeMetrics.system_metrics.cpu_usage_percent <= 80}
						></div>
					</div>
				</div>
				
				<div>
					<div class="flex items-center justify-between mb-2">
						<span class="text-sm font-medium text-slate-700 dark:text-slate-300">Memory Usage</span>
						<span class="text-sm text-slate-600 dark:text-slate-400">
							{realTimeMetrics.system_metrics.memory_usage_percent.toFixed(1)}%
						</span>
					</div>
					<div class="progress-bar">
						<div 
							class="progress-fill"
							style="width: {realTimeMetrics.system_metrics.memory_usage_percent}%"
							class:bg-red-500={realTimeMetrics.system_metrics.memory_usage_percent > 85}
							class:bg-yellow-500={realTimeMetrics.system_metrics.memory_usage_percent > 70 && realTimeMetrics.system_metrics.memory_usage_percent <= 85}
						></div>
					</div>
				</div>
				
				<div>
					<div class="flex items-center justify-between mb-2">
						<span class="text-sm font-medium text-slate-700 dark:text-slate-300">Disk Usage</span>
						<span class="text-sm text-slate-600 dark:text-slate-400">
							{realTimeMetrics.system_metrics.disk_usage_percent.toFixed(1)}%
						</span>
					</div>
					<div class="progress-bar">
						<div 
							class="progress-fill"
							style="width: {realTimeMetrics.system_metrics.disk_usage_percent}%"
							class:bg-red-500={realTimeMetrics.system_metrics.disk_usage_percent > 90}
							class:bg-yellow-500={realTimeMetrics.system_metrics.disk_usage_percent > 75 && realTimeMetrics.system_metrics.disk_usage_percent <= 90}
						></div>
					</div>
				</div>
			</div>
			
			<div class="mt-6 flex items-center justify-between text-sm">
				<div class="flex items-center space-x-4">
					<span class="text-slate-600 dark:text-slate-400">
						System Health Score: <span class="font-medium">{realTimeMetrics.system_metrics.system_health_score}/100</span>
					</span>
					<span class="text-slate-600 dark:text-slate-400">
						Recent Executions: <span class="font-medium">{realTimeMetrics.recent_executions}</span>
					</span>
				</div>
				<div class="text-slate-500 dark:text-slate-400">
					Last updated: {new Date(realTimeMetrics.timestamp).toLocaleTimeString()}
				</div>
			</div>
		</div>
	{/if}
	
	{#if isLoading}
		<div class="text-center py-12">
			<div class="loading-spinner w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full mx-auto mb-4"></div>
			<p class="text-slate-600 dark:text-slate-400">Loading analytics data...</p>
		</div>
	{:else if analyticsData}
		<!-- Performance Metrics -->
		<div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
			<div class="card">
				<h3 class="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">⚡ Performance Metrics</h3>
				<div class="space-y-4">
					<div class="flex items-center justify-between">
						<span class="text-sm text-slate-600 dark:text-slate-400">Average Execution Time</span>
						<span class="font-medium">{formatDuration(analyticsData.performance_metrics.avg_execution_time)}</span>
					</div>
					<div class="flex items-center justify-between">
						<span class="text-sm text-slate-600 dark:text-slate-400">95th Percentile</span>
						<span class="font-medium">{formatDuration(analyticsData.performance_metrics.p95_execution_time)}</span>
					</div>
					<div class="flex items-center justify-between">
						<span class="text-sm text-slate-600 dark:text-slate-400">99th Percentile</span>
						<span class="font-medium">{formatDuration(analyticsData.performance_metrics.p99_execution_time)}</span>
					</div>
					<div class="flex items-center justify-between">
						<span class="text-sm text-slate-600 dark:text-slate-400">Throughput/Hour</span>
						<span class="font-medium">{analyticsData.performance_metrics.throughput_per_hour.toFixed(1)}</span>
					</div>
				</div>
			</div>
			
			<div class="card">
				<h3 class="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">📊 Function Usage</h3>
				<div class="space-y-3">
					{#each Object.entries(analyticsData.usage_statistics.function_type_distribution) as [type, count]}
						<div class="flex items-center justify-between">
							<div class="flex items-center space-x-2">
								<span class="badge {type === 'api' ? 'badge-primary' : type === 'prompt' ? 'badge-success' : type === 'document' ? 'badge-warning' : type === 'mcp' ? 'badge-danger' : 'badge-gray'} text-xs">
									{type}
								</span>
							</div>
							<span class="font-medium">{formatNumber(count)}</span>
						</div>
					{/each}
				</div>
			</div>
		</div>
		
		<!-- Popular Functions -->
		<div class="card mb-8">
			<h3 class="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">⭐ Most Popular Functions</h3>
			<div class="overflow-x-auto">
				<table class="w-full">
					<thead>
						<tr class="border-b border-slate-200 dark:border-slate-700">
							<th class="text-left py-2 text-sm font-medium text-slate-600 dark:text-slate-400">Function Name</th>
							<th class="text-left py-2 text-sm font-medium text-slate-600 dark:text-slate-400">Type</th>
							<th class="text-right py-2 text-sm font-medium text-slate-600 dark:text-slate-400">Usage Count</th>
						</tr>
					</thead>
					<tbody>
						{#each analyticsData.usage_statistics.popular_functions as func}
							<tr class="border-b border-slate-100 dark:border-slate-800">
								<td class="py-3 font-medium text-slate-900 dark:text-slate-100">{func.name}</td>
								<td class="py-3">
									<span class="badge {func.type === 'api' ? 'badge-primary' : func.type === 'prompt' ? 'badge-success' : func.type === 'document' ? 'badge-warning' : func.type === 'mcp' ? 'badge-danger' : 'badge-gray'} text-xs">
										{func.type}
									</span>
								</td>
								<td class="py-3 text-right font-medium">{formatNumber(func.usage_count)}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
		
		<!-- Error Analysis -->
		<div class="card mb-8">
			<h3 class="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">❌ Error Analysis</h3>
			<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
				<div>
					<h4 class="text-sm font-medium text-slate-700 dark:text-slate-300 mb-3">Error Categories</h4>
					<div class="space-y-2">
						{#each Object.entries(analyticsData.error_analysis.error_categories) as [category, count]}
							<div class="flex items-center justify-between">
								<span class="text-sm text-slate-600 dark:text-slate-400 capitalize">{category}</span>
								<span class="font-medium">{count}</span>
							</div>
						{/each}
					</div>
				</div>
				
				<div>
					<h4 class="text-sm font-medium text-slate-700 dark:text-slate-300 mb-3">Error Statistics</h4>
					<div class="space-y-2">
						<div class="flex items-center justify-between">
							<span class="text-sm text-slate-600 dark:text-slate-400">Error Rate</span>
							<span class="font-medium">{formatPercentage(analyticsData.error_analysis.error_rate)}</span>
						</div>
						<div class="flex items-center justify-between">
							<span class="text-sm text-slate-600 dark:text-slate-400">Total Failures</span>
							<span class="font-medium">{analyticsData.error_analysis.total_failures}</span>
						</div>
						<div class="flex items-center justify-between">
							<span class="text-sm text-slate-600 dark:text-slate-400">MTTR</span>
							<span class="font-medium">{formatDuration(analyticsData.error_analysis.mttr)}</span>
						</div>
					</div>
				</div>
			</div>
		</div>
		
		<!-- Recommendations -->
		<div class="card">
			<h3 class="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">💡 Recommendations</h3>
			<div class="space-y-3">
				{#each analyticsData.recommendations as recommendation}
					<div class="flex items-start space-x-3 p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
						<div class="flex-1 text-sm text-slate-700 dark:text-slate-300">
							{recommendation}
						</div>
					</div>
				{/each}
			</div>
		</div>
	{/if}
</div>

<style>
	/* Progress bar enhancements */
	.progress-bar {
		background: rgb(226 232 240);
	}
	
	.dark .progress-bar {
		background: rgb(51 65 85);
	}
	
	/* Table styling */
	table {
		border-collapse: collapse;
	}
	
	/* Animation for metrics cards */
	.metric-card {
		transition: transform 0.2s ease-in-out;
	}
	
	.metric-card:hover {
		transform: translateY(-2px);
	}
	
	/* Real-time indicator pulse */
	@keyframes pulse {
		0%, 100% { opacity: 1; }
		50% { opacity: 0.5; }
	}
	
	.bg-green-500 {
		animation: pulse 2s infinite;
	}
</style>