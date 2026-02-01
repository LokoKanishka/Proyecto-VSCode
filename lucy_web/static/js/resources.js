const resourceGpu = document.getElementById('resource-gpu');
const resourceWindows = document.getElementById('resource-windows');
const summaryText = document.getElementById('memory-summary');
const summaryTimestamp = document.getElementById('memory-summary-timestamp');
const planSummary = document.getElementById('plan-summary');
const planSteps = document.getElementById('plan-steps');
const watcherEventsList = document.getElementById('watcher-events-list');
const busMetricsSummary = document.getElementById('bus-metrics-summary');
const busMetricsRecent = document.getElementById('bus-metrics-recent');
const bridgeMetricsSummary = document.getElementById('bridge-metrics-summary');
const bridgeMetricsRecent = document.getElementById('bridge-metrics-recent');
const stageLatencySummary = document.getElementById('stage-latency-summary');
const stageLatencyRecent = document.getElementById('stage-latency-recent');
const memoryEventsList = document.getElementById('memory-events-list');
const toastContainer = document.getElementById('toast-container');
let lastBridgeToast = 0;

async function updateResourcePanel() {
    try {
        const resp = await fetch('/api/resource_events');
        const data = await resp.json();
        const gpu = data.summary?.gpu;
        resourceGpu.textContent = gpu ? `${(gpu * 100).toFixed(1)}%` : 'N/A';
        resourceWindows.innerHTML = '';
        if (data.summary?.windows.length) {
            data.summary.windows.forEach(win => {
                const item = document.createElement('div');
                item.className = 'resource-window';
                item.textContent = `${win.title} (${win.window_id})`;
                resourceWindows.appendChild(item);
            });
        } else {
        resourceWindows.textContent = 'No hay ventanas recientes.';
    }
        if (gpu && gpu >= 0.85 && window.updateStatus) {
            updateStatus('GPU alta, priorizando tareas ligeras.', 'warning');
        }
    } catch (err) {
        console.error('No se pudo cargar los eventos de recursos', err);
    }
}

async function updateMemorySummary() {
    try {
        const resp = await fetch('/api/memory_summary');
        const data = await resp.json();
        if (data.summary) {
            summaryText.textContent = data.summary;
            if (data.timestamp) {
                const date = new Date(data.timestamp * 1000);
                summaryTimestamp.textContent = `Último resumen: ${date.toLocaleString()}`;
            }
        } else {
            summaryText.textContent = data.note || 'Sin resumen automático aún.';
            summaryTimestamp.textContent = '';
        }
    } catch (err) {
        console.error('No se pudo cargar el resumen de memoria', err);
    }
}

setInterval(updateResourcePanel, 12_000);
setInterval(updateMemorySummary, 30_000);
setInterval(updatePlanPanel, 45_000);
setInterval(updateWatcherPanel, 25_000);
setInterval(updateBusMetricsPanel, 20_000);
setInterval(updateBridgeMetricsPanel, 20_000);
setInterval(updateStageLatencyPanel, 25_000);
setInterval(updateMemoryEventsPanel, 25_000);
updateResourcePanel();
updateMemorySummary();
updatePlanPanel();
updateWatcherPanel();
updateBusMetricsPanel();
updateBridgeMetricsPanel();
updateStageLatencyPanel();
updateMemoryEventsPanel();

const refreshMemoryBtn = document.getElementById('refresh-memory-btn');
if (refreshMemoryBtn) {
    refreshMemoryBtn.addEventListener('click', (event) => {
        event.preventDefault();
        updateMemorySummary();
    });
}

async function updatePlanPanel() {
    if (!planSummary || !planSteps) return;
    try {
        const resp = await fetch('/api/plan_log');
        const data = await resp.json();
        if (!data.plan) {
            planSummary.textContent = 'Sin plan registrado aún.';
            planSteps.innerHTML = '';
            return;
        }
        const date = new Date(data.plan.timestamp * 1000);
        planSummary.textContent = `${data.plan.prompt} (${date.toLocaleString()})`;
        planSteps.innerHTML = '';
        data.plan.steps.forEach(step => {
            const item = document.createElement('div');
            item.className = 'plan-step';
            const title = document.createElement('div');
            title.textContent = `${step.action} → ${step.target}`;
            const reason = document.createElement('div');
            reason.className = 'plan-step-rationale';
            reason.textContent = step.rationale || 'Sin justificación';
            item.appendChild(title);
            item.appendChild(reason);
            planSteps.appendChild(item);
        });
    } catch (err) {
        console.error('No se pudo cargar el plan', err);
    }
}

async function updateWatcherPanel() {
    if (!watcherEventsList) {
        return;
    }
    try {
        const resp = await fetch('/api/watcher_events');
        const data = await resp.json();
        const events = data.events || [];
        watcherEventsList.innerHTML = '';
        if (!events.length) {
            watcherEventsList.textContent = 'Sin eventos recientes.';
            return;
        }
        events.forEach(evt => {
            const item = document.createElement('div');
            item.className = 'watcher-event';
            const timeText = evt.timestamp
                ? new Date(evt.timestamp * 1000).toLocaleTimeString()
                : '—';
            const details = typeof evt.details === 'object'
                ? JSON.stringify(evt.details)
                : evt.details;
            if (evt.type && evt.type.startsWith('bridge_')) {
                item.classList.add('bridge-event');
                if (evt.type === 'bridge_backpressure') {
                    showToast(`Bridge backlog alto (${details})`);
                }
            }
            item.innerHTML = `<strong>${timeText} · ${evt.type}</strong><div>${details}</div>`;
            watcherEventsList.appendChild(item);
        });
    } catch (err) {
        console.error('No se pudo cargar los eventos del sistema', err);
        watcherEventsList.textContent = 'Error cargando eventos.';
    }
}

async function updateBusMetricsPanel() {
    if (!busMetricsSummary || !busMetricsRecent) return;
    try {
        const resp = await fetch('/api/bus_metrics');
        if (!resp.ok) throw new Error('Bus metrics fetch failed');
        const payload = await resp.json();
        const summary = payload.summary?.summary || {};
        const bridge = payload.summary?.bridge || {};
        const latency = payload.summary?.latency || {};
        if (!Object.keys(summary).length) {
            busMetricsSummary.textContent = 'Sin métricas registradas todavía.';
        } else {
            const rows = Object.entries(summary)
                .map(([key, stats]) => `<div><strong>${key}</strong>: última=${stats.latest} avg=${stats.avg}</div>`);
            if (Object.keys(bridge).length) {
                rows.push(
                    `<div><strong>bridge</strong>: latency_ms=${bridge.latency_avg_ms ?? '-'} p50=${bridge.latency_p50_ms ?? '-'} p95=${bridge.latency_p95_ms ?? '-'} backlog=${bridge.backlog_max ?? '-'} dropped=${bridge.dropped ?? '-'}</div>`
                );
            }
            if (Object.keys(latency).length) {
                rows.push(
                    `<div><strong>latencia workers</strong>: ${Object.entries(latency).map(([k,v]) => `${k}=${v}ms`).join(' ')}</div>`
                );
            }
            busMetricsSummary.innerHTML = rows.join('');
        }
        busMetricsRecent.innerHTML = '';
        (payload.summary?.recent || []).forEach(record => {
            const el = document.createElement('div');
            el.className = 'metrics-list-item';
            const time = new Date(record.timestamp).toLocaleTimeString();
            const metrics = record.metrics
                ? Object.entries(record.metrics)
                      .map(([k, v]) => `${k}=${v}`)
                      .join(' ')
                : 'sin detalles';
            el.textContent = `${time} · ${metrics}`;
            busMetricsRecent.appendChild(el);
        });
    } catch (err) {
        console.error('No se pudo cargar métricas del bus', err);
        if (busMetricsSummary) {
            busMetricsSummary.textContent = 'Error cargando métricas del bus.';
        }
    }
}

async function updateBridgeMetricsPanel() {
    if (!bridgeMetricsSummary || !bridgeMetricsRecent) return;
    try {
        const resp = await fetch('/api/bridge_metrics');
        if (!resp.ok) throw new Error('Bridge metrics fetch failed');
        const payload = await resp.json();
        const records = payload.records || [];
        if (!records.length) {
            bridgeMetricsSummary.textContent = 'Sin métricas de bridge todavía.';
            bridgeMetricsRecent.innerHTML = '';
            return;
        }
        const last = records[records.length - 1];
        bridgeMetricsSummary.innerHTML = `latency_ms=${last.latency_avg_ms ?? '-'} p50=${last.latency_p50_ms ?? '-'} p95=${last.latency_p95_ms ?? '-'} backlog=${last.backlog_max ?? '-'} dropped=${last.dropped ?? '-'}`;
        if (last.timestamp && window.updateStatus) {
            const age = Date.now() - (last.timestamp * 1000);
            if (age < 30000) {
                updateStatus('Bridge conectado', 'success');
            } else {
                updateStatus('Bridge sin datos recientes', 'warning');
            }
        }
        bridgeMetricsRecent.innerHTML = '';
        records.slice(-10).forEach(record => {
            const el = document.createElement('div');
            el.className = 'metrics-list-item';
            const time = new Date(record.timestamp * 1000).toLocaleTimeString();
            el.textContent = `${time} · sent=${record.sent ?? 0} recv=${record.received ?? 0} drop=${record.dropped ?? 0} latency=${record.latency_avg_ms ?? '-'} p95=${record.latency_p95_ms ?? '-'}`;
            bridgeMetricsRecent.appendChild(el);
        });
    } catch (err) {
        console.error('No se pudo cargar métricas del bridge', err);
        bridgeMetricsSummary.textContent = 'Error cargando métricas del bridge.';
    }
}

async function updateStageLatencyPanel() {
    if (!stageLatencySummary || !stageLatencyRecent) return;
    try {
        const resp = await fetch('/api/stage_latency');
        if (!resp.ok) throw new Error('Stage latency fetch failed');
        const payload = await resp.json();
        const summary = payload.summary || {};
        if (!Object.keys(summary).length) {
            stageLatencySummary.textContent = 'Sin latencias registradas.';
            stageLatencyRecent.innerHTML = '';
            return;
        }
        const rows = Object.entries(summary).map(([key, stats]) => {
            return `<div><strong>${key}</strong>: avg=${stats.avg_ms}ms count=${stats.count}</div>`;
        });
        stageLatencySummary.innerHTML = rows.join('');
        stageLatencyRecent.innerHTML = '';
        (payload.events || []).slice(-10).forEach(evt => {
            const el = document.createElement('div');
            el.className = 'metrics-list-item';
            const time = evt.timestamp ? new Date(evt.timestamp * 1000).toLocaleTimeString() : '—';
            el.textContent = `${time} · ${evt.worker || 'unknown'}:${evt.action || 'unknown'} ${evt.elapsed_ms ?? '-'}ms`;
            stageLatencyRecent.appendChild(el);
        });
    } catch (err) {
        console.error('No se pudo cargar latencias de etapa', err);
        if (stageLatencySummary) {
            stageLatencySummary.textContent = 'Error cargando latencias.';
        }
    }
}

async function updateMemoryEventsPanel() {
    if (!memoryEventsList) return;
    try {
        const resp = await fetch('/api/memory_events');
        if (!resp.ok) throw new Error('Memory events fetch failed');
        const payload = await resp.json();
        memoryEventsList.innerHTML = '';
        if (!payload.events?.length) {
            memoryEventsList.textContent = 'Sin eventos de memoria recientes.';
            return;
        }
        payload.events.forEach(evt => {
            const el = document.createElement('div');
            el.className = 'memory-events-item';
            if (evt.type && evt.type.startsWith('bridge_')) {
                el.classList.add('bridge-event');
            }
            const timestamp = evt.timestamp || '—';
            const detailText = evt.details ? evt.details : evt.raw || '';
            el.innerHTML = `<strong>${timestamp}</strong><div>${detailText}</div>`;
            memoryEventsList.appendChild(el);
        });
    } catch (err) {
        console.error('No se pudo cargar eventos de memoria', err);
        memoryEventsList.textContent = 'Error cargando eventos de memoria.';
    }
}

function showToast(message) {
    if (!toastContainer) return;
    const now = Date.now();
    if (now - lastBridgeToast < 8000) return;
    lastBridgeToast = now;
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    toastContainer.appendChild(toast);
    setTimeout(() => {
        toast.remove();
    }, 6000);
}
