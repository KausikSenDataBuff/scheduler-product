class SchedulerApp {
    constructor() {
        this.sessionId = null;
        this.chart = null;
        this.orderChart = null;
        this.sections = ['validation', 'jobs', 'scheduling', 'verification', 'kpi', 'visualization'];
        this.currentSectionIndex = -1;
        this.currentChart = 'machine';
        this.phase15Data = null;
        this.init();
    }

    init() {
        // Bind events
        document.getElementById('upload-btn').addEventListener('click', () => this.uploadFiles());
        document.getElementById('next-btn').addEventListener('click', () => this.showNextSection());
        document.getElementById('download-schedule-btn').addEventListener('click', () => this.downloadSchedule());
        document.getElementById('download-chart-btn').addEventListener('click', () => this.downloadChart());
        document.getElementById('reset-btn').addEventListener('click', () => this.resetApp());

        // Bind chart tab events
        document.querySelectorAll('.chart-tab').forEach(tab => {
            tab.addEventListener('click', (e) => this.switchChartTab(e.target.dataset.chart));
        });

        // Initially disable action buttons
        this.setActionButtonsDisabled(true);

        // Show progress tracker and upload section
        this.hideAllSections();
        document.getElementById('progress-section').style.display = 'block';
        document.getElementById('features-section').style.display = 'block';
        document.getElementById('upload-section').style.display = 'block';

        // Initialize current section tracker
        this.currentSectionIndex = -1;
        this.sections = ['upload', 'validation', 'jobs', 'scheduling', 'verification', 'kpi', 'visualization'];
    }

    hideAllSections() {
        const sections = document.querySelectorAll('main section');
        sections.forEach(section => {
            section.style.display = 'none';
        });
    }

    setActionButtonsDisabled(disabled) {
        document.getElementById('download-schedule-btn').disabled = disabled;
        document.getElementById('download-chart-btn').disabled = disabled;
        document.getElementById('reset-btn').disabled = disabled;
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
            if (status === 'running') {
                stepElement.classList.add('running');
            } else if (status === 'success') {
                stepElement.classList.add('success');
            } else if (status === 'error') {
                stepElement.classList.add('error');
            } else {
                stepElement.classList.add('pending');
            }
            if (status === 'success') {
                stepElement.textContent = '✅ ' + stepName;
            } else if (status === 'error') {
                stepElement.textContent = '❌ ' + stepName;
            } else if (status === 'running') {
                stepElement.textContent = '⏳ ' + stepName;
            } else {
                stepElement.textContent = '⬜ ' + stepName;
            }
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
            let html = `<p class="success-message">✓ ${result.validation_message}</p>`;
            if (result.phase15_summary) {
                html += this.formatPhase15Summary(result.phase15_summary);
            }
            validationResults.innerHTML = html;
        } else {
            validationResults.innerHTML = `
                <p class="error-message">✗ ${result.validation_message}</p>
            `;
        }
    }

    formatPhase15Summary(summary) {
        if (!summary) return '';
        let html = '<div class="phase15-info-grid" style="margin-top: 15px;">';

        if (summary.machines_capacity) {
            html += `
                <div class="phase15-info-card">
                    <h4>⚡ Machine Capacities</h4>
                    <p>Departments: ${Object.keys(summary.machines_capacity).join(', ')}</p>
                </div>
            `;
        }

        if (summary.calendar_available !== undefined) {
            const pct = Math.round(summary.calendar_available * 100);
            html += `
                <div class="phase15-info-card">
                    <h4>📅 Calendar Availability</h4>
                    <p>${pct}% available time</p>
                </div>
            `;
        }

        if (summary.setup_transitions) {
            html += `
                <div class="phase15-info-card">
                    <h4>🔧 Setup Transitions</h4>
                    <p>${summary.setup_transitions.toLocaleString()} indexed</p>
                </div>
            `;
        }

        if (summary.sections_count) {
            html += `
                <div class="phase15-info-card">
                    <h4>📦 Sections</h4>
                    <p>${summary.sections_count} sections defined</p>
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

            await new Promise(resolve => setTimeout(resolve, 500));

            this.updateProgressStep('Scheduling', 'success');
            this.updateProgressStep('Verification', 'running');

            await new Promise(resolve => setTimeout(resolve, 300));

            this.updateProgressStep('Verification', 'success');
            this.updateProgressStep('KPI Calculation', 'running');

            await new Promise(resolve => setTimeout(resolve, 300));

            this.updateProgressStep('KPI Calculation', 'success');
            this.updateProgressStep('Visualization', 'running');

            await new Promise(resolve => setTimeout(resolve, 300));

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
            this.displaySchedule(scheduleData);
            this.scheduleData = scheduleData;
            this.createGanttChart(scheduleData);
            this.createOrderGanttChart(scheduleData);

            const kpiResponse = await fetch(`http://localhost:8000/data/${this.sessionId}/kpi`);
            const kpiData = await kpiResponse.json();
            this.displayKPIs(kpiData);

            const verificationResponse = await fetch(`http://localhost:8000/data/${this.sessionId}/verification`);
            const verificationData = await verificationResponse.json();
            this.displayVerification(verificationData);

            this.showAllSections();

        } catch (error) {
            console.error('Error loading results:', error);
            this.showError('Failed to load results: ' + error.message);
        }
    }

    displayJobs(jobsData) {
        const container = document.getElementById('jobs-results');
        if (jobsData.length === 0) {
            container.innerHTML = '<p>No job data available.</p>';
            return;
        }

        // Check if Phase 2 format (candidate_machines) or Phase 1 format
        const isPhase2 = jobsData[0].candidate_machines !== undefined;

        if (isPhase2) {
            // Phase 2 format: show candidate machines info
            let tableHTML = `
                <table class="results-table">
                    <thead>
                        <tr>
                            <th>Order ID</th>
                            <th>Product ID</th>
                            <th>Operation Seq</th>
                            <th>Candidate Machines</th>
                            <th>Primary Machine</th>
                        </tr>
                    </thead>
                    <tbody>
            `;

            const displayData = jobsData.slice(0, 10);
            displayData.forEach(job => {
                const candidates = job.candidate_machines;
                const primaryMachine = candidates.find(c => c.is_primary) || candidates[0];
                const altCount = candidates.filter(c => !c.is_primary).length;
                const machineList = candidates.map(c => c.machine_id).join(', ');

                tableHTML += `
                    <tr>
                        <td>${job.order_id}</td>
                        <td>${job.product_id}</td>
                        <td>${job.operation_seq}</td>
                        <td title="${machineList}">${candidates.length} ${altCount > 0 ? `(+${altCount} alternate)` : ''}</td>
                        <td>${primaryMachine.machine_id} (${primaryMachine.proc_time}min${primaryMachine.efficiency !== 1.0 ? `, eff: ${primaryMachine.efficiency}` : ''})</td>
                    </tr>
                `;
            });

            tableHTML += `
                    </tbody>
                </table>
            `;

            if (jobsData.length > 10) {
                tableHTML += `<p><em>Showing first 10 of ${jobsData.length} operations</em></p>`;
            }

            container.innerHTML = tableHTML;
        } else {
            // Phase 1 format: individual machine assignment
            let tableHTML = `
                <table class="results-table">
                    <thead>
                        <tr>
                            <th>Order ID</th>
                            <th>Product ID</th>
                            <th>Operation Seq</th>
                            <th>Machine ID</th>
                            <th>Proc Time (min)</th>
                        </tr>
                    </thead>
                    <tbody>
            `;

            const displayData = jobsData.slice(0, 10);
            displayData.forEach(job => {
                tableHTML += `
                    <tr>
                        <td>${job.order_id}</td>
                        <td>${job.product_id}</td>
                        <td>${job.operation_seq}</td>
                        <td>${job.machine_id}</td>
                        <td>${job.proc_time_min}</td>
                    </tr>
                `;
            });

            tableHTML += `
                    </tbody>
                </table>
            `;

            if (jobsData.length > 10) {
                tableHTML += `<p><em>Showing first 10 of ${jobsData.length} operations</em></p>`;
            }

            container.innerHTML = tableHTML;
        }
    }

    displaySchedule(scheduleData) {
        const container = document.getElementById('scheduling-results');
        if (scheduleData.length === 0) {
            container.innerHTML = '<p>No schedule data available.</p>';
            return;
        }

        let tableHTML = `
            <table class="results-table">
                <thead>
                    <tr>
                        <th>Order ID</th>
                        <th>Operation Seq</th>
                        <th>Machine ID</th>
                        <th>Start Time</th>
                        <th>End Time</th>
                    </tr>
                </thead>
                <tbody>
        `;

        const displayData = scheduleData.slice(0, 10);
        displayData.forEach(op => {
            tableHTML += `
                <tr>
                    <td>${op.order_id}</td>
                    <td>${op.operation_seq}</td>
                    <td>${op.machine_id}</td>
                    <td>${new Date(op.start).toLocaleString()}</td>
                    <td>${new Date(op.end).toLocaleString()}</td>
                </tr>
            `;
        });

        tableHTML += `
                </tbody>
            </table>
        `;

        if (scheduleData.length > 10) {
            tableHTML += `<p><em>Showing first 10 of ${scheduleData.length} operations</em></p>`;
        }

        container.innerHTML = tableHTML;
    }

    displayKPIs(kpiData) {
        const container = document.getElementById('kpi-results');
        if (!kpiData || Object.keys(kpiData).length === 0) {
            container.innerHTML = '<p>No KPI data available.</p>';
            return;
        }

        let cardsHTML = '<div class="kpi-cards">';

        // Phase 1 KPIs
        const kpiItems = [
            { label: 'Total Orders', value: kpiData.total_orders, icon: '📋' },
            { label: 'On-time Orders', value: kpiData.on_time_orders, icon: '✅',
              color: kpiData.late_orders === 0 ? '#2ecc71' : '#f39c12' },
            { label: 'Late Orders', value: kpiData.late_orders, icon: '⏰',
              color: kpiData.late_orders > 0 ? '#e74c3c' : '#2ecc71' },
            { label: 'Average Delay', value: `${kpiData.avg_delay.toFixed(2)} hrs`, icon: '⏳',
              color: kpiData.avg_delay < 0 ? '#2ecc71' : '#e74c3c' },
            { label: 'Maximum Delay', value: `${kpiData.max_delay.toFixed(2)} hrs`, icon: '📈',
              color: kpiData.max_delay > 0 ? '#e74c3c' : '#2ecc71' }
        ];

        // Phase 2 KPIs
        const phase2Items = [];
        if (kpiData.avg_utilization !== undefined) {
            phase2Items.push({
                label: 'Avg Utilization',
                value: `${kpiData.avg_utilization.toFixed(2)}%`,
                icon: '⚡',
                color: '#3498db'
            });
        }
        if (kpiData.alt_machine_usage_pct !== undefined) {
            phase2Items.push({
                label: 'Alt Machine Usage',
                value: `${kpiData.alt_machine_usage_pct.toFixed(2)}%`,
                icon: '🔀',
                color: '#9b59b6'
            });
        }
        if (kpiData.avg_release_delay !== undefined) {
            phase2Items.push({
                label: 'Avg Release Delay',
                value: `${kpiData.avg_release_delay.toFixed(2)} hrs`,
                icon: '📦',
                color: '#e67e22'
            });
        }

        kpiItems.forEach(item => {
            cardsHTML += `
                <div class="kpi-card" style="border-left: 4px solid ${item.color || '#3498db'};">
                    <div class="kpi-icon">${item.icon}</div>
                    <div class="kpi-content">
                        <div class="kpi-label">${item.label}</div>
                        <div class="kpi-value">${item.value}</div>
                    </div>
                </div>
            `;
        });

        cardsHTML += '</div>';

        // Phase 2 KPIs section
        if (phase2Items.length > 0) {
            cardsHTML += '<h3 style="margin-top: 20px;">Phase 2 KPIs</h3><div class="kpi-cards">';
            phase2Items.forEach(item => {
                cardsHTML += `
                    <div class="kpi-card" style="border-left: 4px solid ${item.color};">
                        <div class="kpi-icon">${item.icon}</div>
                        <div class="kpi-content">
                            <div class="kpi-label">${item.label}</div>
                            <div class="kpi-value">${item.value}</div>
                        </div>
                    </div>
                `;
            });
            cardsHTML += '</div>';
        }

        container.innerHTML = cardsHTML;
    }

    displayVerification(verificationData) {
        const container = document.getElementById('verification-results');
        if (verificationData.passed) {
            container.innerHTML = `
                <p class="success-message">✓ Schedule verification passed:</p>
                <ul>
                    <li>No machine has overlapping operations (respecting capacity)</li>
                    <li>Operation sequence order is respected per order</li>
                    ${verificationData.no_downtime_violations !== false ? '<li>No downtime violations</li>' : ''}
                </ul>
            `;
        } else {
            let errorsHTML = '<p class="error-message">✗ Schedule verification failed:</p><ul>';
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

        if (scheduleData.length === 0) {
            this.chart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: ['No Data'],
                    datasets: [{ label: 'No schedule data', data: [0], backgroundColor: '#95a5a6' }]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
            });
            return;
        }

        const machines = [...new Set(scheduleData.map(op => op.machine_id))].sort();
        const orders = [...new Set(scheduleData.map(op => op.order_id))];
        const colors = this.generateColors(orders.length);
        const orderColorMap = {};
        orders.forEach((order, index) => { orderColorMap[order] = colors[index]; });

        const operationsByMachine = {};
        scheduleData.forEach(op => {
            if (!operationsByMachine[op.machine_id]) operationsByMachine[op.machine_id] = [];
            operationsByMachine[op.machine_id].push(op);
        });

        const operationsByOrder = {};
        scheduleData.forEach(op => {
            if (!operationsByOrder[op.order_id]) operationsByOrder[op.order_id] = [];
            operationsByOrder[op.order_id].push(op);
        });

        const chartData = { labels: machines, datasets: [] };

        Object.keys(operationsByOrder).forEach(orderId => {
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
                label: `Order ${orderId}`,
                data: data,
                backgroundColor: orderColorMap[orderId]
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
                    title: { display: true, text: 'Production Schedule (Machine View)' },
                    legend: { position: 'right' }
                },
                scales: {
                    x: { beginAtZero: true, title: { display: true, text: 'Duration (hours)' } },
                    y: { title: { display: true, text: 'Machine' } }
                }
            }
        });
    }

    createOrderGanttChart(scheduleData) {
        const ctx = document.getElementById('order-gantt-chart').getContext('2d');

        if (this.orderChart) {
            this.orderChart.destroy();
        }

        if (scheduleData.length === 0) {
            this.orderChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: ['No Data'],
                    datasets: [{ label: 'No schedule data', data: [0], backgroundColor: '#95a5a6' }]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
            });
            return;
        }

        const orders = [...new Set(scheduleData.map(op => op.order_id))].sort();
        const machines = [...new Set(scheduleData.map(op => op.machine_id))].sort();
        const colors = this.generateColors(machines.length);
        const machineColorMap = {};
        machines.forEach((machine, index) => { machineColorMap[machine] = colors[index]; });

        const operationsByOrder = {};
        scheduleData.forEach(op => {
            if (!operationsByOrder[op.order_id]) operationsByOrder[op.order_id] = [];
            operationsByOrder[op.order_id].push(op);
        });

        const chartData = { labels: orders, datasets: [] };

        machines.forEach(machine => {
            const data = orders.map(order => {
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
                    title: { display: true, text: 'Production Schedule (Order View)' },
                    legend: { position: 'right' }
                },
                scales: {
                    x: { beginAtZero: true, title: { display: true, text: 'Duration (hours)' } },
                    y: { title: { display: true, text: 'Order' } }
                }
            }
        });
    }

    generateColors(count) {
        const colors = [];
        for (let i = 0; i < count; i++) {
            const hue = (i * 360) / count;
            const saturation = 70 + Math.random() * 30;
            const lightness = 60 + Math.random() * 20;
            colors.push(`hsl(${hue}, ${saturation}%, ${lightness}%)`);
        }
        return colors;
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
        link.download = `${this.currentChart}_gantt_chart.png`;
        link.href = canvas.toDataURL('image/png');
        link.click();
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

    showAllSections() {
        const sections = document.querySelectorAll('main section');
        sections.forEach(section => {
            section.style.display = 'block';
        });
    }

    showNextSection() {
        if (this.currentSectionIndex >= 0) {
            const currentSection = this.sections[this.currentSectionIndex];
            document.getElementById(`${currentSection}-section`).style.display = 'none';
        }

        this.currentSectionIndex++;

        if (this.currentSectionIndex >= this.sections.length) {
            this.showAllSections();
            document.getElementById('next-btn').disabled = true;
            return;
        }

        const nextSection = this.sections[this.currentSectionIndex];
        document.getElementById(`${nextSection}-section`).style.display = 'block';

        if (this.currentSectionIndex >= this.sections.length - 1) {
            document.getElementById('next-btn').textContent = 'Finish';
            document.getElementById('next-btn').disabled = true;
        } else {
            document.getElementById('next-btn').textContent = 'Next Step →';
        }
    }

    resetApp() {
        this.sessionId = null;
        this.currentSectionIndex = -1;
        this.currentChart = 'machine';
        this.phase15Data = null;

        if (this.chart) { this.chart.destroy(); this.chart = null; }
        if (this.orderChart) { this.orderChart.destroy(); this.orderChart = null; }

        document.querySelectorAll('.chart-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.chart === 'machine');
        });
        document.getElementById('machine-gantt-container').style.display = 'block';
        document.getElementById('order-gantt-container').style.display = 'none';

        document.getElementById('machines-file').value = '';
        document.getElementById('products-file').value = '';
        document.getElementById('routing-file').value = '';
        document.getElementById('orders-file').value = '';
        document.getElementById('calendar-file').value = '';
        document.getElementById('setup-file').value = '';
        document.getElementById('sections-file').value = '';
        document.getElementById('buffers-file').value = '';

        this.hideAllSections();
        document.getElementById('features-section').style.display = 'block';
        document.getElementById('upload-section').style.display = 'block';

        document.querySelectorAll('.progress-tracker .step').forEach(step => {
            step.className = 'step';
            if (step.id === 'step-upload') step.textContent = '⬜ Upload';
            else if (step.id === 'step-validation') step.textContent = '⬜ Validation';
            else if (step.id === 'step-jobs') step.textContent = '⬜ Job Building';
            else if (step.id === 'step-scheduling') step.textContent = '⬜ Scheduling';
            else if (step.id === 'step-verification') step.textContent = '⬜ Verification';
            else if (step.id === 'step-kpi') step.textContent = '⬜ KPI Calculation';
            else if (step.id === 'step-visualization') step.textContent = '⬜ Visualization';
        });

        document.getElementById('validation-results').innerHTML = '<p>Please upload files to see validation results.</p>';
        document.getElementById('jobs-results').innerHTML = '<p>Please upload and validate files to see job building results.</p>';
        document.getElementById('scheduling-results').innerHTML = '<p>Please upload and validate files to see scheduling results.</p>';
        document.getElementById('verification-results').innerHTML = '<p>Please upload and validate files to see verification results.</p>';
        document.getElementById('kpi-results').innerHTML = '<p>Please upload and validate files to see KPI results.</p>';

        this.setActionButtonsDisabled(true);
        document.getElementById('next-btn').disabled = true;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.schedulerApp = new SchedulerApp();
});
