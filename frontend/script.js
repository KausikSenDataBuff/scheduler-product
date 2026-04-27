class SchedulerApp {
    constructor() {
        this.sessionId = null;
        this.chart = null;
        this.orderChart = null;
        this.sections = ['validation', 'jobs', 'scheduling', 'verification', 'kpi', 'visualization'];
        this.currentSectionIndex = -1;
        this.currentChart = 'machine';
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
        document.getElementById('upload-section').style.display = 'block';

        // Initialize current section tracker
        this.currentSectionIndex = -1; // Start before first section
        this.sections = ['upload', 'validation', 'jobs', 'scheduling', 'verification', 'kpi', 'visualization'];

        // Debug: Show alert to confirm init is running
        // alert('SchedulerApp initialized');
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
        // status: 'pending', 'running', 'success', 'error'
        // Map step names to element IDs
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
            // Update the emoji indicator
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
        // Get files
        const machinesFile = document.getElementById('machines-file').files[0];
        const productsFile = document.getElementById('products-file').files[0];
        const routingFile = document.getElementById('routing-file').files[0];
        const ordersFile = document.getElementById('orders-file').files[0];

        if (!machinesFile || !productsFile || !routingFile || !ordersFile) {
            alert('Please select all four CSV files.');
            return;
        }

        // Show upload progress
        this.updateProgressStep('Upload', 'running');
        this.setActionButtonsDisabled(true);

        try {
            const formData = new FormData();
            formData.append('machines', machinesFile);
            formData.append('products', productsFile);
            formData.append('routing', routingFile);
            formData.append('orders', ordersFile);

            const response = await fetch('http://localhost:8000/upload', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.detail || 'Upload failed');
            }

            this.sessionId = result.session_id;
            this.showValidationResults(result);
            this.updateProgressStep('Upload', 'success');
            this.updateProgressStep('Validation', 'running');

            // Enable processing if validation passed
            if (result.validation_passed) {
                await this.processWorkflow();
                // Enable next button after successful upload and processing
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
            validationResults.innerHTML = `
                <p class="success-message">✓ ${result.validation_message}</p>
            `;
        } else {
            validationResults.innerHTML = `
                <p class="error-message">✗ ${result.validation_message}</p>
            `;
        }
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

            // Small delay to simulate processing (remove in production)
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

            // Load all results
            await this.loadAllResults();
            this.updateProgressStep('Visualization', 'success');

            // Enable action buttons
            this.setActionButtonsDisabled(false);

        } catch (error) {
            console.error('Processing error:', error);
            this.showError('Processing failed: ' + error.message);
            // Reset progress steps on error
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
            // Load jobs data
            const jobsResponse = await fetch(`http://localhost:8000/data/${this.sessionId}/jobs`);
            const jobsData = await jobsResponse.json();
            this.displayJobs(jobsData);

            // Load schedule data
            const scheduleResponse = await fetch(`http://localhost:8000/data/${this.sessionId}/schedule`);
            const scheduleData = await scheduleResponse.json();
            this.displaySchedule(scheduleData);
            this.scheduleData = scheduleData;
            this.createGanttChart(scheduleData);
            this.createOrderGanttChart(scheduleData);

            // Load KPI data
            const kpiResponse = await fetch(`http://localhost:8000/data/${this.sessionId}/kpi`);
            const kpiData = await kpiResponse.json();
            this.displayKPIs(kpiData);

            // Load verification data
            const verificationResponse = await fetch(`http://localhost:8000/data/${this.sessionId}/verification`);
            const verificationData = await verificationResponse.json();
            this.displayVerification(verificationData);

            // Show all sections
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

        // Create table
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

        // Show first 10 rows
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
            tableHTML += `<p><em>Showing first 10 of ${jobsData.length} jobs</em></p>`;
        }

        container.innerHTML = tableHTML;
    }

    displaySchedule(scheduleData) {
        const container = document.getElementById('scheduling-results');
        if (scheduleData.length === 0) {
            container.innerHTML = '<p>No schedule data available.</p>';
            return;
        }

        // Create table
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

        // Show first 10 rows
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

        // Create KPI cards
        let cardsHTML = '';
        const kpiItems = [
            { label: 'Total Orders', value: kpiData.total_orders, icon: '📋' },
            { label: 'On-time Orders', value: kpiData.on_time_orders, icon: '✅',
              color: kpiData.late_orders === 0 ? '#2ecc71' : '#f39c12' },
            { label: 'Late Orders', value: kpiData.late_orders, icon: '⏰',
              color: kpiData.late_orders > 0 ? '#e74c3c' : '#2ecc71' },
            { label: 'Average Delay', value: `${kpiData.avg_delay.toFixed(2)} hours`, icon: '⏳',
              color: kpiData.avg_delay < 0 ? '#2ecc71' : '#e74c3c' },
            { label: 'Maximum Delay', value: `${kpiData.max_delay.toFixed(2)} hours`, icon: '📈',
              color: kpiData.max_delay > 0 ? '#e74c3c' : '#2ecc71' }
        ];

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

        container.innerHTML = `<div class="kpi-cards">${cardsHTML}</div>`;
    }

    displayVerification(verificationData) {
        const container = document.getElementById('verification-results');
        if (verificationData.passed) {
            container.innerHTML = `
                <p class="success-message">✓ Schedule verification passed:</p>
                <ul>
                    <li>No machine has overlapping operations</li>
                    <li>Operation sequence order is respected per order</li>
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

        // Destroy existing chart if it exists
        if (this.chart) {
            this.chart.destroy();
        }

        if (scheduleData.length === 0) {
            // Show empty chart with message
            this.chart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: ['No Data'],
                    datasets: [{
                        label: 'No schedule data available',
                        data: [0],
                        backgroundColor: '#95a5a6'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: { enabled: false }
                    }
                }
            });
            return;
        }

        // Prepare data for Gantt chart
        const machines = [...new Set(scheduleData.map(op => op.machine_id))].sort();
        const machineIndex = {};
        machines.forEach((machine, index) => {
            machineIndex[machine] = index;
        });

        // Group operations by order for coloring
        const orders = [...new Set(scheduleData.map(op => op.order_id))];
        const colors = this.generateColors(orders.length);
        const orderColorMap = {};
        orders.forEach((order, index) => {
            orderColorMap[order] = colors[index];
        });

        // Create datasets for each machine
        const datasets = machines.map((machine, machineIdx) => ({
            label: machine,
            data: [],
            backgroundColor: 'rgba(54, 162, 235, 0.6)',
            borderColor: 'rgba(54, 162, 235, 1)',
            borderWidth: 1
        }));

        // Prepare labels (time intervals)
        const timeLabels = this.generateTimeLabels(scheduleData);

        // For simplicity, we'll create a simplified Gantt chart
        // In a real implementation, we'd use a more sophisticated approach

        // Actually, let's create a horizontal bar chart showing operations per machine
        const chartData = {
            labels: machines,
            datasets: []
        };

        // Group by machine
        const operationsByMachine = {};
        scheduleData.forEach(op => {
            if (!operationsByMachine[op.machine_id]) {
                operationsByMachine[op.machine_id] = [];
            }
            operationsByMachine[op.machine_id].push(op);
        });

        // Create dataset for each operation type (order)
        const operationsByOrder = {};
        scheduleData.forEach(op => {
            if (!operationsByOrder[op.order_id]) {
                operationsByOrder[op.order_id] = [];
            }
            operationsByOrder[op.order_id].push(op);
        });

        Object.keys(operationsByOrder).forEach(orderId => {
            const data = machines.map(machine => {
                const ops = operationsByMachine[machine] || [];
                const orderOps = ops.filter(op => op.order_id === orderId);
                return orderOps.reduce((total, op) => {
                    const start = new Date(op.start);
                    const end = new Date(op.end);
                    return total + (end - start) / (1000 * 60 * 60); // Convert to hours
                }, 0);
            });

            chartData.datasets.push({
                label: `Order ${orderId}`,
                data: data,
                backgroundColor: orderColorMap[orderId]
            });
        });

        // Create the chart
        this.chart = new Chart(ctx, {
            type: 'bar',
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y', // Horizontal bars
                plugins: {
                    title: {
                        display: true,
                        text: 'Production Schedule Gantt Chart'
                    },
                    legend: {
                        position: 'right'
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Duration (hours)'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Machine'
                        }
                    }
                }
            }
        });
    }

    createOrderGanttChart(scheduleData) {
        const ctx = document.getElementById('order-gantt-chart').getContext('2d');

        // Destroy existing chart if it exists
        if (this.orderChart) {
            this.orderChart.destroy();
        }

        if (scheduleData.length === 0) {
            this.orderChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: ['No Data'],
                    datasets: [{
                        label: 'No schedule data available',
                        data: [0],
                        backgroundColor: '#95a5a6'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: { enabled: false }
                    }
                }
            });
            return;
        }

        // Order Gantt: Y-axis is orders, bars represent machines/resources
        const orders = [...new Set(scheduleData.map(op => op.order_id))].sort();
        const machines = [...new Set(scheduleData.map(op => op.machine_id))].sort();

        // Generate colors for machines
        const colors = this.generateColors(machines.length);
        const machineColorMap = {};
        machines.forEach((machine, index) => {
            machineColorMap[machine] = colors[index];
        });

        // Group operations by order
        const operationsByOrder = {};
        scheduleData.forEach(op => {
            if (!operationsByOrder[op.order_id]) {
                operationsByOrder[op.order_id] = [];
            }
            operationsByOrder[op.order_id].push(op);
        });

        // Create dataset for each machine
        const chartData = {
            labels: orders,
            datasets: []
        };

        machines.forEach(machine => {
            const data = orders.map(order => {
                const ops = operationsByOrder[order] || [];
                const machineOps = ops.filter(op => op.machine_id === machine);
                return machineOps.reduce((total, op) => {
                    const start = new Date(op.start);
                    const end = new Date(op.end);
                    return total + (end - start) / (1000 * 60 * 60); // Convert to hours
                }, 0);
            });

            chartData.datasets.push({
                label: machine,
                data: data,
                backgroundColor: machineColorMap[machine]
            });
        });

        // Create the chart
        this.orderChart = new Chart(ctx, {
            type: 'bar',
            data: chartData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y', // Horizontal bars
                plugins: {
                    title: {
                        display: true,
                        text: 'Order Gantt Chart'
                    },
                    legend: {
                        position: 'right'
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Duration (hours)'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Order'
                        }
                    }
                }
            }
        });
    }

    generateColors(count) {
        const colors = [];
        for (let i = 0; i < count; i++) {
            // Generate evenly spaced hues
            const hue = (i * 360) / count;
            const saturation = 70 + Math.random() * 30; // 70-100%
            const lightness = 60 + Math.random() * 20; // 60-80%
            colors.push(`hsl(${hue}, ${saturation}%, ${lightness}%)`);
        }
        return colors;
    }

    generateTimeLabels(scheduleData) {
        // Generate time labels for the x-axis
        const times = scheduleData.flatMap(op => [new Date(op.start), new Date(op.end)]);
        if (times.length === 0) return [];

        const minTime = new Date(Math.min(...times.map(t => t.getTime())));
        const maxTime = new Date(Math.max(...times.map(t => t.getTime())));

        // Create labels every 6 hours
        const labels = [];
        let current = new Date(minTime);
        while (current <= maxTime) {
            labels.push(current.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
            current = new Date(current.getTime() + 6 * 60 * 60 * 1000); // Add 6 hours
        }
        return labels;
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

        // Convert canvas to image and trigger download
        const canvasId = this.currentChart === 'machine' ? 'gantt-chart' : 'order-gantt-chart';
        const canvas = document.getElementById(canvasId);
        const link = document.createElement('a');
        link.download = `${this.currentChart}_gantt_chart.png`;
        link.href = canvas.toDataURL('image/png');
        link.click();
    }

    switchChartTab(chartType) {
        this.currentChart = chartType;

        // Update tab button states
        document.querySelectorAll('.chart-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.chart === chartType);
        });

        // Toggle chart containers
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
        // Hide current section
        if (this.currentSectionIndex >= 0) {
            const currentSection = this.sections[this.currentSectionIndex];
            document.getElementById(`${currentSection}-section`).style.display = 'none';
        }

        // Move to next section
        this.currentSectionIndex++;

        // If we've gone through all sections, show all sections
        if (this.currentSectionIndex >= this.sections.length) {
            this.showAllSections();
            document.getElementById('next-btn').disabled = true;
            return;
        }

        // Show next section
        const nextSection = this.sections[this.currentSectionIndex];
        document.getElementById(`${nextSection}-section`).style.display = 'block';

        // Update button text and disable if at the end
        if (this.currentSectionIndex >= this.sections.length - 1) {
            document.getElementById('next-btn').textContent = 'Finish';
            document.getElementById('next-btn').disabled = true;
        } else {
            document.getElementById('next-btn').textContent = 'Next Step →';
        }
    }

    resetApp() {
        if (this.sessionId) {
            // Optionally, we could call an API to clean up the session
            // For now, just reset the frontend
        }

        this.sessionId = null;
        this.currentSectionIndex = -1;
        this.currentChart = 'machine';
        if (this.chart) {
            this.chart.destroy();
            this.chart = null;
        }
        if (this.orderChart) {
            this.orderChart.destroy();
            this.orderChart = null;
        }

        // Reset chart tabs
        document.querySelectorAll('.chart-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.chart === 'machine');
        });
        document.getElementById('machine-gantt-container').style.display = 'block';
        document.getElementById('order-gantt-container').style.display = 'none';

        // Reset file inputs
        document.getElementById('machines-file').value = '';
        document.getElementById('products-file').value = '';
        document.getElementById('routing-file').value = '';
        document.getElementById('orders-file').value = '';

        // Reset sections
        this.hideAllSections();
        document.getElementById('upload-section').style.display = 'block';

        // Reset progress tracker
        document.querySelectorAll('.progress-tracker .step').forEach(step => {
            step.className = 'step';
            // Reset emoji based on ID
            if (step.id === 'step-upload') step.textContent = '⬜ Upload';
            else if (step.id === 'step-validation') step.textContent = '⬜ Validation';
            else if (step.id === 'step-jobs') step.textContent = '⬜ Job Building';
            else if (step.id === 'step-scheduling') step.textContent = '⬜ Scheduling';
            else if (step.id === 'step-verification') step.textContent = '⬜ Verification';
            else if (step.id === 'step-kpi') step.textContent = '⬜ KPI Calculation';
            else if (step.id === 'step-visualization') step.textContent = '⬜ Visualization';
        });

        // Reset results containers
        document.getElementById('validation-results').innerHTML = '<p>Please upload files to see validation results.</p>';
        document.getElementById('jobs-results').innerHTML = '<p>Please upload and validate files to see job building results.</p>';
        document.getElementById('scheduling-results').innerHTML = '<p>Please upload and validate files to see scheduling results.</p>';
        document.getElementById('verification-results').innerHTML = '<p>Please upload and validate files to see verification results.</p>';
        document.getElementById('kpi-results').innerHTML = '<p>Please upload and validate files to see KPI results.</p>';
        document.getElementById('gantt-chart').getContext('2d').clearRect(0, 0, 400, 200);

        // Disable action buttons
        this.setActionButtonsDisabled(true);
        document.getElementById('next-btn').disabled = true;
    }
}

// Initialize the app when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.schedulerApp = new SchedulerApp();
});