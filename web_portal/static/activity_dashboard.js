/**
 * Enhanced Activity Dashboard for Barbossa Web Portal
 * Provides real-time activity tracking and visualization
 */

class ActivityDashboard {
    constructor() {
        this.refreshInterval = 30000; // 30 seconds
        this.timeRange = 24; // hours
        this.init();
    }

    async init() {
        // Setup event listeners
        this.setupEventListeners();
        
        // Initial load
        await this.loadAllData();
        
        // Setup auto-refresh
        setInterval(() => this.loadAllData(), this.refreshInterval);
    }

    setupEventListeners() {
        // Time range selector
        const timeRangeSelect = document.getElementById('time-range-select');
        if (timeRangeSelect) {
            timeRangeSelect.addEventListener('change', (e) => {
                this.timeRange = parseInt(e.target.value);
                this.loadAllData();
            });
        }

        // Refresh button
        const refreshBtn = document.getElementById('refresh-activity');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadAllData());
        }
    }

    async loadAllData() {
        try {
            // Show loading state
            this.showLoading(true);

            // Load all data in parallel
            const [summary, timeline, workAreas, insights] = await Promise.all([
                this.loadSummary(),
                this.loadTimeline(),
                this.loadWorkAreas(),
                this.loadInsights()
            ]);

            // Update UI
            this.updateSummary(summary);
            this.updateTimeline(timeline);
            this.updateWorkAreas(workAreas);
            this.updateInsights(insights);

        } catch (error) {
            console.error('Error loading activity data:', error);
            this.showError('Failed to load activity data');
        } finally {
            this.showLoading(false);
        }
    }

    async loadSummary() {
        const response = await fetch(`/api/activity/summary?hours=${this.timeRange}`);
        return await response.json();
    }

    async loadTimeline() {
        const response = await fetch(`/api/activity/timeline?hours=${this.timeRange}&limit=50`);
        return await response.json();
    }

    async loadWorkAreas() {
        const response = await fetch(`/api/activity/work-areas?hours=${this.timeRange}`);
        return await response.json();
    }

    async loadInsights() {
        const response = await fetch(`/api/activity/insights?hours=${this.timeRange}`);
        return await response.json();
    }

    updateSummary(data) {
        // Update summary cards
        const summaryContainer = document.getElementById('activity-summary');
        if (!summaryContainer) return;

        summaryContainer.innerHTML = `
            <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                <div class="stat-card">
                    <div class="stat-value">${data.total_executions || 0}</div>
                    <div class="stat-label">Executions</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${data.files_modified || 0}</div>
                    <div class="stat-label">Files Modified</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${data.commits_made || 0}</div>
                    <div class="stat-label">Commits</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${data.tests_run || 0}</div>
                    <div class="stat-label">Tests Run</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${data.errors_fixed || 0}</div>
                    <div class="stat-label">Errors Fixed</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${data.tickets_enriched || 0}</div>
                    <div class="stat-label">Tickets Enriched</div>
                </div>
            </div>
            <div class="mt-4 text-center">
                <span class="text-sm text-gray-600">Current Focus:</span>
                <span class="ml-2 font-semibold">${data.current_focus || 'General Development'}</span>
            </div>
        `;
    }

    updateTimeline(data) {
        const timelineContainer = document.getElementById('activity-timeline');
        if (!timelineContainer) return;

        const timeline = data.timeline || [];
        
        if (timeline.length === 0) {
            timelineContainer.innerHTML = '<p class="text-gray-500">No recent activity</p>';
            return;
        }

        const timelineHTML = timeline.map(event => `
            <div class="timeline-item">
                <div class="timeline-icon">${event.icon || '•'}</div>
                <div class="timeline-content">
                    <div class="timeline-time">${event.time}</div>
                    <div class="timeline-description">
                        <span class="timeline-category">${event.category}</span>
                        ${this.escapeHtml(event.description)}
                    </div>
                </div>
            </div>
        `).join('');

        timelineContainer.innerHTML = `
            <div class="timeline">
                ${timelineHTML}
            </div>
        `;
    }

    updateWorkAreas(data) {
        const workAreasContainer = document.getElementById('work-areas');
        if (!workAreasContainer) return;

        const areas = Object.entries(data).sort((a, b) => b[1].count - a[1].count);
        
        const workAreasHTML = areas.map(([area, info]) => {
            const percentage = this.calculatePercentage(info.count, areas);
            
            const recentTasksHTML = info.recent_tasks.map(task => `
                <li class="text-sm text-gray-600">
                    <span class="text-xs text-gray-400">${task.time}</span>
                    ${this.escapeHtml(task.description)}
                </li>
            `).join('');

            return `
                <div class="work-area-card">
                    <div class="work-area-header">
                        <span class="work-area-icon">${info.icon}</span>
                        <span class="work-area-name">${this.formatAreaName(area)}</span>
                        <span class="work-area-count">${info.count} activities</span>
                    </div>
                    <div class="work-area-progress">
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${percentage}%"></div>
                        </div>
                    </div>
                    ${recentTasksHTML ? `
                        <div class="work-area-tasks">
                            <ul class="mt-2 space-y-1">
                                ${recentTasksHTML}
                            </ul>
                        </div>
                    ` : ''}
                </div>
            `;
        }).join('');

        workAreasContainer.innerHTML = workAreasHTML;
    }

    updateInsights(data) {
        const insightsContainer = document.getElementById('activity-insights');
        if (!insightsContainer) return;

        const productivityClass = data.productivity_score > 70 ? 'text-green-600' : 
                                 data.productivity_score > 40 ? 'text-yellow-600' : 'text-red-600';

        const achievementsHTML = (data.achievements || []).map(achievement => 
            `<li class="achievement-item">✅ ${this.escapeHtml(achievement)}</li>`
        ).join('');

        const recommendationsHTML = (data.recommendations || []).map(rec => 
            `<li class="recommendation-item">💡 ${this.escapeHtml(rec)}</li>`
        ).join('');

        const focusAreasHTML = (data.focus_areas || []).map(area => 
            `<div class="focus-area">
                <span class="focus-area-name">${area.area}</span>
                <span class="focus-area-percentage">${area.percentage}%</span>
            </div>`
        ).join('');

        insightsContainer.innerHTML = `
            <div class="insights-grid">
                <div class="insight-card">
                    <h4 class="insight-title">Productivity Score</h4>
                    <div class="productivity-score ${productivityClass}">
                        ${data.productivity_score || 0}/100
                    </div>
                    <div class="productivity-bar">
                        <div class="productivity-fill" style="width: ${data.productivity_score}%"></div>
                    </div>
                </div>

                <div class="insight-card">
                    <h4 class="insight-title">Most Active Period</h4>
                    <div class="active-period">
                        ${data.most_active_period?.period || 'N/A'}
                        <span class="text-sm text-gray-500">
                            (${data.most_active_period?.count || 0} activities)
                        </span>
                    </div>
                </div>

                ${focusAreasHTML ? `
                <div class="insight-card">
                    <h4 class="insight-title">Focus Areas</h4>
                    <div class="focus-areas">
                        ${focusAreasHTML}
                    </div>
                </div>
                ` : ''}

                ${achievementsHTML ? `
                <div class="insight-card">
                    <h4 class="insight-title">Recent Achievements</h4>
                    <ul class="achievements-list">
                        ${achievementsHTML}
                    </ul>
                </div>
                ` : ''}

                ${recommendationsHTML ? `
                <div class="insight-card">
                    <h4 class="insight-title">Recommendations</h4>
                    <ul class="recommendations-list">
                        ${recommendationsHTML}
                    </ul>
                </div>
                ` : ''}
            </div>
        `;
    }

    calculatePercentage(count, areas) {
        const total = areas.reduce((sum, [_, info]) => sum + info.count, 0);
        return total > 0 ? Math.round((count / total) * 100) : 0;
    }

    formatAreaName(area) {
        return area.replace(/_/g, ' ')
                  .split(' ')
                  .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                  .join(' ');
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showLoading(show) {
        const loader = document.getElementById('activity-loader');
        if (loader) {
            loader.style.display = show ? 'block' : 'none';
        }
    }

    showError(message) {
        const errorContainer = document.getElementById('activity-error');
        if (errorContainer) {
            errorContainer.innerHTML = `
                <div class="alert alert-error">
                    ${this.escapeHtml(message)}
                </div>
            `;
            setTimeout(() => {
                errorContainer.innerHTML = '';
            }, 5000);
        }
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('activity-dashboard')) {
        window.activityDashboard = new ActivityDashboard();
    }
});