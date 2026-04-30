class SchedulerApp {
    constructor() {
        this.sessionId = null;
        this.chart = null;
        this.orderChart = null;
        this.currentChart = 'machine';
        this.phase15Data = null;
        this.scheduleData = null;
        this.init();
    }

    init() {
        // Bind upload tab events
        document.querySelectorAll('.upload-tab').forEach(tab => {
            tab.addEventListener('click', (e) => this.switchUploadTab(e.target.dataset.phase));
        });

        // Bind main action buttons
        document.getElementById('upload-btn').addEventListener('click', () => this.uploadFiles());
        document.getElementById('next-btn').addEventListener('click', () => this.showNextSection());
        document.getElementById('download-schedule-btn').addEventListener('click', () => this.downloadSchedule());
        document.getElementById('download-chart-btn').addEventListener('click', () => this.downloadChart());
        document.getElementById('reset-btn').addEventListener('click', () => this.resetApp());

        // Bind chart tab events
        document.querySelectorAll('.chart-tab').forEach(tab => {
            tab.addEventListener('click', (e) => this.switchChartTab(e.target.dataset.chart));
        });

        // Disable action buttons initially
        this.setActionButtonsDisabled(true);
    }

    switchUploadTab(phase) {
        // Update tab active states
        document.querySelectorAll('.upload-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.phase === phase);
        });

        // Show/hide panels
        document.getElementById('core-panel').style.display = phase === 'core' ? 'block' : 'none';
        document.getElementById('phase15-panel').style.display = phase === 'phase15' ? 'block' : 'none';
        document.getElementById('phase3-panel').style.display = phase === 'phase3' ? 'block' : 'none';
    }

    setActionButtonsDisabled(disabled) {
        const downloadBtn = document.getElementById('download-schedule-btn');
        const downloadChartBtn = document.getElementById('download-chart-btn');
        const resetBtn = document.getElementById('reset-btn');

        if (downloadBtn) downloadBtn.disabled = disabled;
        if (downloadChartBtn) downloadChartBtn.disabled = disabled;
        if (resetBtn) resetBtn.disabled = disabled;
    }

    updateProgressStep(stepName, status) {
        const stepIdMap = {
            'Upload': 'step-upload',
            'Validation': 'step-validation',
            'Job Building': 'step-jobs',
            'Scheduling': 'step-scheduling',
            'Verification': 'step-verification',
            'KPI Calculation': 'step-kpi',
            'Visualization': 'step-visualization'
        };

        const elementId = stepIdMap[stepName];
        if (!elementId) return;

        const stepElement = document.getElementById(elementId);
        if (stepElement) {
            stepElement.className = 'step';
            stepElement.classList.add(status);
        }
    }

    async uploadFiles() {
        const machinesFile = document.getElementById('machines-file').files[0];
        const productsFile = document.getElementById('products-file').files[0];
        const routingFile = document.getElementById('routing-file').files[0];
        const ordersFile = document.getElementById('orders-file').files[0];

        if (!machinesFile || !productsFile || !routingFile || !ordersFile) {
            alert('Please select all four required CSV files.');
            return;
        }

        this.updateProgressStep('Upload', 'running');
        this.setActionButtonsDisabled(true);

        try {
            const formData = new FormData();
            formData.append('machines', machinesFile);
            formData.append('products', productsFile);
            formData.append('routing', routingFile);
            formData.append('orders', ordersFile);

            // Phase 1.5 optional files
            const calendarFile = document.getElementById('calendar-file').files[0];
            const setupFile = document.getElementById('setup-file').files[0];
            const sectionsFile = document.getElementById('sections-file').files[0];
            const buffersFile = document.getElementById('buffers-file').files[0];

            if (calendarFile) formData.append('machine_calendar', calendarFile);
            if (setupFile) formData.append('setup_matrix', setupFile);
            if (sectionsFile) formData.append('sections', sectionsFile);
            if (buffersFile) formData.append('buffers', buffersFile);

            // Phase 3 optional files
            const ordersMultiFile = document.getElementById('orders-multilevel-file').files[0];
            const orderLinksFile = document.getElementById('order-links-file').files[0];
            const bomFile = document.getElementById('bom-file').files[0];

            if (ordersMultiFile) formData.append('orders_multilevel', ordersMultiFile);
            if (orderLinksFile) formData.append('order_links', orderLinksFile);
            if (bomFile) formData.append('bom', bomFile);

            const response = await fetch('http://localhost:8000/upload', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.detail || 'Upload failed');
            }

            this.sessionId = result.session_id;
            this.phase15Data = result.phase15_summary || null;
            this.showValidationResults(result);
            this.updateProgressStep('Upload', 'success');
            this.updateProgressStep('Validation', 'running');

            if (result.validation_passed) {
                await this.processWorkflow();
                document.getElementById('next-btn').disabled = false;
            } else {
                this.updateProgressStep('Validation', 'error');
                this.setActionButtonsDisabled(false);
            }

        } catch (error) {
            console.error('Upload error:', error);
            this.showError('Upload failed: ' + error.message);
            this.updateProgressStep('Upload', 'error');
            this.setActionButtonsDisabled(false);
        }
    }

    showValidationResults(result) {
        const validationResults = document.getElementById('validation-results');

        if (result.validation_passed) {
            let html = `<p class="success-message">${result.validation_message}</p>`;

            if (result.phase15_summary) {
                html += this.formatPhase15Summary(result.phase15_summary);
            }
            if (result.phase3_summary) {
                html += this.formatPhase3Summary(result.phase3_summary);
            }

            validationResults.innerHTML = html;
        } else {
            validationResults.innerHTML = `
                <p class="error-message">${result.validation_message}</p>
            `;
        }
    }

    formatPhase3Summary(summary) {
        if (!summary) return '';
        let html = '<div style="margin-top: 15px;"><strong>Phase 3 Data Loaded:</strong><ul style="margin-top: 10px; padding-left: 20px;">';

        if (summary.orders_multilevel_uploaded) {
            html += '<li>Multi-Level Orders (hierarchical)</li>';
        }
        if (summary.order_links_uploaded) {
            html += '<li>Order Dependencies (parent-child)</li>';
        }
        if (summary.bom_uploaded) {
            html += '<li>Bill of Materials</li>';
        }

        html += '</ul></div>';
        return html;
    }

    formatPhase15Summary(summary) {
        if (!summary) return '';
        let html = '<div class="phase15-info-grid" style="margin-top: 15px;">';

        if (summary.machines_capacity) {
            const deps = Object.keys(summary.machines_capacity).join(', ');
            html += `
                <div class="phase15-info-card">
                    <h4>Machine Capacities</h4>
                    <p>Departments: ${deps}</p>
                </div>
            `;
        }

        if (summary.calendar_available !== undefined) {
            const pct = Math.round(summary.calendar_available * 100);
            html += `
                <div class="phase15-info-card">
                    <h4>Calendar Availability</h4>
                    <p>${pct}% available</p>
                </div>
            `;
        }

        if (summary.setup_transitions) {
            html += `
                <div class="phase15-info-card">
                    <h4>Setup Transitions</h4>
                    <p>${summary.setup_transitions.toLocaleString()} indexed</p>
                </div>
            `;
        }

        html += '</div>';
        return html;
    }

    async processWorkflow() {
        if (!this.sessionId) return;

        try {
            this.updateProgressStep('Validation', 'success');
            this.updateProgressStep('Job Building', 'running');

            const response = await fetch(`http://localhost:8000/process/${this.sessionId}`, {
                method: 'POST'
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Processing failed');
            }

            const result = await response.json();
            this.updateProgressStep('Job Building', 'success');
            this.updateProgressStep('Scheduling', 'running');

            await new Promise(resolve => setTimeout(resolve, 300));

            this.updateProgressStep('Scheduling', 'success');
            this.updateProgressStep('Verification', 'running');

            await new Promise(resolve => setTimeout(resolve, 200));

            this.updateProgressStep('Verification', 'success');
            this.updateProgressStep('KPI Calculation', 'running');

            await new Promise(resolve => setTimeout(resolve, 200));

            this.updateProgressStep('KPI Calculation', 'success');
            this.updateProgressStep('Visualization', 'running');

            await new Promise(resolve => setTimeout(resolve, 200));

            await this.loadAllResults();
            this.updateProgressStep('Visualization', 'success');

            this.setActionButtonsDisabled(false);

        } catch (error) {
            console.error('Processing error:', error);
            this.showError('Processing failed: ' + error.message);
            this.updateProgressStep('Job Building', 'error');
            this.updateProgressStep('Scheduling', 'error');
            this.updateProgressStep('Verification', 'error');
            this.updateProgressStep('KPI Calculation', 'error');
            this.updateProgressStep('Visualization', 'error');
            this.setActionButtonsDisabled(false);
        }
    }

    async loadAllResults() {
        if (!this.sessionId) return;

        try {
            const jobsResponse = await fetch(`http://localhost:8000/data/${this.sessionId}/jobs`);
            const jobsData = await jobsResponse.json();
            this.displayJobs(jobsData);

            const scheduleResponse = await fetch(`http://localhost:8000/data/${this.sessionId}/schedule`);
            const scheduleData = await scheduleResponse.json();
            this.scheduleData = scheduleData;
            this.displaySchedule(scheduleData);
            this.createGanttChart(scheduleData);
            this.createOrderGanttChart(scheduleData);

            const kpiResponse = await fetch(`http://localhost:8000/data/${this.sessionId}/kpi`);
            const kpiData = await kpiResponse.json();
            this.displayKPIs(kpiData);

            const verificationResponse = await fetch(`http://localhost:8000/data/${this.sessionId}/verification`);
            const verificationData = await verificationResponse.json();
            this.displayVerification(verificationData);

            // Show dependency section if we have order links
            if (this.phase15Data && this.phase15Data.order_links_uploaded) {
                this.showDependencySection();
            }

        } catch (error) {
            console.error('Error loading results:', error);
            this.showError('Failed to load results: ' + error.message);
        }
    }

    displayJobs(jobsData) {
        const container = document.getElementById('jobs-results');
        if (jobsData.length === 0) {
            container.innerHTML = '<div class="empty-state"><p>No job data available.</p></div>';
            return;
        }

        const isPhase2 = jobsData[0].candidate_machines !== undefined;

        let tableHTML = `
            <table class="results-table">
                <thead>
                    <tr>
                        ${isPhase2 ? `
                            <th>Order ID</th>
                            <th>Product ID</th>
                            <th>Operation</th>
                            <th>Candidates</th>
                            <th>Primary Machine</th>
                        ` : `
                            <th>Order ID</th>
                            <th>Product ID</th>
                            <th>Operation</th>
                            <th>Machine</th>
                            <th>Proc Time</th>
                        `}
                    </tr>
                </thead>
                <tbody>
        `;

        const displayData = jobsData.slice(0, 15);
        displayData.forEach(job => {
            if (isPhase2) {
                const candidates = job.candidate_machines;
                const primaryMachine = candidates.find(c => c.is_primary) || candidates[0];
                const altCount = candidates.filter(c => !c.is_primary).length;

                tableHTML += `
                    <tr>
                        <td>${job.order_id}</td>
                        <td>${job.product_id}</td>
                        <td>Op ${job.operation_seq}</td>
                        <td>${candidates.length} ${altCount > 0 ? `(+${altCount} alt)` : ''}</td>
                        <td>${primaryMachine.machine_id} (${primaryMachine.proc_time}min)</td>
                    </tr>
                `;
            } else {
                tableHTML += `
                    <tr>
                        <td>${job.order_id}</td>
                        <td>${job.product_id}</td>
                        <td>Op ${job.operation_seq}</td>
                        <td>${job.machine_id}</td>
                        <td>${job.proc_time_min}min</td>
                    </tr>
                `;
            }
        });

        tableHTML += '</tbody></table>';

        if (jobsData.length > 15) {
            tableHTML += `<p style="margin-top: 10px; color: var(--text-muted); font-size: 0.85rem;">Showing first 15 of ${jobsData.length} operations</p>`;
        }

        container.innerHTML = tableHTML;
    }

    displaySchedule(scheduleData) {
        const container = document.getElementById('scheduling-results');
        if (scheduleData.length === 0) {
            container.innerHTML = '<div class="empty-state"><p>No schedule data available.</p></div>';
            return;
        }

        let tableHTML = `
            <table class="results-table">
                <thead>
                    <tr>
                        <th>Order ID</th>
                        <th>Operation</th>
                        <th>Machine</th>
                        <th>Start Time</th>
                        <th>End Time</th>
                    </tr>
                </thead>
                <tbody>
        `;

        const displayData = scheduleData.slice(0, 15);
        displayData.forEach(op => {
            const start = new Date(op.start).toLocaleString();
            const end = new Date(op.end).toLocaleString();

            tableHTML += `
                <tr>
                    <td>${op.order_id}</td>
                    <td>Op ${op.operation_seq}</td>
                    <td>${op.machine_id}</td>
                    <td>${start}</td>
                    <td>${end}</td>
                </tr>
            `;
        });

        tableHTML += '</tbody></table>';

        if (scheduleData.length > 15) {
            tableHTML += `<p style="margin-top: 10px; color: var(--text-muted); font-size: 0.85rem;">Showing first 15 of ${scheduleData.length} operations</p>`;
        }

        container.innerHTML = tableHTML;
    }

    displayKPIs(kpiData) {
        const container = document.getElementById('kpi-results');
        if (!kpiData || Object.keys(kpiData).length === 0) {
            container.innerHTML = '<div class="empty-state"><p>No KPI data available.</p></div>';
            return;
        }

        let html = '<div class="kpi-cards">';

        // Core KPIs
        const coreItems = [
            { label: 'Total Orders', value: kpiData.total_orders, icon: '📋' },
            { label: 'On-Time Orders', value: kpiData.on_time_orders, icon: '✅', color: kpiData.late_orders === 0 ? '#10b981' : '' },
            { label: 'Late Orders', value: kpiData.late_orders, icon: '⏰', color: kpiData.late_orders > 0 ? '#ef4444' : '' },
            { label: 'Avg Delay', value: `${kpiData.avg_delay.toFixed(1)}h`, icon: '⏳', color: kpiData.avg_delay < 0 ? '#10b981' : '' },
            { label: 'Max Delay', value: `${kpiData.max_delay.toFixed(1)}h`, icon: '📈', color: kpiData.max_delay > 0 ? '#ef4444' : '' }
        ];

        coreItems.forEach(item => {
            html += `
                <div class="kpi-card">
                    <span class="kpi-icon">${item.icon}</span>
                    <div class="kpi-content">
                        <div class="kpi-label">${item.label}</div>
                        <div class="kpi-value" style="${item.color ? `color: ${item.color}` : ''}">${item.value}</div>
                    </div>
                </div>
            `;
        });

        html += '</div>';

        // Phase 2 KPIs
        const phase2Items = [];
        if (kpiData.avg_utilization !== undefined) {
            phase2Items.push({
                label: 'Utilization',
                value: `${kpiData.avg_utilization.toFixed(1)}%`,
                icon: '⚡'
            });
        }
        if (kpiData.alt_machine_usage_pct !== undefined) {
            phase2Items.push({
                label: 'Alt Machine Usage',
                value: `${kpiData.alt_machine_usage_pct.toFixed(1)}%`,
                icon: '🔀'
            });
        }
        if (kpiData.avg_release_delay !== undefined) {
            phase2Items.push({
                label: 'Release Delay',
                value: `${kpiData.avg_release_delay.toFixed(1)}h`,
                icon: '📦'
            });
        }

        if (phase2Items.length > 0) {
            html += '<h4 style="margin: 20px 0 10px; color: var(--text-secondary); font-size: 0.9rem;">Phase 2 Metrics</h4>';
            html += '<div class="kpi-cards">';
            phase2Items.forEach(item => {
                html += `
                    <div class="kpi-card">
                        <span class="kpi-icon">${item.icon}</span>
                        <div class="kpi-content">
                            <div class="kpi-label">${item.label}</div>
                            <div class="kpi-value">${item.value}</div>
                        </div>
                    </div>
                `;
            });
            html += '</div>';
        }

        // Phase 3 KPIs
        const phase3Items = [];
        if (kpiData.dependency_delay !== undefined) {
            phase3Items.push({
                label: 'Dependency Delay',
                value: `${kpiData.dependency_delay.toFixed(1)}h`,
                icon: '🔗'
            });
        }
        if (kpiData.critical_path_length !== undefined) {
            phase3Items.push({
                label: 'Critical Path',
                value: kpiData.critical_path_length,
                icon: '⛓️'
            });
        }
        if (kpiData.component_service_level !== undefined) {
            phase3Items.push({
                label: 'Component Service Lvl',
                value: `${kpiData.component_service_level.toFixed(1)}%`,
                icon: '📊'
            });
        }
        if (kpiData.wip_explosion_factor !== undefined) {
            phase3Items.push({
                label: 'WIP Explosion Factor',
                value: kpiData.wip_explosion_factor.toFixed(2),
                icon: '💥'
            });
        }

        if (phase3Items.length > 0) {
            html += '<h4 style="margin: 20px 0 10px; color: var(--accent-success); font-size: 0.9rem;">Phase 3 Metrics</h4>';
            html += '<div class="kpi-cards">';
            phase3Items.forEach(item => {
                html += `
                    <div class="kpi-card">
                        <span class="kpi-icon">${item.icon}</span>
                        <div class="kpi-content">
                            <div class="kpi-label">${item.label}</div>
                            <div class="kpi-value">${item.value}</div>
                        </div>
                    </div>
                `;
            });
            html += '</div>';
        }

        container.innerHTML = html;
    }

    displayVerification(verificationData) {
        const container = document.getElementById('verification-results');
        if (verificationData.passed) {
            container.innerHTML = `
                <p class="success-message">Schedule verification passed</p>
                <ul style="margin-top: 10px; padding-left: 20px; color: var(--text-secondary);">
                    <li>No machine capacity violations</li>
                    <li>Operation sequence order respected</li>
                    <li>No downtime violations</li>
                </ul>
            `;
        } else {
            let errorsHTML = '<p class="error-message">Verification failed:</p><ul style="margin-top: 10px; padding-left: 20px; color: var(--accent-danger);">';
            verificationData.errors.forEach(error => {
                errorsHTML += `<li>${error}</li>`;
            });
            errorsHTML += '</ul>';
            container.innerHTML = errorsHTML;
        }
    }

    createGanttChart(scheduleData) {
        const ctx = document.getElementById('gantt-chart').getContext('2d');

        if (this.chart) {
            this.chart.destroy();
        }

        if (!scheduleData || scheduleData.length === 0) {
            return;
        }

        const machines = [...new Set(scheduleData.map(op => op.machine_id))].sort();
        const orders = [...new Set(scheduleData.map(op => op.order_id))];

        const colors = this.generateColors(orders.length);
        const orderColorMap = {};
        orders.forEach((order, index) => { orderColorMap[order] = colors[index % colors.length]; });

        const operationsByMachine = {};
        scheduleData.forEach(op => {
            if (!operationsByMachine[op.machine_id]) {
                operationsByMachine[op.machine_id] = [];
            }
            operationsByMachine[op.machine_id].push(op);
        });

        const chartData = { labels: machines, datasets: [] };

        orders.slice(0, 20).forEach(orderId => {
            const data = machines.map(machine => {
                const ops = operationsByMachine[machine] || [];
                const orderOps = ops.filter(op => op.order_id === orderId);
                return orderOps.reduce((total, op) => {
                    const start = new Date(op.start);
                    const end = new Date(op.end);
                    return total + (end - start) / (1000 * 60 * 60);
                }, 0);
            });

            chartData.datasets.push({
                label: orderId,
                data: data,
                backgroundColor: orderColorMap[orderId],
                stack: 'stack'
            });
        });

        this.chart = new Chart(ctx, {
            type: 'bar',
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: {
                    title: {
                        display: true,
                        text: 'Production Schedule - Machine View',
                        color: '#f1f5f9'
                    },
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        stacked: true,
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Duration (hours)',
                            color: '#94a3b8'
                        },
                        ticks: { color: '#94a3b8' },
                        grid: { color: 'rgba(255,255,255,0.1)' }
                    },
                    y: {
                        stacked: true,
                        ticks: { color: '#94a3b8' },
                        grid: { color: 'rgba(255,255,255,0.05)' }
                    }
                }
            }
        });
    }

    createOrderGanttChart(scheduleData) {
        const ctx = document.getElementById('order-gantt-chart').getContext('2d');

        if (this.orderChart) {
            this.orderChart.destroy();
        }

        if (!scheduleData || scheduleData.length === 0) {
            return;
        }

        const orders = [...new Set(scheduleData.map(op => op.order_id))].sort();
        const machines = [...new Set(scheduleData.map(op => op.machine_id))].sort();

        const colors = this.generateColors(machines.length);
        const machineColorMap = {};
        machines.forEach((machine, index) => { machineColorMap[machine] = colors[index % colors.length]; });

        const operationsByOrder = {};
        scheduleData.forEach(op => {
            if (!operationsByOrder[op.order_id]) {
                operationsByOrder[op.order_id] = [];
            }
            operationsByOrder[op.order_id].push(op);
        });

        const chartData = { labels: orders.slice(0, 30), datasets: [] };

        machines.forEach(machine => {
            const data = orders.slice(0, 30).map(order => {
                const ops = operationsByOrder[order] || [];
                const machineOps = ops.filter(op => op.machine_id === machine);
                return machineOps.reduce((total, op) => {
                    const start = new Date(op.start);
                    const end = new Date(op.end);
                    return total + (end - start) / (1000 * 60 * 60);
                }, 0);
            });

            chartData.datasets.push({
                label: machine,
                data: data,
                backgroundColor: machineColorMap[machine]
            });
        });

        this.orderChart = new Chart(ctx, {
            type: 'bar',
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: {
                    title: {
                        display: true,
                        text: 'Production Schedule - Order View',
                        color: '#f1f5f9'
                    },
                    legend: {
                        position: 'right',
                        labels: { color: '#94a3b8' }
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Duration (hours)',
                            color: '#94a3b8'
                        },
                        ticks: { color: '#94a3b8' },
                        grid: { color: 'rgba(255,255,255,0.1)' }
                    },
                    y: {
                        ticks: { color: '#94a3b8' },
                        grid: { color: 'rgba(255,255,255,0.05)' }
                    }
                }
            }
        });
    }

    generateColors(count) {
        const baseColors = [
            '#00d4ff', '#7c3aed', '#10b981', '#f59e0b', '#ef4444',
            '#ec4899', '#8b5cf6', '#06b6d4', '#84cc16', '#f97316'
        ];
        const colors = [];
        for (let i = 0; i < count; i++) {
            colors.push(baseColors[i % baseColors.length]);
        }
        return colors;
    }

    showDependencySection() {
        const depSection = document.getElementById('dependency-section');
        if (depSection) {
            depSection.style.display = 'block';
        }
    }

    switchChartTab(chartType) {
        this.currentChart = chartType;

        document.querySelectorAll('.chart-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.chart === chartType);
        });

        document.getElementById('machine-gantt-container').style.display = chartType === 'machine' ? 'block' : 'none';
        document.getElementById('order-gantt-container').style.display = chartType === 'order' ? 'block' : 'none';
    }

    showError(message) {
        alert('Error: ' + message);
    }

    showNextSection() {
        // Simple implementation - scroll to next section
        const sections = document.querySelectorAll('section');
        let foundCurrent = false;

        for (const section of sections) {
            if (foundCurrent) {
                section.scrollIntoView({ behavior: 'smooth' });
                break;
            }
            if (section.style.display !== 'none') {
                foundCurrent = true;
            }
        }
    }

    downloadSchedule() {
        if (!this.sessionId) return;
        window.location.href = `http://localhost:8000/download/${this.sessionId}/schedule`;
    }

    downloadChart() {
        const activeChart = this.currentChart === 'machine' ? this.chart : this.orderChart;
        if (!activeChart) {
            alert('No chart to download.');
            return;
        }

        const canvasId = this.currentChart === 'machine' ? 'gantt-chart' : 'order-gantt-chart';
        const canvas = document.getElementById(canvasId);
        const link = document.createElement('a');
        link.download = `${this.currentChart}_schedule.png`;
        link.href = canvas.toDataURL('image/png');
        link.click();
    }

    resetApp() {
        this.sessionId = null;
        this.currentChart = 'machine';
        this.phase15Data = null;
        this.scheduleData = null;

        if (this.chart) { this.chart.destroy(); this.chart = null; }
        if (this.orderChart) { this.orderChart.destroy(); this.orderChart = null; }

        // Reset file inputs
        document.getElementById('machines-file').value = '';
        document.getElementById('products-file').value = '';
        document.getElementById('routing-file').value = '';
        document.getElementById('orders-file').value = '';
        document.getElementById('calendar-file').value = '';
        document.getElementById('setup-file').value = '';
        document.getElementById('sections-file').value = '';
        document.getElementById('buffers-file').value = '';
        document.getElementById('orders-multilevel-file').value = '';
        document.getElementById('order-links-file').value = '';
        document.getElementById('bom-file').value = '';

        // Reset progress steps
        document.querySelectorAll('.progress-tracker .step').forEach(step => {
            step.className = 'step';
        });

        // Reset result containers
        document.getElementById('validation-results').innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">📋</span>
                <p>Awaiting file upload...</p>
            </div>
        `;
        document.getElementById('jobs-results').innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">⚙️</span>
                <p>Jobs will appear after successful validation</p>
            </div>
        `;
        document.getElementById('scheduling-results').innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">📅</span>
                <p>Schedule will be generated after job building</p>
            </div>
        `;
        document.getElementById('verification-results').innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">✅</span>
                <p>Verification results will appear here</p>
            </div>
        `;
        document.getElementById('kpi-results').innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">📊</span>
                <p>KPI metrics will appear after scheduling</p>
            </div>
        `;

        // Hide dependency section
        const depSection = document.getElementById('dependency-section');
        if (depSection) {
            depSection.style.display = 'none';
        }

        // Reset buttons
        document.getElementById('next-btn').disabled = true;
        this.setActionButtonsDisabled(true);

        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.schedulerApp = new SchedulerApp();
});
