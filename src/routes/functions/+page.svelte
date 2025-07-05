<script>
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';
	
	// State management
	let functions = [];
	let isLoading = false;
	let showCreateModal = false;
	let showEditModal = false;
	let selectedFunction = null;
	let searchQuery = '';
	let filterType = 'all';
	let sortBy = 'name';
	let sortOrder = 'asc';
	
	// Form state
	let formData = {
		name: '',
		description: '',
		function_type: 'basic',
		parameters: {},
		prompt_template: '',
		api_config: null,
		document_content: '',
		mcp_config: null,
		extra_data: {},
		is_active: true
	};
	
	// Form validation
	let formErrors = {};
	
	// Mock API base URL
	const API_BASE = 'http://localhost:8000';
	
	// Function types configuration
	const functionTypes = [
		{ value: 'basic', label: 'Basic', description: 'Simple function execution' },
		{ value: 'api', label: 'API', description: 'HTTP API integration' },
		{ value: 'prompt', label: 'Prompt', description: 'AI-powered text processing' },
		{ value: 'document', label: 'Document', description: 'Knowledge base search' },
		{ value: 'mcp', label: 'MCP', description: 'Model Context Protocol' }
	];
	
	onMount(async () => {
		await loadFunctions();
	});
	
	async function loadFunctions() {
		isLoading = true;
		try {
			const response = await fetch(`${API_BASE}/functions/`, {
				headers: {
					'Content-Type': 'application/json',
				},
			});
			
			if (response.ok) {
				functions = await response.json();
			}
		} catch (error) {
			console.error('Failed to load functions:', error);
			// Fallback to mock data
			functions = [
				{
					id: 1,
					name: 'Weather Check',
					description: 'Get current weather information for any location',
					function_type: 'api',
					parameters: { location: 'string' },
					api_config: {
						method: 'GET',
						endpoint: 'https://api.openweathermap.org/data/2.5/weather',
						headers: { 'Content-Type': 'application/json' }
					},
					is_active: true,
					created_at: '2024-01-01T00:00:00Z',
					updated_at: '2024-01-01T00:00:00Z'
				},
				{
					id: 2,
					name: 'Code Review',
					description: 'AI-powered code review and feedback',
					function_type: 'prompt',
					parameters: { code: 'string', language: 'string' },
					prompt_template: 'Please review this {{language}} code and provide feedback:\n\n{{code}}',
					is_active: true,
					created_at: '2024-01-01T00:00:00Z',
					updated_at: '2024-01-01T00:00:00Z'
				},
				{
					id: 3,
					name: 'Document Search',
					description: 'Search through knowledge base documents',
					function_type: 'document',
					parameters: { query: 'string' },
					document_content: 'Sample knowledge base content...',
					is_active: true,
					created_at: '2024-01-01T00:00:00Z',
					updated_at: '2024-01-01T00:00:00Z'
				}
			];
		} finally {
			isLoading = false;
		}
	}
	
	async function saveFunction() {
		// Validate form
		formErrors = {};
		
		if (!formData.name.trim()) {
			formErrors.name = 'Function name is required';
		}
		
		if (!formData.description.trim()) {
			formErrors.description = 'Description is required';
		}
		
		if (formData.function_type === 'prompt' && !formData.prompt_template.trim()) {
			formErrors.prompt_template = 'Prompt template is required for prompt functions';
		}
		
		if (formData.function_type === 'api' && !formData.api_config) {
			formErrors.api_config = 'API configuration is required for API functions';
		}
		
		if (formData.function_type === 'document' && !formData.document_content.trim()) {
			formErrors.document_content = 'Document content is required for document functions';
		}
		
		if (Object.keys(formErrors).length > 0) {
			return;
		}
		
		try {
			const url = selectedFunction 
				? `${API_BASE}/functions/${selectedFunction.id}`
				: `${API_BASE}/functions/`;
			
			const method = selectedFunction ? 'PUT' : 'POST';
			
			const response = await fetch(url, {
				method,
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify(formData)
			});
			
			if (response.ok) {
				await loadFunctions();
				closeModal();
				showToast('Function saved successfully!', 'success');
			} else {
				throw new Error('Failed to save function');
			}
		} catch (error) {
			console.error('Error saving function:', error);
			showToast('Failed to save function', 'error');
		}
	}
	
	async function deleteFunction(func) {
		if (!confirm(`Are you sure you want to delete "${func.name}"?`)) {
			return;
		}
		
		try {
			const response = await fetch(`${API_BASE}/functions/${func.id}`, {
				method: 'DELETE',
			});
			
			if (response.ok) {
				await loadFunctions();
				showToast('Function deleted successfully!', 'success');
			} else {
				throw new Error('Failed to delete function');
			}
		} catch (error) {
			console.error('Error deleting function:', error);
			showToast('Failed to delete function', 'error');
		}
	}
	
	async function toggleFunctionStatus(func) {
		try {
			const response = await fetch(`${API_BASE}/functions/${func.id}`, {
				method: 'PUT',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					...func,
					is_active: !func.is_active
				})
			});
			
			if (response.ok) {
				await loadFunctions();
				showToast(`Function ${func.is_active ? 'deactivated' : 'activated'}!`, 'success');
			} else {
				throw new Error('Failed to update function status');
			}
		} catch (error) {
			console.error('Error updating function status:', error);
			showToast('Failed to update function status', 'error');
		}
	}
	
	function openCreateModal() {
		formData = {
			name: '',
			description: '',
			function_type: 'basic',
			parameters: {},
			prompt_template: '',
			api_config: null,
			document_content: '',
			mcp_config: null,
			extra_data: {},
			is_active: true
		};
		formErrors = {};
		selectedFunction = null;
		showCreateModal = true;
	}
	
	function openEditModal(func) {
		formData = { ...func };
		formErrors = {};
		selectedFunction = func;
		showEditModal = true;
	}
	
	function closeModal() {
		showCreateModal = false;
		showEditModal = false;
		selectedFunction = null;
		formData = {
			name: '',
			description: '',
			function_type: 'basic',
			parameters: {},
			prompt_template: '',
			api_config: null,
			document_content: '',
			mcp_config: null,
			extra_data: {},
			is_active: true
		};
		formErrors = {};
	}
	
	function showToast(message, type = 'info') {
		// Simple toast notification - in production, use a proper toast library
		const toast = document.createElement('div');
		toast.className = `fixed top-4 right-4 z-50 px-4 py-2 rounded-lg shadow-lg text-white ${
			type === 'success' ? 'bg-green-600' : 
			type === 'error' ? 'bg-red-600' : 
			'bg-blue-600'
		}`;
		toast.textContent = message;
		document.body.appendChild(toast);
		
		setTimeout(() => {
			toast.remove();
		}, 3000);
	}
	
	function handleParametersChange(event) {
		try {
			formData.parameters = JSON.parse(event.target.value);
			delete formErrors.parameters;
		} catch (error) {
			formErrors.parameters = 'Invalid JSON format';
		}
	}
	
	function handleApiConfigChange(event) {
		try {
			formData.api_config = JSON.parse(event.target.value);
			delete formErrors.api_config;
		} catch (error) {
			formErrors.api_config = 'Invalid JSON format';
		}
	}
	
	function handleMcpConfigChange(event) {
		try {
			formData.mcp_config = JSON.parse(event.target.value);
			delete formErrors.mcp_config;
		} catch (error) {
			formErrors.mcp_config = 'Invalid JSON format';
		}
	}
	
	function getFunctionTypeBadge(type) {
		const badges = {
			api: 'badge-primary',
			prompt: 'badge-success',
			document: 'badge-warning',
			mcp: 'badge-danger',
			basic: 'badge-gray'
		};
		return badges[type] || 'badge-gray';
	}
	
	function formatDate(dateString) {
		return new Date(dateString).toLocaleDateString([], {
			year: 'numeric',
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}
	
	// Filter and sort functions
	$: filteredFunctions = functions
		.filter(func => {
			const matchesSearch = func.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
				func.description.toLowerCase().includes(searchQuery.toLowerCase());
			const matchesType = filterType === 'all' || func.function_type === filterType;
			return matchesSearch && matchesType;
		})
		.sort((a, b) => {
			let aValue = a[sortBy];
			let bValue = b[sortBy];
			
			if (sortBy === 'created_at' || sortBy === 'updated_at') {
				aValue = new Date(aValue);
				bValue = new Date(bValue);
			}
			
			if (sortOrder === 'asc') {
				return aValue > bValue ? 1 : -1;
			} else {
				return aValue < bValue ? 1 : -1;
			}
		});
</script>

<svelte:head>
	<title>Functions - ATTILA AI</title>
</svelte:head>

<div class="p-6">
	<!-- Header -->
	<div class="flex items-center justify-between mb-6">
		<div>
			<h1 class="text-2xl font-bold text-slate-900 dark:text-slate-100">Functions</h1>
			<p class="text-slate-600 dark:text-slate-400">Manage your AI-powered functions and integrations</p>
		</div>
		<button 
			class="btn-primary"
			on:click={openCreateModal}
		>
			Create Function
		</button>
	</div>
	
	<!-- Filters and Search -->
	<div class="bg-white dark:bg-slate-800 rounded-lg shadow border border-slate-200 dark:border-slate-700 p-4 mb-6">
		<div class="flex flex-wrap items-center gap-4">
			<div class="flex-1 min-w-64">
				<input
					type="text"
					placeholder="Search functions..."
					bind:value={searchQuery}
					class="form-input"
				/>
			</div>
			<div class="flex items-center space-x-4">
				<select bind:value={filterType} class="form-select">
					<option value="all">All Types</option>
					{#each functionTypes as type}
						<option value={type.value}>{type.label}</option>
					{/each}
				</select>
				<select bind:value={sortBy} class="form-select">
					<option value="name">Sort by Name</option>
					<option value="function_type">Sort by Type</option>
					<option value="created_at">Sort by Created</option>
					<option value="updated_at">Sort by Updated</option>
				</select>
				<button 
					class="btn-outline"
					on:click={() => sortOrder = sortOrder === 'asc' ? 'desc' : 'asc'}
				>
					{sortOrder === 'asc' ? '↑' : '↓'}
				</button>
			</div>
		</div>
	</div>
	
	<!-- Functions List -->
	{#if isLoading}
		<div class="text-center py-12">
			<div class="loading-spinner w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full mx-auto mb-4"></div>
			<p class="text-slate-600 dark:text-slate-400">Loading functions...</p>
		</div>
	{:else if filteredFunctions.length === 0}
		<div class="text-center py-12">
			<div class="w-16 h-16 bg-slate-100 dark:bg-slate-700 rounded-full flex items-center justify-center mx-auto mb-4">
				<svg class="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path>
				</svg>
			</div>
			<h2 class="text-xl font-semibold text-slate-900 dark:text-slate-100 mb-2">No functions found</h2>
			<p class="text-slate-600 dark:text-slate-400 mb-4">
				{searchQuery || filterType !== 'all' ? 'Try adjusting your search or filters' : 'Get started by creating your first function'}
			</p>
			{#if !searchQuery && filterType === 'all'}
				<button 
					class="btn-primary"
					on:click={openCreateModal}
				>
					Create Your First Function
				</button>
			{/if}
		</div>
	{:else}
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
			{#each filteredFunctions as func}
				<div class="card">
					<div class="flex items-start justify-between mb-3">
						<div class="flex items-center space-x-3">
							<h3 class="text-lg font-semibold text-slate-900 dark:text-slate-100">{func.name}</h3>
							<span class="badge {getFunctionTypeBadge(func.function_type)}">
								{func.function_type}
							</span>
						</div>
						<div class="flex items-center space-x-2">
							<div class="status-indicator {func.is_active ? 'status-online' : 'status-offline'}" title={func.is_active ? 'Active' : 'Inactive'}></div>
							<button 
								class="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-700"
								on:click={() => toggleFunctionStatus(func)}
								title={func.is_active ? 'Deactivate' : 'Activate'}
							>
								{#if func.is_active}
									<svg class="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
									</svg>
								{:else}
									<svg class="w-4 h-4 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
									</svg>
								{/if}
							</button>
						</div>
					</div>
					
					<p class="text-slate-600 dark:text-slate-400 mb-4">{func.description}</p>
					
					{#if func.parameters && Object.keys(func.parameters).length > 0}
						<div class="mb-4">
							<h4 class="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">Parameters:</h4>
							<div class="flex flex-wrap gap-1">
								{#each Object.keys(func.parameters) as param}
									<span class="badge badge-gray text-xs">{param}</span>
								{/each}
							</div>
						</div>
					{/if}
					
					<div class="flex items-center justify-between text-sm text-slate-500 dark:text-slate-400 mb-4">
						<span>Created: {formatDate(func.created_at)}</span>
						{#if func.updated_at !== func.created_at}
							<span>Updated: {formatDate(func.updated_at)}</span>
						{/if}
					</div>
					
					<div class="flex items-center justify-between">
						<div class="flex items-center space-x-2">
							<button 
								class="btn-secondary text-sm"
								on:click={() => openEditModal(func)}
							>
								Edit
							</button>
							<button 
								class="btn-outline text-sm text-red-600 hover:text-red-700 hover:border-red-300"
								on:click={() => deleteFunction(func)}
							>
								Delete
							</button>
						</div>
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>

<!-- Create/Edit Modal -->
{#if showCreateModal || showEditModal}
	<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
		<div class="bg-white dark:bg-slate-800 rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
			<div class="p-6 border-b border-slate-200 dark:border-slate-700">
				<h2 class="text-xl font-semibold text-slate-900 dark:text-slate-100">
					{selectedFunction ? 'Edit Function' : 'Create Function'}
				</h2>
			</div>
			
			<div class="p-6 space-y-4">
				<!-- Basic Information -->
				<div>
					<label class="form-label">Function Name</label>
					<input 
						type="text" 
						bind:value={formData.name}
						class="form-input"
						class:border-red-500={formErrors.name}
						placeholder="Enter function name"
					/>
					{#if formErrors.name}
						<p class="form-error">{formErrors.name}</p>
					{/if}
				</div>
				
				<div>
					<label class="form-label">Description</label>
					<textarea 
						bind:value={formData.description}
						class="form-textarea"
						class:border-red-500={formErrors.description}
						placeholder="Describe what this function does"
					></textarea>
					{#if formErrors.description}
						<p class="form-error">{formErrors.description}</p>
					{/if}
				</div>
				
				<div>
					<label class="form-label">Function Type</label>
					<select bind:value={formData.function_type} class="form-select">
						{#each functionTypes as type}
							<option value={type.value}>{type.label} - {type.description}</option>
						{/each}
					</select>
				</div>
				
				<div>
					<label class="form-label">Parameters (JSON)</label>
					<textarea 
						value={JSON.stringify(formData.parameters, null, 2)}
						on:input={handleParametersChange}
						class="form-textarea font-mono text-sm"
						class:border-red-500={formErrors.parameters}
						placeholder='{"param1": "string", "param2": "number"}'
					></textarea>
					{#if formErrors.parameters}
						<p class="form-error">{formErrors.parameters}</p>
					{/if}
				</div>
				
				<!-- Type-specific fields -->
				{#if formData.function_type === 'prompt'}
					<div>
						<label class="form-label">Prompt Template</label>
						<textarea 
							bind:value={formData.prompt_template}
							class="form-textarea font-mono"
							class:border-red-500={formErrors.prompt_template}
							placeholder="Enter your prompt template with {{variables}}"
							rows="6"
						></textarea>
						{#if formErrors.prompt_template}
							<p class="form-error">{formErrors.prompt_template}</p>
						{/if}
					</div>
				{/if}
				
				{#if formData.function_type === 'api'}
					<div>
						<label class="form-label">API Configuration (JSON)</label>
						<textarea 
							value={JSON.stringify(formData.api_config, null, 2)}
							on:input={handleApiConfigChange}
							class="form-textarea font-mono text-sm"
							class:border-red-500={formErrors.api_config}
							placeholder='{"method": "GET", "endpoint": "https://api.example.com", "headers": {}}'
							rows="8"
						></textarea>
						{#if formErrors.api_config}
							<p class="form-error">{formErrors.api_config}</p>
						{/if}
					</div>
				{/if}
				
				{#if formData.function_type === 'document'}
					<div>
						<label class="form-label">Document Content</label>
						<textarea 
							bind:value={formData.document_content}
							class="form-textarea"
							class:border-red-500={formErrors.document_content}
							placeholder="Enter your document content for search"
							rows="8"
						></textarea>
						{#if formErrors.document_content}
							<p class="form-error">{formErrors.document_content}</p>
						{/if}
					</div>
				{/if}
				
				{#if formData.function_type === 'mcp'}
					<div>
						<label class="form-label">MCP Configuration (JSON)</label>
						<textarea 
							value={JSON.stringify(formData.mcp_config, null, 2)}
							on:input={handleMcpConfigChange}
							class="form-textarea font-mono text-sm"
							class:border-red-500={formErrors.mcp_config}
							placeholder='{"endpoint": "wss://mcp.example.com", "protocol_version": "1.0"}'
							rows="6"
						></textarea>
						{#if formErrors.mcp_config}
							<p class="form-error">{formErrors.mcp_config}</p>
						{/if}
					</div>
				{/if}
				
				<div class="flex items-center">
					<input 
						type="checkbox" 
						bind:checked={formData.is_active}
						class="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
					/>
					<label class="ml-2 text-sm text-slate-700 dark:text-slate-300">
						Active (function can be executed)
					</label>
				</div>
			</div>
			
			<div class="p-6 border-t border-slate-200 dark:border-slate-700 flex justify-end space-x-3">
				<button 
					class="btn-secondary"
					on:click={closeModal}
				>
					Cancel
				</button>
				<button 
					class="btn-primary"
					on:click={saveFunction}
				>
					{selectedFunction ? 'Update' : 'Create'} Function
				</button>
			</div>
		</div>
	</div>
{/if}

<style>
	/* Modal animations */
	.fixed {
		animation: fadeIn 0.3s ease-out;
	}
	
	/* Card hover effects */
	.card:hover {
		transform: translateY(-2px);
		box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
	}
	
	/* Form focus states */
	.form-input:focus, .form-textarea:focus, .form-select:focus {
		border-color: #3b82f6;
		box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
	}
	
	/* Error states */
	.border-red-500 {
		border-color: #ef4444;
	}
	
	.border-red-500:focus {
		border-color: #ef4444;
		box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1);
	}
</style>