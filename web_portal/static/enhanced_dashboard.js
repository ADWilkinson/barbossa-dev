// Enhanced Dashboard JavaScript - Full functionality for all buttons and displays

let currentData = {};
let refreshInterval = null;

// Initialize enhanced dashboard
async function initEnhancedDashboard() {
    console.log('Initializing Enhanced Dashboard v4...');
    
    // Load all data sources
    await Promise.all([
        loadWorkDistribution(),
        loadProjects(),
        loadWorkflows(),
        loadAnomalies(),
        loadIntegrations(),
        loadOptimizations(),
        loadPerformanceMetrics()
    ]);
    
    // Start auto-refresh
    startAutoRefresh();
    
    // Initialize event handlers
    initEventHandlers();
}

// Load work distribution with detailed stats
async function loadWorkDistribution() {
    try {
        const response = await fetch('/api/v4/work-distribution');
        const data = await response.json();
        
        const tallyDiv = document.getElementById('work-tally');
        tallyDiv.innerHTML = '';
        
        Object.entries(data).forEach(([area, info]) => {
            const div = document.createElement('div');
            div.className = 'mb-2 p-2 bg-terminal/5 border border-terminal/20 cursor-pointer hover:bg-terminal/10';
            div.onclick = () => showWorkAreaDetails(area, info);
            
            const percentage = info.percentage.toFixed(1);
            const barWidth = Math.min(percentage, 100);
            
            div.innerHTML = `
                <div class="flex justify-between items-center text-[10px] mb-1">
                    <span class="text-terminal">${area.replace(/_/g, ' ').toUpperCase()}</span>
                    <span class="font-bold">${info.count} (${percentage}%)</span>
                </div>
                <div class="w-full bg-black border border-terminal/30 h-2">
                    <div class="bg-terminal h-full transition-all duration-500" style="width: ${barWidth}%"></div>
                </div>
                ${info.next_scheduled ? `
                    <div class="text-[9px] text-terminal-dim mt-1">
                        Next: ${new Date(info.next_scheduled).toLocaleString()}
                    </div>
                ` : ''}
            `;
            
            tallyDiv.appendChild(div);
        });
    } catch (error) {
        console.error('Error loading work distribution:', error);
    }
}

// Load and display projects with details
async function loadProjects() {
    try {
        const projects = [
            'davy-jones-intern',
            'saylormemes',
            'the-flying-dutchman-theme',
            'adw'
        ];
        
        const projectsList = document.getElementById('projects-list');
        projectsList.innerHTML = '';
        
        for (const project of projects) {
            const response = await fetch(`/api/v4/project/${project}`);
            const details = await response.json();
            
            if (!details.error) {
                const div = document.createElement('div');
                div.className = 'p-2 bg-terminal/5 border border-terminal/20 mb-1 cursor-pointer hover:bg-terminal/10';
                div.onclick = () => showProjectDetails(project, details);
                
                const sizeInMB = (details.size / 1024 / 1024).toFixed(1);
                
                div.innerHTML = `
                    <div class="flex justify-between items-center">
                        <span class="text-[10px] font-bold text-terminal">${project}</span>
                        <span class="text-[9px] text-terminal-dim">${details.file_count} files</span>
                    </div>
                    <div class="text-[9px] text-terminal-dim mt-1">
                        Size: ${sizeInMB}MB | 
                        ${details.test_coverage ? `Coverage: ${details.test_coverage}%` : 'No coverage'}
                    </div>
                `;
                
                projectsList.appendChild(div);
            }
        }
    } catch (error) {
        console.error('Error loading projects:', error);
    }
}

// Load workflows with status
async function loadWorkflows() {
    try {
        const workflows = [
            'ticket_enrichment',
            'performance_optimization',
            'project_development'
        ];
        
        const workflowsList = document.getElementById('workflows-list');
        workflowsList.innerHTML = '';
        
        for (const workflow of workflows) {
            const response = await fetch(`/api/v4/workflow/${workflow}`);
            const data = await response.json();
            
            if (!data.error) {
                const div = document.createElement('div');
                div.className = 'p-2 bg-terminal/5 border border-terminal/20 mb-1 cursor-pointer hover:bg-terminal/10';
                div.onclick = () => showWorkflowDetails(workflow, data);
                
                div.innerHTML = `
                    <div class="flex justify-between items-center">
                        <span class="text-[10px] font-bold text-terminal">${data.name}</span>
                        <span class="text-[9px] text-green-500">ACTIVE</span>
                    </div>
                    <div class="text-[9px] text-terminal-dim mt-1">
                        ${data.schedule}
                    </div>
                `;
                
                workflowsList.appendChild(div);
            }
        }
    } catch (error) {
        console.error('Error loading workflows:', error);
    }
}

// Load system anomalies
async function loadAnomalies() {
    try {
        const response = await fetch('/api/v4/anomalies');
        const data = await response.json();
        
        const anomaliesList = document.getElementById('anomalies-list');
        anomaliesList.innerHTML = '';
        
        if (data.anomalies && data.anomalies.length > 0) {
            data.anomalies.forEach(anomaly => {
                const div = document.createElement('div');
                div.className = 'p-2 bg-red-900/20 border border-red-500/30 mb-1';
                
                const severityColor = {
                    'critical': 'text-red-500',
                    'warning': 'text-yellow-500',
                    'low': 'text-terminal-dim'
                }[anomaly.severity] || 'text-terminal';
                
                div.innerHTML = `
                    <div class="flex items-center justify-between">
                        <span class="text-[10px] ${severityColor} font-bold">
                            ${anomaly.severity.toUpperCase()}
                        </span>
                        <button onclick="fixAnomaly('${anomaly.type}')" 
                            class="text-[9px] px-2 py-0.5 border border-terminal hover:bg-terminal/20">
                            FIX
                        </button>
                    </div>
                    <div class="text-[9px] text-terminal-dim mt-1">${anomaly.message}</div>
                `;
                
                anomaliesList.appendChild(div);
            });
        } else {
            anomaliesList.innerHTML = '<div class="text-[10px] text-terminal-dim">No anomalies detected ✅</div>';
        }
    } catch (error) {
        console.error('Error loading anomalies:', error);
    }
}

// Load integration status
async function loadIntegrations() {
    try {
        const response = await fetch('/api/v4/integrations');
        const data = await response.json();
        
        const integrationsList = document.getElementById('integrations-list');
        integrationsList.innerHTML = '';
        
        Object.entries(data).forEach(([key, integration]) => {
            const div = document.createElement('div');
            div.className = 'flex justify-between items-center mb-1 p-1';
            
            const statusColor = integration.status === 'active' || integration.status === 'configured' ? 
                'text-terminal' : 'text-red-500';
            
            div.innerHTML = `
                <span class="text-[10px] text-terminal-dim">${integration.name}:</span>
                <span class="text-[10px] ${statusColor} uppercase">${integration.status}</span>
            `;
            
            integrationsList.appendChild(div);
        });
    } catch (error) {
        console.error('Error loading integrations:', error);
    }
}

// Load optimization suggestions
async function loadOptimizations() {
    try {
        const response = await fetch('/api/v4/optimizations');
        const data = await response.json();
        
        const optimizationsList = document.getElementById('optimization-suggestions');
        optimizationsList.innerHTML = '';
        
        if (data.suggestions && data.suggestions.length > 0) {
            data.suggestions.forEach(suggestion => {
                const div = document.createElement('div');
                div.className = 'p-2 bg-terminal/5 border border-terminal/20 mb-1';
                
                const priorityColor = {
                    'high': 'text-red-500',
                    'medium': 'text-yellow-500',
                    'low': 'text-terminal-dim'
                }[suggestion.priority] || 'text-terminal';
                
                div.innerHTML = `
                    <div class="flex justify-between items-center">
                        <span class="text-[10px] ${priorityColor}">
                            ${suggestion.priority.toUpperCase()} - ${suggestion.category}
                        </span>
                        <button onclick="executeOptimization('${suggestion.action}')" 
                            class="text-[9px] px-2 py-0.5 border border-terminal hover:bg-terminal/20">
                            EXECUTE
                        </button>
                    </div>
                    <div class="text-[9px] text-terminal-dim mt-1">${suggestion.suggestion}</div>
                `;
                
                optimizationsList.appendChild(div);
            });
        } else {
            optimizationsList.innerHTML = '<div class="text-[10px] text-terminal-dim">System is optimized ✅</div>';
        }
    } catch (error) {
        console.error('Error loading optimizations:', error);
    }
}

// Load performance metrics
async function loadPerformanceMetrics() {
    try {
        const response = await fetch('/api/v4/performance-metrics');
        const data = await response.json();
        
        if (data && data.system) {
            document.getElementById('avg-response-time').textContent = 
                data.system.cpu_percent ? `${data.system.cpu_percent.toFixed(1)}%` : '--';
            
            // Calculate request rate from network connections
            const reqRate = data.system.network_connections || 0;
            document.getElementById('request-rate').textContent = reqRate.toString();
            
            // Error rate placeholder
            document.getElementById('error-rate').textContent = '0%';
        }
    } catch (error) {
        console.error('Error loading performance metrics:', error);
    }
}

// Show work area details modal
function showWorkAreaDetails(area, info) {
    const modal = document.getElementById('logModal');
    const content = document.getElementById('modal-log-content');
    
    content.innerHTML = `
        <h3 class="text-terminal text-sm font-bold mb-3">${area.replace(/_/g, ' ').toUpperCase()} DETAILS</h3>
        <div class="space-y-2">
            <div class="flex justify-between">
                <span class="text-terminal-dim">Sessions Completed:</span>
                <span class="text-terminal font-bold">${info.count}</span>
            </div>
            <div class="flex justify-between">
                <span class="text-terminal-dim">Work Percentage:</span>
                <span class="text-terminal font-bold">${info.percentage.toFixed(1)}%</span>
            </div>
            ${info.last_run ? `
                <div class="flex justify-between">
                    <span class="text-terminal-dim">Last Run:</span>
                    <span class="text-terminal">${new Date(info.last_run).toLocaleString()}</span>
                </div>
            ` : ''}
            ${info.next_scheduled ? `
                <div class="flex justify-between">
                    <span class="text-terminal-dim">Next Scheduled:</span>
                    <span class="text-terminal">${new Date(info.next_scheduled).toLocaleString()}</span>
                </div>
            ` : ''}
        </div>
        <div class="mt-4 flex gap-2">
            <button onclick="triggerBarbossa('${area}')" 
                class="px-3 py-1 border border-terminal bg-terminal/10 hover:bg-terminal/20 text-xs">
                TRIGGER NOW
            </button>
            <button onclick="closeModal()" 
                class="px-3 py-1 border border-terminal/50 hover:bg-terminal/10 text-xs">
                CLOSE
            </button>
        </div>
    `;
    
    modal.style.display = 'block';
}

// Show project details modal
function showProjectDetails(project, details) {
    const modal = document.getElementById('logModal');
    const content = document.getElementById('modal-log-content');
    
    const sizeInMB = (details.size / 1024 / 1024).toFixed(2);
    
    content.innerHTML = `
        <h3 class="text-terminal text-sm font-bold mb-3">${project.toUpperCase()} PROJECT</h3>
        <div class="space-y-2">
            <div class="flex justify-between">
                <span class="text-terminal-dim">Files:</span>
                <span class="text-terminal font-bold">${details.file_count}</span>
            </div>
            <div class="flex justify-between">
                <span class="text-terminal-dim">Size:</span>
                <span class="text-terminal font-bold">${sizeInMB} MB</span>
            </div>
            ${details.test_coverage !== null ? `
                <div class="flex justify-between">
                    <span class="text-terminal-dim">Test Coverage:</span>
                    <span class="text-terminal font-bold">${details.test_coverage}%</span>
                </div>
            ` : ''}
            ${details.dependencies && details.dependencies.prod ? `
                <div class="flex justify-between">
                    <span class="text-terminal-dim">Dependencies:</span>
                    <span class="text-terminal">${details.dependencies.prod} prod, ${details.dependencies.dev} dev</span>
                </div>
            ` : ''}
        </div>
        ${details.recent_changes && details.recent_changes.length > 0 ? `
            <div class="mt-3">
                <h4 class="text-terminal-dim text-xs mb-2">Recent Changes:</h4>
                <div class="text-[10px] font-mono space-y-1 max-h-40 overflow-y-auto">
                    ${details.recent_changes.slice(0, 5).map(change => 
                        `<div class="text-terminal-dim">${change}</div>`
                    ).join('')}
                </div>
            </div>
        ` : ''}
        <div class="mt-4 flex gap-2">
            <button onclick="triggerBarbossa('personal_projects', 'Work on ${project}')" 
                class="px-3 py-1 border border-terminal bg-terminal/10 hover:bg-terminal/20 text-xs">
                WORK ON PROJECT
            </button>
            <button onclick="closeModal()" 
                class="px-3 py-1 border border-terminal/50 hover:bg-terminal/10 text-xs">
                CLOSE
            </button>
        </div>
    `;
    
    modal.style.display = 'block';
}

// Show workflow details modal
function showWorkflowDetails(workflow, data) {
    const modal = document.getElementById('logModal');
    const content = document.getElementById('modal-log-content');
    
    let detailsHtml = '';
    
    if (workflow === 'ticket_enrichment' && data.stats) {
        detailsHtml = `
            <div class="space-y-2 mt-3">
                <div class="flex justify-between">
                    <span class="text-terminal-dim">Total Enriched:</span>
                    <span class="text-terminal font-bold">${data.stats.statistics?.total_enriched || 0}</span>
                </div>
                <div class="flex justify-between">
                    <span class="text-terminal-dim">GitHub Issues:</span>
                    <span class="text-terminal">${data.stats.statistics?.github_issues || 0}</span>
                </div>
                ${data.stats.last_run ? `
                    <div class="flex justify-between">
                        <span class="text-terminal-dim">Last Run:</span>
                        <span class="text-terminal">${new Date(data.stats.last_run).toLocaleString()}</span>
                    </div>
                ` : ''}
            </div>
        `;
    } else if (workflow === 'performance_optimization' && data.metrics) {
        detailsHtml = `
            <div class="space-y-2 mt-3">
                <div class="flex justify-between">
                    <span class="text-terminal-dim">CPU Usage:</span>
                    <span class="text-terminal font-bold">${data.metrics.system?.cpu_percent || '--'}%</span>
                </div>
                <div class="flex justify-between">
                    <span class="text-terminal-dim">Memory Usage:</span>
                    <span class="text-terminal font-bold">${data.metrics.system?.memory_percent || '--'}%</span>
                </div>
                <div class="flex justify-between">
                    <span class="text-terminal-dim">Disk Usage:</span>
                    <span class="text-terminal font-bold">${data.metrics.system?.disk_usage_percent || '--'}%</span>
                </div>
            </div>
        `;
    }
    
    content.innerHTML = `
        <h3 class="text-terminal text-sm font-bold mb-3">${data.name.toUpperCase()}</h3>
        <div class="text-terminal-dim text-xs mb-2">${data.schedule}</div>
        ${detailsHtml}
        <div class="mt-4 flex gap-2">
            ${workflow === 'ticket_enrichment' ? `
                <button onclick="enrichTickets()" 
                    class="px-3 py-1 border border-terminal bg-terminal/10 hover:bg-terminal/20 text-xs">
                    RUN NOW
                </button>
            ` : ''}
            <button onclick="closeModal()" 
                class="px-3 py-1 border border-terminal/50 hover:bg-terminal/10 text-xs">
                CLOSE
            </button>
        </div>
    `;
    
    modal.style.display = 'block';
}

// Trigger Barbossa work
async function triggerBarbossa(area, customPrompt = null) {
    try {
        const response = await fetch('/api/v4/trigger-work', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ area, prompt: customPrompt })
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert(`✅ ${result.message}\nSession ID: ${result.session_id}`);
            setTimeout(() => {
                loadWorkDistribution();
            }, 2000);
        } else {
            alert(`❌ Error: ${result.error}`);
        }
    } catch (error) {
        alert(`❌ Error: ${error.message}`);
    }
}

// Enrich tickets manually
async function enrichTickets() {
    try {
        const response = await fetch('/api/v4/enrich-tickets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert(`✅ Ticket Enrichment Complete\n` +
                  `Enriched: ${result.results.enriched}\n` +
                  `Failed: ${result.results.failed}\n` +
                  `Skipped: ${result.results.skipped}`);
        } else {
            alert(`❌ Error: ${result.error}`);
        }
    } catch (error) {
        alert(`❌ Error: ${error.message}`);
    }
}

// Execute optimization
async function executeOptimization(action) {
    if (!confirm(`Execute optimization: ${action}?`)) {
        return;
    }
    
    try {
        const response = await fetch('/api/v4/execute-optimization', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action })
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert(`✅ ${result.message}`);
            setTimeout(() => {
                loadOptimizations();
            }, 2000);
        } else {
            alert(`❌ Error: ${result.message}`);
        }
    } catch (error) {
        alert(`❌ Error: ${error.message}`);
    }
}

// Fix anomaly
async function fixAnomaly(type) {
    const fixes = {
        'high_cpu': 'Investigate and optimize high CPU usage processes',
        'high_memory': 'Clear memory and restart resource-intensive services',
        'low_disk': 'Clean up disk space by removing old logs and cache',
        'zombie_process': 'Kill zombie processes',
        'high_errors': 'Investigate and fix error sources'
    };
    
    const prompt = fixes[type] || 'Fix system anomaly';
    
    await triggerBarbossa('infrastructure', prompt);
}

// Close modal
function closeModal() {
    document.getElementById('logModal').style.display = 'none';
}

// Initialize event handlers
function initEventHandlers() {
    // Close modal on click outside
    window.onclick = function(event) {
        const modal = document.getElementById('logModal');
        if (event.target === modal) {
            closeModal();
        }
    }
    
    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeModal();
        }
        if (e.key === 'r' && e.ctrlKey) {
            e.preventDefault();
            refreshAll();
        }
    });
}

// Refresh all data
async function refreshAll() {
    console.log('Refreshing all data...');
    await Promise.all([
        loadWorkDistribution(),
        loadProjects(),
        loadWorkflows(),
        loadAnomalies(),
        loadIntegrations(),
        loadOptimizations(),
        loadPerformanceMetrics()
    ]);
}

// Start auto-refresh
function startAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
    
    refreshInterval = setInterval(() => {
        refreshAll();
    }, 30000); // Refresh every 30 seconds
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', initEnhancedDashboard);