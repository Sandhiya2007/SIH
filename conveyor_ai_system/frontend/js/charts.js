/**
 * Conveyor AI - Charting and Real-Time Data Visualization System
 * Manages Chart.js real-time sensor streams, degradation curves, and condition distributions.
 */

class ConveyorCharts {
    constructor() {
        this.trendChart = null;
        this.rulChart = null;
        this.faultChart = null;
        this.activeChannel = 'vibration';

        // Historical time-series buffers (stores last 30 data points)
        this.maxDataPoints = 30;
        this.timeLabels = [];
        this.sensorBuffers = {
            voltage: [],
            current: [],
            powerFactor: [],
            vibration: [],
            peakAcc: [],
            domFreq: [],
            spectralEnergy: []
        };

        // Channel Configurations matching Section 15
        this.channelConfigs = {
            voltage: {
                label: 'Voltage RMS (V)',
                color: '#00f2fe',
                bgColor: 'rgba(0, 242, 254, 0.1)',
                unit: 'V'
            },
            current: {
                label: 'Current RMS (A)',
                color: '#818cf8',
                bgColor: 'rgba(129, 140, 248, 0.1)',
                unit: 'A'
            },
            powerFactor: {
                label: 'Power Factor',
                color: '#ec4899',
                bgColor: 'rgba(236, 72, 153, 0.1)',
                unit: 'PF'
            },
            vibration: {
                label: 'RMS Vibration (mm/s)',
                color: '#00ff9d',
                bgColor: 'rgba(0, 255, 157, 0.1)',
                unit: 'mm/s'
            },
            peakAcc: {
                label: 'Peak Acceleration (g)',
                color: '#f59e0b',
                bgColor: 'rgba(245, 158, 11, 0.1)',
                unit: 'g'
            },
            domFreq: {
                label: 'Dominant Frequency (Hz)',
                color: '#38bdf8',
                bgColor: 'rgba(56, 189, 248, 0.1)',
                unit: 'Hz'
            },
            spectralEnergy: {
                label: 'Spectral Energy',
                color: '#a855f7',
                bgColor: 'rgba(168, 85, 247, 0.1)',
                unit: 'J'
            }
        };

        this.initTrendChart();
    }

    initTrendChart() {
        const ctx = document.getElementById('liveTrendCanvas');
        if (!ctx) return;

        const cfg = this.channelConfigs[this.activeChannel];

        this.trendChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: this.timeLabels,
                datasets: [{
                    label: cfg.label,
                    data: this.sensorBuffers[this.activeChannel],
                    borderColor: cfg.color,
                    backgroundColor: cfg.bgColor,
                    borderWidth: 2.2,
                    tension: 0.35,
                    fill: true,
                    pointRadius: 3,
                    pointHoverRadius: 6,
                    pointBackgroundColor: cfg.color,
                    pointBorderColor: '#0a0e17',
                    pointBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 250
                },
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.05)',
                            drawBorder: false
                        },
                        ticks: {
                            color: '#64748b',
                            font: { family: 'JetBrains Mono', size: 10 }
                        }
                    },
                    y: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.06)',
                            drawBorder: false
                        },
                        ticks: {
                            color: '#94a3b8',
                            font: { family: 'JetBrains Mono', size: 11 },
                            callback: (val) => `${val} ${cfg.unit}`
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(11, 16, 28, 0.95)',
                        titleColor: '#00f2fe',
                        bodyColor: '#fff',
                        borderColor: 'rgba(0, 242, 254, 0.3)',
                        borderWidth: 1,
                        padding: 10,
                        titleFont: { family: 'JetBrains Mono', size: 12 },
                        bodyFont: { family: 'JetBrains Mono', size: 12 }
                    }
                }
            }
        });
    }

    setChannel(channelKey) {
        if (!this.channelConfigs[channelKey]) return;
        this.activeChannel = channelKey;
        const cfg = this.channelConfigs[channelKey];

        if (this.trendChart) {
            const ds = this.trendChart.data.datasets[0];
            ds.label = cfg.label;
            ds.data = this.sensorBuffers[channelKey];
            ds.borderColor = cfg.color;
            ds.backgroundColor = cfg.bgColor;
            ds.pointBackgroundColor = cfg.color;

            this.trendChart.options.scales.y.ticks.callback = (val) => `${val} ${cfg.unit}`;
            this.trendChart.update();
        }

        // Sync dropdown selector if present
        const select = document.getElementById('chartChannelSelect');
        if (select && select.value !== channelKey) {
            select.value = channelKey;
        }

        // Sync tab buttons if present
        document.querySelectorAll('.channel-tab').forEach((tab) => {
            if (tab.getAttribute('data-channel') === channelKey) {
                tab.classList.add('active');
            } else {
                tab.classList.remove('active');
            }
        });
    }

    addTelemetryPoint(packet) {
        if (!packet || !packet.sensor_data) return;

        const s = packet.sensor_data;
        const rowLabel = `R${packet.row_number || 1}`;

        // Push Row / Time label
        this.timeLabels.push(rowLabel);
        if (this.timeLabels.length > this.maxDataPoints) {
            this.timeLabels.shift();
        }

        // Map sensor channels directly from dataset
        const channels = {
            voltage: s.Voltage_RMS !== undefined ? s.Voltage_RMS : 415.2,
            current: s.Irms !== undefined ? s.Irms : 18.4,
            powerFactor: s.Power_Factor !== undefined ? s.Power_Factor : 0.91,
            vibration: s.RMS_Vibration !== undefined ? s.RMS_Vibration : 2.84,
            peakAcc: s.Peak_Acceleration !== undefined ? s.Peak_Acceleration : 4.12,
            domFreq: s.Dominant_Frequency !== undefined ? s.Dominant_Frequency : 49.8,
            spectralEnergy: s.Spectral_Energy !== undefined ? s.Spectral_Energy : 145.2
        };

        Object.keys(channels).forEach((key) => {
            if (this.sensorBuffers[key]) {
                this.sensorBuffers[key].push(channels[key]);
                if (this.sensorBuffers[key].length > this.maxDataPoints) {
                    this.sensorBuffers[key].shift();
                }
            }
        });

        // Update live chart
        if (this.trendChart) {
            this.trendChart.update('none');
        }
    }

    // Initialize RUL Degradation Chart for Predictive Maintenance Page
    initRulChart(canvasId = 'rulDegradationCanvas') {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        const labels = ['T-24h', 'T-20h', 'T-16h', 'T-12h', 'T-8h', 'T-4h', 'NOW', 'T+4h (Est)', 'T+8h (Est)', 'T+12h (Est)'];
        const values = [240, 232, 224, 215, 203, 192, 184, 175, 166, 155];

        this.rulChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Simulated RUL Hours (Demonstration)',
                        data: values,
                        borderColor: '#00f2fe',
                        backgroundColor: 'rgba(0, 242, 254, 0.08)',
                        borderWidth: 2.5,
                        tension: 0.3,
                        fill: true,
                        pointBackgroundColor: '#00f2fe'
                    },
                    {
                        label: 'Critical Threshold (24h)',
                        data: [24, 24, 24, 24, 24, 24, 24, 24, 24, 24],
                        borderColor: '#ef4444',
                        borderWidth: 1.5,
                        borderDash: [6, 4],
                        pointRadius: 0,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: '#64748b', font: { family: 'JetBrains Mono', size: 10 } }
                    },
                    y: {
                        min: 0,
                        max: 280,
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: '#94a3b8', font: { family: 'JetBrains Mono', size: 11 }, callback: (v) => `${v} h` }
                    }
                },
                plugins: {
                    legend: {
                        labels: { color: '#94a3b8', font: { family: 'JetBrains Mono', size: 11 } }
                    }
                }
            }
        });
    }

    // Initialize Dynamic Condition Distribution Chart
    initFaultDistributionChart(canvasId = 'faultDistCanvas', classes = [], counts = {}) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        // Default to detected classes if empty
        const classLabels = (classes && classes.length > 0)
            ? classes
            : ['normal load', 'overload', 'misalignment', 'splice rupture'];

        const data = classLabels.map(c => counts[c] || 0);
        const displayLabels = classLabels.map(c => c.toUpperCase());

        const bgColors = classLabels.map(c => {
            const lc = c.toLowerCase();
            if (lc === 'normal load') return 'rgba(0, 255, 157, 0.45)';
            if (lc === 'overload') return 'rgba(245, 158, 11, 0.45)';
            if (lc === 'misalignment') return 'rgba(249, 115, 22, 0.45)';
            return 'rgba(239, 68, 68, 0.45)'; // splice rupture or belt tear
        });

        const borderColors = classLabels.map(c => {
            const lc = c.toLowerCase();
            if (lc === 'normal load') return '#00ff9d';
            if (lc === 'overload') return '#f59e0b';
            if (lc === 'misalignment') return '#f97316';
            return '#ef4444';
        });

        this.faultChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: displayLabels,
                datasets: [{
                    label: 'Condition Samples',
                    data: data,
                    backgroundColor: bgColors,
                    borderColor: borderColors,
                    borderWidth: 2,
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { color: '#94a3b8', font: { family: 'Rajdhani', size: 13, weight: '600' } }
                    },
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: '#94a3b8', font: { family: 'JetBrains Mono', size: 11 } }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }

    updateFaultChart(classes, counts) {
        if (!this.faultChart) return;
        if (classes && classes.length > 0) {
            this.faultChart.data.labels = classes.map(c => c.toUpperCase());
            this.faultChart.data.datasets[0].data = classes.map(c => counts[c] || 0);
        } else {
            const currentLabels = this.faultChart.data.labels;
            this.faultChart.data.datasets[0].data = currentLabels.map(l => counts[l.toLowerCase()] || 0);
        }
        this.faultChart.update();
    }
}

// Global Charts Manager
window.conveyorCharts = new ConveyorCharts();
