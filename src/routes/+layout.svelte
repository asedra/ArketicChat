<script>
	import '../app.css';
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { browser } from '$app/environment';
	
	// Theme management
	let darkMode = false;
	
	onMount(() => {
		// Initialize theme from localStorage or system preference
		if (browser) {
			const saved = localStorage.getItem('darkMode');
			if (saved !== null) {
				darkMode = JSON.parse(saved);
			} else {
				darkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
			}
			updateTheme();
		}
	});
	
	function toggleTheme() {
		darkMode = !darkMode;
		if (browser) {
			localStorage.setItem('darkMode', JSON.stringify(darkMode));
		}
		updateTheme();
	}
	
	function updateTheme() {
		if (browser) {
			document.documentElement.classList.toggle('dark', darkMode);
		}
	}
	
	// Navigation state
	let sidebarOpen = false;
	
	// Navigation items
	const navItems = [
		{ href: '/', label: 'Chat Interface', icon: '💬' },
		{ href: '/functions', label: 'Functions', icon: '⚙️' },
		{ href: '/analytics', label: 'Analytics', icon: '📊' },
		{ href: '/settings', label: 'Settings', icon: '🔧' }
	];
	
	// Check if current route is active
	$: isActive = (href) => {
		if (href === '/') {
			return $page.url.pathname === '/';
		}
		return $page.url.pathname.startsWith(href);
	};
</script>

<svelte:head>
	<title>ATTILA AI - Enhanced Function Management System</title>
	<meta name="description" content="AI-powered function orchestration platform" />
</svelte:head>

<div class="min-h-screen bg-slate-50 dark:bg-slate-900">
	<!-- Mobile sidebar overlay -->
	{#if sidebarOpen}
		<div 
			class="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
			on:click={() => sidebarOpen = false}
			on:keydown={(e) => e.key === 'Escape' && (sidebarOpen = false)}
		></div>
	{/if}
	
	<!-- Sidebar -->
	<div 
		class="fixed inset-y-0 left-0 z-50 w-64 bg-white dark:bg-slate-800 shadow-lg transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:inset-0"
		class:translate-x-0={sidebarOpen}
		class:-translate-x-full={!sidebarOpen}
	>
		<div class="flex items-center justify-between h-16 px-4 border-b border-slate-200 dark:border-slate-700">
			<div class="flex items-center space-x-3">
				<div class="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
					<span class="text-white font-bold text-sm">AI</span>
				</div>
				<h1 class="text-xl font-bold text-slate-900 dark:text-slate-100">ATTILA</h1>
			</div>
			<button 
				class="lg:hidden p-2 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700"
				on:click={() => sidebarOpen = false}
			>
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
				</svg>
			</button>
		</div>
		
		<nav class="mt-6 px-3">
			{#each navItems as item}
				<a 
					href={item.href}
					class="flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors duration-200 mb-1"
					class:nav-link-active={isActive(item.href)}
					class:nav-link={!isActive(item.href)}
					on:click={() => sidebarOpen = false}
				>
					<span class="text-lg">{item.icon}</span>
					<span>{item.label}</span>
				</a>
			{/each}
		</nav>
		
		<!-- Sidebar footer -->
		<div class="absolute bottom-0 left-0 right-0 p-4 border-t border-slate-200 dark:border-slate-700">
			<div class="flex items-center justify-between">
				<div class="flex items-center space-x-2">
					<div class="status-indicator status-online"></div>
					<span class="text-sm text-slate-600 dark:text-slate-400">System Online</span>
				</div>
				<button 
					class="p-2 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors duration-200"
					on:click={toggleTheme}
					title="Toggle theme"
				>
					{#if darkMode}
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"></path>
						</svg>
					{:else}
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"></path>
						</svg>
					{/if}
				</button>
			</div>
			
			<!-- Version info -->
			<div class="mt-2 text-xs text-slate-500 dark:text-slate-400">
				v1.0.0 - Phase 3 Complete
			</div>
		</div>
	</div>
	
	<!-- Main content area -->
	<div class="lg:ml-64">
		<!-- Top header -->
		<header class="bg-white dark:bg-slate-800 shadow-sm border-b border-slate-200 dark:border-slate-700 lg:hidden">
			<div class="flex items-center justify-between h-16 px-4">
				<button 
					class="p-2 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700"
					on:click={() => sidebarOpen = true}
				>
					<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path>
					</svg>
				</button>
				<h1 class="text-lg font-semibold text-slate-900 dark:text-slate-100">ATTILA AI</h1>
				<div class="w-10"></div>
			</div>
		</header>
		
		<!-- Page content -->
		<main class="min-h-screen">
			<slot></slot>
		</main>
	</div>
</div>

<!-- Global loading indicator -->
<div id="loading-indicator" class="fixed top-4 right-4 z-50 hidden">
	<div class="bg-blue-600 text-white px-4 py-2 rounded-lg shadow-lg flex items-center space-x-2">
		<div class="loading-spinner w-4 h-4 border-2 border-white border-t-transparent rounded-full"></div>
		<span>Processing...</span>
	</div>
</div>

<!-- Global toast notifications -->
<div id="toast-container" class="fixed top-4 right-4 z-50 space-y-2">
	<!-- Toast notifications will be dynamically added here -->
</div>

<style>
	/* Custom scrollbar for sidebar */
	nav {
		scrollbar-width: thin;
		scrollbar-color: rgb(203 213 225) transparent;
	}
	
	.dark nav {
		scrollbar-color: rgb(71 85 105) transparent;
	}
	
	/* Smooth transitions */
	.nav-link, .nav-link-active {
		transition: all 0.2s ease-in-out;
	}
	
	/* Mobile responsive adjustments */
	@media (max-width: 1024px) {
		.sidebar {
			transform: translateX(-100%);
		}
		
		.sidebar.open {
			transform: translateX(0);
		}
	}
</style>