/**
 * Conveyor AI - Main Command Center Dashboard Logic
 * Integrates Digital Twin SVG, AI Health Gauge, Simulated RUL, Live Sensor Matrix,
 * Dynamic 4-Condition Status Cards, and Probability Distributions with real-time WebSocket feeds.
 */

// Configurable Class Display Names (Supports dynamic replacement if dataset uses "belt tear")
const CLASS_DISPLAY_NAMES = {
    "normal load": "NORMAL LOAD",
    "overload": "OVERLOAD",
    "misalignment": "MISALIGNMENT",
    "splice rupture": "SPLICE RUPTURE",
    "belt tear": "BELT TEAR"
};

/**
 * Simulated RUL Calculation Function for Demonstration
 * IMPORTANT: The current XGBoost model is a classifier.
 * This demo generator provides realistic wear simulation until an LSTM/GRU
 * degradation model is connected in the future.
 */
function getRemainingLife(faultClass = "normal load", confidence = 0.99) {
    const baseMap = {
        "normal load": 184.0,
        "overload": 78.0,
        "misalignment": 44.0,
        "splice rupture": 6.0,
        "belt tear": 4.0
    };

    const norm = String(faultClass).toLowerCase().trim();
    const base = baseMap[norm] || 96.0;
    const hours = Math.max(2.0, Math.round(base + (Math.random() * 4 - 2)));
    const days = Math.floor(hours / 24);
    const remHours = Math.round(hours % 24);
    const formatted = days > 0 ? `${days} DAYS ${remHours} HOURS` : `${remHours} HOURS`;

    let degradation = "LOW";
    let maintenance = "MONITOR";
    let gaugePct = 92;

    if (hours > 120) {
        degradation = "LOW";
        maintenance = "MONITOR";
        gaugePct = 92;
    } else if (hours > 50) {
        degradation = "MEDIUM";
        maintenance = "INSPECT LOAD / DRIVE SYSTEM";
        gaugePct = 64;
    } else if (hours > 15) {
        degradation = "HIGH";
        maintenance = "INSPECT BELT ALIGNMENT";
        gaugePct = 35;
    } else {
        degradation = "CRITICAL";
        maintenance = "IMMEDIATE INSPECTION";
        gaugePct = 10;
    }

    return {
        hours: hours,
        formatted: formatted,
        degradation: degradation,
        maintenance: maintenance,
        gaugePercentage: gaugePct,
        isSimulated: true,
        disclaimer: "SIMULATED RUL – DEMONSTRATION ONLY"
    };
}

class DashboardManager {
    constructor() {
        this.sparklineHistory = {};
        this.detectedClasses = [];
        this.classCounts = {};
        this.totalRows = 2000;
        this.init();
    }

    async init() {
        console.log('[Dashboard] Initializing Command Center UI...');

        // 1. Fetch dataset metadata and dynamic classes
        await this.loadDatasetMetadata();

        // 2. Subscribe to WebSocket Telemetry
        if (window.conveyorWS) {
            window.conveyorWS.onTelemetry((packet) => this.handleTelemetry(packet));
        }

        // 3. Channel Selector Dropdown
        const channelSelect = document.getElementById('chartChannelSelect');
        if (channelSelect) {
            channelSelect.addEventListener('change', (e) => {
                if (window.conveyorCharts) {
                    window.conveyorCharts.setChannel(e.target.value);
                }
            });
        }

        // 4. Fetch initial system status
        this.fetchStatus();
    }

    async loadDatasetMetadata() {
        try {
            const res = await fetch('/api/dataset/info');
            const data = await res.json();
            if (data && data.loaded) {
                this.totalRows = data.total_rows || 2000;
                this.detectedClasses = data.detected_classes || ['normal load', 'overload', 'misalignment', 'splice rupture'];
                this.classCounts = data.class_counts || {};

                // Update Header sample count
                const headerSamples = document.getElementById('headerDatasetSamples');
                if (headerSamples) {
                    headerSamples.textContent = `${this.totalRows} SAMPLES`;
                }

                // Render condition status cards dynamically
                this.renderConditionCards(data.conditions || []);

                // Render initial probability bars
                this.renderProbabilityBars(this.detectedClasses);
            }
        } catch (e) {
            console.warn('[Dashboard] Could not fetch /api/dataset/info:', e);
        }
    }

    renderConditionCards(conditions) {
        const container = document.getElementById('fourConditionContainer');
        if (!container) return;

        if (conditions && conditions.length > 0) {
            container.innerHTML = '';
            conditions.forEach((c, idx) => {
                const normClass = c.raw_label.toLowerCase().replace(/\s+/g, '_');
                const card = document.createElement('div');
                card.className = `condition-card ${idx === 0 ? 'active' : ''}`;
                card.id = `cond_card_${normClass}`;

                let ledClass = 'online';
                if (c.raw_label === 'overload' || c.raw_label === 'misalignment') ledClass = 'active';
                if (c.raw_label === 'splice rupture' || c.raw_label === 'belt tear') ledClass = 'critical';

                card.innerHTML = `
                    <div class="condition-card-header">
                        <span class="label">CONDITION 0${idx + 1}</span>
                        <span class="status-led ${ledClass}"></span>
                    </div>
                    <div class="condition-card-name">${c.display_name}</div>
                    <div class="condition-card-samples"><span>${c.sample_count}</span> SAMPLES</div>
                `;
                container.appendChild(card);
            });
        }
    }

    renderProbabilityBars(classes) {
        const container = document.getElementById('probBarsContainer');
        if (!container) return;

        container.innerHTML = '';
        classes.forEach((cls) => {
            const normKey = cls.toLowerCase().replace(/\s+/g, '_');
            const displayTitle = CLASS_DISPLAY_NAMES[cls.toLowerCase()] || cls.toUpperCase();

            let barColor = 'var(--cyan-primary)';
            if (cls.toLowerCase() === 'normal load') barColor = 'var(--status-normal)';
            if (cls.toLowerCase() === 'overload') barColor = 'var(--status-warning)';
            if (cls.toLowerCase() === 'misalignment') barColor = '#f97316';
            if (cls.toLowerCase() === 'splice rupture' || cls.toLowerCase() === 'belt tear') barColor = 'var(--status-critical)';

            const item = document.createElement('div');
            item.className = 'prob-bar-item';
            item.id = `prob_item_${normKey}`;
            item.innerHTML = `
                <div class="prob-bar-header">
                    <span class="prob-bar-label">${displayTitle}</span>
                    <span class="prob-bar-val" id="prob_val_${normKey}">0.0%</span>
                </div>
                <div class="prob-track">
                    <div class="prob-fill" id="prob_fill_${normKey}" style="width: 0%; background: ${barColor};"></div>
                </div>
            `;
            container.appendChild(item);
        });
    }

    async fetchStatus() {
        try {
            const res = await fetch('/api/status');
            const data = await res.json();
            if (data && data.server_time) {
                const clockEl = document.getElementById('serverClock');
                if (clockEl) clockEl.textContent = data.server_time;
            }
        } catch (e) {
            console.warn('[Dashboard] Could not fetch /api/status:', e);
        }
    }

    handleTelemetry(packet) {
        if (!packet) return;

        // Skip connection handshake packets
        if (packet.type === 'CONNECTION_ESTABLISHED') {
            if (packet.dataset_info) {
                this.totalRows = packet.dataset_info.total_rows || 2000;
                this.renderConditionCards(packet.dataset_info.conditions);
            }
            return;
        }

        // 1. Update Central AI Hero Display (Section 9)
        this.updateCentralHero(packet);

        // 2. Highlight Active Condition Card in Four Condition Grid (Section 10)
        this.updateActiveConditionCard(packet.prediction);

        // 3. Digital Twin Conveyor Animation & Status (Section 8)
        this.updateDigitalTwin(packet);

        // 4. Machine Health / AI Condition Circular Gauge (Section 11)
        this.updateHealthGauge(packet);

        // 5. Remaining Useful Life (RUL) Section (Section 12)
        this.updateRulSection(packet);

        // 6. Live Sensor Matrix (Section 13, 14)
        this.updateSensorMatrix(packet.sensor_data);

        // 7. AI Condition Assessment & Horizontal Probabilities (Section 16)
        this.updateAiConditionAssessment(packet);

        // 8. Interactive Live Chart Update (Section 15)
        if (window.conveyorCharts) {
            window.conveyorCharts.addTelemetryPoint(packet);
        }

        // 9. Alert Timeline (Section 37, 38)
        this.appendAlertEvent(packet);

        // 10. Update system clock
        if (packet.timestamp) {
            const clockEl = document.getElementById('serverClock');
            if (clockEl) clockEl.textContent = packet.timestamp;
        }
    }

    updateCentralHero(packet) {
        const titleEl = document.getElementById('heroConditionTitle');
        const confEl = document.getElementById('heroConfidenceValue');
        const rowEl = document.getElementById('heroRowValue');
        const hoursEl = document.getElementById('heroOpHoursValue');
        const matchEl = document.getElementById('heroMatchValue');
        const pillEl = document.getElementById('heroStatusPill');
        const ledEl = document.getElementById('heroStatusLed');
        const textEl = document.getElementById('heroStatusText');

        const displayPred = packet.prediction_display_name || packet.prediction.toUpperCase();
        if (titleEl) {
            titleEl.textContent = displayPred;
            // Colorize title
            if (packet.status === 'NORMAL') titleEl.style.color = 'var(--status-normal)';
            else if (packet.status === 'WARNING') titleEl.style.color = 'var(--status-warning)';
            else titleEl.style.color = 'var(--status-critical)';
        }

        if (confEl) confEl.textContent = `${packet.confidence}%`;
        if (rowEl) rowEl.textContent = `${packet.row_number} / ${this.totalRows}`;
        if (hoursEl) hoursEl.textContent = `${packet.operating_hours.toLocaleString()} H`;

        if (matchEl) {
            if (packet.correct === true) {
                matchEl.textContent = '✓ CORRECT';
                matchEl.style.color = 'var(--status-normal)';
            } else if (packet.correct === false) {
                matchEl.textContent = `✗ MISMATCH (ACTUAL: ${packet.actual_display_name})`;
                matchEl.style.color = 'var(--status-critical)';
            } else {
                matchEl.textContent = 'INFERENCE ACTIVE';
                matchEl.style.color = 'var(--cyan-primary)';
            }
        }

        if (pillEl && textEl && ledEl) {
            pillEl.className = `status-hero-pill ${packet.status.toLowerCase()}`;
            textEl.textContent = packet.status;
            if (packet.status === 'NORMAL') ledEl.className = 'status-led online';
            else if (packet.status === 'WARNING') ledEl.className = 'status-led active';
            else ledEl.className = 'status-led critical';
        }
    }

    updateActiveConditionCard(predictedCondition) {
        const norm = predictedCondition.toLowerCase().replace(/\s+/g, '_');
        document.querySelectorAll('.condition-card').forEach(card => {
            card.classList.remove('active');
        });
        const activeCard = document.getElementById(`cond_card_${norm}`);
        if (activeCard) {
            activeCard.classList.add('active');
        }
    }

    updateDigitalTwin(packet) {
        const statusText = document.getElementById('twinStatusText');
        const motorBox = document.getElementById('motorBox');
        const gearboxBox = document.getElementById('gearboxBox');
        const drivePulley = document.getElementById('drivePulleyOuter');
        const tailPulley = document.getElementById('tailPulleyOuter');
        const topBelt = document.getElementById('topBeltPath');
        const bottomBelt = document.getElementById('bottomBeltPath');

        const displayPred = packet.prediction_display_name || packet.prediction.toUpperCase();
        let color = '#00ff9d';
        let statusTagClass = 'online';

        if (packet.status === 'NORMAL') {
            color = '#00ff9d';
            statusTagClass = 'online';
        } else if (packet.prediction.toLowerCase() === 'overload') {
            color = '#f59e0b';
            statusTagClass = 'active';
        } else if (packet.prediction.toLowerCase() === 'misalignment') {
            color = '#f97316';
            statusTagClass = 'active';
        } else {
            color = '#ef4444';
            statusTagClass = 'critical';
        }

        if (statusText) {
            statusText.textContent = `${packet.status} - ${displayPred}`;
            statusText.style.borderColor = color;
            statusText.style.color = color;
        }

        // Colorize conveyor SVG elements
        [motorBox, gearboxBox, drivePulley, tailPulley, topBelt, bottomBelt].forEach(el => {
            if (el) {
                el.style.stroke = color;
                el.style.transition = 'stroke 0.4s ease';
            }
        });

        // Update HUD floating nodes
        const s = packet.sensor_data;
        if (s) {
            const v = document.getElementById('hudVoltage');
            const i = document.getElementById('hudCurrent');
            const t = document.getElementById('hudTemp');
            const vib = document.getElementById('hudVibration');
            if (v) v.textContent = `${s.Voltage_RMS} V`;
            if (i) i.textContent = `${s.Irms} A`;
            if (t) t.textContent = `${s.Bearing_Temperature} °C`;
            if (vib) vib.textContent = `${s.RMS_Vibration} mm/s`;
        }
    }

    updateHealthGauge(packet) {
        const valEl = document.getElementById('healthGaugeValue');
        const statusEl = document.getElementById('healthGaugeStatus');
        const circle = document.getElementById('healthGaugeCircle');
        const condName = document.getElementById('aiConditionName');
        const condConf = document.getElementById('aiConditionConfidence');

        if (valEl) valEl.textContent = `${packet.confidence}%`;
        if (statusEl) {
            statusEl.textContent = packet.status;
            statusEl.className = `gauge-meta-status ${packet.status.toLowerCase()}`;
        }

        if (condName) {
            condName.textContent = packet.prediction_display_name || packet.prediction.toUpperCase();
            if (packet.status === 'NORMAL') condName.style.color = 'var(--status-normal)';
            else if (packet.status === 'WARNING') condName.style.color = 'var(--status-warning)';
            else condName.style.color = 'var(--status-critical)';
        }

        if (condConf) condConf.textContent = `${packet.confidence}%`;

        if (circle) {
            // Circumference of r=75 is 2 * PI * 75 ≈ 471.24
            const maxDash = 471.24;
            const pct = Math.min(100, Math.max(0, packet.confidence));
            const offset = maxDash - (maxDash * (pct / 100));
            circle.style.strokeDashoffset = offset;

            if (packet.status === 'NORMAL') circle.style.stroke = 'var(--status-normal)';
            else if (packet.status === 'WARNING') circle.style.stroke = 'var(--status-warning)';
            else circle.style.stroke = 'var(--status-critical)';
        }
    }

    updateRulSection(packet) {
        const rul = packet.rul || getRemainingLife(packet.prediction, packet.confidence_ratio);
        const hoursEl = document.getElementById('rulHoursValue');
        const fmtEl = document.getElementById('rulFormattedValue');
        const degEl = document.getElementById('rulDegradationStatus');
        const actEl = document.getElementById('rulMaintenanceAction');
        const circle = document.getElementById('rulGaugeCircle');

        if (hoursEl) hoursEl.textContent = `${rul.rul_hours} HOURS`;
        if (fmtEl) fmtEl.textContent = rul.rul_formatted;

        if (degEl) {
            degEl.textContent = rul.degradation;
            if (rul.degradation === 'LOW') degEl.style.color = 'var(--status-normal)';
            else if (rul.degradation === 'MEDIUM' || rul.degradation === 'MODERATE') degEl.style.color = 'var(--status-warning)';
            else degEl.style.color = 'var(--status-critical)';
        }

        if (actEl) actEl.textContent = rul.maintenance_action;

        if (circle) {
            const maxDash = 471.24;
            const pct = Math.min(100, Math.max(0, rul.gauge_percentage));
            const offset = maxDash - (maxDash * (pct / 100));
            circle.style.strokeDashoffset = offset;
        }
    }

    updateAiConditionAssessment(packet) {
        const titleEl = document.getElementById('aiConditionBannerTitle');
        const confEl = document.getElementById('aiConditionBannerConfidence');
        const tagEl = document.getElementById('aiConditionClassificationTag');

        const displayPred = packet.prediction_display_name || packet.prediction.toUpperCase();
        if (titleEl) titleEl.textContent = displayPred;
        if (confEl) confEl.textContent = `CONFIDENCE: ${packet.confidence}%`;

        if (tagEl) {
            tagEl.className = `badge-pill ${packet.status.toLowerCase()}`;
            tagEl.textContent = packet.status;
        }

        // Update probability bars from model.predict_proba()
        const probs = packet.probabilities || {};
        Object.keys(probs).forEach((key) => {
            const normKey = key.toLowerCase().replace(/\s+/g, '_');
            const valEl = document.getElementById(`prob_val_${normKey}`);
            const fillEl = document.getElementById(`prob_fill_${normKey}`);
            const pct = probs[key];

            if (valEl) valEl.textContent = `${pct}%`;
            if (fillEl) fillEl.style.width = `${pct}%`;
        });
    }

    updateSensorMatrix(s) {
        if (!s) return;

        const mapping = {
            sensor_Voltage_RMS: { val: s.Voltage_RMS, unit: 'V' },
            sensor_Irms: { val: s.Irms, unit: 'A' },
            sensor_Power_Factor: { val: s.Power_Factor, unit: 'PF' },
            sensor_Phase_Angle: { val: s.Phase_Angle, unit: '°' },
            sensor_I_THD: { val: s.I_THD, unit: '%' },
            sensor_RMS_Vibration: { val: s.RMS_Vibration, unit: 'mm/s' },
            sensor_Peak_Acceleration: { val: s.Peak_Acceleration, unit: 'g' },
            sensor_Dominant_Frequency: { val: s.Dominant_Frequency, unit: 'Hz' },
            sensor_Spectral_Energy: { val: s.Spectral_Energy, unit: 'J' },
            sensor_Operating_Hours: { val: s.Operating_Hours, unit: 'H' },
            sensor_Vibration_X: { val: s.Vibration_X, unit: 'g' },
            sensor_Vibration_Y: { val: s.Vibration_Y, unit: 'g' },
            sensor_Vibration_Z: { val: s.Vibration_Z, unit: 'g' },
            sensor_Kurtosis: { val: s.Kurtosis, unit: 'stat' },
            sensor_Skewness: { val: s.Skewness, unit: 'stat' },
            sensor_Variance: { val: s.Variance, unit: 'σ²' },
            sensor_Peak_to_Peak: { val: s.Peak_to_Peak, unit: 'mm' }
        };

        Object.keys(mapping).forEach(tileId => {
            const tile = document.getElementById(tileId);
            if (!tile) return;

            const cfg = mapping[tileId];
            if (cfg.val === undefined) return;

            const valEl = tile.querySelector('.tile-value');
            if (valEl) valEl.textContent = cfg.val;

            // Draw sparkline
            const canvas = tile.querySelector('.tile-sparkline');
            if (canvas) {
                this.drawSparkline(tileId, canvas, cfg.val);
            }
        });
    }

    drawSparkline(key, canvas, newVal) {
        if (!this.sparklineHistory[key]) {
            this.sparklineHistory[key] = [];
        }
        const hist = this.sparklineHistory[key];
        hist.push(newVal);
        if (hist.length > 25) hist.shift();

        const ctx = canvas.getContext('2d');
        const w = canvas.width;
        const h = canvas.height;
        ctx.clearRect(0, 0, w, h);

        if (hist.length < 2) return;

        const min = Math.min(...hist);
        const max = Math.max(...hist);
        const range = max - min || 1;

        ctx.beginPath();
        ctx.strokeStyle = '#00f2fe';
        ctx.lineWidth = 1.5;

        hist.forEach((val, idx) => {
            const x = (idx / (hist.length - 1)) * w;
            const y = h - ((val - min) / range) * (h - 4) - 2;
            if (idx === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });
        ctx.stroke();
    }

    appendAlertEvent(packet) {
        const container = document.getElementById('alertFeedContainer');
        if (!container) return;

        const timeStr = (packet.timestamp || '').split(' ')[1] || new Date().toLocaleTimeString();
        const displayPred = packet.prediction_display_name || packet.prediction.toUpperCase();
        const status = packet.status;

        const item = document.createElement('div');
        item.className = 'alert-event-item';
        item.innerHTML = `
            <div>
                <strong>${timeStr} – ${displayPred} DETECTED</strong>
                <div style="font-size: 0.72rem; color: var(--text-secondary); margin-top: 2px;">
                    Confidence: ${packet.confidence}% | Recommendation: ${packet.recommendation}
                </div>
            </div>
            <span class="badge-pill ${status.toLowerCase()}">${status}</span>
        `;

        container.insertBefore(item, container.firstChild);

        // Keep maximum 30 events
        while (container.children.length > 30) {
            container.removeChild(container.lastChild);
        }
    }
}

// Global Dashboard Instance
document.addEventListener('DOMContentLoaded', () => {
    window.dashboardManager = new DashboardManager();
});
