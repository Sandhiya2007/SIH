/**
 * Conveyor AI - WebSocket Client Engine
 * Handles real-time bi-directional telemetry streaming and auto-reconnection.
 */

class ConveyorWebSocket {
    constructor() {
        this.socket = null;
        this.listeners = [];
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 50;
        this.reconnectInterval = 2000;
        this.isConnected = false;

        this.init();
    }

    getSocketUrl() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host || 'localhost:8000';
        return `${protocol}//${host}/ws`;
    }

    init() {
        const url = this.getSocketUrl();
        console.log(`[WS] Initializing connection to: ${url}`);
        
        try {
            this.socket = new WebSocket(url);

            this.socket.onopen = () => {
                console.log('[WS] Connected to Conveyor AI Telemetry Stream');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                this.updateUIStatus(true);
            };

            this.socket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.notifyListeners(data);
                } catch (err) {
                    console.error('[WS] Failed to parse message JSON:', err);
                }
            };

            this.socket.onclose = () => {
                console.warn('[WS] Connection closed. Attempting reconnect...');
                this.isConnected = false;
                this.updateUIStatus(false);
                this.scheduleReconnect();
            };

            this.socket.onerror = (err) => {
                console.error('[WS] Socket error encountered:', err);
                this.socket.close();
            };
        } catch (e) {
            console.error('[WS] Initialization error:', e);
            this.scheduleReconnect();
        }
    }

    scheduleReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const timeout = Math.min(10000, this.reconnectInterval * Math.min(this.reconnectAttempts, 4));
            setTimeout(() => {
                console.log(`[WS] Reconnecting (Attempt ${this.reconnectAttempts})...`);
                this.init();
            }, timeout);
        }
    }

    onTelemetry(callback) {
        if (typeof callback === 'function') {
            this.listeners.push(callback);
        }
    }

    notifyListeners(data) {
        this.listeners.forEach((cb) => {
            try {
                cb(data);
            } catch (e) {
                console.error('[WS] Error in subscriber callback:', e);
            }
        });
    }

    send(data) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(typeof data === 'string' ? data : JSON.stringify(data));
        } else {
            console.warn('[WS] Cannot send message; socket not connected.');
        }
    }

    updateUIStatus(connected) {
        const connBadges = document.querySelectorAll('.conn-badge');
        const connTexts = document.querySelectorAll('.conn-status-text');
        const dataStreamLeds = document.querySelectorAll('#data-stream-led');

        connBadges.forEach(b => {
            if (connected) {
                b.classList.remove('disconnected');
                b.innerHTML = '<span class="status-led online"></span> WS CONNECTED';
            } else {
                b.classList.add('disconnected');
                b.innerHTML = '<span class="status-led critical"></span> DISCONNECTED';
            }
        });

        connTexts.forEach(t => {
            t.textContent = connected ? 'CONNECTED' : 'OFFLINE';
            t.style.color = connected ? 'var(--status-normal)' : 'var(--status-critical)';
        });

        dataStreamLeds.forEach(led => {
            if (connected) {
                led.className = 'status-led active';
            } else {
                led.className = 'status-led critical';
            }
        });
    }
}

// Global WebSocket Instance
window.conveyorWS = new ConveyorWebSocket();
