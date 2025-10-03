let ws;
let reconnectInterval;

// 基本要素
const statusDotEl = document.getElementById('status-dot');
const statusTextEl = document.getElementById('status-text');
const tempEl = document.getElementById('temp');
const humidEl = document.getElementById('hum');
const intervalTextEl = document.getElementById('interval-text');
const lastUpdateEl = document.getElementById('last-update');

// 快適性指標要素
const feelsLikeEl = document.getElementById('feels-like');
const comfortLevelEl = document.getElementById('comfort-level');
const comfortAdviceEl = document.getElementById('comfort-advice');
const discomfortIndexEl = document.getElementById('discomfort-index');
const comfortIndicatorEl = document.getElementById('comfort-indicator');

// ThingSpeak関連要素
const thingspeakStatusEl = document.getElementById('thingspeak-status');

// ログ関連要素
const logEl = document.getElementById('log');
const logStatsEl = document.getElementById('log-stats');
const logSearchEl = document.getElementById('log-search');
const clearLogsBtn = document.getElementById('clearLogs');
const downloadLogBtn = document.getElementById('download-log');

// 範囲表示要素
const tempRangeEl = document.getElementById('temp-range');
const humRangeEl = document.getElementById('hum-range');

// セッション継続性のための変数
let connectionCount = 0;
let totalUptime = 0;
let lastConnectTime = 0;

// データ保存用
let sensorData = {
    temperature: { min: null, max: null, history: [] },
    humidity: { min: null, max: null, history: [] }
};

// ログ機能
let systemLogs = [];
let logFilters = {
    categories: { sensor: true, network: true, cloud: true, system: true, general: true },
    levels: { debug: false, info: true, warning: true, error: true }
};

// 更新間隔
let currentInterval = 30;

// ログ機能の拡張
function log(message, category = 'general', level = 'info') {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('ja-JP');
    const fullMessage = `[${timeStr}] ${message}`;

    console.log(fullMessage);

    // システムログに追加
    const logEntry = {
        timestamp: now,
        message: message,
        category: category,
        level: level,
        timeStr: timeStr
    };

    systemLogs.unshift(logEntry); // 新しいログを先頭に追加

    // 最大1000件まで保持
    if (systemLogs.length > 1000) {
        systemLogs = systemLogs.slice(0, 1000);
    }

    updateLogDisplay();
}

// ログ表示の更新
function updateLogDisplay() {
    if (!logEl) return;

    // フィルタリング
    const filteredLogs = systemLogs.filter(entry => {
        return logFilters.categories[entry.category] && logFilters.levels[entry.level];
    });

    // 検索フィルタ
    const searchTerm = logSearchEl?.value?.toLowerCase() || '';
    const searchedLogs = filteredLogs.filter(entry =>
        entry.message.toLowerCase().includes(searchTerm)
    );

    // 表示更新
    logEl.innerHTML = searchedLogs.map(entry => {
        const levelIcon = {
            debug: '🔍',
            info: 'ℹ️',
            warning: '⚠️',
            error: '❌'
        }[entry.level] || 'ℹ️';

        const categoryIcon = {
            sensor: '🌡️',
            network: '📡',
            cloud: '☁️',
            system: '⚙️',
            general: '📝'
        }[entry.category] || '📝';

        return `
            <div class="log-entry ${entry.level}">
                <span class="log-time">${entry.timeStr}</span>
                <span class="log-category">${categoryIcon}</span>
                <span class="log-level">${levelIcon}</span>
                <span class="log-message">${entry.message}</span>
            </div>
        `;
    }).join('');

    // 統計更新
    if (logStatsEl) {
        logStatsEl.textContent = `表示中: ${searchedLogs.length}/${systemLogs.length} 件`;
    }
}

// WebSocket接続を確立
function connectWebSocket() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        return;
    }

    log('🔌 WebSocket接続試行中...');
    ws = new WebSocket('ws://' + window.location.host + '/');

    ws.onopen = function() {
        connectionCount++;
        lastConnectTime = Date.now();

        log(`connected (#${connectionCount})`, 'network', 'info');

        // 接続状態の表示更新
        if (statusDotEl) {
            statusDotEl.className = 'status-dot green';
        }
        if (statusTextEl) {
            statusTextEl.textContent = `接続済み (#${connectionCount})`;
        }

        // 更新間隔表示
        if (intervalTextEl) {
            intervalTextEl.textContent = `更新間隔: ${currentInterval}秒`;
        }

        // 再接続タイマーをクリア
        if (reconnectInterval) {
            clearTimeout(reconnectInterval);
            reconnectInterval = null;
        }

        // Keep-alive ping送信（8秒間隔でより頻繁に）
        ws.pingInterval = setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
                log('Keep-alive ping送信', 'network', 'debug');
                ws.send('ping');
            }
        }, 8000);
    };

    ws.onclose = function(event) {
        // 接続時間を計算
        if (lastConnectTime > 0) {
            const sessionDuration = (Date.now() - lastConnectTime) / 1000;
            totalUptime += sessionDuration;
            log(`closed after ${sessionDuration.toFixed(1)}s (code: ${event.code})`, 'network', 'warning');
            log(`Stats - Connections: ${connectionCount}, Total uptime: ${totalUptime.toFixed(1)}s`, 'network', 'info');
        }

        // 再接続状態の表示
        if (statusDotEl) {
            statusDotEl.className = 'status-dot orange';
        }
        if (statusTextEl) {
            statusTextEl.textContent = '再接続中...';
        }

        // Pingタイマーをクリア
        if (ws.pingInterval) {
            clearInterval(ws.pingInterval);
        }

        // 即座に再接続（ESP32-S3の10秒制限対応）
        if (!reconnectInterval) {
            reconnectInterval = setTimeout(() => {
                log('高速再接続試行...', 'network', 'info');
                connectWebSocket();
            }, 100);  // 100ms後に即座に再接続
        }
    };

    ws.onerror = function(error) {
        log('WebSocketエラー: ' + error, 'network', 'error');

        // エラー状態の表示
        if (statusDotEl) {
            statusDotEl.className = 'status-dot red';
        }
        if (statusTextEl) {
            statusTextEl.textContent = 'エラー';
        }
    };

    ws.onmessage = function(event) {
        // Pingレスポンスは無視
        if (event.data === 'pong') {
            log('Keep-alive pong受信', 'network', 'debug');
            return;
        }

        try {
            const data = JSON.parse(event.data);

            // キープアライブデータの処理
            if (data.type === 'keepalive') {
                log(`キープアライブ受信 - メモリ:${data.memory}B, 接続数:${data.clients}`, 'system', 'debug');
                return;
            }

            // ThingSpeakステータス更新
            if (data.thingspeak_status && thingspeakStatusEl) {
                thingspeakStatusEl.textContent = data.thingspeak_status;
            }

            if (data.error) {
                log('センサーエラー: ' + data.error, 'sensor', 'error');

                // エラー状態の表示
                if (tempEl) tempEl.textContent = '--';
                if (humidEl) humidEl.textContent = '--';
                if (feelsLikeEl) feelsLikeEl.textContent = '--°C';
                if (comfortLevelEl) comfortLevelEl.textContent = '--';
                if (comfortAdviceEl) comfortAdviceEl.textContent = '--';
                if (discomfortIndexEl) discomfortIndexEl.textContent = '--';
            } else {
                // センサーデータの更新
                updateSensorData(data);

                log(`センサー値更新 - 温度:${data.temperature.toFixed(1)}°C, 湿度:${data.humidity.toFixed(1)}%`, 'sensor', 'info');
            }
        } catch (e) {
            log('データ解析エラー: ' + e.message, 'system', 'error');
        }
    }
}

// センサーデータ更新関数
function updateSensorData(data) {
    const temp = data.temperature;
    const humid = data.humidity;

    // 基本データ表示
    if (tempEl) {
        tempEl.textContent = temp.toFixed(1);
    }
    if (humidEl) {
        humidEl.textContent = humid.toFixed(1);
    }

    // データ履歴に追加
    sensorData.temperature.history.push(temp);
    sensorData.humidity.history.push(humid);

    // 最新100ポイントのみ保持
    if (sensorData.temperature.history.length > 100) {
        sensorData.temperature.history.shift();
        sensorData.humidity.history.shift();
    }

    // 最小最大値の更新
    if (sensorData.temperature.min === null || temp < sensorData.temperature.min) {
        sensorData.temperature.min = temp;
    }
    if (sensorData.temperature.max === null || temp > sensorData.temperature.max) {
        sensorData.temperature.max = temp;
    }
    if (sensorData.humidity.min === null || humid < sensorData.humidity.min) {
        sensorData.humidity.min = humid;
    }
    if (sensorData.humidity.max === null || humid > sensorData.humidity.max) {
        sensorData.humidity.max = humid;
    }

    // 範囲表示の更新
    if (tempRangeEl) {
        tempRangeEl.textContent = `範囲: ${sensorData.temperature.min?.toFixed(1) || '--'}°C 〜 ${sensorData.temperature.max?.toFixed(1) || '--'}°C`;
    }
    if (humRangeEl) {
        humRangeEl.textContent = `範囲: ${sensorData.humidity.min?.toFixed(1) || '--'}% 〜 ${sensorData.humidity.max?.toFixed(1) || '--%'}%`;
    }

    // 快適性指標の計算と更新
    updateComfortIndicators(temp, humid);

    // 最終更新時刻
    if (lastUpdateEl) {
        lastUpdateEl.textContent = `最終更新: ${new Date().toLocaleTimeString('ja-JP')}`;
    }
}

// 快適性指標の計算
function updateComfortIndicators(temp, humid) {
    // 体感温度（Heat Index）の計算
    const feelsLike = calculateFeelsLike(temp, humid);
    if (feelsLikeEl) {
        feelsLikeEl.textContent = `${feelsLike.toFixed(1)}°C`;
    }

    // 不快指数の計算
    const discomfortIndex = 0.81 * temp + 0.01 * humid * (0.99 * temp - 14.3) + 46.3;
    if (discomfortIndexEl) {
        discomfortIndexEl.textContent = discomfortIndex.toFixed(1);
    }

    // 快適度の判定
    const comfort = getComfortLevel(temp, humid, discomfortIndex);
    if (comfortLevelEl) {
        comfortLevelEl.textContent = comfort.level;
    }
    if (comfortAdviceEl) {
        comfortAdviceEl.textContent = comfort.advice;
    }

    // 快適性バーの更新
    if (comfortIndicatorEl) {
        const percentage = Math.max(0, Math.min(100, (80 - discomfortIndex) * 2.5));
        comfortIndicatorEl.style.width = `${percentage}%`;
        comfortIndicatorEl.className = `comfort-progress ${comfort.class}`;
    }
}

// 体感温度計算
function calculateFeelsLike(temp, humid) {
    if (temp >= 27) {
        // 暑い場合の体感温度
        return temp + 0.36 * (humid - 70);
    } else if (temp <= 10) {
        // 寒い場合の体感温度（風速は仮に5km/hとする）
        const windSpeed = 5;
        return 13.12 + 0.6215 * temp - 11.37 * Math.pow(windSpeed, 0.16) + 0.3965 * temp * Math.pow(windSpeed, 0.16);
    } else {
        // 中間の場合は実温度とほぼ同じ
        return temp;
    }
}

// 快適度判定（改善版：一般的な体感に合わせて調整）
function getComfortLevel(temp, humid, discomfortIndex) {
    if (discomfortIndex < 55) {
        return { level: '寒い', advice: '暖房・厚着推奨', class: 'cold' };
    } else if (discomfortIndex < 60) {
        return { level: 'やや寒い', advice: '軽い防寒対策', class: 'cool' };
    } else if (discomfortIndex < 65) {
        return { level: '快適', advice: '理想的な環境', class: 'comfortable' };
    } else if (discomfortIndex < 70) {
        return { level: 'やや快適', advice: '概ね良好な環境', class: 'comfortable' };
    } else if (discomfortIndex < 75) {
        return { level: 'やや暑い', advice: '軽い冷房推奨', class: 'warm' };
    } else if (discomfortIndex < 80) {
        return { level: '暑い', advice: '冷房・水分補給', class: 'hot' };
    } else if (discomfortIndex < 85) {
        return { level: '非常に暑い', advice: '強力な冷房必要', class: 'very-hot' };
    } else {
        return { level: '危険な暑さ', advice: '熱中症注意・屋内避難', class: 'dangerous' };
    }
}

// ログイベントハンドラーの初期化
function initializeLogEventHandlers() {
    // 検索フィルタ
    if (logSearchEl) {
        logSearchEl.addEventListener('input', updateLogDisplay);
    }

    // フィルタチェックボックス
    const categoryFilters = ['sensor', 'network', 'cloud', 'system', 'general'];
    categoryFilters.forEach(category => {
        const checkbox = document.getElementById(`filter-${category}`);
        if (checkbox) {
            checkbox.checked = logFilters.categories[category];
            checkbox.addEventListener('change', () => {
                logFilters.categories[category] = checkbox.checked;
                updateLogDisplay();
            });
        }
    });

    const levelFilters = ['debug', 'info', 'warning', 'error'];
    levelFilters.forEach(level => {
        const checkbox = document.getElementById(`filter-${level}`);
        if (checkbox) {
            checkbox.checked = logFilters.levels[level];
            checkbox.addEventListener('change', () => {
                logFilters.levels[level] = checkbox.checked;
                updateLogDisplay();
            });
        }
    });

    // クイックアクション
    const enableAllCategoriesBtn = document.getElementById('enableAllCategories');
    if (enableAllCategoriesBtn) {
        enableAllCategoriesBtn.addEventListener('click', () => {
            categoryFilters.forEach(category => {
                logFilters.categories[category] = true;
                const checkbox = document.getElementById(`filter-${category}`);
                if (checkbox) checkbox.checked = true;
            });
            updateLogDisplay();
        });
    }

    const disableAllCategoriesBtn = document.getElementById('disableAllCategories');
    if (disableAllCategoriesBtn) {
        disableAllCategoriesBtn.addEventListener('click', () => {
            categoryFilters.forEach(category => {
                logFilters.categories[category] = false;
                const checkbox = document.getElementById(`filter-${category}`);
                if (checkbox) checkbox.checked = false;
            });
            updateLogDisplay();
        });
    }

    const enableAllLevelsBtn = document.getElementById('enableAllLevels');
    if (enableAllLevelsBtn) {
        enableAllLevelsBtn.addEventListener('click', () => {
            levelFilters.forEach(level => {
                logFilters.levels[level] = true;
                const checkbox = document.getElementById(`filter-${level}`);
                if (checkbox) checkbox.checked = true;
            });
            updateLogDisplay();
        });
    }

    const errorOnlyBtn = document.getElementById('errorOnlyFilter');
    if (errorOnlyBtn) {
        errorOnlyBtn.addEventListener('click', () => {
            levelFilters.forEach(level => {
                logFilters.levels[level] = (level === 'error');
                const checkbox = document.getElementById(`filter-${level}`);
                if (checkbox) checkbox.checked = (level === 'error');
            });
            updateLogDisplay();
        });
    }

    // ログクリア
    if (clearLogsBtn) {
        clearLogsBtn.addEventListener('click', () => {
            if (confirm('すべてのログをクリアしますか？')) {
                systemLogs = [];
                updateLogDisplay();
                log('ログがクリアされました', 'system', 'info');
            }
        });
    }

    // ログダウンロード
    if (downloadLogBtn) {
        downloadLogBtn.addEventListener('click', () => {
            downloadLogs();
        });
    }
}

// ログダウンロード機能
function downloadLogs() {
    const logText = systemLogs.map(entry =>
        `${entry.timestamp.toISOString()} [${entry.level.toUpperCase()}] [${entry.category}] ${entry.message}`
    ).join('\n');

    const blob = new Blob([logText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `esp32-logs-${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    log('ログファイルをダウンロードしました', 'system', 'info');
}

// 初期化処理
function initialize() {
    log('DHT22 Monitor初期化開始', 'system', 'info');

    // ログイベントハンドラーの初期化
    initializeLogEventHandlers();

    // WebSocket接続を開始
    connectWebSocket();

    log('初期化完了', 'system', 'info');
}

// 接続状況監視（デバッグ用）
setInterval(() => {
    if (ws) {
        log(`WebSocket状態: ${ws.readyState} (0:接続中, 1:開放, 2:閉鎖中, 3:閉鎖済み)`, 'network', 'debug');

        // メモリ使用量監視（対応ブラウザのみ）
        if (performance.memory) {
            const usedMB = Math.round(performance.memory.usedJSHeapSize / 1024 / 1024);
            const totalMB = Math.round(performance.memory.totalJSHeapSize / 1024 / 1024);
            log(`メモリ使用量: ${usedMB}MB / ${totalMB}MB`, 'system', 'debug');
        }
    }
}, 60000); // 60秒間隔

// DOMContentLoadedで初期化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize);
} else {
    initialize();
}