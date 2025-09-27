class DHT22MonitorApp {
    constructor() {
        this.elements = {};
        this.state = {
            pollingInterval: null,
            isPolling: false,
            logPollingInterval: null,
            pollingAlignTimeout: null,
            localLogs: [],
            serverLogs: [],
            tempHistory: [],
            humHistory: [],
            lastServerLogStats: { total: 0, shown: 0 },
            filters: {
                categories: new Set(),
                levels: new Set(),
                query: ''
            }
        };
        this.POLL_INTERVAL_MS = 30000;

        document.addEventListener('DOMContentLoaded', () => this.init());
    }

    init() {
        this._initDOMElements();
        this._initEventListeners();
        this._initDisplay();
        this.start();
    }

    _initDOMElements() {
        const ids = [
            'temp', 'hum', 'status-dot', 'status-text', 'last-update', 'interval-text',
            'temp-range', 'hum-range', 'feels-like', 'comfort-level', 'comfort-advice',
            'comfort-indicator', 'discomfort-index', 'temp-trend-inline', 'hum-trend-inline',
            'log', 'log-stats', 'clearLogs', 'download-log', 'log-search',
            'filter-sensor', 'filter-network', 'filter-cloud', 'filter-system', 'filter-general',
            'filter-debug', 'filter-info', 'filter-warning', 'filter-error',
            'enableAllCategories', 'disableAllCategories', 'enableAllLevels', 'errorOnlyFilter',
            'thingspeak-status', 'ts-channel-link', 'ts-json-link', 'ts-csv-link', 'ts-footer-link', 'ts-footer-json'
        ];
        ids.forEach(id => {
            // Convert kebab-case to camelCase for property names
            const camelCaseId = id.replace(/-(\w)/g, (_, c) => c.toUpperCase());
            this.elements[camelCaseId] = document.getElementById(id);
        });
    }

    _initEventListeners() {
        this.elements.clearLogs?.addEventListener('click', () => {
            this.state.localLogs = [];
            this.state.serverLogs = [];
            this.updateLogDisplay();
        });

        this.elements.downloadLog?.addEventListener('click', () => this.downloadLogs());
        this.elements.logSearch?.addEventListener('input', e => {
            this.state.filters.query = e.target.value || '';
            this.updateLogDisplay();
        });

        const filterCheckboxes = [
            this.elements.filterSensor, this.elements.filterNetwork, this.elements.filterCloud,
            this.elements.filterSystem, this.elements.filterGeneral, this.elements.filterDebug,
            this.elements.filterInfo, this.elements.filterWarning, this.elements.filterError
        ];
        filterCheckboxes.forEach(el => el?.addEventListener('change', () => this.syncFilters()));

        this._initQuickActionListeners();
    }

    _initQuickActionListeners() {
        this.elements.enableAllCategories?.addEventListener('click', () => {
            this._setFilterState(['filterSensor', 'filterNetwork', 'filterCloud', 'filterSystem', 'filterGeneral'], true);
        });
        this.elements.disableAllCategories?.addEventListener('click', () => {
            this._setFilterState(['filterSensor', 'filterNetwork', 'filterCloud', 'filterSystem', 'filterGeneral'], false, true);
        });
        this.elements.enableAllLevels?.addEventListener('click', () => {
            this._setFilterState(['filterDebug', 'filterInfo', 'filterWarning', 'filterError'], true);
        });
        this.elements.errorOnlyFilter?.addEventListener('click', () => {
            this._setFilterState(['filterDebug', 'filterInfo', 'filterWarning'], false);
            if (this.elements.filterError) this.elements.filterError.checked = true;
            this.syncFilters();
        });
    }

    _setFilterState(elementKeys, checked, isCategoryOff = false) {
        elementKeys.forEach(key => {
            if (this.elements[key]) this.elements[key].checked = checked;
        });
        this.syncFilters();
        if (isCategoryOff && this.state.filters.categories.size === 0) {
            this.state.filters.categories.add('__NONE__'); // Dummy category to filter out everything
            this.updateLogDisplay();
        }
    }

    _initDisplay() {
        if (this.elements.tempRange) this.elements.tempRange.textContent = '0分間: --°C 〜 --°C';
        if (this.elements.humRange) this.elements.humRange.textContent = '0分間: --% 〜 --%';
        if (this.elements.feelsLike) this.elements.feelsLike.textContent = '--°C';
        if (this.elements.comfortLevel) this.elements.comfortLevel.textContent = '--';
        if (this.elements.comfortAdvice) this.elements.comfortAdvice.textContent = '--';
    }

    start() {
        this.log('🌡️ ESP32 DHT22環境モニター開始', 'system', 'info');
        this.fetchServerLogs();
        this.state.logPollingInterval = setInterval(() => this.fetchServerLogs(), 30000);
        this.initThingSpeakStatus();
        this.startPolling();
    }

    log(msg, category = 'system', level = 'info') {
        const entry = { timestamp: new Date().toLocaleTimeString('ja-JP', { hour12: false }), message: msg, category, level, source: 'local' };
        this.state.localLogs.unshift(entry);
        if (this.state.localLogs.length > 100) this.state.localLogs.pop();
        this.updateLogDisplay();
    }

    async fetchServerLogs() {
        try {
            const res = await fetch('/api/logs?limit=50');
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            this.state.serverLogs = (data.logs || []).map(l => ({ ...l, source: 'server' }));
            this.state.lastServerLogStats.total = data.total_logs || this.state.serverLogs.length;
            this.updateLogDisplay();
        } catch (e) {
            // Non-critical error
        }
    }

    getCombinedLogs() {
        const all = [...this.state.serverLogs, ...this.state.localLogs];
        const { query, categories, levels } = this.state.filters;
        const q = query.trim().toLowerCase();
        const hasCat = categories.size > 0;
        const hasLvl = levels.size > 0;

        const filtered = all.filter(e => {
            if (hasCat && !categories.has(e.category)) return false;
            if (hasLvl && !levels.has(e.level)) return false;
            if (q && !((e.message || '').toLowerCase().includes(q) || (e.timestamp || '').toLowerCase().includes(q))) return false;
            return true;
        });
        return filtered.slice(0, 50);
    }

    updateLogDisplay() {
        if (!this.elements.log) return;
        const combined = this.getCombinedLogs();
        this.state.lastServerLogStats.shown = combined.length;

        const categoryEmoji = cat => ({ sensor: '🌡️', network: '📡', cloud: '☁️', system: '⚙️', general: '📝' }[cat] || '📝');
        const levelEmoji = lv => ({ error: '❌', warning: '⚠️', info: 'ℹ️', debug: '🔍' }[lv] || 'ℹ️');

        this.elements.log.innerHTML = combined.map(e => `
            <div class="log-entry log-${e.level}">
                <span class="log-icon category" title="${e.category}">${categoryEmoji(e.category)}</span>
                <span class="log-icon level" title="${e.level}">${levelEmoji(e.level)}</span>
                <span class="log-time">${e.timestamp}</span>
                <span class="log-sep">|</span>
                <span class="log-message">${e.message}</span>
            </div>`).join('');

        if (this.elements.logStats) {
            this.elements.logStats.textContent = `表示中: ${this.state.lastServerLogStats.shown}/${this.state.lastServerLogStats.total} 件`;
        }
    }

    setStatus(kind, text) {
        if (this.elements.statusDot) {
            this.elements.statusDot.className = 'status-dot ' + kind;
        }
        if (this.elements.statusText) {
            this.elements.statusText.textContent = text;
        }
    }

    async startPolling() {
        if (this.state.isPolling) return;
        this.state.isPolling = true;
        this.setStatus('yellow', '接続中...');
        this.log('HTTPポーリング開始', 'network', 'info');
        if (this.elements.intervalText) this.elements.intervalText.textContent = `更新間隔: ${this.POLL_INTERVAL_MS / 1000}秒`;

        const doFetchUpdate = async () => {
            // プライマリ: /api/realtime → フォールバック: /api/data
            const tryRealtime = async () => {
                const res = await fetch('/api/realtime');
                if (!res.ok) {
                    const err = new Error(`HTTP ${res.status}`);
                    err.status = res.status;
                    throw err;
                }
                const data = await res.json();
                if (data && data.temp_c !== undefined && data.hum_pct !== undefined) return data;
                throw new Error('無効なデータ形式');
            };

            const tryDataFallback = async () => {
                const res = await fetch('/api/data');
                if (!res.ok) {
                    const err = new Error(`HTTP ${res.status}`);
                    err.status = res.status;
                    throw err;
                }
                const d = await res.json();
                if (d && d.temperature !== undefined && d.humidity !== undefined) {
                    return {
                        type: 'dht11',
                        temp_c: Number(d.temperature),
                        hum_pct: Number(d.humidity),
                        timestamp: d.timestamp || '',
                        measurement_count: d.measurement_count || 0
                    };
                }
                throw new Error('無効なフォールバックデータ形式');
            };

            try {
                let payload = null;
                try {
                    payload = await tryRealtime();
                } catch (e1) {
                    // /api/realtime が 404 等の場合、/api/data にフォールバック
                    if (e1 && (e1.status === 404 || e1.status === 500 || e1.status === 0)) {
                        this.log('Realtime API 不可 → Data API にフォールバック', 'network', 'warning');
                        payload = await tryDataFallback();
                    } else {
                        throw e1;
                    }
                }

                this.updateSensorReadings(payload);
                this.setStatus('green', '接続済み');
                this.log(`センサーデータ: ${payload.temp_c.toFixed(1)}°C, ${payload.hum_pct.toFixed(1)}%`, 'sensor', 'info');
            } catch (e) {
                console.error('Polling error:', e);
                this.setStatus('red', 'エラー');
                this.log(`通信エラー: ${e.message}`, 'network', 'error');
                if (this.elements.temp) this.elements.temp.textContent = '--';
                if (this.elements.hum) this.elements.hum.textContent = '--';
            }
        };

        await doFetchUpdate();
        const delayToBoundary = this.POLL_INTERVAL_MS - (Date.now() % this.POLL_INTERVAL_MS);
        this.state.pollingAlignTimeout = setTimeout(() => {
            doFetchUpdate();
            this.state.pollingInterval = setInterval(doFetchUpdate, this.POLL_INTERVAL_MS);
        }, delayToBoundary);
    }

    updateSensorReadings(data) {
        if (this.elements.temp) this.elements.temp.textContent = data.temp_c.toFixed(1);
        if (this.elements.hum) this.elements.hum.textContent = data.hum_pct.toFixed(1);
        if (this.elements.lastUpdate) this.elements.lastUpdate.textContent = data.timestamp || '--';
        this.updateComfort(data.temp_c, data.hum_pct);
        this.updateRanges(data.temp_c, data.hum_pct);
    }

    updateComfort(temp, hum) {
        if (temp == null || hum == null) return;
        const feels = temp + (hum - 60) * 0.1;
        let level = '普通', advice = '--', score = 70, color = '#eab308';
        if (temp < 18) { level = '寒い'; advice = '暖房推奨'; score = 40; color = '#ef4444'; }
        else if (temp > 26) { level = '暑い'; advice = '冷房推奨'; score = 40; color = '#ef4444'; }
        else if (temp >= 22 && temp <= 25 && hum >= 45 && hum <= 65) { level = '快適'; advice = '理想的'; score = 90; color = '#22c55e'; }

        if (this.elements.feelsLike) this.elements.feelsLike.textContent = feels.toFixed(1) + '°C';
        if (this.elements.comfortLevel) this.elements.comfortLevel.textContent = level;
        if (this.elements.comfortAdvice) this.elements.comfortAdvice.textContent = advice;
        if (this.elements.comfortIndicator) {
            this.elements.comfortIndicator.style.width = score + '%';
            this.elements.comfortIndicator.style.backgroundColor = color;
        }
        const di = 0.81 * temp + 0.01 * hum * (0.99 * temp - 14.3) + 46.3;
        if (this.elements.discomfortIndex) this.elements.discomfortIndex.textContent = di.toFixed(1);
    }

    updateRanges(temp, hum) {
        const now = Date.now();
        this.state.tempHistory.unshift({ value: temp, time: now });
        this.state.humHistory.unshift({ value: hum, time: now });

        const tenMinAgo = now - 600000;
        this.state.tempHistory = this.state.tempHistory.filter(d => d.time > tenMinAgo).slice(0, 60);
        this.state.humHistory = this.state.humHistory.filter(d => d.time > tenMinAgo).slice(0, 60);

        this._updateRangeElement(this.elements.tempRange, this.elements.tempTrendInline, this.state.tempHistory, '°C');
        this._updateRangeElement(this.elements.humRange, this.elements.humTrendInline, this.state.humHistory, '%');
    }

    _updateRangeElement(rangeEl, trendEl, history, unit) {
        if (rangeEl && history.length > 1) {
            const values = history.map(d => d.value);
            const min = Math.min(...values), max = Math.max(...values);
            const duration = Math.floor((Date.now() - Math.min(...history.map(d => d.time))) / 60000);
            const trend = history.length >= 3 ? (history[0].value > history[2].value ? '📈' : history[0].value < history[2].value ? '📉' : '➡️') : '➡️';
            rangeEl.textContent = `${duration}分間: ${min.toFixed(1)}${unit} 〜 ${max.toFixed(1)}${unit}`;
            if (trendEl) trendEl.textContent = trend;
        }
    }

    syncFilters() {
        const catMap = { sensor: this.elements.filterSensor, network: this.elements.filterNetwork, cloud: this.elements.filterCloud, system: this.elements.filterSystem, general: this.elements.filterGeneral };
        const lvlMap = { debug: this.elements.filterDebug, info: this.elements.filterInfo, warning: this.elements.filterWarning, error: this.elements.filterError };

        this.state.filters.categories.clear();
        for (const [k, el] of Object.entries(catMap)) { if (el?.checked) this.state.filters.categories.add(k); }

        this.state.filters.levels.clear();
        for (const [k, el] of Object.entries(lvlMap)) { if (el?.checked) this.state.filters.levels.add(k); }

        this.updateLogDisplay();
    }

    downloadLogs() {
        const rows = this.getCombinedLogs().map(e => ({
            time: e.timestamp || '',
            level: e.level || '',
            category: e.category || '',
            source: e.source || '',
            message: (e.message || '').replace(/\n/g, ' ')
        }));
        const header = 'time,level,category,source,message';
        const csv = [header, ...rows.map(r => [
            r.time, r.level, r.category, r.source, `"${r.message.replace(/"/g, '""')}"`
        ].join(','))].join('\n');

        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        const ts = new Date().toISOString().replace(/[:T]/g, '-').split('.')[0];
        a.href = url;
        a.download = `logs-${ts}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    async initThingSpeakStatus() {
        try {
            const res = await fetch('/config');
            if (!res.ok) return;
            const cfg = await res.json();

            let statusText = '無効';
            if (cfg.thingspeak_enabled && cfg.urequests_available && cfg.thingspeak_api_key_configured) {
                statusText = '有効';
            } else if (cfg.thingspeak_enabled) {
                statusText = '未設定';
            }
            if (this.elements.thingspeakStatus) this.elements.thingspeakStatus.textContent = statusText;

            if (cfg.thingspeak_channel_id) {
                const chUrl = `https://thingspeak.com/channels/${cfg.thingspeak_channel_id}`;
                const jsonUrl = `https://api.thingspeak.com/channels/${cfg.thingspeak_channel_id}/feeds.json?results=10`;
                const csvUrl = `https://api.thingspeak.com/channels/${cfg.thingspeak_channel_id}/feeds.csv?results=20`;

                if (this.elements.tsChannelLink) { this.elements.tsChannelLink.href = chUrl; this.elements.tsChannelLink.textContent = String(cfg.thingspeak_channel_id); }
                if (this.elements.tsJsonLink) this.elements.tsJsonLink.href = jsonUrl;
                if (this.elements.tsCsvLink) this.elements.tsCsvLink.href = csvUrl;
                if (this.elements.tsFooterLink) this.elements.tsFooterLink.href = chUrl;
                if (this.elements.tsFooterJson) this.elements.tsFooterJson.href = jsonUrl;
            }
        } catch (e) {
            // Non-critical error
        }
    }
}

new DHT22MonitorApp();