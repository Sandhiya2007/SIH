/**
 * Conveyor AI - Data Simulation & Stream Control Engine (Two-Laptop Support)
 * Manages dataset row selection, streaming lifecycle, and ground-truth comparison.
 */

class ControlManager {
    constructor() {
        this.totalRows = 2000;
        this.currentRow = 1;
        this.isStreaming = false;

        this.init();
    }

    async init() {
        console.log('[Control] Initializing Data Simulation Controller...');

        // Bind button actions
        this.bindEvents();

        // Fetch dataset info
        await this.loadDatasetInfo();

        // Fetch system status for LAN URLs
        await this.loadSystemStatus();

        // Subscribe to WebSocket for real-time stream synchronization across laptops
        if (window.conveyorWS) {
            window.conveyorWS.onTelemetry((packet) => this.handleTelemetry(packet));
        }

        // Fetch current stream status
        await this.fetchStreamStatus();
    }

    bindEvents() {
        const btnStart = document.getElementById('btnStartStream');
        const btnPause = document.getElementById('btnPauseStream');
        const btnStop = document.getElementById('btnStopStream');
        const btnReset = document.getElementById('btnResetStream');
        const btnInject = document.getElementById('btnInjectRow');
        const rowInput = document.getElementById('rowInputNumber');
        const rowSlider = document.getElementById('rowSlider');

        if (btnStart) btnStart.addEventListener('click', () => this.startStream());
        if (btnPause) btnPause.addEventListener('click', () => this.pauseStream());
        if (btnStop) btnStop.addEventListener('click', () => this.stopStream());
        if (btnReset) btnReset.addEventListener('click', () => this.resetStream());

        if (btnInject) {
            btnInject.addEventListener('click', () => {
                const val = parseInt(rowInput.value, 10) || 1;
                this.injectRow(val);
            });
        }

        if (rowSlider && rowInput) {
            rowSlider.addEventListener('input', (e) => {
                rowInput.value = e.target.value;
            });
            rowInput.addEventListener('change', (e) => {
                rowSlider.value = e.target.value;
            });
        }
    }

    async loadDatasetInfo() {
        try {
            const res = await fetch('/api/dataset/info');
            const data = await res.json();
            if (data && data.loaded) {
                this.totalRows = data.total_rows || 2000;

                const fnEl = document.getElementById('datasetFileName');
                const rowsEl = document.getElementById('datasetTotalRows');
                const condEl = document.getElementById('datasetConditionsCount');
                const metaFn = document.getElementById('metaDatasetName');
                const metaRows = document.getElementById('metaTotalRows');
                const metaCond = document.getElementById('metaTotalConditions');
                const slider = document.getElementById('rowSlider');
                const endRowInput = document.getElementById('endRowInput');
                const rowInput = document.getElementById('rowInputNumber');

                if (fnEl) fnEl.textContent = data.filename;
                if (rowsEl) rowsEl.textContent = `${this.totalRows} SAMPLES`;
                if (condEl) condEl.textContent = `${(data.detected_classes || []).length} CLASSES`;
                if (metaFn) metaFn.textContent = data.filename;
                if (metaRows) metaRows.textContent = `${this.totalRows.toLocaleString()} Rows`;
                if (metaCond) metaCond.textContent = `${(data.detected_classes || []).length} Classes (${(data.detected_classes || []).map(c => c.toUpperCase()).join(', ')})`;
                if (slider) slider.max = this.totalRows;
                if (endRowInput) endRowInput.value = this.totalRows;
                if (rowInput) rowInput.max = this.totalRows;
            }
        } catch (e) {
            console.error('[Control] Failed to load dataset info:', e);
        }
    }

    async loadSystemStatus() {
        try {
            const res = await fetch('/api/status');
            const data = await res.json();
            if (data) {
                const l1 = document.getElementById('laptop1Url');
                const l2 = document.getElementById('laptop2Url');
                if (l1) l1.textContent = `http://${data.lan_ip}:${data.port}/dashboard`;
                if (l2) l2.textContent = `http://${data.lan_ip}:${data.port}/control`;
            }
        } catch (e) {
            console.warn('[Control] Failed to fetch system status:', e);
        }
    }

    async fetchStreamStatus() {
        try {
            const res = await fetch('/api/stream/status');
            const data = await res.json();
            if (data) {
                this.updateStreamUI(data);
            }
        } catch (e) {
            console.warn('[Control] Failed to fetch stream status:', e);
        }
    }

    async startStream() {
        const startRow = parseInt(document.getElementById('startRowInput')?.value, 10) || 1;
        const endRow = parseInt(document.getElementById('endRowInput')?.value, 10) || this.totalRows;
        const speed = parseFloat(document.getElementById('streamSpeedSelect')?.value) || 2.0;

        try {
            const res = await fetch('/api/stream/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ start_row: startRow, end_row: endRow, speed: speed })
            });
            const data = await res.json();
            if (data.status === 'success') {
                this.isStreaming = true;
                this.updateStreamingControls(true);
            }
        } catch (e) {
            console.error('[Control] Failed to start stream:', e);
        }
    }

    async pauseStream() {
        try {
            await fetch('/api/stream/pause', { method: 'POST' });
            this.updateStreamingControls(false);
        } catch (e) {
            console.error('[Control] Failed to pause stream:', e);
        }
    }

    async stopStream() {
        try {
            await fetch('/api/stream/stop', { method: 'POST' });
            this.isStreaming = false;
            this.updateStreamingControls(false);
        } catch (e) {
            console.error('[Control] Failed to stop stream:', e);
        }
    }

    async resetStream() {
        try {
            await fetch('/api/stream/reset', { method: 'POST' });
            this.isStreaming = false;
            this.updateStreamingControls(false);

            // Reset UI counters
            document.getElementById('statTotalPredictions').textContent = '0';
            document.getElementById('statCorrectPredictions').textContent = '0';
            document.getElementById('statIncorrectPredictions').textContent = '0';
            document.getElementById('statRunningAccuracy').textContent = '100.0%';
            document.getElementById('currentRowDisplay').textContent = `ROW 1 / ${this.totalRows} (0.05%)`;
            document.getElementById('streamProgressBar').style.width = '0.05%';
            document.getElementById('injectedRowsTableBody').innerHTML = '';
        } catch (e) {
            console.error('[Control] Failed to reset stream:', e);
        }
    }

    async injectRow(rowNumber) {
        try {
            const res = await fetch('/api/stream/inject-row', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ row_number: rowNumber })
            });
            const data = await res.json();
            if (data.status === 'success' && data.packet) {
                this.handleTelemetry(data.packet);
            }
        } catch (e) {
            console.error('[Control] Failed to inject row:', e);
        }
    }

    handleTelemetry(packet) {
        if (!packet || packet.type === 'CONNECTION_ESTABLISHED') return;

        // 1. Progress & Row
        const row = packet.row_number || 1;
        this.currentRow = row;
        const pct = Math.min(100, Math.max(0, (row / this.totalRows) * 100)).toFixed(2);

        const rowDisplay = document.getElementById('currentRowDisplay');
        const progressBar = document.getElementById('streamProgressBar');
        const slider = document.getElementById('rowSlider');
        const inputNum = document.getElementById('rowInputNumber');

        if (rowDisplay) rowDisplay.textContent = `ROW ${row} / ${this.totalRows} (${pct}%)`;
        if (progressBar) progressBar.style.width = `${pct}%`;
        if (slider) slider.value = row;
        if (inputNum) inputNum.value = row;

        // 2. Running Accuracy Statistics (Section 24)
        const st = packet.stream_status;
        if (st) {
            const totEl = document.getElementById('statTotalPredictions');
            const corrEl = document.getElementById('statCorrectPredictions');
            const incEl = document.getElementById('statIncorrectPredictions');
            const accEl = document.getElementById('statRunningAccuracy');

            if (totEl) totEl.textContent = (st.total_processed || 0).toLocaleString();
            if (corrEl) corrEl.textContent = (st.correct_predictions || 0).toLocaleString();
            if (incEl) incEl.textContent = (st.incorrect_predictions || 0).toLocaleString();
            if (accEl) accEl.textContent = `${st.running_accuracy || 100.0}%`;
        }

        // 3. Comparison Hero Card (Section 23)
        const compRow = document.getElementById('compareRowNumber');
        const compHours = document.getElementById('compareOperatingHours');
        const actualEl = document.getElementById('compareActualLabel');
        const predEl = document.getElementById('compareAiPrediction');
        const confEl = document.getElementById('compareConfidence');
        const matchBanner = document.getElementById('compareMatchBanner');

        if (compRow) compRow.textContent = `ROW ${row} SNAPSHOT`;
        if (compHours) compHours.textContent = `OPERATING HOURS: ${packet.operating_hours.toLocaleString()} H`;

        const displayActual = packet.actual_display_name || packet.actual_condition.toUpperCase();
        const displayPred = packet.prediction_display_name || packet.prediction.toUpperCase();

        if (actualEl) actualEl.textContent = displayActual;
        if (predEl) {
            predEl.textContent = displayPred;
            if (packet.status === 'NORMAL') predEl.style.color = 'var(--status-normal)';
            else if (packet.status === 'WARNING') predEl.style.color = 'var(--status-warning)';
            else predEl.style.color = 'var(--status-critical)';
        }

        if (confEl) confEl.textContent = `${packet.confidence}%`;

        if (matchBanner) {
            if (packet.correct === true) {
                matchBanner.className = 'match-result-banner match';
                matchBanner.innerHTML = '<span>✓</span> RESULT: CORRECT (ACTUAL == PREDICTED)';
            } else if (packet.correct === false) {
                matchBanner.className = 'match-result-banner mismatch';
                matchBanner.innerHTML = '<span>✗</span> RESULT: MISMATCH (DISCREPANCY DETECTED)';
            } else {
                matchBanner.className = 'match-result-banner match';
                matchBanner.innerHTML = '<span>●</span> INFERENCE ACTIVE';
            }
        }

        // 4. Append to Stream History Table
        this.appendHistoryRow(packet);
    }

    appendHistoryRow(packet) {
        const tbody = document.getElementById('injectedRowsTableBody');
        if (!tbody) return;

        const row = document.createElement('tr');
        const isMatch = packet.correct === true;
        const matchBadge = isMatch
            ? '<span class="badge-pill normal" style="font-size:0.7rem; padding: 2px 8px;">✓ CORRECT</span>'
            : '<span class="badge-pill critical" style="font-size:0.7rem; padding: 2px 8px;">✗ MISMATCH</span>';

        const displayActual = packet.actual_display_name || packet.actual_condition.toUpperCase();
        const displayPred = packet.prediction_display_name || packet.prediction.toUpperCase();

        row.innerHTML = `
            <td style="font-family: var(--font-mono); font-weight: 700; color: var(--cyan-primary);">${packet.row_number}</td>
            <td style="font-family: var(--font-mono);">${packet.operating_hours.toLocaleString()} H</td>
            <td style="font-weight: 600; color: #38bdf8;">${displayActual}</td>
            <td style="font-weight: 600;">${displayPred}</td>
            <td style="font-family: var(--font-mono);">${packet.confidence}%</td>
            <td>${matchBadge}</td>
        `;

        tbody.insertBefore(row, tbody.firstChild);

        // Keep maximum 40 rows
        while (tbody.children.length > 40) {
            tbody.removeChild(tbody.lastChild);
        }
    }

    updateStreamUI(status) {
        this.isStreaming = status.is_streaming && !status.is_paused;
        this.updateStreamingControls(this.isStreaming);
    }

    updateStreamingControls(active) {
        const tag = document.getElementById('streamEngineStatusTag');
        const btnStart = document.getElementById('btnStartStream');

        if (tag) {
            if (active) {
                tag.textContent = 'STREAMING RUNNING';
                tag.className = 'badge-pill normal';
            } else {
                tag.textContent = 'IDLE / PAUSED';
                tag.className = 'badge-pill warning';
            }
        }

        if (btnStart) {
            btnStart.style.opacity = active ? '0.7' : '1.0';
        }
    }
}

// Global Control Instance
document.addEventListener('DOMContentLoaded', () => {
    window.controlManager = new ControlManager();
});
