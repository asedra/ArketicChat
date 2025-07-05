<script>
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';
	
	// Chat state management
	let messages = [];
	let currentMessage = '';
	let isLoading = false;
	let selectedFunctions = [];
	let availableFunctions = [];
	
	// Function execution state
	let executionResults = [];
	let currentExecution = null;
	
	// UI state
	let chatContainer;
	let messageInput;
	let showFunctionPanel = false;
	let routerAnalysis = null;
	
	// Mock API base URL - in production this would come from environment
	const API_BASE = 'http://localhost:8000';
	
	onMount(async () => {
		// Load available functions
		await loadFunctions();
		
		// Load chat history from localStorage
		if (browser) {
			const saved = localStorage.getItem('chatHistory');
			if (saved) {
				messages = JSON.parse(saved);
			}
		}
		
		// Focus input on load
		if (messageInput) {
			messageInput.focus();
		}
	});
	
	async function loadFunctions() {
		try {
			const response = await fetch(`${API_BASE}/functions/`, {
				headers: {
					'Content-Type': 'application/json',
				},
			});
			
			if (response.ok) {
				availableFunctions = await response.json();
			}
		} catch (error) {
			console.error('Failed to load functions:', error);
			// Fallback to mock data
			availableFunctions = [
				{
					id: 1,
					name: 'Weather Check',
					function_type: 'api',
					description: 'Get current weather information',
					parameters: { location: 'string' },
					is_active: true
				},
				{
					id: 2,
					name: 'Code Review',
					function_type: 'prompt',
					description: 'AI-powered code review and feedback',
					parameters: { code: 'string', language: 'string' },
					is_active: true
				},
				{
					id: 3,
					name: 'Document Search',
					function_type: 'document',
					description: 'Search through knowledge base',
					parameters: { query: 'string' },
					is_active: true
				}
			];
		}
	}
	
	async function sendMessage() {
		if (!currentMessage.trim() || isLoading) return;
		
		const userMessage = {
			id: Date.now(),
			content: currentMessage,
			role: 'user',
			timestamp: new Date().toISOString()
		};
		
		messages = [...messages, userMessage];
		const messageToSend = currentMessage;
		currentMessage = '';
		isLoading = true;
		
		// Save to localStorage
		if (browser) {
			localStorage.setItem('chatHistory', JSON.stringify(messages));
		}
		
		// Scroll to bottom
		scrollToBottom();
		
		try {
			// First, get AI routing analysis
			const routingResponse = await fetch(`${API_BASE}/router/analyze`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					user_input: messageToSend,
					available_functions: availableFunctions.map(f => f.id)
				})
			});
			
			if (routingResponse.ok) {
				routerAnalysis = await routingResponse.json();
				
				// Add router analysis message
				const analysisMessage = {
					id: Date.now() + 1,
					content: `🧠 **AI Router Analysis**\n\n**Confidence:** ${(routerAnalysis.confidence * 100).toFixed(1)}%\n**Recommended Functions:** ${routerAnalysis.recommended_functions.join(', ')}\n**Reasoning:** ${routerAnalysis.reasoning}`,
					role: 'system',
					timestamp: new Date().toISOString(),
					type: 'router_analysis'
				};
				
				messages = [...messages, analysisMessage];
			}
			
			// Execute the recommended functions or use selected ones
			const functionsToExecute = selectedFunctions.length > 0 ? selectedFunctions : (routerAnalysis?.recommended_functions || []);
			
			if (functionsToExecute.length > 0) {
				// Execute functions
				const executionResponse = await fetch(`${API_BASE}/execute`, {
					method: 'POST',
					headers: {
						'Content-Type': 'application/json',
					},
					body: JSON.stringify({
						function_ids: functionsToExecute,
						context: {
							user_input: messageToSend,
							parameters: extractParameters(messageToSend)
						}
					})
				});
				
				if (executionResponse.ok) {
					const executionResult = await executionResponse.json();
					currentExecution = executionResult;
					
					// Add execution result message
					const resultMessage = {
						id: Date.now() + 2,
						content: formatExecutionResult(executionResult),
						role: 'assistant',
						timestamp: new Date().toISOString(),
						type: 'execution_result',
						executionData: executionResult
					};
					
					messages = [...messages, resultMessage];
				}
			} else {
				// No functions to execute, provide general AI response
				const aiMessage = {
					id: Date.now() + 2,
					content: `I understand you're asking about "${messageToSend}". I don't have specific functions configured for this request, but I can help you with:\n\n• Weather information\n• Code review\n• Document search\n• Function management\n\nYou can also create custom functions or select specific ones from the Functions panel.`,
					role: 'assistant',
					timestamp: new Date().toISOString(),
					type: 'general_response'
				};
				
				messages = [...messages, aiMessage];
			}
			
		} catch (error) {
			console.error('Error sending message:', error);
			
			// Add error message
			const errorMessage = {
				id: Date.now() + 3,
				content: `❌ **Error**: Failed to process your request. ${error.message}`,
				role: 'system',
				timestamp: new Date().toISOString(),
				type: 'error'
			};
			
			messages = [...messages, errorMessage];
		} finally {
			isLoading = false;
			selectedFunctions = [];
			
			// Save updated messages
			if (browser) {
				localStorage.setItem('chatHistory', JSON.stringify(messages));
			}
			
			scrollToBottom();
		}
	}
	
	function extractParameters(userInput) {
		// Simple parameter extraction - in production, this would be more sophisticated
		const params = {};
		
		// Extract common patterns
		const locationMatch = userInput.match(/(?:weather|temperature|forecast).*?(?:in|for|at)\s+([a-zA-Z\s]+?)(?:\s|$|[,.!?])/i);
		if (locationMatch) {
			params.location = locationMatch[1].trim();
		}
		
		const codeMatch = userInput.match(/```(\w+)?\n(.*?)```/s);
		if (codeMatch) {
			params.code = codeMatch[2];
			params.language = codeMatch[1] || 'unknown';
		}
		
		// Extract search query
		const searchMatch = userInput.match(/(?:search|find|look for)\s+(.+)/i);
		if (searchMatch) {
			params.query = searchMatch[1];
		}
		
		return params;
	}
	
	function formatExecutionResult(result) {
		if (!result) return 'No execution result available.';
		
		let content = `✅ **Execution Complete**\n\n`;
		
		if (result.session_id) {
			content += `**Session ID:** ${result.session_id}\n`;
		}
		
		if (result.total_execution_time) {
			content += `**Total Time:** ${result.total_execution_time.toFixed(2)}s\n`;
		}
		
		if (result.results && result.results.length > 0) {
			content += `\n**Results:**\n`;
			
			result.results.forEach((funcResult, index) => {
				content += `\n**${index + 1}. ${funcResult.function_type.toUpperCase()} Function**\n`;
				content += `• Status: ${funcResult.status}\n`;
				content += `• Time: ${funcResult.execution_time?.toFixed(2) || 'N/A'}s\n`;
				
				if (funcResult.status === 'completed' && funcResult.result) {
					if (typeof funcResult.result === 'string') {
						content += `• Result: ${funcResult.result}\n`;
					} else if (funcResult.result.result) {
						content += `• Result: ${JSON.stringify(funcResult.result.result, null, 2)}\n`;
					}
				}
				
				if (funcResult.error) {
					content += `• Error: ${funcResult.error}\n`;
				}
			});
		}
		
		return content;
	}
	
	function scrollToBottom() {
		if (chatContainer) {
			setTimeout(() => {
				chatContainer.scrollTop = chatContainer.scrollHeight;
			}, 100);
		}
	}
	
	function handleKeyDown(event) {
		if (event.key === 'Enter' && !event.shiftKey) {
			event.preventDefault();
			sendMessage();
		}
	}
	
	function toggleFunctionSelection(functionId) {
		if (selectedFunctions.includes(functionId)) {
			selectedFunctions = selectedFunctions.filter(id => id !== functionId);
		} else {
			selectedFunctions = [...selectedFunctions, functionId];
		}
	}
	
	function clearChat() {
		messages = [];
		if (browser) {
			localStorage.removeItem('chatHistory');
		}
	}
	
	function formatTime(timestamp) {
		return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
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
</script>

<svelte:head>
	<title>ATTILA AI - Chat Interface</title>
</svelte:head>

<div class="flex h-screen bg-slate-50 dark:bg-slate-900">
	<!-- Main chat area -->
	<div class="flex-1 flex flex-col">
		<!-- Chat header -->
		<div class="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 px-6 py-4">
			<div class="flex items-center justify-between">
				<div>
					<h1 class="text-xl font-semibold text-slate-900 dark:text-slate-100">AI Chat Interface</h1>
					<p class="text-sm text-slate-600 dark:text-slate-400">Enhanced with intelligent function routing</p>
				</div>
				<div class="flex items-center space-x-3">
					<button 
						class="btn-secondary text-sm"
						on:click={() => showFunctionPanel = !showFunctionPanel}
					>
						{showFunctionPanel ? 'Hide' : 'Show'} Functions
					</button>
					<button 
						class="btn-outline text-sm"
						on:click={clearChat}
					>
						Clear Chat
					</button>
				</div>
			</div>
		</div>
		
		<!-- Chat messages -->
		<div 
			bind:this={chatContainer}
			class="flex-1 overflow-y-auto p-6 space-y-4"
		>
			{#if messages.length === 0}
				<div class="text-center py-12">
					<div class="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center mx-auto mb-4">
						<span class="text-white font-bold text-xl">AI</span>
					</div>
					<h2 class="text-xl font-semibold text-slate-900 dark:text-slate-100 mb-2">Welcome to ATTILA AI</h2>
					<p class="text-slate-600 dark:text-slate-400 mb-6">Start a conversation and let AI intelligently route your requests to the best functions.</p>
					<div class="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-2xl mx-auto">
						<div class="card-compact">
							<div class="text-2xl mb-2">🌤️</div>
							<h3 class="font-medium text-slate-900 dark:text-slate-100">Weather Info</h3>
							<p class="text-sm text-slate-600 dark:text-slate-400">Ask about weather conditions</p>
						</div>
						<div class="card-compact">
							<div class="text-2xl mb-2">🔍</div>
							<h3 class="font-medium text-slate-900 dark:text-slate-100">Code Review</h3>
							<p class="text-sm text-slate-600 dark:text-slate-400">Get AI-powered code analysis</p>
						</div>
						<div class="card-compact">
							<div class="text-2xl mb-2">📚</div>
							<h3 class="font-medium text-slate-900 dark:text-slate-100">Document Search</h3>
							<p class="text-sm text-slate-600 dark:text-slate-400">Search through knowledge base</p>
						</div>
					</div>
				</div>
			{/if}
			
			{#each messages as message}
				<div class="chat-message" class:chat-message-user={message.role === 'user'} class:chat-message-assistant={message.role === 'assistant'}>
					<div class="flex items-start space-x-3">
						<!-- Avatar -->
						<div class="flex-shrink-0">
							{#if message.role === 'user'}
								<div class="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
									<span class="text-white font-medium text-sm">U</span>
								</div>
							{:else if message.role === 'system'}
								<div class="w-8 h-8 bg-yellow-600 rounded-full flex items-center justify-center">
									<span class="text-white font-medium text-sm">S</span>
								</div>
							{:else}
								<div class="w-8 h-8 bg-green-600 rounded-full flex items-center justify-center">
									<span class="text-white font-medium text-sm">AI</span>
								</div>
							{/if}
						</div>
						
						<!-- Message content -->
						<div class="flex-1 min-w-0">
							<div class="flex items-center space-x-2 mb-1">
								<span class="text-sm font-medium text-slate-900 dark:text-slate-100">
									{message.role === 'user' ? 'You' : message.role === 'system' ? 'System' : 'ATTILA AI'}
								</span>
								<span class="text-xs text-slate-500 dark:text-slate-400">
									{formatTime(message.timestamp)}
								</span>
								{#if message.type}
									<span class="badge badge-gray text-xs">
										{message.type.replace('_', ' ')}
									</span>
								{/if}
							</div>
							
							<div class="chat-bubble" class:chat-bubble-user={message.role === 'user'} class:chat-bubble-assistant={message.role !== 'user'}>
								<div class="whitespace-pre-wrap">{message.content}</div>
								
								{#if message.executionData}
									<div class="mt-3 pt-3 border-t border-slate-200 dark:border-slate-600">
										<div class="text-xs text-slate-500 dark:text-slate-400">
											Execution ID: {message.executionData.session_id}
										</div>
									</div>
								{/if}
							</div>
						</div>
					</div>
				</div>
			{/each}
			
			{#if isLoading}
				<div class="chat-message chat-message-assistant">
					<div class="flex items-start space-x-3">
						<div class="w-8 h-8 bg-green-600 rounded-full flex items-center justify-center">
							<div class="loading-spinner w-4 h-4 border-2 border-white border-t-transparent rounded-full"></div>
						</div>
						<div class="flex-1">
							<div class="chat-bubble chat-bubble-assistant">
								<div class="flex items-center space-x-2">
									<span>Processing your request...</span>
								</div>
							</div>
						</div>
					</div>
				</div>
			{/if}
		</div>
		
		<!-- Input area -->
		<div class="bg-white dark:bg-slate-800 border-t border-slate-200 dark:border-slate-700 p-4">
			{#if selectedFunctions.length > 0}
				<div class="mb-3">
					<div class="flex items-center space-x-2 mb-2">
						<span class="text-sm font-medium text-slate-700 dark:text-slate-300">Selected Functions:</span>
						<button 
							class="text-xs text-blue-600 hover:text-blue-700"
							on:click={() => selectedFunctions = []}
						>
							Clear All
						</button>
					</div>
					<div class="flex flex-wrap gap-2">
						{#each selectedFunctions as funcId}
							{@const func = availableFunctions.find(f => f.id === funcId)}
							{#if func}
								<div class="flex items-center space-x-2 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 px-3 py-1 rounded-full text-sm">
									<span>{func.name}</span>
									<button 
										class="hover:bg-blue-100 dark:hover:bg-blue-900/40 rounded-full p-0.5"
										on:click={() => toggleFunctionSelection(funcId)}
									>
										<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
										</svg>
									</button>
								</div>
							{/if}
						{/each}
					</div>
				</div>
			{/if}
			
			<div class="flex items-end space-x-3">
				<div class="flex-1">
					<textarea
						bind:this={messageInput}
						bind:value={currentMessage}
						on:keydown={handleKeyDown}
						placeholder="Type your message... (Shift+Enter for new line)"
						class="form-textarea resize-none"
						rows="1"
						disabled={isLoading}
					></textarea>
				</div>
				<button 
					class="btn-primary"
					on:click={sendMessage}
					disabled={isLoading || !currentMessage.trim()}
				>
					{#if isLoading}
						<div class="loading-spinner w-4 h-4 border-2 border-white border-t-transparent rounded-full"></div>
					{:else}
						Send
					{/if}
				</button>
			</div>
		</div>
	</div>
	
	<!-- Function selection panel -->
	{#if showFunctionPanel}
		<div class="w-80 bg-white dark:bg-slate-800 border-l border-slate-200 dark:border-slate-700 flex flex-col">
			<div class="p-4 border-b border-slate-200 dark:border-slate-700">
				<h3 class="text-lg font-semibold text-slate-900 dark:text-slate-100">Available Functions</h3>
				<p class="text-sm text-slate-600 dark:text-slate-400">Select functions to include in your next message</p>
			</div>
			
			<div class="flex-1 overflow-y-auto p-4 space-y-3">
				{#each availableFunctions as func}
					<div 
						class="function-card"
						class:function-card-selected={selectedFunctions.includes(func.id)}
						on:click={() => toggleFunctionSelection(func.id)}
					>
						<div class="flex items-start justify-between mb-2">
							<h4 class="font-medium text-slate-900 dark:text-slate-100">{func.name}</h4>
							<div class="flex items-center space-x-2">
								<span class="badge {getFunctionTypeBadge(func.function_type)}">
									{func.function_type}
								</span>
								{#if selectedFunctions.includes(func.id)}
									<div class="w-4 h-4 bg-blue-600 rounded-full flex items-center justify-center">
										<svg class="w-2.5 h-2.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
										</svg>
									</div>
								{/if}
							</div>
						</div>
						<p class="text-sm text-slate-600 dark:text-slate-400 mb-2">{func.description}</p>
						{#if func.parameters}
							<div class="text-xs text-slate-500 dark:text-slate-400">
								Parameters: {Object.keys(func.parameters).join(', ')}
							</div>
						{/if}
					</div>
				{/each}
			</div>
		</div>
	{/if}
</div>

<style>
	/* Auto-resize textarea */
	textarea {
		resize: none;
		min-height: 42px;
		max-height: 120px;
	}
	
	/* Smooth scrolling */
	.overflow-y-auto {
		scroll-behavior: smooth;
	}
	
	/* Message animations */
	.chat-message {
		animation: slideInUp 0.3s ease-out;
	}
	
	/* Selection animations */
	.function-card {
		transition: all 0.2s ease-in-out;
	}
	
	.function-card:hover {
		transform: translateY(-1px);
	}
	
	.function-card-selected {
		transform: translateY(-1px);
		box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
	}
</style>